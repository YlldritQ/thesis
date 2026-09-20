"""Rule-based anomaly screening — the transparent heuristic baseline.

Each indicator is a transparent boolean screening fact.  It is not a fraud
label and its weight is not a calibrated probability.  Only indicators with
``score_enabled=True`` contribute author-chosen priority points to the
``rule_score``; data-quality and operational-follow-up indicators remain
visible but cannot silently train the weak-label model.

The score is ``clip(sum(enabled weights × triggered) / 2, 0, 1)``.  The
division by two is a display scale, not an empirically estimated threshold.
The exact contribution of every indicator is exposed by
:func:`rule_descriptions` and is reproducible with a calculator.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd

from ..domain.procedures import PRICE_QUOTATION, STANDARD_OPEN, classify_procedure_series

# Awarded/estimated ratios above this are routed to a field-comparability
# diagnostic rather than interpreted economically. See apply_rules().
IMPLAUSIBLE_RATIO_CEILING = 4.0
# Minimum difference before the above-estimate diagnostic fires; tiny
# differences are treated as numeric/source noise (review M-28).
OVERSHOOT_MARGIN = 1.05
# Value floor for WINNER_TAKES_ALL_LARGE — the "_LARGE" name must mean large
# (review M-29).
WINNER_TAKES_ALL_VALUE_FLOOR = 100_000.0
PRICE_QUOTATION_UPPER_BOUND_EUR = 10_000.0
RULE_SCORE_NORMALISER = 2.0


@dataclass(frozen=True)
class Rule:
    """One anomaly rule.

    Attributes:
        code: Short snake_case identifier used as the column name in gold.
        description: Plain-English explanation surfaced in the UI.
        weight: ``0..1`` importance for the composite score.
        reference: Optional citation / motivation.
        score_enabled: Whether the signal contributes to ``rule_score``.
        signal_type: ``review``, ``data_quality`` or ``operational``.
        threshold_rationale: Provenance for the exact implemented boundary.
        limitations: Important competing interpretations or missing inputs.
    """

    code: str
    description: str
    weight: float
    reference: str = ""
    score_enabled: bool = True
    signal_type: str = "review"
    threshold_rationale: str = "Author-selected screening priority; uncalibrated."
    limitations: str = "Requires human review; not evidence of wrongdoing."


def explain_rule_score(
    row: Mapping[str, object],
    *,
    published_score: Optional[float] = None,
    atol: float = 1e-12,
) -> dict[str, Any]:
    """Return calculator-reproducible rule-score arithmetic for one record."""
    enabled = [rule for rule in RULES if rule.score_enabled and bool(row.get(rule.code, False))]
    diagnostics = [
        rule for rule in RULES if not rule.score_enabled and bool(row.get(rule.code, False))
    ]
    raw_weight_sum = float(sum(rule.weight for rule in enabled))
    unclipped_score = raw_weight_sum / RULE_SCORE_NORMALISER
    reconstructed = float(min(max(unclipped_score, 0.0), 1.0))
    if published_score is not None and not np.isclose(
        reconstructed,
        float(published_score),
        rtol=0.0,
        atol=atol,
    ):
        raise ValueError("published rule_score does not match triggered-rule arithmetic")
    return {
        "triggered_score_enabled": [
            {
                "code": rule.code,
                "weight": float(rule.weight),
                "normalized_contribution_before_clipping": float(
                    rule.weight / RULE_SCORE_NORMALISER
                ),
            }
            for rule in enabled
        ],
        "triggered_zero_weight_diagnostics": [rule.code for rule in diagnostics],
        "raw_weight_sum": raw_weight_sum,
        "normaliser": RULE_SCORE_NORMALISER,
        "unclipped_score": unclipped_score,
        "clipped": not np.isclose(unclipped_score, reconstructed, rtol=0.0, atol=atol),
        "reconstructed_score": reconstructed,
    }


RULES: tuple[Rule, ...] = (
    Rule(
        "SINGLE_BIDDER",
        "One bidder outside a standard open procedure (context signal)",
        weight=0.25,
        reference="OECD (2009) discusses single bidding among bid-rigging screens.",
        threshold_rationale="Observed bidder count equals one; descriptive, not a legal breach.",
        limitations="Procedure design, market size and bidder-data coverage can explain one bid.",
    ),
    Rule(
        "SINGLE_BIDDER_OPEN",
        "One bidder in a source-identified standard open procedure",
        weight=0.75,
        reference="Fazekas et al. (2016) uses open-procedure single bidding "
        "as a cross-country corruption-risk proxy; here it is only "
        "a review signal.",
        threshold_rationale=(
            "Observed bidder count equals one within the standard-open source subtype; "
            "the 0.75 priority weight is an explicit author choice and keeps this "
            "one condition below the 0.5 review threshold after display scaling."
        ),
        limitations=(
            "Does not establish collusion; the source does not measure qualified market size "
            "or bids excluded before publication."
        ),
    ),
    Rule(
        "ZERO_BIDDER",
        "Zero bidders and zero awards recorded (operational follow-up)",
        weight=0.0,
        reference="",
        score_enabled=False,
        signal_type="operational",
        threshold_rationale="Observed bidder count equals zero.",
        limitations=(
            "The predicate also requires zero recorded awards; it is not a direct-award signal. "
            "Missing bidder publication cannot trigger it."
        ),
    ),
    Rule(
        "RATIO_BELOW_50",
        "Awarded is at least 1 % but below 50 % of estimated value",
        weight=0.0,
        reference=(
            "World Bank (2017) discusses abnormally low bids; this project has "
            "only tender-level totals, so the ratio is a data diagnostic."
        ),
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Legacy 0.01–0.50 diagnostic band; not legally calibrated.",
        limitations="Tender-level award totals may not be comparable with lot-level estimates.",
    ),
    Rule(
        "RATIO_ABOVE_ESTIMATE",
        "Awarded total is ≥105 % and ≤400 % of estimate (comparison band)",
        weight=0.0,
        reference="OECD (2007) — overestimation may signal tailoring.",
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Legacy 1.05–4.00 diagnostic band; not legally calibrated.",
        limitations="Disabled from scoring until estimates and awards are comparable by lot/contract.",
    ),
    Rule(
        "IMPLAUSIBLE_ESTIMATE",
        "Awarded > 4× estimate — likely incomparable fields or a data error",
        weight=0.0,
        reference="Fazekas & Kocsis (2017) — estimate manipulation.",
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Legacy ratio above 4.0, routed to data-quality review.",
        limitations="A source error is a direct competing explanation; no integrity inference is made.",
    ),
    Rule(
        "NEGATIVE_DAYS_TO_AWARD",
        "Award date precedes recorded tender end date (date-quality check)",
        weight=0.0,
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Recorded first-award timestamp is earlier than recorded end timestamp.",
        limitations="Source date semantics or corrections may explain the ordering.",
    ),
    Rule(
        "ULTRA_SHORT_OPEN",
        "Source-identified standard-open record lasting < 7 days (diagnostic only)",
        weight=0.0,
        reference=(
            "Kosovo Regulation 001/2022, as amended by Regulation 002/2024, "
            "Art. 51.5 separately permits a five-day "
            "price-quotation procedure; quotations are explicitly excluded here."
        ),
        score_enabled=False,
        signal_type="operational",
        threshold_rationale="Conservative author-selected screen, not a statutory deadline test.",
        limitations=(
            "The extract does not encode urgency, corrigenda or all period-specific exceptions; "
            "therefore this indicator is disabled from the composite."
        ),
    ),
    Rule(
        "PRICE_QUOTATION_VALUE_BAND_CONFLICT",
        "Price-quotation source code with estimated value ≥ €10,000 (DQ review)",
        weight=0.0,
        reference=(
            "Kosovo Public Procurement Law, Article 19, defines the low-value "
            "band as at least €1,000 and below €10,000; the consolidated "
            "Regulation 001/2022 as amended by Regulation 002/2024, Article "
            "51.3, restricts price quotation to the stated low-value and "
            "subject-matter conditions."
        ),
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Published price-quotation subtype and estimated value ≥ €10,000.",
        limitations=(
            "May reflect source errors, amendments, lot/framework semantics or another "
            "documented circumstance; it is not a finding of illegality."
        ),
    ),
    Rule(
        "BUYER_NAME_ID_COLLISION",
        "Normalized buyer name is published under multiple source IDs (DQ review)",
        weight=0.0,
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Same normalized buyer name maps to more than one nonblank source ID.",
        limitations=(
            "May reflect an identifier migration or different legal entities with similar names; "
            "the pipeline does not merge them."
        ),
    ),
    Rule(
        "HIGH_VALUE_SINGLE",
        "Top-1 % value AND single-bidder",
        weight=0.75,
        threshold_rationale="Within-category 99th percentile plus one bidder; author-selected.",
        limitations="Snapshot-relative percentile; an interaction signal, not independent evidence.",
    ),
    Rule(
        "END_BEFORE_START_OPEN",
        "Standard-open record with end-before-start (date-quality check)",
        weight=0.0,
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Recorded end timestamp precedes recorded start timestamp.",
        limitations="Kept as a source-quality diagnostic, not an integrity label.",
    ),
    Rule(
        "LOT_VALUE_MISMATCH",
        "Lot sum differs by both >€100 and >0.1 % from tender value",
        weight=0.0,
        score_enabled=False,
        signal_type="data_quality",
        threshold_rationale="Hybrid absolute (€100) and relative (0.1 %) materiality tolerance.",
        limitations="Lot and tender fields can use different aggregation semantics.",
    ),
    Rule(
        "WINNER_TAKES_ALL_LARGE",
        "Single supplier captures ≥95 % of recorded award value in a multi-lot tender worth ≥ €100 K",
        weight=0.5,
        threshold_rationale="Author-selected 95 % share and €100k value floor.",
        limitations=(
            "Uses tender-level award totals because award-to-lot linkage is title-only; "
            "requires review of lot structure and is not outcome-calibrated."
        ),
    ),
    Rule(
        "UNAWARDED_HIGH_VALUE",
        "Top-5 % value tender with zero awards (operational follow-up)",
        weight=0.0,
        score_enabled=False,
        signal_type="operational",
        threshold_rationale="Within-category 95th percentile and no recorded award.",
        limitations="May be cancelled, incomplete or legitimately unawarded; not a corruption signal.",
    ),
)


def apply_rules(features: pd.DataFrame) -> pd.DataFrame:
    """Add one boolean column per rule + the composite ``rule_score``.

    Args:
        features: The :func:`thesis.domain.features.build_tender_features`
            output.

    Returns:
        DataFrame with one column per rule code plus ``rule_score`` and
        ``rule_count``.
    """
    f = features
    out = pd.DataFrame(index=f.index)

    subtype = (
        f["procedure_subtype"] if "procedure_subtype" in f.columns else classify_procedure_series(f)
    )
    standard_open = subtype.eq(STANDARD_OPEN)
    single = f["is_single_bidder"].fillna(0).astype(bool)
    # Mutually exclusive: one observed fact contributes at most once.
    out["SINGLE_BIDDER_OPEN"] = (single & standard_open).fillna(False)
    out["SINGLE_BIDDER"] = (single & ~standard_open).fillna(False)
    out["ZERO_BIDDER"] = f["is_zero_bidder"].fillna(0).astype(bool) & f["n_awards"].fillna(0).eq(0)

    # Route value-ratio comparisons by data plausibility. A ratio of 988×
    # (e.g. a €180 estimate beside a €178 K contract total) is likely a
    # unit/field comparability problem. Likewise, a ratio near zero can reflect
    # partial or mismatched aggregation. The comparison bands are diagnostics,
    # and the extreme high tail gets its own data-quality indicator.
    ratio = f["awarded_value_ratio"]
    out["RATIO_BELOW_50"] = ((ratio < 0.5) & (ratio >= 0.01)).fillna(False)
    out["RATIO_ABOVE_ESTIMATE"] = (
        (ratio >= OVERSHOOT_MARGIN) & (ratio <= IMPLAUSIBLE_RATIO_CEILING)
    ).fillna(False)
    out["IMPLAUSIBLE_ESTIMATE"] = (ratio > IMPLAUSIBLE_RATIO_CEILING).fillna(False)

    out["NEGATIVE_DAYS_TO_AWARD"] = (f["days_to_first_award"] < 0).fillna(False)

    open_short = standard_open & (f["days_tender_open"] >= 0) & (f["days_tender_open"] < 7)
    out["ULTRA_SHORT_OPEN"] = open_short.fillna(False)
    out["PRICE_QUOTATION_VALUE_BAND_CONFLICT"] = (
        subtype.eq(PRICE_QUOTATION) & f["estimated_value_eur"].ge(PRICE_QUOTATION_UPPER_BOUND_EUR)
    ).fillna(False)
    buyer_collision = f.get("buyer_name_id_collision", pd.Series(False, index=f.index))
    out["BUYER_NAME_ID_COLLISION"] = buyer_collision.fillna(False).astype(bool)

    # High-value thresholds are peer-group-relative: "high value" for a goods
    # tender differs from works (review H-10). We use the 99th/95th percentile
    # WITHIN each procurement category rather than a single national cutoff.
    # (A production monitor would freeze these from a fixed reference period;
    # here they are deterministic given the gold snapshot.)
    cat_q99 = f.groupby("category")["estimated_value_eur"].transform(lambda s: s.quantile(0.99))
    cat_q95 = f.groupby("category")["estimated_value_eur"].transform(lambda s: s.quantile(0.95))
    out["HIGH_VALUE_SINGLE"] = (
        (f["estimated_value_eur"] >= cat_q99) & f["is_single_bidder"].astype(bool)
    ).fillna(False)

    out["END_BEFORE_START_OPEN"] = (standard_open & f["end_before_start"].astype(bool)).fillna(
        False
    )

    out["LOT_VALUE_MISMATCH"] = f["lot_value_mismatch"].astype(bool)

    num_lots = f.get("num_lots", pd.Series(0, index=f.index))
    out["WINNER_TAKES_ALL_LARGE"] = (
        (num_lots.fillna(0) > 1)
        & (f["n_awards"].fillna(0) > 1)
        & (f["winner_top_share"] >= 0.95)
        & (f["estimated_value_eur"].fillna(0) >= WINNER_TAKES_ALL_VALUE_FLOOR)
    ).fillna(False)

    out["UNAWARDED_HIGH_VALUE"] = (
        (f["estimated_value_eur"] >= cat_q95) & (f["n_awards"].fillna(0) == 0)
    ).fillna(False)

    weights = {r.code: r.weight for r in RULES if r.score_enabled}
    raw = sum(out[code].astype(float) * w for code, w in weights.items())
    out["rule_score"] = (raw / RULE_SCORE_NORMALISER).clip(upper=1.0)
    out["rule_count"] = sum(out[r.code].astype(int) for r in RULES if r.score_enabled)
    out["indicator_count"] = sum(out[r.code].astype(int) for r in RULES)
    out["diagnostic_count"] = sum(out[r.code].astype(int) for r in RULES if not r.score_enabled)
    return out


def rule_descriptions() -> pd.DataFrame:
    """Return a tidy DataFrame of all rules — used by the UI and docs."""
    return pd.DataFrame(
        [
            {
                "code": r.code,
                "description": r.description,
                "weight": r.weight,
                "reference": r.reference,
                "score_enabled": r.score_enabled,
                "signal_type": r.signal_type,
                "threshold_rationale": r.threshold_rationale,
                "limitations": r.limitations,
            }
            for r in RULES
        ]
    )
