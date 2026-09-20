"""Publication-safety regressions for the ML pipeline stage."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.domain.features import ML_FEATURES
from thesis.pipeline import ml


class _Scorer:
    model = object()

    def fit(self, X, y=None):
        return self

    def score(self, X):
        return pd.Series(np.linspace(0.0, 1.0, len(X)), index=X.index)


class _DQFailure:
    passed = False
    error_count = 1
    warning_count = 0

    def __init__(self):
        self.written = False

    def write(self):
        self.written = True

    def release_payload(self, artifact, frame):
        return {
            "passed": self.passed,
            "rows": len(frame),
            "columns": frame.shape[1],
            "release_binding": {"artifact_path": str(artifact)},
        }


class _DQPass(_DQFailure):
    passed = True
    error_count = 0


def _complete_champions(*, ensemble: list[str] | None = None) -> dict:
    return {
        "schema_version": ml.CHAMPIONS_SCHEMA_VERSION,
        "created_at": "2026-07-18T00:00:00+00:00",
        "implementation_fingerprint": "implementation-fixture",
        "_verified_semantic_fingerprint": "semantic-fixture",
        "model_election_sensitivity": {"status": "rank_sensitivity_only"},
        "unsupervised": {family: {"params": {}} for family in ml.FAMILY_REGISTRY},
        "ensemble_families": ensemble or ["pca", "iso", "hbos", "knn"],
        "explainer": {"params": {"max_depth": 3, "learning_rate": 0.05, "max_iter": 20}},
    }


def test_gold_dq_failure_prevents_all_ml_publication(monkeypatch):
    n = 6
    features = pd.DataFrame({name: np.arange(n, dtype=float) for name in ML_FEATURES})
    features.insert(0, "ocid", [f"ocid-{i}" for i in range(n)])
    features["rule_score"] = [0.0, 0.8, 0.0, 0.8, 0.0, 0.8]
    features["year"] = 2023
    dq_failure = _DQFailure()
    publications = []

    monkeypatch.setattr(ml, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        ml,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="a" * 64),
    )
    monkeypatch.setattr(ml, "load_gold_features", lambda: features)
    monkeypatch.setattr(
        ml,
        "_load_champions",
        lambda X, score, years: _complete_champions(),
    )
    monkeypatch.setattr(ml, "build_scorer", lambda family, params: _Scorer())
    monkeypatch.setattr(ml, "SupervisedScorer", lambda **kwargs: _Scorer())
    monkeypatch.setattr(
        ml,
        "contextual_score",
        lambda frame: pd.Series(0.0, index=frame.index),
    )
    monkeypatch.setattr(ml, "run_suite", lambda suite, frame: dq_failure)
    monkeypatch.setattr(
        ml,
        "write_parquet",
        lambda *args, **kwargs: publications.append("parquet"),
    )
    monkeypatch.setattr(
        ml,
        "write_json",
        lambda *args, **kwargs: publications.append("json"),
    )
    monkeypatch.setattr(
        ml,
        "write_joblib",
        lambda *args, **kwargs: publications.append("joblib"),
    )

    with pytest.raises(ValueError, match="before publication"):
        ml.run()

    assert dq_failure.written
    assert publications == []


def test_ml_reports_deployed_family_stability_and_bundle_provenance(monkeypatch):
    n = 6
    features = pd.DataFrame({name: np.arange(n, dtype=float) for name in ML_FEATURES})
    features.insert(0, "ocid", [f"ocid-{i}" for i in range(n)])
    features["rule_score"] = 0.0
    features["year"] = 2023
    champions = _complete_champions()
    champions["unsupervised"]["pca"]["params"] = {"n_components": 5}
    champions["unsupervised"]["iso"]["params"] = {"n_estimators": 100}
    dq_pass = _DQPass()
    stability_scorers = []
    written_json = {}
    written_joblib = {}
    released = {}

    def fake_build_scorer(family, params):
        scorer = _Scorer()
        scorer.family = family
        scorer.params = params
        return scorer

    def fake_stability(X, factory, **kwargs):
        del X, kwargs
        scorer = factory()
        stability_scorers.append(scorer)
        return {"runs": 2, "mean_jaccard": 0.75, "mean_top_overlap": 0.8}

    monkeypatch.setattr(ml, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        ml,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="a" * 64),
    )
    monkeypatch.setattr(ml, "load_gold_features", lambda: features)
    monkeypatch.setattr(ml, "_load_champions", lambda X, score, years: champions)
    monkeypatch.setattr(ml, "build_scorer", fake_build_scorer)
    monkeypatch.setattr(ml, "SupervisedScorer", lambda **kwargs: _Scorer())
    monkeypatch.setattr(
        ml,
        "contextual_score",
        lambda frame: pd.Series(0.0, index=frame.index),
    )
    monkeypatch.setattr(ml, "run_suite", lambda suite, frame: dq_pass)
    monkeypatch.setattr(
        ml,
        "shap_values_for",
        lambda model, X: (np.zeros((len(X), len(ML_FEATURES))), 0.0),
    )
    monkeypatch.setattr(
        ml,
        "cross_validate_supervised",
        lambda X, score, params: {"rocauc_mean": None, "note": "fixture"},
    )
    monkeypatch.setattr(ml, "stability_bootstrap", fake_stability)
    monkeypatch.setattr(ml, "inter_model_agreement", lambda scores: {"models": []})
    monkeypatch.setattr(
        ml,
        "rank_vote_quantile_sensitivity",
        lambda *args, **kwargs: {"status": "rank_membership_sensitivity_only"},
    )
    monkeypatch.setattr(
        ml,
        "deployed_feature_family_ablation",
        lambda *args, **kwargs: {"status": "rank_stability_only"},
    )
    monkeypatch.setattr(
        ml,
        "persisted_shap_release_payload",
        lambda *args, **kwargs: {
            "passed": True,
            "error_count": 0,
            "release_binding": {"artifact_path": str(ml.SHAP_VALUES)},
        },
    )
    monkeypatch.setattr(ml, "validate_persisted_json_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(ml, "validate_persisted_model_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(ml, "_OBSOLETE_MODEL_PATHS", ())
    monkeypatch.setattr(
        ml,
        "publish_release",
        lambda *args, **kwargs: released.update(kwargs),
    )
    monkeypatch.setattr(
        ml,
        "write_json",
        lambda payload, path: written_json.__setitem__(path, payload),
    )
    monkeypatch.setattr(
        ml,
        "write_joblib",
        lambda payload, path: written_joblib.__setitem__(path, payload),
    )
    monkeypatch.setattr(ml, "write_parquet", lambda *args, **kwargs: None)

    result = ml.run()

    assert result["gold_rows"] == n
    assert [scorer.family for scorer in stability_scorers] == [
        "pca",
        "iso",
        "hbos",
        "knn",
    ]
    assert stability_scorers[0].params["n_components"] == 5
    assert stability_scorers[1].params["n_estimators"] == 100
    report = written_json[ml.MODEL_VALIDATION]
    feature_list = written_json[ml.FEATURE_LIST]
    release_dq = written_json[ml.GOLD_TENDERS_RELEASE_DQ]
    shap_release_dq = written_json[ml.SHAP_VALUES_RELEASE_DQ]
    bundle = written_joblib[ml.CHAMPION_MODELS]
    hgb_artifact = written_joblib[ml.HGB_MODEL]
    assert set(report["stability_by_ensemble_family"]) == {"pca", "iso", "hbos", "knn"}
    assert report["benchmark_complete"] is True
    assert report["data_fingerprint"] == feature_list["data_fingerprint"]
    assert bundle["provenance"] == {key: report[key] for key in bundle["provenance"]}
    assert hgb_artifact["provenance"] == bundle["provenance"]
    assert hgb_artifact["family"] == "hgb"
    assert report["benchmark_implementation_fingerprint"] == "implementation-fixture"
    assert report["benchmark_semantic_fingerprint"] == "semantic-fixture"
    assert report["model_election_sensitivity"]["status"] == "rank_sensitivity_only"
    assert report["deployed_score_feature_ablation"]["status"] == "rank_stability_only"
    assert report["ensemble_explanation"]["target"] == "ensemble_score"
    assert report["ensemble_explanation"]["component_count"] == 6
    assert report["shap_explanation"]["does_not_explain"] == "ensemble_score"
    assert feature_list["ensemble_explanation"] == report["ensemble_explanation"]
    assert release_dq["release_binding"]["artifact_path"] == str(ml.GOLD_TENDERS)
    assert shap_release_dq["passed"] is True
    assert released["checks"] == [ml.GOLD_TENDERS_RELEASE_DQ, ml.SHAP_VALUES_RELEASE_DQ]
    assert released["expected_input_manifest_sha256"][ml.GOLD_RELEASE] == "a" * 64
    assert released["expected_input_manifest_sha256"][ml.BENCHMARK_RELEASE] == "a" * 64
