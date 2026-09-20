"""Regression tests for coverage-sensitive gold summaries."""

from __future__ import annotations

import pandas as pd
import pytest

from thesis.dq.framework import run_suite
from thesis.dq.suites import (
    gold_entity_summary_suite_for,
    gold_monthly_metrics_suite_for,
    gold_supplier_summary_suite_for,
)
from thesis.pipeline.gold import _entity_summary, _monthly, _supplier_summary


def _awards() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ocid": ["t1", "t2", "t3"],
            "supplier_business_id": ["A-1", "", None],
            "supplier_party_id": ["party-a", "party-b", ""],
            "supplier_uid": ["uid-a", "uid-b", ""],
            "supplier_name": ["Alpha LLC", "Beta SHPK", ""],
            "awarded_value_eur": [100.0, 50.0, 50.0],
            "award_date": pd.to_datetime(["2022-01-02", "2022-02-02", "2022-03-02"], utc=True),
            "procuring_entity_id": ["e1", "e1", "e1"],
            "category": ["goods", "goods", "goods"],
            "method": ["open", "open", "open"],
        }
    )


def _features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ocid": ["t1", "t2", "t3"],
            "is_single_bidder": [1, 0, 1],
            "bidder_data_observed": [True, True, False],
        }
    )


def _tenders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ocid": ["t1", "t2", "t3"],
            "procuring_entity_id": ["e1", "e1", "e1"],
            "procuring_entity_name": ["Entity", "Entity", "Entity"],
            "was_awarded": [1, 1, 1],
            "estimated_value_eur": [120.0, 60.0, 70.0],
            "total_awarded_eur": [100.0, 50.0, 50.0],
            "is_single_bidder": [1, 0, 1],
            "is_zero_bidder": [0, 0, 0],
            "bidder_data_observed": [True, True, False],
            "buyer_name_id_collision": [0, 0, 0],
            "end_before_start": [0, 0, 0],
            "awarded_value_ratio": [100 / 120, 50 / 60, 50 / 70],
            "rule_score": [0.5, 0.0, 0.5],
            "release_date": pd.to_datetime(["2022-01-01", "2022-02-01", None], utc=True),
        }
    )


def test_supplier_summary_isolates_unknown_identity_and_discloses_coverage():
    out = _supplier_summary(_awards(), _features())
    assert set(out["identity_source"]) == {"business_id", "name_fallback"}
    assert len(out) == 2
    assert out["total_awarded_eur"].sum() == pytest.approx(150.0)
    assert out["share_of_total_awarded_pct"].sum() == pytest.approx(75.0)
    assert out["identity_value_coverage_pct"].nunique() == 1
    assert out["identity_value_coverage_pct"].iat[0] == pytest.approx(75.0)


def test_entity_concentration_reports_identity_sensitivity_and_coverage():
    out = _entity_summary(_awards(), _tenders()).set_index("procuring_entity_id").loc["e1"]
    assert out["supplier_hhi_name_fallback"] == pytest.approx(5555.56, rel=1e-3)
    assert out["supplier_hhi_source_party_fallback"] == pytest.approx(5555.56, rel=1e-3)
    assert out["supplier_hhi_id_only"] == pytest.approx(10000.0)
    assert out["supplier_identity_value_coverage_pct"] == pytest.approx(75.0)
    assert out["supplier_business_id_value_coverage_pct"] == pytest.approx(50.0)
    assert out["bidder_data_coverage_pct"] == pytest.approx(66.67)


def test_source_party_sensitivity_does_not_merge_same_name_distinct_parties():
    awards = _awards().iloc[:2].copy()
    awards["supplier_business_id"] = None
    awards["supplier_name"] = "Same published name"
    awards["supplier_party_id"] = ["party-a", "party-b"]
    tenders = _tenders().iloc[:2].copy()

    row = _entity_summary(awards, tenders).iloc[0]

    assert row["supplier_hhi_name_fallback"] == pytest.approx(10_000.0)
    assert row["supplier_hhi_source_party_fallback"] == pytest.approx(5555.56, rel=1e-3)


def test_monthly_summary_keeps_unknown_dates_and_reconciles_exact_totals():
    tenders = _tenders()
    out = _monthly(tenders)
    unknown = out[out["period_label"].eq("unknown_date")]
    assert len(unknown) == 1
    assert unknown["tenders"].iat[0] == 1
    assert out["tenders"].sum() == len(tenders)
    assert out["estimated_value_eur"].sum() == pytest.approx(tenders["estimated_value_eur"].sum())
    assert out["total_awarded_eur"].sum() == pytest.approx(tenders["total_awarded_eur"].sum())


def test_generated_gold_summaries_pass_dynamic_source_reconciliation():
    awards = _awards()
    features = _features()
    tenders = _tenders()
    supplier_result = run_suite(
        gold_supplier_summary_suite_for(awards),
        _supplier_summary(awards, features),
    )
    entity_result = run_suite(
        gold_entity_summary_suite_for(tenders),
        _entity_summary(awards, tenders),
    )
    monthly_result = run_suite(
        gold_monthly_metrics_suite_for(tenders),
        _monthly(tenders),
    )

    assert supplier_result.passed
    assert entity_result.passed
    assert monthly_result.passed
