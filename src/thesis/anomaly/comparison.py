"""Contextual comparison scoring.

Anomaly is a *contextual* concept. A €5 m tender from a small municipality
is unusual; the same value from the Ministry of Infrastructure is routine.
This module produces a single ``context_score ∈ [0, 1]`` summarising how
unusual a tender is relative to:

* its **procuring entity's** snapshot distribution
* the **category** distribution
* the **procurement method** distribution

The score is the maximum absolute z-score across the contextual features
``thesis.domain.features.CONTEXT_FEATURES`` mapped through ``tanh`` to
``[0, 1]``. This bounded descriptive scale enters the deployed hybrid ensemble
directly; only unsupervised detector scores are percentile-rank transformed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional, cast

import numpy as np
import pandas as pd

from ..domain.features import CONTEXT_FEATURES


@dataclass(frozen=True)
class ContextScoreExplanation:
    """Exact reconstruction of the transparent contextual component."""

    drivers: tuple[str, ...]
    signed_z_by_driver: dict[str, float]
    max_absolute_z: float
    reconstructed_score: float


def explain_context_score(
    row: Mapping[str, object],
    *,
    published_score: Optional[float] = None,
    atol: float = 1e-12,
) -> ContextScoreExplanation:
    """Explain which contextual z-score(s) produce ``context_score``.

    Tied maximum absolute z-scores are all returned. Missing values do not
    become zero-valued observations; when every contextual value is missing,
    the aggregate is zero and there is no driver.
    """
    values: dict[str, float] = {}
    for feature in CONTEXT_FEATURES:
        value = row.get(feature)
        if value is None or pd.isna(value):
            continue
        numeric = float(cast(Any, value))
        if not np.isfinite(numeric):
            raise ValueError(f"context feature is non-finite: {feature}")
        values[feature] = numeric
    max_abs = max((abs(value) for value in values.values()), default=0.0)
    drivers = tuple(
        feature
        for feature in CONTEXT_FEATURES
        if feature in values and np.isclose(abs(values[feature]), max_abs, rtol=0.0, atol=atol)
    )
    reconstructed = float(np.tanh(max_abs / 2.0))
    if published_score is not None and not np.isclose(
        reconstructed,
        float(published_score),
        rtol=0.0,
        atol=atol,
    ):
        raise ValueError(
            "published context_score does not match its contextual z-score explanation"
        )
    return ContextScoreExplanation(
        drivers=drivers,
        signed_z_by_driver={feature: values[feature] for feature in drivers},
        max_absolute_z=max_abs,
        reconstructed_score=reconstructed,
    )


def contextual_score(features: pd.DataFrame) -> pd.Series:
    """Aggregate the contextual z-scores into a single ``[0, 1]`` series.

    Procedure:

    1. Collect the contextual z-score columns (all already standardised).
    2. Take the row-wise *maximum absolute value* — the "most unusual
       context" wins.
    3. Pass through ``tanh`` so the final score is bounded in ``[0, 1]``.

    Args:
        features: Output of :func:`thesis.domain.features.build_tender_features`.

    Returns:
        Series indexed like ``features`` with values in ``[0, 1]``.
    """
    cols = [c for c in CONTEXT_FEATURES if c in features.columns]
    if not cols:
        return pd.Series(0.0, index=features.index, name="context_score")

    sub = features[cols].astype(float).abs()
    raw = sub.max(axis=1, skipna=True).fillna(0.0)
    # tanh squashing: max-abs-z=1 -> 0.76, =3 -> 0.995
    return pd.Series(np.tanh(raw / 2.0), index=features.index, name="context_score")
