"""Unit tests for the DQ expectation framework."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly.rules import RULES
from thesis.domain.features import ML_FEATURES
from thesis.dq.framework import (
    Expectation,
    ExpectationSuite,
    Severity,
    run_suite,
)
from thesis.dq.suites import (
    GOLD_SCORE_COLUMNS,
    gold_entity_summary_suite_for,
    gold_monthly_metrics_suite_for,
    gold_supplier_summary_suite_for,
    gold_tender_features_suite_for,
    gold_tender_summary_suite,
    silver_awards_suite,
    silver_awards_suite_for,
    silver_tenders_suite,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "value": [10.0, 20.0, 30.0, 40.0, 50.0],
            "name": ["a", "b", "c", "d", "e"],
        }
    )


def test_run_suite_all_pass(sample_df):
    suite = ExpectationSuite(
        name="t",
        table="t",
        expectations=[
            Expectation("not_empty", "table not empty", lambda df: (len(df) > 0, len(df))),
            Expectation(
                "id_unique",
                "id unique",
                lambda df: (df["id"].is_unique, int(df["id"].duplicated().sum())),
            ),
        ],
    )
    res = run_suite(suite, sample_df)
    assert res.passed
    assert res.error_count == 0
    assert res.pass_count == 2
    assert res.fail_count == 0


def test_run_suite_warning_does_not_fail(sample_df):
    suite = ExpectationSuite(
        name="t",
        table="t",
        expectations=[
            Expectation(
                "non_existent_constraint",
                "should always fail",
                lambda df: (False, "boom"),
                severity=Severity.WARNING,
            ),
        ],
    )
    res = run_suite(suite, sample_df)
    assert res.passed  # warnings don't fail the suite
    assert res.warning_count == 1
    assert res.error_count == 0


def test_run_suite_coerces_numpy_boolean_for_json_evidence(sample_df):
    suite = ExpectationSuite(
        name="t",
        table="t",
        expectations=[
            Expectation(
                "numpy_boolean",
                "numpy scalar",
                lambda df: (np.bool_(len(df) > 0), len(df)),
            )
        ],
    )

    result = run_suite(suite, sample_df)

    assert result.expectations[0].passed is True
    assert json.loads(json.dumps(result.expectations[0].__dict__))["passed"] is True


def test_run_suite_error_fails(sample_df):
    suite = ExpectationSuite(
        name="t",
        table="t",
        expectations=[
            Expectation(
                "must_pass", "must pass", lambda df: (False, "boom"), severity=Severity.ERROR
            ),
        ],
    )
    res = run_suite(suite, sample_df)
    assert not res.passed
    assert res.error_count == 1


def test_predicate_exception_recorded_as_failure(sample_df):
    suite = ExpectationSuite(
        name="t",
        table="t",
        expectations=[
            Expectation(
                "buggy_predicate", "raises", lambda df: (1 / 0, None), severity=Severity.ERROR
            ),
        ],
    )
    res = run_suite(suite, sample_df)
    assert not res.passed
    assert res.expectations[0].observed.startswith("exception:")


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -0.01, 1.01])
def test_scored_gold_dq_rejects_invalid_model_scores(bad_value):
    frame = pd.DataFrame(
        {
            "ocid": ["one", "two"],
            **{column: [0.2, 0.8] for column in GOLD_SCORE_COLUMNS},
            "ensemble_rank_ocsvm": [0.5, 1.0],
            "ensemble_rank_iso": [0.5, 1.0],
            "ensemble_rank_hbos": [0.5, 1.0],
            "ensemble_rank_knn": [0.5, 1.0],
            "model_agreement_count": [0, 4],
            "high_confidence": [0, 1],
        }
    )
    frame["ensemble_score"] = [0.4, 14.0 / 15.0]
    frame.loc[0, "iso_score"] = bad_value

    result = run_suite(gold_tender_summary_suite, frame)

    assert not result.passed
    assert result.error_count >= 1


def test_scored_gold_dq_rejects_tampered_ensemble_explanation() -> None:
    frame = pd.DataFrame(
        {
            "ocid": ["one", "two"],
            **{column: [0.2, 0.8] for column in GOLD_SCORE_COLUMNS},
            "ensemble_rank_ocsvm": [0.5, 1.0],
            "ensemble_rank_iso": [0.5, 1.0],
            "ensemble_rank_hbos": [0.5, 1.0],
            "ensemble_rank_knn": [0.5, 1.0],
            "model_agreement_count": [0, 4],
            "high_confidence": [0, 1],
        }
    )
    frame["ensemble_score"] = [0.4, 14.0 / 15.0]
    frame.loc[0, "ensemble_rank_iso"] = 0.75

    result = run_suite(gold_tender_summary_suite, frame)

    assert not result.passed
    assert any(
        item.name == "ensemble_xai_exact_reconstruction" and not item.passed
        for item in result.expectations
    )


@pytest.mark.parametrize("bad_value", [np.inf, -np.inf, "not-numeric"])
def test_base_gold_dq_rejects_invalid_ml_feature_values(bad_value):
    frame = pd.DataFrame(
        {
            "ocid": ["one", "two"],
            "procedure_subtype": ["standard_open", "price_quotation"],
            **{column: [0.0, 1.0] for column in ML_FEATURES},
            **{rule.code: [False, False] for rule in RULES},
            "rule_score": [0.0, 0.0],
        }
    )
    if isinstance(bad_value, str):
        frame[ML_FEATURES[0]] = frame[ML_FEATURES[0]].astype(object)
    frame.loc[0, ML_FEATURES[0]] = bad_value
    suite = gold_tender_features_suite_for(pd.Series(["one", "two"]))

    result = run_suite(suite, frame)

    assert not result.passed
    assert result.error_count >= 1


def test_base_gold_dq_rejects_silver_ocid_population_drift():
    frame = pd.DataFrame(
        {
            "ocid": ["one"],
            "procedure_subtype": ["standard_open"],
            **{column: [0.0] for column in ML_FEATURES},
            **{rule.code: [False] for rule in RULES},
            "rule_score": [0.0],
        }
    )
    suite = gold_tender_features_suite_for(pd.Series(["one", "missing-two"]))

    result = run_suite(suite, frame)

    assert not result.passed
    parity = next(item for item in result.expectations if item.name == "silver_to_gold_ocid_parity")
    assert parity.observed["missing_ocids"] == 1


def _expectation(suite, name):
    return next(expectation for expectation in suite.expectations if expectation.name == name)


def test_silver_dq_rejects_inconsistent_nullable_bidder_observation():
    frame = pd.DataFrame({"num_bidders": [pd.NA, 2], "bidder_data_observed": [True, True]})
    passed, observed = _expectation(
        silver_tenders_suite,
        "bidder_observation_matches_nullable_count",
    ).predicate(frame)
    assert not passed
    assert observed == 1


def test_silver_dq_reports_price_quotation_threshold_conflict_at_boundary():
    frame = pd.DataFrame(
        {
            "procedure_code": ["6", "6", "1"],
            "estimated_value_eur": [9_999.99, 10_000.0, 20_000.0],
        }
    )
    passed, observed = _expectation(
        silver_tenders_suite,
        "price_quotation_value_band_conflicts",
    ).predicate(frame)
    assert not passed
    assert observed == 1


def test_silver_dq_reports_buyer_name_to_multiple_id_collision_without_merging():
    frame = pd.DataFrame(
        {
            "procuring_entity_name": ["Komuna e Testit", "  KOMUNA E TESTIT  "],
            "procuring_entity_id": ["buyer-1", "buyer-2"],
        }
    )
    passed, observed = _expectation(
        silver_tenders_suite,
        "buyer_name_id_collisions",
    ).predicate(frame)
    assert not passed
    assert observed["normalized_names_with_multiple_ids"] == 1
    assert observed["affected_source_ids"] == 2


def test_silver_award_dq_blocks_non_normalized_business_id_sentinel():
    frame = pd.DataFrame({"supplier_business_id": ["valid-1", "N/A", None]})
    passed, observed = _expectation(
        silver_awards_suite,
        "supplier_business_id_sentinels_normalized",
    ).predicate(frame)
    assert not passed
    assert observed == 1


def test_silver_award_dq_reports_non_unique_lot_title_linkage():
    frame = pd.DataFrame(
        {
            "award_lot_match_status": [
                "exact_unique",
                "no_exact_match",
                "exact_ambiguous",
                "missing_title",
            ]
        }
    )
    passed, observed = _expectation(
        silver_awards_suite,
        "award_lot_title_linkage",
    ).predicate(frame)
    assert not passed
    assert observed == {
        "exact_unique": 1,
        "no_exact_match": 1,
        "exact_ambiguous": 1,
        "missing_title": 1,
    }


def test_silver_award_dq_accepts_award_subset_of_exact_tender_population():
    suite = silver_awards_suite_for(pd.Series(["tender-2", "tender-1"]))
    expectation = _expectation(suite, "award_ocids_reference_tenders")

    passed, observed = expectation.predicate(pd.DataFrame({"ocid": ["tender-1", "tender-1"]}))

    assert passed
    assert expectation.severity is Severity.ERROR
    assert observed["expected_tender_ocids"] == 2
    assert len(observed["tender_ocid_population_sha256"]) == 64
    assert observed["orphan_rows"] == 0
    assert observed["orphan_ocids"] == 0
    assert observed["orphan_ocid_sample"] == []


def test_silver_award_dq_rejects_and_reports_orphan_ocids():
    suite = silver_awards_suite_for(pd.Series(["tender-1", "tender-2"]))
    expectation = _expectation(suite, "award_ocids_reference_tenders")

    passed, observed = expectation.predicate(
        pd.DataFrame({"ocid": ["tender-1", "orphan-2", "orphan-1", "orphan-2", None]})
    )

    assert not passed
    assert observed["award_rows"] == 5
    assert observed["orphan_rows"] == 4
    assert observed["orphan_ocids"] == 2
    assert observed["null_award_ocids"] == 1
    assert observed["orphan_ocid_sample"] == ["orphan-1", "orphan-2"]


def test_gold_supplier_dq_reconciles_only_identified_awards_and_coverage():
    awards = pd.DataFrame(
        {
            "supplier_business_id": ["A-1", "", None],
            "supplier_name": ["Alpha", "Beta", ""],
            "supplier_party_id": ["party-a", "party-b", ""],
            "supplier_uid": ["uid-a", "uid-b", ""],
            "awarded_value_eur": [100.0, 50.0, 50.0],
        }
    )
    summary = pd.DataFrame(
        {
            "supplier_key": ["A-1", "name::beta"],
            "award_rows": [1, 1],
            "total_awarded_eur": [100.0, 50.0],
            "identity_value_coverage_pct": [75.0, 75.0],
        }
    )
    expectation = _expectation(
        gold_supplier_summary_suite_for(awards),
        "source_award_reconciliation",
    )

    passed, observed = expectation.predicate(summary)

    assert passed
    assert observed["identified_award_rows"] == 2
    assert observed["unidentified_award_rows"] == 1
    assert observed["unidentified_awarded_eur"] == pytest.approx(50.0)
    assert observed["expected_identity_value_coverage_pct"] == pytest.approx(75.0)

    summary.loc[1, "total_awarded_eur"] = 49.0
    passed, observed = expectation.predicate(summary)
    assert not passed
    assert observed["per_key_awarded_value_mismatches"] == 1


def test_gold_entity_dq_reconciles_each_source_group_and_global_totals():
    features = pd.DataFrame(
        {
            "ocid": ["t1", "t2", "t3"],
            "procuring_entity_id": ["e1", "e1", None],
            "estimated_value_eur": [100.0, 50.0, 25.0],
            "total_awarded_eur": [80.0, 0.0, 20.0],
        }
    )
    summary = pd.DataFrame(
        {
            "procuring_entity_id": ["e1", None],
            "tenders": [2, 1],
            "total_estimated_eur": [150.0, 25.0],
            "total_awarded_eur": [80.0, 20.0],
        }
    )
    expectation = _expectation(
        gold_entity_summary_suite_for(features),
        "source_feature_reconciliation",
    )

    passed, observed = expectation.predicate(summary)

    assert passed
    assert observed["expected_entity_rows"] == 2
    assert observed["actual_tenders"] == 3
    assert observed["actual_total_estimated_eur"] == pytest.approx(175.0)

    summary.loc[0, "total_awarded_eur"] = 81.0
    passed, observed = expectation.predicate(summary)
    assert not passed
    assert observed["per_entity_awarded_value_mismatches"] == 1


def test_gold_monthly_dq_reconciles_unknown_date_bucket_separately():
    features = pd.DataFrame(
        {
            "ocid": ["t1", "t2", "t3"],
            "release_date": pd.to_datetime(["2022-01-01", "2022-02-01", None], utc=True),
            "estimated_value_eur": [100.0, 50.0, 25.0],
            "total_awarded_eur": [80.0, 0.0, 20.0],
        }
    )
    summary = pd.DataFrame(
        {
            "period_label": ["2022-01", "2022-02", "unknown_date"],
            "date_known": [True, True, False],
            "tenders": [1, 1, 1],
            "estimated_value_eur": [100.0, 50.0, 25.0],
            "total_awarded_eur": [80.0, 0.0, 20.0],
        }
    )
    expectation = _expectation(
        gold_monthly_metrics_suite_for(features),
        "source_feature_reconciliation",
    )

    passed, observed = expectation.predicate(summary)

    assert passed
    assert observed["expected_unknown_date_tenders"] == 1
    assert observed["actual_unknown_date_tenders"] == 1
    assert observed["actual_total_awarded_eur"] == pytest.approx(100.0)

    summary.loc[0, "tenders"] = 2
    summary.loc[2, "tenders"] = 0
    passed, observed = expectation.predicate(summary)
    assert not passed
    assert observed["actual_tenders"] == 3
    assert observed["actual_unknown_date_tenders"] == 0


def test_suite_write_resolves_reloaded_dq_path_at_call_time(sample_df, tmp_path, monkeypatch):
    """An already-imported framework must follow a later data-dir redirect."""
    from thesis import config, paths

    suite_name = f"runtime_path_{tmp_path.name}"
    canonical_json = paths.DQ / f"{suite_name}.dq.json"
    canonical_before = canonical_json.read_bytes() if canonical_json.exists() else None
    result = run_suite(
        ExpectationSuite(
            name=suite_name,
            table="fixture",
            expectations=[
                Expectation("not_empty", "table not empty", lambda df: (bool(len(df)), len(df)))
            ],
        ),
        sample_df,
    )

    try:
        with monkeypatch.context() as scoped:
            scoped.setenv("THESIS_DATA_DIR", str(tmp_path))
            config.reset_settings_for_tests()
            importlib.reload(paths)

            out = result.write()
            assert out == tmp_path / "dq" / f"{suite_name}.dq.json"
            assert json.loads(out.read_text())["suite"] == suite_name
            assert out.with_suffix(".md").exists()
    finally:
        # Restore the shared module object for tests that run after this one.
        config.reset_settings_for_tests()
        importlib.reload(paths)

    canonical_after = canonical_json.read_bytes() if canonical_json.exists() else None
    assert canonical_after == canonical_before


def test_release_payload_binds_exact_persisted_artifact(sample_df, tmp_path, monkeypatch):
    from thesis.dq import framework

    monkeypatch.setattr(framework.paths, "DATA", tmp_path)
    artifact = tmp_path / "gold" / "checked.parquet"
    artifact.parent.mkdir(parents=True)
    sample_df.to_parquet(artifact, index=False)
    result = run_suite(
        ExpectationSuite(
            name="release_bound",
            table="gold.checked",
            expectations=[
                Expectation("not_empty", "table not empty", lambda df: (bool(len(df)), len(df)))
            ],
        ),
        sample_df,
    )

    payload = result.release_payload(artifact, sample_df)

    assert payload["rows"] == len(sample_df)
    assert payload["columns"] == sample_df.shape[1]
    assert payload["release_binding"]["artifact_path"] == "gold/checked.parquet"
    assert len(payload["release_binding"]["artifact_sha256"]) == 64
