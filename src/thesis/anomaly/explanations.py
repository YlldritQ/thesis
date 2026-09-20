"""Post-hoc explanation helpers with explicit fidelity boundaries.

The supervised model is **weakly supervised** (its labels are derived
from the rule layer), so SHAP here answers the question:

  "Which features does the model lean on to *approximate* the rule
  layer for *this* procurement record?"

It is an interpretability aid — not an independent detection signal.
It does not explain the deployed unsupervised/hybrid ``ensemble_score``;
that score has a separate exact component decomposition in
``thesis.anomaly.ensemble``. That distinction is reinforced in the dashboard.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .models import to_model_matrix


def shap_values_for(model, X: pd.DataFrame) -> tuple[np.ndarray, float]:
    """Return ``(shap_values, base_value)`` for a sklearn tree classifier.

    Args:
        model: A fitted sklearn tree-based classifier (binary).
        X: Feature matrix to explain.

    Returns:
        Tuple of:
        * ``shap_values``: ``(n_rows, n_features)`` matrix for the positive class.
        * ``base_value``: scalar log-odds expected value for the positive class.
    """
    import shap

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(to_model_matrix(X))
    if isinstance(sv, list):
        sv = sv[1]
    elif sv.ndim == 3:
        sv = sv[..., 1]
    ev = explainer.expected_value
    if hasattr(ev, "__len__") and len(ev) > 1:
        base_value = float(ev[1])
    elif hasattr(ev, "__len__"):
        base_value = float(ev[0])
    else:
        base_value = float(ev)
    return sv, base_value


def top_contributions(
    feature_names: list[str],
    values: np.ndarray,
    k: int = 5,
) -> list[tuple[str, float]]:
    """Return the top-k absolute contributions sorted by magnitude (desc)."""
    order = np.argsort(np.abs(values))[::-1][:k]
    return [(feature_names[i], float(values[i])) for i in order]


def feature_deviation_profile(
    reference: pd.DataFrame,
    row: pd.Series | dict,
    feature_names: list[str],
    *,
    top_k: int = 8,
) -> pd.DataFrame:
    """Describe unusual input values without calling them model attribution.

    Observed numeric values receive a mid-rank percentile over the complete
    released snapshot. Missing inputs are described through their snapshot
    missingness frequency. ``unusualness`` is a sorting aid only; it is not a
    detector contribution and is never included in ``ensemble_score``.
    """
    if top_k < 1:
        raise ValueError("top_k must be positive")
    missing_columns = sorted(set(feature_names).difference(reference.columns))
    if missing_columns:
        raise ValueError(f"reference feature columns are missing: {missing_columns}")

    records: list[dict[str, object]] = []
    for feature in feature_names:
        population = pd.to_numeric(reference[feature], errors="coerce")
        valid = population.dropna()
        missing_rate = float(population.isna().mean())
        observed = row.get(feature)
        if observed is None or pd.isna(observed):
            records.append(
                {
                    "feature": feature,
                    "observed_value": np.nan,
                    "missing": True,
                    "missing_rate": missing_rate,
                    "snapshot_median": float(valid.median()) if len(valid) else np.nan,
                    "percentile": np.nan,
                    "direction": "missing",
                    "unusualness": float(1.0 - missing_rate),
                    "basis": "missingness_frequency",
                }
            )
            continue
        numeric = float(observed)
        if not np.isfinite(numeric):
            raise ValueError(f"record feature is non-finite: {feature}")
        if valid.empty:
            percentile = np.nan
            unusualness = 0.0
            median = np.nan
            direction = "no_reference"
        else:
            less = int((valid < numeric).sum())
            equal = int((valid == numeric).sum())
            percentile = float((less + 0.5 * equal) / len(valid))
            unusualness = float(2.0 * abs(percentile - 0.5))
            median = float(valid.median())
            direction = "high" if percentile > 0.5 else "low" if percentile < 0.5 else "middle"
        records.append(
            {
                "feature": feature,
                "observed_value": numeric,
                "missing": False,
                "missing_rate": missing_rate,
                "snapshot_median": median,
                "percentile": percentile,
                "direction": direction,
                "unusualness": unusualness,
                "basis": "empirical_midrank_percentile",
            }
        )
    profile = pd.DataFrame(records)
    return (
        profile.sort_values(["unusualness", "feature"], ascending=[False, True])
        .head(top_k)
        .reset_index(drop=True)
    )
