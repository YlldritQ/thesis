"""Generate ``docs/findings.md`` from the *live* gold layer.

Every number is recomputed from the shipped artifacts at generation time, and
an integration drift guard requires the committed document to match that live
render exactly (review C-6/M-09/M-22/M-39). Run via
``thesis report findings`` after ``pipeline run``.

The numbers are reported at the **correct unit of analysis** the review
demanded: single-bidding within open procedures (not the pooled rate),
concentration per category (not a single national HHI), and the rule×
ensemble confusion instead of an "agreement" claim.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .anomaly.rules import RULES
from .audit import AUDIT_METADATA
from .config import settings
from .domain.features import (
    normalise_supplier_business_id,
    supplier_key,
    supplier_source_identity_key,
)
from .domain.procedures import STANDARD_OPEN, classify_procedure_series
from .io import readers
from .io.writers import write_markdown
from .jsonutil import loads_json
from .lineage import file_sha256
from .paths import (
    BENCHMARK_RELEASE,
    CHAMPIONS,
    DOCS,
    GOLD_RELEASE,
    GOLD_SUPPLIERS,
    GOLD_TENDERS,
    ML_RELEASE,
    MODEL_VALIDATION,
    SILVER_AWARDS,
)

FINDINGS_INPUTS = (
    GOLD_TENDERS,
    SILVER_AWARDS,
    GOLD_SUPPLIERS,
    MODEL_VALIDATION,
    CHAMPIONS,
    GOLD_RELEASE,
    BENCHMARK_RELEASE,
    ML_RELEASE,
    AUDIT_METADATA,
)


def _hhi(values: pd.Series) -> float:
    total = values.sum()
    if total <= 0:
        return float("nan")
    shares = values / total
    return float((shares**2).sum() * 10000)


def _artifact_timestamp(paths: list[Path]) -> str:
    """Stable report timestamp: latest input mtime, not wall-clock time."""
    existing = [p for p in paths if p.exists()]
    if not existing:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(
        max(p.stat().st_mtime for p in existing), tz=timezone.utc
    ).isoformat()


def _fmt_eur(x: float) -> str:
    if pd.isna(x):
        return "—"
    if x >= 1e9:
        return f"€{x / 1e9:.2f} bn"
    if x >= 1e6:
        return f"€{x / 1e6:.1f} M"
    return f"€{x:,.0f}"


def compute_findings() -> dict:
    """Recompute every headline number from the live gold layer."""
    g = readers.load_gold_tenders()
    aw = readers.load_silver_awards()
    sup = readers.load_gold_suppliers()
    val = readers.load_validation_report()
    champions = readers.load_champions() if CHAMPIONS.exists() or BENCHMARK_RELEASE.exists() else {}
    try:
        audit = (
            loads_json(AUDIT_METADATA.read_text())
            if AUDIT_METADATA.exists()
            else {"status": "not_generated", "labels_completed": 0}
        )
    except (ValueError, TypeError):
        audit = {"status": "invalid_metadata", "labels_completed": 0}

    cfg = settings()
    n = len(g)
    awarded = g[g["was_awarded"].eq(1)]
    if "procedure_subtype" not in g.columns:
        g = g.copy()
        g["procedure_subtype"] = classify_procedure_series(g)

    # Single bidding by source subtype and award eligibility. No external EU
    # equivalence is asserted because its denominator/exclusions are not
    # replicated here.
    by_procedure: dict[str, dict] = {}
    for subtype, sub in g.groupby("procedure_subtype", dropna=False):
        sub_awarded = sub[sub["was_awarded"].eq(1)]
        observed = sub[sub.get("bidder_data_observed", sub["num_bidders"].notna()).fillna(False)]
        observed_awarded = sub_awarded[
            sub_awarded.get(
                "bidder_data_observed",
                sub_awarded["num_bidders"].notna(),
            ).fillna(False)
        ]
        by_procedure[str(subtype)] = {
            "n_all": int(len(sub)),
            "n_bidder_observed_all": int(len(observed)),
            "bidder_coverage_pct_all": round(100 * len(observed) / max(len(sub), 1), 2),
            "single_bidder_pct_all": (
                round(100 * float(observed["is_single_bidder"].mean()), 2)
                if len(observed)
                else None
            ),
            "n_awarded": int(len(sub_awarded)),
            "n_bidder_observed_awarded": int(len(observed_awarded)),
            "single_bidder_pct_awarded": (
                round(100 * float(observed_awarded["is_single_bidder"].mean()), 2)
                if len(observed_awarded)
                else None
            ),
            "median_value": float(sub["estimated_value_eur"].median()),
        }

    standard_awarded = g[g["procedure_subtype"].eq(STANDARD_OPEN) & g["was_awarded"].eq(1)]
    standard_awarded = standard_awarded[
        standard_awarded.get(
            "bidder_data_observed",
            standard_awarded["num_bidders"].notna(),
        ).fillna(False)
    ]
    standard_open_by_year = {
        str(int(year)): {
            "n": int(len(sub)),
            "single_bidder_pct": round(100 * float(sub["is_single_bidder"].mean()), 2),
        }
        for year, sub in standard_awarded.dropna(subset=["year"]).groupby("year")
    }
    value_bands = pd.cut(
        standard_awarded["estimated_value_eur"],
        bins=[-float("inf"), 10_000, 100_000, float("inf")],
        labels=["≤€10k", "€10k–€100k", ">€100k"],
    )
    standard_open_by_value = {
        str(band): {
            "n": int(len(sub)),
            "single_bidder_pct": round(100 * float(sub["is_single_bidder"].mean()), 2),
        }
        for band, sub in standard_awarded.groupby(value_bands, observed=True)
    }

    # Broad-category concentration sensitivity.  Business-ID-only and robust
    # name-fallback keys are both shown; unidentified value is isolated.  These
    # categories are not claimed to be competition-law relevant markets.
    cat_hhi = {}
    a2 = aw[aw["awarded_value_eur"].notna()].copy()
    a2["supplier_key"] = supplier_key(a2)
    a2["source_party_identity_key"] = supplier_source_identity_key(a2)
    a2["business_id_valid"] = a2["supplier_business_id"].map(normalise_supplier_business_id)
    if "category" in a2.columns:
        for cat, sub in a2.groupby("category"):
            total_value = float(sub["awarded_value_eur"].sum())
            robust = sub.dropna(subset=["supplier_key"])
            source_party = sub.dropna(subset=["source_party_identity_key"])
            id_only = sub[sub["business_id_valid"].notna()]
            per_robust = robust.groupby("supplier_key")["awarded_value_eur"].sum()
            per_source_party = source_party.groupby("source_party_identity_key")[
                "awarded_value_eur"
            ].sum()
            per_id = id_only.groupby("business_id_valid")["awarded_value_eur"].sum()
            robust_value = float(robust["awarded_value_eur"].sum())
            source_party_value = float(source_party["awarded_value_eur"].sum())
            id_value = float(id_only["awarded_value_eur"].sum())
            unknown = sub.loc[sub["source_party_identity_key"].isna(), "awarded_value_eur"]
            known_sq = (
                float(((per_source_party / total_value) ** 2).sum()) if total_value > 0 else None
            )
            cat_hhi[str(cat)] = {
                "hhi_name_fallback": round(_hhi(per_robust), 0),
                "hhi_source_party_fallback": round(_hhi(per_source_party), 0),
                "hhi_id_only": round(_hhi(per_id), 0),
                "hhi_unknown_one_group_scenario": (
                    round((known_sq + (float(unknown.sum()) / total_value) ** 2) * 10000, 0)
                    if known_sq is not None
                    else None
                ),
                "hhi_unknown_distinct_rows_scenario": (
                    round((known_sq + float(((unknown / total_value) ** 2).sum())) * 10000, 0)
                    if known_sq is not None
                    else None
                ),
                "top1_share_name_fallback_pct": (
                    round(100 * float(per_robust.max()) / robust_value, 1)
                    if robust_value > 0
                    else None
                ),
                "n_supplier_keys": int(per_robust.shape[0]),
                "identity_row_coverage_pct": round(100 * len(robust) / max(len(sub), 1), 2),
                "identity_value_coverage_pct": round(100 * robust_value / max(total_value, 1), 2),
                "source_party_identity_row_coverage_pct": round(
                    100 * len(source_party) / max(len(sub), 1), 2
                ),
                "source_party_identity_value_coverage_pct": round(
                    100 * source_party_value / max(total_value, 1), 2
                ),
                "business_id_row_coverage_pct": round(100 * len(id_only) / max(len(sub), 1), 2),
                "business_id_value_coverage_pct": round(100 * id_value / max(total_value, 1), 2),
            }

    # per-rule counts (all current rules)
    rule_counts = {
        r.code: {
            "n": int(g[r.code].sum()),
            "pct": round(100 * g[r.code].mean(), 2),
            "weight": r.weight,
            "score_enabled": r.score_enabled,
            "signal_type": r.signal_type,
        }
        for r in RULES
        if r.code in g.columns
    }

    # triage sizes (clearly labelled populations)
    ensemble_score = (
        g["ensemble_score"] if "ensemble_score" in g.columns else pd.Series(0.0, index=g.index)
    )
    triage = {
        "rule_score_ge_0.5": int((g["rule_score"] >= 0.5).sum()),
        "rule_score_ge_0.7": int((g["rule_score"] >= 0.7).sum()),
        "ensemble_ge_0.5": int((ensemble_score >= 0.5).sum()),
        "ensemble_ge_0.7": int((ensemble_score >= 0.7).sum()),
        "high_confidence": int(g["high_confidence"].sum()) if "high_confidence" in g else 0,
    }

    # temporal coverage (honest — count real months)
    release_dates = pd.to_datetime(g["release_date"], errors="coerce", utc=True)
    months = release_dates.dt.tz_localize(None).dt.to_period("M").dropna()
    span = {
        "date_min": str(g["release_date"].min())[:10],
        "date_max": str(g["release_date"].max())[:10],
        "distinct_months": int(months.nunique()),
        "calendar_months_in_span": int((months.max() - months.min()).n + 1) if len(months) else 0,
    }
    bidder_observed_all = g[g.get("bidder_data_observed", g["num_bidders"].notna()).fillna(False)]
    lot_linkage = (
        {
            str(status): int(count)
            for status, count in aw["award_lot_match_status"].value_counts().items()
        }
        if "award_lot_match_status" in aw
        else {}
    )

    return {
        "generated_at": _artifact_timestamp(list(FINDINGS_INPUTS)),
        "input_sha256": {str(path): file_sha256(path) for path in FINDINGS_INPUTS if path.exists()},
        "n_tenders": n,
        "n_awards_silver": int(len(aw)),
        "award_lot_title_linkage": lot_linkage,
        "n_awarded_tenders": int((g["n_awards"].fillna(0) >= 1).sum()),
        "total_estimated_eur": float(g["estimated_value_eur"].sum()),
        "total_awarded_eur": float(g["total_awarded_eur"].sum()),
        "n_procuring_entities": int(g["procuring_entity_id"].nunique()),
        "n_supplier_keys": int(len(sup)),
        "n_rules": len(RULES),
        "n_scoring_rules": sum(r.score_enabled for r in RULES),
        "single_bidding_by_procedure": by_procedure,
        "standard_open_awarded_by_year": standard_open_by_year,
        "standard_open_awarded_by_value": standard_open_by_value,
        "single_bidding_pooled_pct": (
            round(100 * bidder_observed_all["is_single_bidder"].mean(), 2)
            if len(bidder_observed_all)
            else None
        ),
        "bidder_data_coverage_pct": round(100 * len(bidder_observed_all) / max(len(g), 1), 2),
        "concentration_by_category": cat_hhi,
        "rule_counts": rule_counts,
        "triage_sizes": triage,
        "temporal": span,
        "rule_ensemble_confusion": val.get("rule_only_baseline_and_confusion", {}),
        "ensemble_families": champions.get("ensemble_families", []),
        "manual_audit": audit,
        "value_ratio_pctiles": {
            f"p{int(q * 100)}": round(float(awarded["awarded_value_ratio"].quantile(q)), 3)
            for q in [0.25, 0.5, 0.75, 0.95, 0.99]
        },
        "rule_label_threshold": cfg.rule_label_threshold,
    }


def render_findings_md(d: dict) -> str:
    """Render the findings dict to Markdown."""
    L: list[str] = []
    p = L.append
    p("# Findings — Kosovo Public Procurement")
    p("")
    p(
        f"> **Auto-generated from the live gold layer** at `{d['generated_at']}` "
        "by `thesis report findings`. Numbers are recomputed from the declared "
        "gold, silver and model inputs; do not hand-edit."
    )
    p(
        "> Input hashes: "
        + " · ".join(
            f"`{Path(path).name}:{digest[:12]}`" for path, digest in d["input_sha256"].items()
        )
    )
    p("")
    p(
        "> ⚠️ **This is a bachelor-thesis research project, not an official "
        "government tool.** Anomaly flags are signals for review, never proof "
        "of wrongdoing. See `docs/responsible_use.md`."
    )
    p("")

    p("## 1. Scale")
    p("")
    p(f"- Tenders: **{d['n_tenders']:,}**  ·  awarded: **{d['n_awarded_tenders']:,}**")
    p(f"- Award rows (silver, post-dedup): **{d['n_awards_silver']:,}**")
    p(
        f"- Total estimated: **{_fmt_eur(d['total_estimated_eur'])}**  ·  "
        f"total awarded: **{_fmt_eur(d['total_awarded_eur'])}**"
    )
    p(
        f"- Populated procuring-entity IDs: **{d['n_procuring_entities']:,}**  ·  "
        f"resolved supplier keys (business ID, else normalized name, else source party): "
        f"**{d['n_supplier_keys']:,}**"
    )
    p(
        "- Scope: records in KRPP/OCP OCDS publication 115; this is not a "
        "claim of complete national-census coverage."
    )
    lot_linkage = d.get("award_lot_title_linkage", {})
    if lot_linkage:
        p(
            "- Award→lot title linkage: "
            f"**{lot_linkage.get('exact_unique', 0):,}** exact unique · "
            f"**{lot_linkage.get('exact_ambiguous', 0):,}** exact ambiguous · "
            f"**{lot_linkage.get('no_exact_match', 0):,}** no exact match · "
            f"**{lot_linkage.get('missing_title', 0):,}** missing award lot title. "
            "Award values and ratio diagnostics therefore remain tender-level; "
            "title equality is not treated as a verified lot identifier."
        )
    p("")

    p("## 2. Single-bidding — source subtype and eligible population")
    p("")
    p(
        "The coarse OCDS value `open` mixes ordinary open procedures with a "
        "distinct price-quotation procedure (consolidated Regulation 001/2022 "
        "as amended by 002/2024, Arts. 12.3 and 51.3; Art. 51.5 sets its "
        "five-day minimum), while official KRPP "
        "code 3 identifies design contests. The "
        "table keeps source subtypes separate and computes bidder rates only where "
        "bidder data was published. No EU equivalence is claimed because the "
        "external indicator's year, exclusions and denominator have not been replicated."
    )
    p("")
    p(
        "| Source subtype | All records | Bidder data observed | Single-bidder "
        "(observed) | Awarded records | Single-bidder (awarded + observed) | Median value |"
    )
    p("|---|---:|---:|---:|---:|---:|---:|")
    for subtype, s in sorted(d["single_bidding_by_procedure"].items()):
        all_pct = (
            f"{s['single_bidder_pct_all']:.1f}%" if s["single_bidder_pct_all"] is not None else "—"
        )
        awarded_pct = (
            f"{s['single_bidder_pct_awarded']:.1f}%"
            if s["single_bidder_pct_awarded"] is not None
            else "—"
        )
        p(
            f"| {subtype} | {s['n_all']:,} | {s['n_bidder_observed_all']:,} "
            f"({s['bidder_coverage_pct_all']:.1f}%) | {all_pct} | {s['n_awarded']:,} | "
            f"{awarded_pct} | {_fmt_eur(s['median_value'])} |"
        )
    pooled_pct = (
        f"{d['single_bidding_pooled_pct']:.1f}%"
        if d["single_bidding_pooled_pct"] is not None
        else "—"
    )
    p(
        f"| **pooled (descriptive only)** | {d['n_tenders']:,} | — "
        f"({d['bidder_data_coverage_pct']:.1f}%) | **{pooled_pct}** | — | — | — |"
    )
    p("")
    p("### Awarded standard-open records by value band")
    p("")
    p("| Estimated-value band | Records | Single-bidder % |")
    p("|---|---:|---:|")
    for band, s in d["standard_open_awarded_by_value"].items():
        p(f"| {band} | {s['n']:,} | {s['single_bidder_pct']:.1f}% |")
    p("")
    p("### Awarded standard-open records by year")
    p("")
    p("| Year | Records | Single-bidder % |")
    p("|---:|---:|---:|")
    for year, s in d["standard_open_awarded_by_year"].items():
        p(f"| {year} | {s['n']:,} | {s['single_bidder_pct']:.1f}% |")
    p("")
    p(
        "Year-level rates support time-matched comparison; none is interpreted "
        "here as detection evidence."
    )
    p("")

    p("## 3. Supplier concentration — identity sensitivity, not market HHI")
    p("")
    p(
        "Broad procurement categories are not defensible relevant markets. The "
        "descriptive concentration below is therefore a sensitivity check only. "
        "It reports name-first, published-party-ID-first and business-ID-only "
        "sensitivities with coverage. A source party ID is publication identity, "
        "not a verified legal identifier; every fallback can split or merge firms."
    )
    p("")
    p(
        "| Category | HHI (ID/name/party fallback) | HHI (ID/party/name) | "
        "HHI (ID only) | Top-1 (name-first) | Name-first coverage | "
        "Party-first coverage | ID coverage | Keys |"
    )
    p("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cat, s in sorted(d["concentration_by_category"].items()):
        top1 = (
            f"{s['top1_share_name_fallback_pct']:.1f}%"
            if s["top1_share_name_fallback_pct"] is not None
            else "—"
        )
        p(
            f"| {cat} | {s['hhi_name_fallback']:,.0f} | "
            f"{s['hhi_source_party_fallback']:,.0f} | {s['hhi_id_only']:,.0f} | "
            f"{top1} | {s['identity_row_coverage_pct']:.1f}% / "
            f"{s['identity_value_coverage_pct']:.1f}% | "
            f"{s['source_party_identity_row_coverage_pct']:.1f}% / "
            f"{s['source_party_identity_value_coverage_pct']:.1f}% | "
            f"{s['business_id_row_coverage_pct']:.1f}% / "
            f"{s['business_id_value_coverage_pct']:.1f}% | "
            f"{s['n_supplier_keys']:,} |"
        )
    p("")
    p(
        "No national or broad-category figure is interpreted as a healthy, "
        "moderate or concentrated *market* without a defensible market definition. "
        "Unknown-one-group and unknown-distinct-row scenarios are retained in the "
        "computed report data; they are allocation sensitivities, not truth bounds."
    )
    p("")

    p("## 4. Transparent indicator registry — counts live")
    p("")
    p(
        f"There are **{d['n_rules']}** visible indicators; only "
        f"**{d['n_scoring_rules']}** contribute author-selected priority points. "
        "The remaining diagnostics cannot train the weak-label target."
    )
    p("")
    p("| Indicator | Type | In score | Weight | Records | % |")
    p("|---|---|---:|---:|---:|---:|")
    for code, s in sorted(d["rule_counts"].items(), key=lambda kv: -kv[1]["n"]):
        p(
            f"| `{code}` | {s['signal_type']} | "
            f"{'yes' if s['score_enabled'] else 'no'} | {s['weight']} | "
            f"{s['n']:,} | {s['pct']:.2f}% |"
        )
    p("")

    p("## 5. Triage populations (each clearly labelled)")
    p("")
    t = d["triage_sizes"]
    for k, v in t.items():
        p(f"- `{k}`: **{v:,}** ({100 * v / max(d['n_tenders'], 1):.1f}% of tenders)")
    p("")
    conf = d.get("rule_ensemble_confusion", {})
    if conf.get("confusion"):
        c = conf["confusion"]
        p("### Rule layer × ensemble — they substantially DISAGREE")
        p("")
        p(
            "The rule layer is the auditable heuristic baseline. The layered "
            "ensemble is exploratory and **not** a corroboration of it:"
        )
        p("")
        p(f"- both flagged: **{c['both_flagged']:,}**")
        p(
            f"- rule-flagged but ensemble demoted it: "
            f"**{c['rule_only_demoted_by_ensemble']:,}** "
            f"({100 * conf.get('pct_rule_flags_demoted', 0):.1f}% of rule flags)"
        )
        p(
            f"- ensemble-only (ML, unvalidated, no rule support): "
            f"**{c['ensemble_only_ml_unvalidated']:,}** "
            f"({100 * conf.get('pct_ensemble_that_is_ml_only', 0):.1f}% of ensemble flags)"
        )
        p("")

    p("## 6. Award value ratio (awarded ÷ estimated)")
    p("")
    p("| percentile | value |")
    p("|---|---:|")
    for k, v in d["value_ratio_pctiles"].items():
        p(f"| {k} | {v} |")
    p("")

    p("## 7. Temporal coverage")
    p("")
    s = d["temporal"]
    p(f"- Span: **{s['date_min']} → {s['date_max']}**")
    p(
        f"- Distinct months with data: **{s['distinct_months']}** of "
        f"{s['calendar_months_in_span']} calendar months in the span "
        f"({s['calendar_months_in_span'] - s['distinct_months']} missing — a "
        "publishing-coverage gap, not continuous coverage)."
    )
    p("")

    p("## 7b. External outcome validation — withdrawn")
    p("")
    p(
        "The bundled OSHP snapshot contains operator and authority names but no "
        "request outcome, case/activity identifier, decision date or exact tender "
        "link. Supplier-name overlap expanded to historical wins is therefore "
        "**not an outcome label set and is not reported as validation**. A future "
        "evaluation requires approved decisions linked to exact tenders and "
        "eligible controls, with supplier-clustered uncertainty."
    )
    p("")

    p("## 7c. Manual outcome audit — not yet labelled")
    p("")
    audit = d.get("manual_audit", {})
    if audit.get("status") in {
        "awaiting_human_review",
        "review_in_progress",
        "partially_reviewed",
        "human_review_complete",
    }:
        counts = audit.get("sample_by_quadrant", {})
        p(
            "A deterministic stratified queue over the four possible quadrants "
            "has been generated for human document review: "
            + ", ".join(f"`{name}` {count}" for name, count in counts.items())
            + "."
        )
        empty = audit.get("empty_quadrants", [])
        if empty:
            p(
                "Empty source strata are reported rather than synthetically "
                "filled: " + ", ".join(f"`{name}`" for name in empty) + "."
            )
        p(
            f"Completed labels recorded in its provenance: **"
            f"{audit.get('labels_completed', 0)}**. Empty review fields are "
            "unreviewed, not negative labels. See `docs/manual_audit_protocol.md`."
        )
    else:
        p(
            "The four-quadrant human-review queue has not been generated. See "
            "`docs/manual_audit_protocol.md`; no tender-level outcome labels exist."
        )
    p("")

    p("## 8. What the thesis CAN legitimately claim")
    p("")
    p(
        "1. A reproducible **static, retrospective medallion pipeline** "
        "(bronze→silver→gold) over publication-115 records, with lineage, typed "
        "contracts and data-quality checks."
    )
    p(
        "2. A **transparent heuristic indicator registry** "
        f"({d['n_rules']} visible indicators; {d['n_scoring_rules']} score-enabled) "
        "producing calculator-reproducible author-selected priority points. "
        "References motivate constructs, not exact calibrated weights."
    )
    p(
        "3. **Descriptive statistics** separated by source procedure subtype, "
        "award eligibility and supplier-identity coverage; no EU-equivalence or "
        "relevant-market conclusion is asserted."
    )
    p(
        "4. An **exact additive XAI contract for the published hybrid score**: "
        "the released detector percentile ranks, rule score and context score "
        "reconstruct every `ensemble_score`; snapshot-baseline effects show "
        "which components raised or lowered the ordering. This explains the "
        "system arithmetic, not causation or wrongdoing."
    )
    p(
        "5. A **surrogate supervised model** that reproduces the deterministic "
        "rule proxy with near-perfect AUC expected from heavily overlapping "
        "inputs, used **solely** for raw-feature attribution of its log-odds via "
        "SHAP. It does not explain `ensemble_score`, directly identify which "
        "rule fired, or provide independent evidence."
    )
    families = d.get("ensemble_families", [])
    family_text = "/".join(families) if families else "configured champions"
    p(
        f"6. An **exploratory unsupervised layer** (a {len(families) or 'configured'}"
        f"-model ensemble — {family_text}) that produces a ranking whose added value over the "
        "rules is **not yet validated** against external ground truth."
    )
    p(
        "7. Every peer rank, quantile and detector calibration is relative to "
        "the complete shipped snapshot; scores are not stable single-row or live "
        "monitoring outputs."
    )
    p("")

    p("## 9. What the thesis CANNOT claim")
    p("")
    p(
        "1. **Cannot** claim any measured *detection* performance. The AUC/OOT/"
        "proxy-AUC figures are agreement with the model's own deterministic "
        "inputs, not detection of anomaly or fraud."
    )
    p(
        "2. **Cannot** claim temporal generalization — the out-of-time "
        "experiment measures only faithfulness to an internally generated rule "
        "proxy whose inputs overlap heavily with the model matrix."
    )
    p(
        "3. **Cannot** claim the unsupervised layer 'surfaces real anomalies the "
        "rules miss' — the majority of the ensemble inbox is ML-only with no "
        "ground-truth check (see §5)."
    )
    p(
        "4. **Cannot** claim 'principled model selection' beat a rule-only "
        "baseline — no external validation was run."
    )
    p(
        "5. **Cannot** claim SHAP explains the hybrid ensemble or gives "
        "independent evidence — it restates the rule proxy through overlapping "
        "raw features. The exact ensemble decomposition explains score arithmetic, "
        "not the real-world cause of a procurement pattern."
    )
    p(
        "6. **Cannot** claim OSHP validation, calibrated confidence/risk, "
        "production monitoring, or score comparability across rebuilds."
    )
    p("")
    p(
        "**Defensible positioning:** *a static, transparent heuristic review "
        "queue with an exploratory unsupervised layer, exact component-level "
        "XAI for its published hybrid score, and a separately labelled "
        "rule-proxy SHAP surrogate; its ML ordering is engineered but not yet "
        "validated against external ground truth.*"
    )
    p("")
    return "\n".join(L)


def generate(write: bool = True) -> str:
    """Compute + render + (optionally) write ``docs/findings.md``."""
    d = compute_findings()
    md = render_findings_md(d)
    if write:
        DOCS.mkdir(parents=True, exist_ok=True)
        write_markdown(md, DOCS / "findings.md")
    return md
