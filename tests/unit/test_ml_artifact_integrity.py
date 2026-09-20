"""Persisted ML artifacts must reproduce the generation being released."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from thesis.anomaly import artifact_integrity as integrity
from thesis.io.writers import write_json
from thesis.paths import SHAP_VALUES_RELEASE_DQ
from thesis.pipeline.dag import default_dag
from thesis.release import canonical_release_contract


class _LinearScorer:
    fitted = True

    def __init__(self, offset: float):
        self.offset = offset

    def score(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(X["f1"].to_numpy(dtype=float) + self.offset, index=X.index)


class _DecisionClassifier:
    def decision_function(self, values: np.ndarray) -> np.ndarray:
        return 0.2 + values[:, 0] + values[:, 1]


class _HGBWrapper:
    model = _DecisionClassifier()


def _provenance() -> dict:
    return {
        "data_fingerprint": "data-fixture",
        "protocol_fingerprint": "protocol-fixture",
        "benchmark_complete": True,
        "champions_schema_version": 2,
        "champions_created_at": "2026-07-19T00:00:00+00:00",
        "benchmark_implementation_fingerprint": "implementation-fixture",
        "benchmark_semantic_fingerprint": "semantic-fixture",
    }


def _json_payloads() -> tuple[dict, dict]:
    provenance = _provenance()
    ensemble_explanation = {
        "schema_version": 1,
        "target": "ensemble_score",
        "explanation_type": "exact_additive_component_decomposition",
        "detector_families": ["iso"],
    }
    shap_explanation = {
        "target": "rule_proxy_binary_label",
        "output_space": "raw_log_odds",
        "does_not_explain": "ensemble_score",
    }
    feature_list = {
        "schema_version": integrity.ML_JSON_SCHEMA_VERSION,
        **provenance,
        "ml_features": ["f1", "f2"],
        "ensemble_families": ["iso"],
        "model_selection": "benchmark champions",
        "ensemble_explanation": ensemble_explanation,
        "shap_explanation": shap_explanation,
        "shap_base_value": 0.25,
    }
    report = {
        "schema_version": integrity.ML_JSON_SCHEMA_VERSION,
        **provenance,
        "n_records": 3,
        "n_features": 2,
        "features": ["f1", "f2"],
        "ensemble_models": ["iso"],
        "all_detector_families": ["iso", "hbos"],
        "model_selection": "benchmark champions",
        "supervised_model": "hgb proxy surrogate",
        "rule_label_threshold": 0.4,
        "IMPORTANT_metrics_are_faithfulness_to_rules_not_detection": True,
        "circularity_note": "proxy only",
        "cross_validation": {},
        "rule_only_baseline_and_confusion": {},
        "stability_by_ensemble_family": {"iso": {}},
        "limited_replication_note": "limited",
        "inter_model_agreement": {},
        "rank_agreement_quantile_sensitivity": {},
        "deployed_score_feature_ablation": {},
        "model_election_sensitivity": {},
        "supervised_calibration": {},
        "ensemble_explanation": ensemble_explanation,
        "shap_explanation": shap_explanation,
        "shap_base_value": 0.25,
    }
    return feature_list, report


def test_persisted_shap_release_dq_binds_exact_gold_order(tmp_path, monkeypatch):
    monkeypatch.setattr(integrity.paths, "DATA", tmp_path)
    gold_path = tmp_path / "gold" / "tender_summary.parquet"
    shap_path = tmp_path / "models" / "shap_values.parquet"
    gold_path.parent.mkdir(parents=True)
    shap_path.parent.mkdir(parents=True)
    gold = pd.DataFrame({"ocid": ["a", "b", "c"], "other": [1, 2, 3]})
    shap = pd.DataFrame(
        {
            "ocid": gold["ocid"],
            "base_value": [0.2, 0.2, 0.2],
            "f1": [0.1, -0.1, 0.0],
            "f2": [0.3, 0.2, -0.2],
        }
    )
    gold.to_parquet(gold_path, index=False)
    shap.to_parquet(shap_path, index=False)

    payload = integrity.persisted_shap_release_payload(
        shap_path, gold_path, expected_features=["f1", "f2"]
    )

    assert payload["passed"] is True
    assert payload["release_binding"]["artifact_path"] == "models/shap_values.parquet"
    assert payload["gold_reference_binding"]["artifact_path"] == ("gold/tender_summary.parquet")
    assert payload["expected_columns"] == ["ocid", "base_value", "f1", "f2"]
    assert payload["xai_semantics"]["does_not_explain"] == "ensemble_score"


def test_persisted_shap_release_dq_reconstructs_rule_proxy_raw_log_odds(tmp_path, monkeypatch):
    monkeypatch.setattr(integrity.paths, "DATA", tmp_path)
    gold_path = tmp_path / "gold" / "tender_summary.parquet"
    shap_path = tmp_path / "models" / "shap_values.parquet"
    hgb_path = tmp_path / "models" / "hgb_classifier.joblib"
    gold_path.parent.mkdir(parents=True)
    shap_path.parent.mkdir(parents=True)
    gold = pd.DataFrame({"ocid": ["a", "b"], "f1": [0.1, 0.3], "f2": [0.2, -0.1]})
    shap = pd.DataFrame(
        {
            "ocid": gold["ocid"],
            "base_value": [0.2, 0.2],
            "f1": gold["f1"],
            "f2": gold["f2"],
        }
    )
    gold.to_parquet(gold_path, index=False)
    shap.to_parquet(shap_path, index=False)
    joblib.dump({"model": _HGBWrapper()}, hgb_path)

    payload = integrity.persisted_shap_release_payload(
        shap_path,
        gold_path,
        expected_features=["f1", "f2"],
        hgb_path=hgb_path,
    )

    assert payload["passed"] is True
    additivity = next(
        item
        for item in payload["expectations"]
        if item["name"] == "rule_proxy_raw_output_additivity"
    )
    assert additivity["passed"] is True
    assert additivity["observed"]["max_absolute_delta"] == pytest.approx(0.0)


@pytest.mark.parametrize("tamper", ["ocid_order", "columns", "rows", "nonfinite", "nonnumeric"])
def test_persisted_shap_release_dq_rejects_semantic_tampering(tmp_path, monkeypatch, tamper):
    monkeypatch.setattr(integrity.paths, "DATA", tmp_path)
    gold_path = tmp_path / "gold" / "tender_summary.parquet"
    shap_path = tmp_path / "models" / "shap_values.parquet"
    gold_path.parent.mkdir(parents=True)
    shap_path.parent.mkdir(parents=True)
    gold = pd.DataFrame({"ocid": ["a", "b", "c"]})
    shap = pd.DataFrame(
        {
            "ocid": ["a", "b", "c"],
            "base_value": [0.2, 0.2, 0.2],
            "f1": [0.1, -0.1, 0.0],
            "f2": [0.3, 0.2, -0.2],
        }
    )
    if tamper == "ocid_order":
        shap["ocid"] = ["b", "a", "c"]
    elif tamper == "columns":
        shap = shap[["ocid", "base_value", "f2", "f1"]]
    elif tamper == "rows":
        shap = shap.iloc[:-1]
    elif tamper == "nonfinite":
        shap.loc[1, "f1"] = np.inf
    elif tamper == "nonnumeric":
        shap["f1"] = ["0.1", "-0.1", "0.0"]
    gold.to_parquet(gold_path, index=False)
    shap.to_parquet(shap_path, index=False)

    payload = integrity.persisted_shap_release_payload(
        shap_path, gold_path, expected_features=["f1", "f2"]
    )

    assert payload["passed"] is False
    assert payload["error_count"] >= 1


def test_json_artifacts_reload_with_exact_schema_and_provenance(tmp_path):
    feature_list, report = _json_payloads()
    feature_path = tmp_path / "feature_list.json"
    report_path = tmp_path / "validation_report.json"
    write_json(feature_list, feature_path)
    write_json(report, report_path)

    observed_feature, observed_report = integrity.validate_persisted_json_artifacts(
        feature_path,
        report_path,
        expected_feature_list=feature_list,
        expected_validation_report=report,
        expected_provenance=_provenance(),
        expected_features=["f1", "f2"],
        expected_ensemble_families=["iso"],
        expected_all_families=["iso", "hbos"],
    )

    assert observed_feature == feature_list
    assert observed_report == report


@pytest.mark.parametrize("tamper", ["extra_key", "provenance", "feature_order", "warning"])
def test_json_artifact_reload_rejects_tampering(tmp_path, tamper):
    feature_list, report = _json_payloads()
    expected_feature = dict(feature_list)
    expected_report = dict(report)
    if tamper == "extra_key":
        feature_list["unexpected"] = True
    elif tamper == "provenance":
        report["data_fingerprint"] = "stale"
    elif tamper == "feature_order":
        feature_list["ml_features"] = ["f2", "f1"]
    elif tamper == "warning":
        report["IMPORTANT_metrics_are_faithfulness_to_rules_not_detection"] = False
    feature_path = tmp_path / "feature_list.json"
    report_path = tmp_path / "validation_report.json"
    write_json(feature_list, feature_path)
    write_json(report, report_path)

    with pytest.raises(integrity.MLArtifactIntegrityError):
        integrity.validate_persisted_json_artifacts(
            feature_path,
            report_path,
            expected_feature_list=expected_feature,
            expected_validation_report=expected_report,
            expected_provenance=_provenance(),
            expected_features=["f1", "f2"],
            expected_ensemble_families=["iso"],
            expected_all_families=["iso", "hbos"],
        )


def _write_model_artifacts(tmp_path: Path, *, tamper: str | None = None):
    provenance = _provenance()
    X = pd.DataFrame({"f1": [0.0, 0.2, 0.4], "f2": [0.3, 0.4, 0.5]})
    ocids = pd.Series(["a", "b", "c"])
    scorers = {
        "iso": _LinearScorer(0.0),
        "hbos": _LinearScorer(0.1),
        "knn": _LinearScorer(0.2),
        "ocsvm": _LinearScorer(0.3),
    }
    bundle = {
        "schema_version": integrity.MODEL_BUNDLE_SCHEMA_VERSION,
        "provenance": provenance,
        "scorers": scorers,
        "explainer": _LinearScorer(0.4),
        "ensemble_families": ["iso", "hbos", "knn", "ocsvm"],
    }
    hgb = {
        "schema_version": integrity.HGB_ARTIFACT_SCHEMA_VERSION,
        "family": "hgb",
        "provenance": provenance,
        "model": _LinearScorer(0.4),
    }
    scored = pd.DataFrame(
        {
            "ocid": ocids,
            "iso_score": X["f1"],
            "hbos_score": X["f1"] + 0.1,
            "knn_score": X["f1"] + 0.2,
            "ocsvm_score": X["f1"] + 0.3,
            "hgb_score": X["f1"] + 0.4,
            "rule_score": [0.0, 0.2, 0.4],
            "context_score": [0.1, 0.3, 0.5],
        }
    )
    composition = integrity.compose_hybrid_ensemble(
        scored,
        ["iso", "hbos", "knn", "ocsvm"],
        flag_quantile=integrity.settings().benchmark_flag_quantile,
        minimum_models_agreeing=(integrity.settings().minimum_models_agreeing_for_high_confidence),
    )
    for column in composition.detector_rank_columns:
        scored[column] = composition.detector_ranks[column]
    scored["ensemble_score"] = composition.ensemble_score
    scored["model_agreement_count"] = composition.model_agreement_count
    scored["high_confidence"] = composition.high_confidence
    if tamper == "missing_family":
        bundle["scorers"] = {"iso": scorers["iso"]}
    elif tamper == "provenance":
        hgb["provenance"] = {**provenance, "data_fingerprint": "stale"}
    elif tamper == "detector_score":
        scored["iso_score"] += 0.01
    elif tamper == "hgb_score":
        scored["hgb_score"] += 0.01
    elif tamper == "ensemble_score":
        scored["ensemble_score"] += 0.01
    elif tamper == "rank_score":
        scored["ensemble_rank_iso"] += 0.01
    elif tamper == "agreement":
        scored["model_agreement_count"] += 1
    bundle_path = tmp_path / "champion_models.joblib"
    hgb_path = tmp_path / "hgb_classifier.joblib"
    scored_path = tmp_path / "tender_summary.parquet"
    joblib.dump(bundle, bundle_path)
    joblib.dump(hgb, hgb_path)
    scored.to_parquet(scored_path, index=False)
    return bundle_path, hgb_path, scored_path, X, ocids, provenance


def test_joblib_reload_reproduces_every_persisted_score(tmp_path):
    bundle_path, hgb_path, scored_path, X, ocids, provenance = _write_model_artifacts(tmp_path)

    integrity.validate_persisted_model_artifacts(
        bundle_path,
        hgb_path,
        scored_path,
        X=X,
        expected_ocids=ocids,
        expected_provenance=provenance,
        expected_families=["iso", "hbos", "knn", "ocsvm"],
        expected_ensemble_families=["iso", "hbos", "knn", "ocsvm"],
    )


@pytest.mark.parametrize(
    "tamper",
    [
        "missing_family",
        "provenance",
        "detector_score",
        "hgb_score",
        "ensemble_score",
        "rank_score",
        "agreement",
    ],
)
def test_joblib_reload_rejects_schema_provenance_or_score_tampering(tmp_path, tamper):
    bundle_path, hgb_path, scored_path, X, ocids, provenance = _write_model_artifacts(
        tmp_path, tamper=tamper
    )

    with pytest.raises(integrity.MLArtifactIntegrityError):
        integrity.validate_persisted_model_artifacts(
            bundle_path,
            hgb_path,
            scored_path,
            X=X,
            expected_ocids=ocids,
            expected_provenance=provenance,
            expected_families=["iso", "hbos", "knn", "ocsvm"],
            expected_ensemble_families=["iso", "hbos", "knn", "ocsvm"],
        )


def test_corrupt_joblib_fails_closed(tmp_path):
    bundle_path, hgb_path, scored_path, X, ocids, provenance = _write_model_artifacts(tmp_path)
    bundle_path.write_bytes(b"not-a-joblib")

    with pytest.raises(integrity.MLArtifactIntegrityError, match="not loadable"):
        integrity.validate_persisted_model_artifacts(
            bundle_path,
            hgb_path,
            scored_path,
            X=X,
            expected_ocids=ocids,
            expected_provenance=provenance,
            expected_families=["iso", "hbos", "knn", "ocsvm"],
            expected_ensemble_families=["iso", "hbos", "knn", "ocsvm"],
        )


def test_ml_canonical_contract_and_dag_require_shap_dq():
    contract = canonical_release_contract("ml")
    task = default_dag()["ml"]

    assert SHAP_VALUES_RELEASE_DQ in contract.checks
    assert SHAP_VALUES_RELEASE_DQ in task.outputs
