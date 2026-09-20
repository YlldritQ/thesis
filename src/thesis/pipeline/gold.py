"""Silver → Gold transformation.

Produces:

* ``gold.tender_features`` — immutable features + rule flags
* ``gold.supplier_summary``— per robust supplier key rollup
* ``gold.procuring_entity_summary``
* ``gold.monthly_metrics``

The scored canonical ``gold.tender_summary`` is a separate artifact written
only by :mod:`thesis.pipeline.ml`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..anomaly.rules import RULES, apply_rules
from ..config import settings
from ..domain.features import (
    build_tender_features,
    normalise_supplier_business_id,
    supplier_key,
    supplier_source_identity_key,
)
from ..dq.framework import run_suite
from ..dq.suites import (
    gold_entity_summary_suite_for,
    gold_monthly_metrics_suite_for,
    gold_supplier_summary_suite_for,
    gold_tender_features_suite_for,
)
from ..io.readers import load_silver_bundle
from ..io.writers import write_json, write_parquet
from ..logging import bind, get_logger, unbind
from ..paths import (
    GOLD_ENTITIES,
    GOLD_ENTITIES_RELEASE_DQ,
    GOLD_FEATURES,
    GOLD_FEATURES_RELEASE_DQ,
    GOLD_MONTHLY,
    GOLD_MONTHLY_RELEASE_DQ,
    GOLD_RELEASE,
    GOLD_SUPPLIERS,
    GOLD_SUPPLIERS_RELEASE_DQ,
    SILVER_AWARDS,
    SILVER_RELEASE,
    SILVER_TENDERS,
    ensure_dirs,
)
from ..release import ReleaseIntegrityError, publish_release, validate_canonical_release

log = get_logger("pipeline.gold")


def _supplier_summary(awards: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    a = awards.copy()
    biz = a["supplier_business_id"].map(normalise_supplier_business_id)
    names = a["supplier_name"].fillna("").astype(str).str.strip()
    party_ids = a.get("supplier_party_id", pd.Series(index=a.index, dtype=object))
    party_uids = a.get("supplier_uid", pd.Series(index=a.index, dtype=object))
    party_ids = party_ids.fillna("").astype(str).str.strip()
    party_uids = party_uids.fillna("").astype(str).str.strip()
    source_party_ids = party_ids.where(party_ids.ne(""), party_uids)
    a["supplier_key"] = supplier_key(a)
    a["source_party_identity_key"] = supplier_source_identity_key(a)
    a["identity_source"] = np.select(
        [biz.notna(), names.ne(""), source_party_ids.ne("")],
        ["business_id", "name_fallback", "source_party_id_fallback"],
        default="unidentified",
    )
    a.loc[a["supplier_key"].isna(), "identity_source"] = "unidentified"
    total_awarded = float(a["awarded_value_eur"].sum(min_count=1) or 0.0)
    a = a.dropna(subset=["supplier_key"]).copy()
    a["awarded_value_eur"] = a["awarded_value_eur"].fillna(0)
    g = a.groupby("supplier_key")

    def _primary_business_id(values: pd.Series) -> str | None:
        cleaned = values.map(normalise_supplier_business_id).dropna()
        return cleaned.mode().iat[0] if not cleaned.empty else None

    def _mode_nonblank(values: pd.Series) -> str | None:
        cleaned = values.fillna("").astype(str).str.strip()
        cleaned = cleaned[cleaned.ne("")]
        return cleaned.mode().iat[0] if not cleaned.empty else None

    out = pd.DataFrame(
        {
            "tenders_won": g["ocid"].nunique(),
            "award_rows": g.size(),
            "total_awarded_eur": g["awarded_value_eur"].sum(),
            "median_awarded_eur": g["awarded_value_eur"].median(),
            "max_awarded_eur": g["awarded_value_eur"].max(),
            "first_award": g["award_date"].min(),
            "last_award": g["award_date"].max(),
            "distinct_procuring_entities": g["procuring_entity_id"].nunique(),
            "distinct_categories": g["category"].nunique(),
            "distinct_methods": g["method"].nunique(),
            "distinct_names": g["supplier_name"].nunique(),
            "primary_name": g["supplier_name"].agg(
                lambda s: s.dropna().mode().iat[0] if not s.dropna().empty else None
            ),
            "supplier_business_id": g["supplier_business_id"].agg(_primary_business_id),
            "supplier_party_id": g["supplier_party_id"].agg(_mode_nonblank),
            "supplier_uid": g["supplier_uid"].agg(_mode_nonblank),
            "source_party_identity_key": g["source_party_identity_key"].agg(_mode_nonblank),
            "distinct_source_identity_keys": g["source_party_identity_key"].nunique(),
            "identity_source": g["identity_source"].agg(
                lambda s: s.mode().iat[0] if not s.mode().empty else "unidentified"
            ),
        }
    ).reset_index()
    identified_total = float(out["total_awarded_eur"].sum())
    out["share_of_total_awarded_pct"] = (
        out["total_awarded_eur"] / max(total_awarded, 1) * 100
    ).round(4)
    out["share_of_identified_value_pct"] = (
        out["total_awarded_eur"] / max(identified_total, 1) * 100
    ).round(4)
    out["identity_value_coverage_pct"] = round(100 * identified_total / max(total_awarded, 1), 2)
    competition_columns = ["ocid", "is_single_bidder"]
    if "bidder_data_observed" not in a:
        competition_columns.append("bidder_data_observed")
    sb = a.merge(features[competition_columns], on="ocid", how="left")
    sb["single_bidder_observed"] = sb["is_single_bidder"].where(sb["bidder_data_observed"])
    sb_pct = sb.groupby("supplier_key")["single_bidder_observed"].mean()
    out = out.merge(sb_pct.rename("single_bidder_win_pct"), on="supplier_key", how="left")
    out["single_bidder_win_pct"] = (out["single_bidder_win_pct"] * 100).round(2)
    return out.sort_values("total_awarded_eur", ascending=False)


def _entity_summary(awards: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    g = ts.groupby("procuring_entity_id", dropna=False)

    # Supplier concentration per entity. Report name-first, source-party-first,
    # and business-ID-only sensitivities; none is a relevant-market HHI. A
    # source party ID is publication identity, not a verified legal identifier.
    hhi_rows = []
    for eid, sub in awards.groupby("procuring_entity_id"):
        s = sub[sub["awarded_value_eur"].notna()].copy()
        total_eur = float(s["awarded_value_eur"].sum())
        biz = s["supplier_business_id"].map(normalise_supplier_business_id)
        s["supplier_key_name_fallback"] = supplier_key(s)
        s["supplier_key_source_party_fallback"] = supplier_source_identity_key(s)
        keyed = s.dropna(subset=["supplier_key_name_fallback"])
        source_keyed = s.dropna(subset=["supplier_key_source_party_fallback"])
        keyed_total = float(keyed["awarded_value_eur"].sum())
        source_keyed_total = float(source_keyed["awarded_value_eur"].sum())
        id_only = s[biz.notna()].copy()
        id_only["supplier_business_id_valid"] = biz[biz.notna()]
        id_total = float(id_only["awarded_value_eur"].sum())

        def _group_hhi(frame: pd.DataFrame, key: str, denominator: float) -> float:
            if denominator <= 0 or frame.empty:
                return np.nan
            shares = frame.groupby(key)["awarded_value_eur"].sum() / denominator
            return float((shares**2).sum() * 10000)

        robust_hhi = _group_hhi(keyed, "supplier_key_name_fallback", keyed_total)
        source_party_hhi = _group_hhi(
            source_keyed,
            "supplier_key_source_party_fallback",
            source_keyed_total,
        )
        id_hhi = _group_hhi(id_only, "supplier_business_id_valid", id_total)

        # Two transparent allocation scenarios for rows with no usable identity.
        # They are sensitivities, not mathematical bounds on the unknown truth.
        known_values = source_keyed.groupby("supplier_key_source_party_fallback")[
            "awarded_value_eur"
        ].sum()
        unknown_values = s.loc[s["supplier_key_source_party_fallback"].isna(), "awarded_value_eur"]
        known_shares_sq = float(((known_values / total_eur) ** 2).sum()) if total_eur else np.nan
        unknown_total = float(unknown_values.sum())
        hhi_unknown_one_group = (
            (known_shares_sq + (unknown_total / total_eur) ** 2) * 10000
            if total_eur > 0
            else np.nan
        )
        hhi_unknown_distinct_rows = (
            (known_shares_sq + ((unknown_values / total_eur) ** 2).sum()) * 10000
            if total_eur > 0
            else np.nan
        )
        hhi_rows.append(
            {
                "procuring_entity_id": eid,
                "supplier_hhi": robust_hhi,
                "supplier_hhi_name_fallback": robust_hhi,
                "supplier_hhi_source_party_fallback": source_party_hhi,
                "supplier_hhi_id_only": id_hhi,
                "supplier_hhi_unknown_one_group_scenario": hhi_unknown_one_group,
                "supplier_hhi_unknown_distinct_rows_scenario": hhi_unknown_distinct_rows,
                "supplier_identity_value_coverage_pct": (
                    round(100 * keyed_total / total_eur, 2) if total_eur > 0 else np.nan
                ),
                "supplier_source_party_identity_value_coverage_pct": (
                    round(100 * source_keyed_total / total_eur, 2) if total_eur > 0 else np.nan
                ),
                "supplier_business_id_value_coverage_pct": (
                    round(100 * id_total / total_eur, 2) if total_eur > 0 else np.nan
                ),
            }
        )
    hhi_df = pd.DataFrame(hhi_rows)

    observed_bidders = ts["bidder_data_observed"].fillna(False).astype(bool)
    ts_for_rates = ts.copy()
    ts_for_rates["single_bidder_observed"] = ts_for_rates["is_single_bidder"].where(
        observed_bidders
    )
    ts_for_rates["zero_bidder_observed"] = ts_for_rates["is_zero_bidder"].where(observed_bidders)
    g = ts_for_rates.groupby("procuring_entity_id", dropna=False)

    out = pd.DataFrame(
        {
            "tenders": g["ocid"].count(),
            "awarded_tenders": g["was_awarded"].sum(),
            "total_estimated_eur": g["estimated_value_eur"].sum(),
            "total_awarded_eur": g["total_awarded_eur"].sum(),
            "median_estimated_eur": g["estimated_value_eur"].median(),
            "bidder_data_coverage_pct": (g["bidder_data_observed"].mean() * 100).round(2),
            "single_bidder_pct": (g["single_bidder_observed"].mean() * 100).round(2),
            "zero_bidder_pct": (g["zero_bidder_observed"].mean() * 100).round(2),
            "buyer_name_id_collision": g["buyer_name_id_collision"].max(),
            "end_before_start_pct": (g["end_before_start"].mean() * 100).round(2),
            "median_awarded_ratio": g["awarded_value_ratio"].median(),
            "rule_score_avg": g["rule_score"].mean().round(3),
            "rule_score_max": g["rule_score"].max().round(3),
            "first_release": g["release_date"].min(),
            "last_release": g["release_date"].max(),
            "name": g["procuring_entity_name"].agg(
                lambda s: s.dropna().mode().iat[0] if not s.dropna().empty else None
            ),
        }
    ).reset_index()
    out = out.merge(hhi_df, on="procuring_entity_id", how="left")
    return out.sort_values("total_estimated_eur", ascending=False)


def _monthly(ts: pd.DataFrame) -> pd.DataFrame:
    m = ts.dropna(subset=["release_date"]).copy()
    observed = m["bidder_data_observed"].fillna(False).astype(bool)
    m["single_bidder_observed"] = m["is_single_bidder"].where(observed)
    m["zero_bidder_observed"] = m["is_zero_bidder"].where(observed)
    m = m.set_index(pd.to_datetime(m["release_date"], utc=True)).sort_index()
    monthly = pd.DataFrame(
        {
            "tenders": m["ocid"].resample("ME").count(),
            "estimated_value_eur": m["estimated_value_eur"].resample("ME").sum(),
            "total_awarded_eur": m["total_awarded_eur"].resample("ME").sum(),
            "value_mn": (m["estimated_value_eur"].resample("ME").sum() / 1e6).round(2),
            "awarded_value_mn": (m["total_awarded_eur"].resample("ME").sum() / 1e6).round(2),
            "median_estimated_eur": m["estimated_value_eur"].resample("ME").median().round(0),
            "bidder_data_coverage_pct": (
                m["bidder_data_observed"].resample("ME").mean() * 100
            ).round(2),
            "single_bidder_pct": (m["single_bidder_observed"].resample("ME").mean() * 100).round(2),
            "zero_bidder_pct": (m["zero_bidder_observed"].resample("ME").mean() * 100).round(2),
            "rule_score_mean": m["rule_score"].resample("ME").mean().round(4),
            "flagged_count": (m["rule_score"] >= 0.5).resample("ME").sum(),
        }
    )
    monthly["roll12_median"] = monthly["tenders"].rolling(12, min_periods=6).median()
    monthly = monthly.reset_index()
    monthly["period_label"] = monthly["release_date"].dt.strftime("%Y-%m")
    monthly["date_known"] = True

    unknown = ts[ts["release_date"].isna()]
    if not unknown.empty:
        unknown_row = pd.DataFrame(
            [
                {
                    "release_date": pd.NaT,
                    "tenders": int(len(unknown)),
                    "estimated_value_eur": float(unknown["estimated_value_eur"].sum()),
                    "total_awarded_eur": float(unknown["total_awarded_eur"].sum()),
                    "value_mn": round(float(unknown["estimated_value_eur"].sum()) / 1e6, 2),
                    "awarded_value_mn": round(float(unknown["total_awarded_eur"].sum()) / 1e6, 2),
                    "median_estimated_eur": round(
                        float(unknown["estimated_value_eur"].median()), 0
                    ),
                    "bidder_data_coverage_pct": round(
                        float(unknown["bidder_data_observed"].mean()) * 100,
                        2,
                    ),
                    "single_bidder_pct": round(
                        float(
                            unknown.loc[unknown["bidder_data_observed"], "is_single_bidder"].mean()
                        )
                        * 100,
                        2,
                    ),
                    "zero_bidder_pct": round(
                        float(unknown.loc[unknown["bidder_data_observed"], "is_zero_bidder"].mean())
                        * 100,
                        2,
                    ),
                    "rule_score_mean": round(float(unknown["rule_score"].mean()), 4),
                    "flagged_count": int((unknown["rule_score"] >= 0.5).sum()),
                    "roll12_median": np.nan,
                    "period_label": "unknown_date",
                    "date_known": False,
                }
            ]
        )
        monthly = pd.concat([monthly, unknown_row], ignore_index=True)
    return monthly


def run() -> dict:
    """Build immutable tender features and the three descriptive summaries."""
    bind(stage="gold")
    try:
        ensure_dirs()
        log.info("gold.start")
        silver_release = validate_canonical_release(
            "silver",
            require_current_provenance=True,
            require_current_runtime=True,
        )
        tenders, awards = load_silver_bundle()
        silver_after_read = validate_canonical_release(
            "silver",
            require_current_provenance=True,
            require_current_runtime=True,
        )
        if silver_after_read.manifest_sha256 != silver_release.manifest_sha256:
            raise ReleaseIntegrityError("Silver release changed while building Gold")

        features = build_tender_features(tenders, awards)
        rules = apply_rules(features)
        ts = pd.concat([features, rules], axis=1)
        ts["year"] = ts["release_date"].dt.year.astype("Int64")
        ts["month"] = ts["release_date"].dt.tz_localize(None).dt.to_period("M").astype(str)

        # rule rollup logging
        flagged = (ts["rule_score"] >= 0.5).sum()
        log.info(
            "gold.rules.flagged", flagged=int(flagged), share=round(flagged / max(len(ts), 1), 4)
        )
        for r in RULES:
            log.info("gold.rules.count", code=r.code, n=int(ts[r.code].sum()))

        # Base gold is the benchmark/model-selection input. Validate it before
        # publishing so invalid engineered features or rule scores cannot be
        # elected into champions and only discovered later by the ML stage.
        feature_suite = gold_tender_features_suite_for(tenders["ocid"])
        gold_res = run_suite(feature_suite, ts)
        gold_res.write()
        if not gold_res.passed:
            raise ValueError(
                "gold feature DQ ERROR — aborting before publication "
                f"(errors={gold_res.error_count})"
            )
        if settings().fail_fast_on_dq and gold_res.warning_count:
            raise ValueError(
                "gold feature DQ warnings — aborting before publication because "
                "THESIS_FAIL_FAST_ON_DQ=true"
            )
        sup = _supplier_summary(awards, features)
        ent = _entity_summary(awards, ts)
        mon = _monthly(ts)
        supplier_suite = gold_supplier_summary_suite_for(awards)
        entity_suite = gold_entity_summary_suite_for(ts)
        monthly_suite = gold_monthly_metrics_suite_for(ts)
        summary_results = {
            GOLD_SUPPLIERS: run_suite(supplier_suite, sup),
            GOLD_ENTITIES: run_suite(entity_suite, ent),
            GOLD_MONTHLY: run_suite(monthly_suite, mon),
        }
        for result in summary_results.values():
            result.write()
        failed_summaries = [
            result.suite for result in summary_results.values() if not result.passed
        ]
        if failed_summaries:
            raise ValueError(
                "gold summary DQ ERROR — aborting before publication: "
                + ", ".join(failed_summaries)
            )
        if settings().fail_fast_on_dq and any(
            result.warning_count for result in summary_results.values()
        ):
            raise ValueError(
                "gold summary DQ warnings — aborting before publication because "
                "THESIS_FAIL_FAST_ON_DQ=true"
            )

        write_parquet(
            ts,
            GOLD_FEATURES,
            table="gold.tender_features",
            layer="gold",
            inputs=[SILVER_RELEASE, SILVER_TENDERS, SILVER_AWARDS],
        )
        write_parquet(
            sup,
            GOLD_SUPPLIERS,
            table="gold.supplier_summary",
            layer="gold",
            inputs=[SILVER_RELEASE, SILVER_AWARDS, GOLD_FEATURES],
        )
        write_parquet(
            ent,
            GOLD_ENTITIES,
            table="gold.procuring_entity_summary",
            layer="gold",
            inputs=[SILVER_RELEASE, GOLD_FEATURES, SILVER_AWARDS],
        )
        write_parquet(
            mon, GOLD_MONTHLY, table="gold.monthly_metrics", layer="gold", inputs=[GOLD_FEATURES]
        )

        # Re-run every release gate against the exact Parquet round-trip, then
        # bind each check to that artifact's hash, shape and data fingerprint.
        persisted_frames = {
            GOLD_FEATURES: pd.read_parquet(GOLD_FEATURES),
            GOLD_SUPPLIERS: pd.read_parquet(GOLD_SUPPLIERS),
            GOLD_ENTITIES: pd.read_parquet(GOLD_ENTITIES),
            GOLD_MONTHLY: pd.read_parquet(GOLD_MONTHLY),
        }
        persisted_results = {
            GOLD_FEATURES: run_suite(feature_suite, persisted_frames[GOLD_FEATURES]),
            GOLD_SUPPLIERS: run_suite(
                gold_supplier_summary_suite_for(awards),
                persisted_frames[GOLD_SUPPLIERS],
            ),
            GOLD_ENTITIES: run_suite(
                gold_entity_summary_suite_for(persisted_frames[GOLD_FEATURES]),
                persisted_frames[GOLD_ENTITIES],
            ),
            GOLD_MONTHLY: run_suite(
                gold_monthly_metrics_suite_for(persisted_frames[GOLD_FEATURES]),
                persisted_frames[GOLD_MONTHLY],
            ),
        }
        if any(not result.passed for result in persisted_results.values()):
            raise ValueError("persisted Gold artifacts fail release DQ")
        if settings().fail_fast_on_dq and any(
            result.warning_count for result in persisted_results.values()
        ):
            raise ValueError("persisted Gold DQ warnings and THESIS_FAIL_FAST_ON_DQ=true")
        release_checks = {
            GOLD_FEATURES: GOLD_FEATURES_RELEASE_DQ,
            GOLD_SUPPLIERS: GOLD_SUPPLIERS_RELEASE_DQ,
            GOLD_ENTITIES: GOLD_ENTITIES_RELEASE_DQ,
            GOLD_MONTHLY: GOLD_MONTHLY_RELEASE_DQ,
        }
        for artifact, result in persisted_results.items():
            write_json(
                result.release_payload(artifact, persisted_frames[artifact]),
                release_checks[artifact],
            )

        # Commit the four-file gold generation only after all primaries,
        # lineage sidecars, and DQ evidence are durable.
        publish_release(
            GOLD_RELEASE,
            stage="gold",
            inputs=[SILVER_RELEASE, SILVER_TENDERS, SILVER_AWARDS],
            artifacts=[GOLD_FEATURES, GOLD_SUPPLIERS, GOLD_ENTITIES, GOLD_MONTHLY],
            checks=[
                GOLD_FEATURES_RELEASE_DQ,
                GOLD_SUPPLIERS_RELEASE_DQ,
                GOLD_ENTITIES_RELEASE_DQ,
                GOLD_MONTHLY_RELEASE_DQ,
            ],
            metadata={
                "tender_features": len(ts),
                "supplier_summary": len(sup),
                "entity_summary": len(ent),
                "monthly_metrics": len(mon),
            },
            expected_input_manifest_sha256={
                SILVER_RELEASE: silver_release.manifest_sha256,
            },
        )

        log.info(
            "gold.done", tenders=len(ts), suppliers=len(sup), entities=len(ent), months=len(mon)
        )
        return {
            "tender_features": len(ts),
            "supplier_summary": len(sup),
            "entity_summary": len(ent),
            "monthly_metrics": len(mon),
        }
    finally:
        unbind("stage")
