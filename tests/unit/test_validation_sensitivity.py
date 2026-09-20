"""Rank-only sensitivity diagnostics must stay label-free and deterministic."""

from __future__ import annotations

import numpy as np
import pandas as pd

from thesis.anomaly import detectors
from thesis.anomaly.validation import (
    cross_validate_supervised,
    deployed_feature_family_ablation,
    rank_vote_quantile_sensitivity,
)


def test_rank_vote_sensitivity_reports_declared_quantiles_without_accuracy_claims():
    ranks = pd.DataFrame(
        {
            "a": np.linspace(0.01, 1.0, 100),
            "b": np.linspace(1.0, 0.01, 100),
            "c": np.linspace(0.01, 1.0, 100),
            "d": np.linspace(0.01, 1.0, 100),
        }
    )
    report = rank_vote_quantile_sensitivity(
        ranks,
        minimum_agreement=3,
        declared_quantile=0.95,
    )
    assert list(report["quantiles"]) == ["q0.90", "q0.95", "q0.99"]
    assert (
        report["quantiles"]["q0.90"]["flagged_count"]
        >= report["quantiles"]["q0.95"]["flagged_count"]
    )
    assert report["quantiles"]["q0.95"]["membership_jaccard_vs_declared"] == 1.0
    assert "not confidence calibration" in report["interpretation"]


def test_deployed_feature_ablation_refits_and_reports_only_rank_stability(monkeypatch):
    class Scorer:
        def fit(self, X):
            self.columns = list(X.columns)
            return self

        def score(self, X):
            return pd.Series(X.sum(axis=1), index=X.index)

    monkeypatch.setattr(detectors, "build_scorer", lambda family, params: Scorer())
    X = pd.DataFrame(
        {
            "fact_a": np.arange(20, dtype=float),
            "fact_b": np.arange(20, dtype=float) ** 2,
            "outcome": np.arange(20, dtype=float)[::-1],
        }
    )
    full_family = pd.DataFrame({"iso_score": X.sum(axis=1)}, index=X.index)
    fixed = pd.DataFrame({"rule_score": 0.0, "context_score": 0.0}, index=X.index)
    full_ensemble = pd.concat([full_family.rank(pct=True), fixed], axis=1).mean(axis=1)
    report = deployed_feature_family_ablation(
        X,
        ensemble_families=["iso"],
        family_params={"iso": {}},
        full_family_scores=full_family,
        full_ensemble_score=full_ensemble,
        fixed_ensemble_components=fixed,
        feature_subsets={"raw_fact_only": ["fact_a", "fact_b"]},
    )
    subset = report["subsets"]["raw_fact_only"]
    assert subset["status"] == "ok"
    assert subset["families"]["iso"]["status"] == "ok"
    assert 0.0 <= subset["ensemble_comparison"]["top_5pct_jaccard"] <= 1.0
    assert "accuracy" in report["interpretation"]


def test_cross_validation_accepts_nullable_numeric_feature():
    rng = np.random.default_rng(23)
    n = 120
    signal = rng.normal(size=n)
    X = pd.DataFrame(
        {
            "continuous": signal,
            "num_bidders": pd.Series(rng.integers(0, 5, size=n), dtype="Int64"),
        }
    )
    X.loc[[4, 41, 97], "num_bidders"] = pd.NA
    rule_score = pd.Series(np.where(signal > 0, 0.8, 0.1))

    report = cross_validate_supervised(
        X,
        rule_score,
        n_splits=2,
        params={"max_depth": 2, "max_iter": 10, "learning_rate": 0.1},
    )

    assert report["n_splits"] == 2
    assert np.isfinite(report["rocauc_mean"])
