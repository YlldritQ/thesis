"""Unit tests for the multi-model anomaly scorers."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly import (
    fit_elliptic_envelope,
    fit_isolation_forest,
    fit_local_outlier_factor,
    fit_one_class_svm,
    fit_supervised_hgb,
    shap_values_for,
)


@pytest.fixture
def sample_matrix() -> pd.DataFrame:
    """Synthetic 200×5 numeric matrix with 5 % planted outliers."""
    rng = np.random.default_rng(42)
    n_inliers, n_outliers = 190, 10
    inliers = rng.normal(0, 1, (n_inliers, 5))
    outliers = rng.normal(8, 2, (n_outliers, 5))  # far from the cluster
    X = np.vstack([inliers, outliers])
    return pd.DataFrame(X, columns=[f"f{i}" for i in range(5)])


def test_isolation_forest_round_trip(sample_matrix):
    m = fit_isolation_forest(sample_matrix)
    assert m.fitted
    s = m.score(sample_matrix)
    assert s.between(0.0, 1.0).all()
    # Outliers (last 10 rows) should score above the median
    assert s.iloc[-10:].mean() > s.iloc[:-10].mean()


def test_lof_round_trip(sample_matrix):
    m = fit_local_outlier_factor(sample_matrix)
    s = m.score(sample_matrix)
    assert s.between(0.0, 1.0).all()
    assert len(s) == len(sample_matrix)


def test_elliptic_envelope_round_trip(sample_matrix):
    m = fit_elliptic_envelope(sample_matrix)
    s = m.score(sample_matrix)
    assert s.between(0.0, 1.0).all()


def test_one_class_svm_round_trip(sample_matrix):
    m = fit_one_class_svm(sample_matrix)
    s = m.score(sample_matrix)
    assert s.between(0.0, 1.0).all()


def test_supervised_hgb_round_trip(sample_matrix):
    rule_score = pd.Series(
        # last 10 rows are "anomalous"
        [0.1] * 190 + [0.9] * 10
    )
    m = fit_supervised_hgb(sample_matrix, rule_score)
    proba = m.score(sample_matrix)
    assert proba.between(0.0, 1.0).all()
    assert proba.iloc[-10:].mean() > proba.iloc[:-10].mean()


def test_supervised_hgb_accepts_nullable_numeric_feature(sample_matrix):
    X = sample_matrix.copy()
    X["num_bidders"] = pd.Series(np.arange(len(X)) % 4, dtype="Int64")
    X.loc[[2, 19, 111], "num_bidders"] = pd.NA
    rule_score = pd.Series([0.1] * 190 + [0.9] * 10)

    scorer = fit_supervised_hgb(X, rule_score)
    proba = scorer.score(X)

    assert len(proba) == len(X)
    assert proba.between(0.0, 1.0).all()


def test_shap_boundary_converts_nullable_numeric_feature(monkeypatch):
    X = pd.DataFrame(
        {
            "continuous": [0.1, 0.2, 0.3],
            "num_bidders": pd.Series([1, pd.NA, 2], dtype="Int64"),
        }
    )

    class FakeExplainer:
        expected_value = [0.0, 1.0]

        def __init__(self, model):
            assert model is sentinel_model

        def shap_values(self, values):
            assert values.dtype == np.float64
            assert np.isnan(values[1, 1])
            return [np.zeros_like(values), np.ones_like(values)]

    sentinel_model = object()
    monkeypatch.setitem(sys.modules, "shap", SimpleNamespace(TreeExplainer=FakeExplainer))

    values, base_value = shap_values_for(sentinel_model, X)

    assert values.shape == X.shape
    assert base_value == 1.0


def test_iso_score_constant_input_returns_zeros():
    """Edge case: constant features → no variation → all-zero scores."""
    X = pd.DataFrame(np.zeros((50, 5)), columns=[f"f{i}" for i in range(5)])
    m = fit_isolation_forest(X)
    s = m.score(X)
    # Either all zero or essentially flat — assert no NaN, no out-of-range
    assert not s.isna().any()
    assert s.between(0.0, 1.0).all()
