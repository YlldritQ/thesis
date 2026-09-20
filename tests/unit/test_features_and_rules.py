"""Unit tests for feature engineering and the rule book.

Run from project root:  PYTHONPATH=src .venv/bin/python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
from datetime import timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly import RULES, apply_rules
from thesis.domain.features import (
    aggregate_awards_per_tender,
    build_tender_features,
    normalise_supplier_business_id,
    safe_log10,
)
from thesis.domain.procedures import (
    DESIGN_CONTEST,
    FRAMEWORK_MINI_TENDER,
    MINIMUM_VALUE,
    NEGOTIATED_WITH_NOTICE,
    NEGOTIATED_WITHOUT_NOTICE,
    PRICE_QUOTATION,
    RESTRICTED,
    STANDARD_OPEN,
    UNKNOWN,
    classify_procedure,
)

# =========================================================== fixtures

UTC = timezone.utc


def _tender_row(**overrides) -> dict:
    base = {
        "ocid": "ocds-test-001",
        "release_id": "rel-1",
        "release_date": pd.Timestamp("2023-06-01", tz=UTC),
        "tender_id": "t-x",
        "title": "test tender",
        "status": "active",
        "category": "goods",
        "method": "open",
        "method_details": "x",
        "award_criteria": "priceOnly",
        "estimated_value_eur": 100_000.0,
        "currency": "EUR",
        "start_date": pd.Timestamp("2023-05-01", tz=UTC),
        "end_date": pd.Timestamp("2023-05-30", tz=UTC),
        "duration_reported_days": 29.0,
        "procuring_entity_id": "e1",
        "procuring_entity_uid": "u-e1",
        "procuring_entity_name": "ENTITY ONE",
        "num_lots": 1,
        "lots_value_sum": 100_000.0,
        "num_bidders": 3,
        "bidder_data_observed": True,
        "num_suppliers_in_parties": 1,
        "num_parties": 4,
        "num_awards": 1,
        "duration_computed_days": 29.0,
        "end_before_start": False,
        "year": 2023,
        "month": "2023-06",
    }
    base.update(overrides)
    return base


def _award_row(**overrides) -> dict:
    base = {
        "ocid": "ocds-test-001",
        "tender_id": "t-x",
        "award_id": "a-1",
        "award_uid": "u-a1",
        "award_title": "test award",
        "award_description": "",
        "award_lot_title": "",
        "award_lot_match_status": "missing_title",
        "award_date": pd.Timestamp("2023-06-15", tz=UTC),
        "award_status_id": "active",
        "awarded_value_eur": 80_000.0,
        "awarded_currency": "EUR",
        "supplier_party_id": "p1",
        "supplier_uid": "u-p1",
        "supplier_name": "Supplier A",
        "supplier_legal_name": "Supplier A SH.P.K.",
        "supplier_business_id": "12345",
        "supplier_business_id_raw": "12345",
        "supplier_org_schema": "XK",
        "category": "goods",
        "method": "open",
        "estimated_value_eur": 100_000.0,
        "procuring_entity_id": "e1",
        "procuring_entity_name": "ENTITY ONE",
        "num_bidders": 3,
        "bidder_data_observed": True,
        "num_awards": 1,
        "value_ratio": 0.8,
    }
    base.update(overrides)
    return base


# ====================================================== tests: helpers


def test_safe_log10_handles_zeros_and_negatives():
    s = pd.Series([100.0, 0.0, -1.0, 1e6])
    out = safe_log10(s)
    assert out.iloc[0] == pytest.approx(2.0)
    assert pd.isna(out.iloc[1])
    assert pd.isna(out.iloc[2])
    assert out.iloc[3] == pytest.approx(6.0)


# ============================================== tests: award aggregation


def test_aggregate_awards_per_tender_sums_correctly():
    awards = pd.DataFrame(
        [
            _award_row(awarded_value_eur=60_000),
            _award_row(award_id="a-2", awarded_value_eur=40_000, supplier_business_id="67890"),
        ]
    )
    out = aggregate_awards_per_tender(awards)
    assert len(out) == 1
    assert out["n_awards"].iat[0] == 2
    assert out["total_awarded_eur"].iat[0] == 100_000
    assert out["n_supplier_business_ids"].iat[0] == 2


def test_aggregate_awards_handles_missing_values():
    awards = pd.DataFrame(
        [
            _award_row(awarded_value_eur=None),
            _award_row(award_id="a-2", awarded_value_eur=50_000),
        ]
    )
    out = aggregate_awards_per_tender(awards)
    assert out["n_awards"].iat[0] == 2
    # min_count=1 means single-value sums survive
    assert out["total_awarded_eur"].iat[0] == 50_000


# ====================================================== tests: feature build


def test_build_tender_features_adds_derivations():
    tenders = pd.DataFrame([_tender_row()])
    awards = pd.DataFrame([_award_row()])
    out = build_tender_features(tenders, awards)
    row = out.iloc[0]
    assert row["log_estimated_eur"] == pytest.approx(5.0)
    assert row["log_awarded_eur"] == pytest.approx(np.log10(80_000))
    assert row["awarded_value_ratio"] == pytest.approx(0.8)
    assert row["was_awarded"] == 1
    assert row["is_single_bidder"] == 0
    assert row["winner_top_share"] == pytest.approx(1.0)


def test_build_tender_features_zero_awards():
    tenders = pd.DataFrame([_tender_row(num_awards=0)])
    awards = pd.DataFrame(columns=[*_award_row().keys()])
    out = build_tender_features(tenders, awards)
    assert out["was_awarded"].iat[0] == 0
    # No award is a valid procurement state, not missing data or a zero-value
    # contract. Counts/totals are zero; award-dependent measures are undefined.
    assert "award_data_missing" not in out
    assert out["n_awards"].iat[0] == 0
    assert out["total_awarded_eur"].iat[0] == 0.0
    assert pd.isna(out["winner_top_share"].iat[0])
    assert pd.isna(out["awarded_value_ratio"].iat[0])


def test_missing_bidder_data_is_not_silently_converted_to_zero():
    tenders = pd.DataFrame(
        [_tender_row(num_bidders=None, bidder_data_observed=False, num_awards=0)]
    )
    awards = pd.DataFrame(columns=[*_award_row().keys()])

    out = _build_with_rules(tenders, awards).iloc[0]

    assert pd.isna(out["num_bidders"])
    assert out["bidder_data_missing"] == 1
    assert out["is_zero_bidder"] == 0
    assert not out["ZERO_BIDDER"]


def test_procedure_taxonomy_uses_detail_not_coarse_open_value():
    assert classify_procedure("open", "otvoreni postupak") == STANDARD_OPEN
    assert (
        classify_procedure("open", "postupak bagatelne nabave - javna objava poziva")
        == PRICE_QUOTATION
    )
    assert classify_procedure("open", None) == UNKNOWN


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("1", STANDARD_OPEN),
        ("2", RESTRICTED),
        ("3", DESIGN_CONTEST),
        ("4", NEGOTIATED_WITH_NOTICE),
        ("5", NEGOTIATED_WITHOUT_NOTICE),
        ("6", PRICE_QUOTATION),
        ("7", MINIMUM_VALUE),
        ("8", FRAMEWORK_MINI_TENDER),
    ],
)
def test_procedure_taxonomy_uses_official_terminal_source_code(code, expected):
    assert classify_procedure("open", "otvoreni postupak", f"616-26-123-{code}") == expected


def test_code_three_design_contest_is_not_promoted_to_standard_open():
    assert classify_procedure("open", "otvoreni natjecaj", "616-26-123-3") == DESIGN_CONTEST


@pytest.mark.parametrize("sentinel", [None, "", " ", "N/A", "0", "/", "//", "."])
def test_business_id_sentinels_are_missing_not_entities(sentinel):
    assert normalise_supplier_business_id(sentinel) is None


@pytest.mark.parametrize(
    ("estimate", "lot_sum", "expected"),
    [
        (100_000.0, 100_050.0, 0),  # below absolute €100 tolerance
        (10_000_000.0, 10_000_500.0, 0),  # below relative 0.1% tolerance
        (100_000.0, 100_200.0, 1),  # exceeds both tolerances
    ],
)
def test_lot_mismatch_requires_absolute_and_relative_materiality(estimate, lot_sum, expected):
    tenders = pd.DataFrame(
        [
            _tender_row(
                num_lots=2,
                estimated_value_eur=estimate,
                lots_value_sum=lot_sum,
            )
        ]
    )
    out = build_tender_features(tenders, pd.DataFrame([_award_row()]))
    assert out["lot_value_mismatch"].iat[0] == expected


# =========================================================== tests: rules


def _build_with_rules(tenders, awards):
    f = build_tender_features(tenders, awards)
    r = apply_rules(f)
    return pd.concat([f, r], axis=1)


def test_rule_single_bidder():
    t = pd.DataFrame([_tender_row(num_bidders=1)])
    a = pd.DataFrame([_award_row()])
    out = _build_with_rules(t, a)
    assert out["SINGLE_BIDDER"].iat[0]
    assert out["rule_score"].iat[0] > 0


def test_standard_open_single_bidder_is_exclusive_strong_variant():
    t = pd.DataFrame([_tender_row(num_bidders=1, method_details="otvoreni postupak")])
    out = _build_with_rules(t, pd.DataFrame([_award_row()]))
    assert out["procedure_subtype"].iat[0] == STANDARD_OPEN
    assert out["SINGLE_BIDDER_OPEN"].iat[0]
    assert not out["SINGLE_BIDDER"].iat[0]
    assert out["rule_score"].iat[0] == pytest.approx((0.75 + 0.75) / 2)


def test_standard_open_single_bidder_alone_stays_below_review_threshold():
    tenders = pd.DataFrame(
        [
            _tender_row(
                ocid="target",
                tender_id="target",
                num_bidders=1,
                method_details="otvoreni postupak",
                estimated_value_eur=100_000,
            ),
            _tender_row(
                ocid="peer",
                tender_id="peer",
                num_bidders=3,
                method_details="otvoreni postupak",
                estimated_value_eur=10_000_000,
            ),
        ]
    )
    awards = pd.DataFrame(
        [
            _award_row(ocid="target", tender_id="target", awarded_value_eur=90_000),
            _award_row(
                ocid="peer",
                tender_id="peer",
                award_id="peer-a",
                award_uid="peer-u",
                awarded_value_eur=9_000_000,
            ),
        ]
    )
    row = _build_with_rules(tenders, awards).set_index("ocid").loc["target"]
    assert row["SINGLE_BIDDER_OPEN"]
    assert not row["HIGH_VALUE_SINGLE"]
    assert row["rule_score"] == pytest.approx(0.75 / 2)
    assert row["rule_score"] < 0.5


def test_five_day_price_quotation_is_not_short_standard_open():
    t = pd.DataFrame(
        [
            _tender_row(
                num_bidders=1,
                tender_id="616-23-123-6",
                method="open",
                method_details="postupak bagatelne nabave - javna objava poziva",
                start_date=pd.Timestamp("2023-05-01", tz=UTC),
                end_date=pd.Timestamp("2023-05-06", tz=UTC),
                duration_computed_days=5,
            )
        ]
    )
    out = _build_with_rules(t, pd.DataFrame([_award_row()]))
    assert out["procedure_subtype"].iat[0] == PRICE_QUOTATION
    assert not out["ULTRA_SHORT_OPEN"].iat[0]
    assert out["SINGLE_BIDDER"].iat[0]
    assert not out["SINGLE_BIDDER_OPEN"].iat[0]


def test_rule_zero_bidder():
    t = pd.DataFrame([_tender_row(num_bidders=0)])
    a = pd.DataFrame(columns=[*_award_row().keys()])
    out = _build_with_rules(t, a)
    assert out["ZERO_BIDDER"].iat[0]


def test_zero_bidder_with_recorded_award_is_not_operational_zero_award_flag():
    t = pd.DataFrame([_tender_row(num_bidders=0, bidder_data_observed=True)])
    out = _build_with_rules(t, pd.DataFrame([_award_row()]))
    assert not out["ZERO_BIDDER"].iat[0]


@pytest.mark.parametrize(("estimate", "expected"), [(9_999.99, False), (10_000.0, True)])
def test_price_quotation_value_band_diagnostic_boundary(estimate, expected):
    tender = _tender_row(
        tender_id="616-23-123-6",
        estimated_value_eur=estimate,
        lots_value_sum=estimate,
    )
    award = _award_row(awarded_value_eur=estimate, estimated_value_eur=estimate)
    out = _build_with_rules(pd.DataFrame([tender]), pd.DataFrame([award]))
    assert bool(out["PRICE_QUOTATION_VALUE_BAND_CONFLICT"].iat[0]) is expected
    assert out["rule_score"].iat[0] == 0.0


def test_buyer_name_collision_is_diagnostic_and_does_not_merge_ids():
    tenders = pd.DataFrame(
        [
            _tender_row(ocid="a", tender_id="a", procuring_entity_id="id-1"),
            _tender_row(ocid="b", tender_id="b", procuring_entity_id="id-2"),
        ]
    )
    awards = pd.DataFrame(
        [
            _award_row(ocid="a", tender_id="a", procuring_entity_id="id-1"),
            _award_row(
                ocid="b",
                tender_id="b",
                award_id="b-award",
                award_uid="b-award-uid",
                procuring_entity_id="id-2",
            ),
        ]
    )
    out = _build_with_rules(tenders, awards)

    assert out["buyer_name_id_collision"].eq(1).all()
    assert out["BUYER_NAME_ID_COLLISION"].all()
    assert out["procuring_entity_id"].nunique() == 2
    assert out["rule_score"].eq(0.0).all()


def test_rule_ratio_below_50():
    t = pd.DataFrame([_tender_row(estimated_value_eur=100_000)])
    a = pd.DataFrame([_award_row(awarded_value_eur=20_000)])
    out = _build_with_rules(t, a)
    assert out["RATIO_BELOW_50"].iat[0]


def test_near_zero_ratio_is_outside_documented_low_ratio_band():
    t = pd.DataFrame([_tender_row(estimated_value_eur=100_000)])
    a = pd.DataFrame([_award_row(awarded_value_eur=500)])
    out = _build_with_rules(t, a)
    assert out["awarded_value_ratio"].iat[0] == pytest.approx(0.005)
    assert not out["RATIO_BELOW_50"].iat[0]


def test_rule_ratio_above_estimate():
    t = pd.DataFrame([_tender_row(estimated_value_eur=100_000)])
    a = pd.DataFrame([_award_row(awarded_value_eur=120_000)])
    out = _build_with_rules(t, a)
    assert out["RATIO_ABOVE_ESTIMATE"].iat[0]


def test_rule_negative_days_to_award():
    t = pd.DataFrame([_tender_row(end_date=pd.Timestamp("2023-07-01", tz=UTC))])
    a = pd.DataFrame([_award_row(award_date=pd.Timestamp("2023-06-15", tz=UTC))])
    out = _build_with_rules(t, a)
    assert out["NEGATIVE_DAYS_TO_AWARD"].iat[0]


def test_rule_score_saturates_at_1():
    """Independent score-enabled signals still cap the display score at 1."""
    t = pd.DataFrame(
        [
            _tender_row(
                num_bidders=1,
                num_lots=2,
                estimated_value_eur=10_000_000_000,
                method_details="otvoreni postupak",
            )
        ]
    )
    a = pd.DataFrame(
        [
            _award_row(awarded_value_eur=9_000_000_000),
            _award_row(award_id="a-2", award_uid="u-a2", awarded_value_eur=500_000_000),
        ]
    )
    out = _build_with_rules(t, a)
    assert out["SINGLE_BIDDER_OPEN"].iat[0]
    assert out["HIGH_VALUE_SINGLE"].iat[0]
    assert out["WINNER_TAKES_ALL_LARGE"].iat[0]
    assert out["rule_score"].iat[0] == pytest.approx(1.0, abs=1e-9)


def test_winner_takes_all_large_requires_multiple_published_lots():
    tender = pd.DataFrame(
        [_tender_row(num_lots=1, estimated_value_eur=1_000_000, lots_value_sum=1_000_000)]
    )
    awards = pd.DataFrame(
        [
            _award_row(awarded_value_eur=600_000),
            _award_row(
                award_id="a-2",
                award_uid="u-a2",
                awarded_value_eur=400_000,
            ),
        ]
    )

    out = _build_with_rules(tender, awards)

    assert out["n_awards"].iat[0] == 2
    assert out["winner_top_share"].iat[0] == pytest.approx(1.0)
    assert not out["WINNER_TAKES_ALL_LARGE"].iat[0]


def test_rule_count_matches_individual_flags():
    t = pd.DataFrame([_tender_row(num_bidders=1)])
    a = pd.DataFrame([_award_row(awarded_value_eur=10_000)])  # ratio_below_50 too
    out = _build_with_rules(t, a)
    assert int(out["rule_count"].iat[0]) == sum(
        bool(out[r.code].iat[0]) for r in RULES if r.score_enabled
    )
    assert int(out["indicator_count"].iat[0]) == sum(bool(out[r.code].iat[0]) for r in RULES)
    # The low-ratio data-quality signal stays visible but adds no priority.
    assert out["RATIO_BELOW_50"].iat[0]
    assert out["rule_score"].iat[0] == pytest.approx((0.25 + 0.75) / 2)


def test_rules_are_independent_columns():
    """Every rule code must appear as an output column."""
    t = pd.DataFrame([_tender_row()])
    a = pd.DataFrame([_award_row()])
    out = _build_with_rules(t, a)
    for r in RULES:
        assert r.code in out.columns
