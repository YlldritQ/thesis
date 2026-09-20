"""Exploratory snapshot-relative ensemble of anomaly scorers.

Strategy
--------
* Each scorer produces a ``[0, 1]`` score, rank-transformed within the query
  snapshot before detector scores are combined.
* The ensemble averages the detector ranks and any transparent rule/context
  inputs (equal weight by default).
* A separate ``model_agreement_count`` field counts how many *unsupervised*
  detectors place the record in the query snapshot's top 5%. The historical
  ``high_confidence`` column name means rank agreement only; it is not a
  calibrated confidence or false-positive guarantee.

Why average not max?
We deliberately *do not* use ``max`` because that would let any single
detector decide. For a sensitive subject (procurement integrity) we want
several exploratory rankings to contribute before a record is highlighted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

from ..config import settings

HIGH_CONFIDENCE_PER_MODEL_THRESHOLD = 0.95
ENSEMBLE_RANK_METHOD = "average"
ENSEMBLE_RANK_PREFIX = "ensemble_rank_"
ENSEMBLE_FIXED_COMPONENTS = ("rule_score", "context_score")
ENSEMBLE_EXPLANATION_SCHEMA_VERSION = 1


def detector_rank_column(family: str) -> str:
    """Return the persisted percentile-rank column for one detector family."""
    if not family or not family.replace("_", "").isalnum():
        raise ValueError(f"invalid detector family: {family!r}")
    return f"{ENSEMBLE_RANK_PREFIX}{family}"


@dataclass(frozen=True)
class HybridEnsembleComposition:
    """Exact, intrinsically interpretable decomposition of the hybrid score.

    Detector raw scores are converted to percentile ranks over the *complete
    released snapshot*.  Those ranks, ``rule_score`` and ``context_score`` are
    combined with equal weights.  The centered contributions use the complete
    snapshot component means as their reference, so for every record::

        baseline_score + sum(effect_vs_baseline) == ensemble_score

    This explains the arithmetic that produced the published score.  It is not
    a causal explanation, a probability, or evidence that a procurement is
    improper.
    """

    detector_families: tuple[str, ...]
    detector_score_columns: tuple[str, ...]
    detector_rank_columns: tuple[str, ...]
    component_columns: tuple[str, ...]
    detector_ranks: pd.DataFrame
    component_values: pd.DataFrame
    weights: pd.Series
    direct_contributions: pd.DataFrame
    component_baselines: pd.Series
    baseline_score: float
    centered_contributions: pd.DataFrame
    ensemble_score: pd.Series
    model_agreement_count: pd.Series
    high_confidence: pd.Series
    flag_quantile: float
    minimum_models_agreeing: int

    def definition(self) -> dict[str, Any]:
        """Return the versioned, JSON-serialisable explanation contract."""
        return {
            "schema_version": ENSEMBLE_EXPLANATION_SCHEMA_VERSION,
            "target": "ensemble_score",
            "explanation_type": "exact_additive_component_decomposition",
            "aggregation": "equal_weight_arithmetic_mean",
            "rank_scope": "complete_released_snapshot",
            "rank_method": ENSEMBLE_RANK_METHOD,
            "detector_transform": "pandas_percentile_rank",
            "detector_families": list(self.detector_families),
            "detector_score_columns": list(self.detector_score_columns),
            "detector_rank_columns": list(self.detector_rank_columns),
            "fixed_component_columns": list(ENSEMBLE_FIXED_COMPONENTS),
            "component_columns": list(self.component_columns),
            "component_count": len(self.component_columns),
            "weights": {column: float(self.weights[column]) for column in self.component_columns},
            "baseline_kind": "component_mean_over_complete_released_snapshot",
            "component_baselines": {
                column: float(self.component_baselines[column]) for column in self.component_columns
            },
            "baseline_score": self.baseline_score,
            "flag_quantile": self.flag_quantile,
            "minimum_models_agreeing": self.minimum_models_agreeing,
            "interpretation": (
                "Exact arithmetic explanation of the published hybrid score; "
                "not a causal explanation, probability, legal finding, or "
                "independent validation of anomalousness."
            ),
        }

    def explain_record(
        self,
        index: object,
        *,
        published_score: Optional[float] = None,
        atol: float = 1e-12,
    ) -> pd.DataFrame:
        """Return exact per-component values and effects for one record.

        ``published_score`` should be supplied by readers of a persisted scored
        table.  A mismatch fails closed so a filtered/reranked population or a
        mixed release cannot be presented as the explanation of that score.
        """
        if index not in self.component_values.index:
            raise KeyError(f"record index is not in the composed snapshot: {index!r}")
        reconstructed = float(self.ensemble_score.loc[index])
        if published_score is not None and not np.isclose(
            reconstructed,
            float(published_score),
            rtol=0.0,
            atol=atol,
        ):
            raise ValueError(
                "published ensemble_score does not match the complete-snapshot "
                f"explanation (published={published_score}, reconstructed={reconstructed})"
            )
        rows = []
        for column in self.component_columns:
            component_type = "detector_rank"
            family = None
            if column in ENSEMBLE_FIXED_COMPONENTS:
                component_type = "rule" if column == "rule_score" else "context"
            else:
                family = column.removeprefix(ENSEMBLE_RANK_PREFIX)
            rows.append(
                {
                    "component": column,
                    "component_type": component_type,
                    "detector_family": family,
                    "value_in_formula": float(self.component_values.at[index, column]),
                    "weight": float(self.weights[column]),
                    "direct_contribution": float(self.direct_contributions.at[index, column]),
                    "baseline": float(self.component_baselines[column]),
                    "effect_vs_baseline": float(self.centered_contributions.at[index, column]),
                }
            )
        explanation = pd.DataFrame(rows)
        direct_total = float(explanation["direct_contribution"].sum())
        centered_total = self.baseline_score + float(explanation["effect_vs_baseline"].sum())
        if not (
            np.isclose(direct_total, reconstructed, rtol=0.0, atol=atol)
            and np.isclose(centered_total, reconstructed, rtol=0.0, atol=atol)
        ):
            raise RuntimeError("ensemble component explanation failed exact additivity")
        return explanation


def _validated_numeric_frame(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    label: str,
) -> pd.DataFrame:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{label} columns are missing: {missing}")
    values = frame[list(columns)].apply(pd.to_numeric, errors="coerce")
    matrix = values.to_numpy(dtype=np.float64, na_value=np.nan)
    if not np.isfinite(matrix).all():
        raise ValueError(f"{label} contains null, non-numeric, or non-finite values")
    outside = (matrix < 0.0) | (matrix > 1.0)
    if outside.any():
        raise ValueError(f"{label} must be bounded in [0, 1]")
    return values.astype(float)


def compose_hybrid_ensemble(
    scored_snapshot: pd.DataFrame,
    detector_families: Sequence[str],
    *,
    flag_quantile: float = HIGH_CONFIDENCE_PER_MODEL_THRESHOLD,
    minimum_models_agreeing: int = 3,
) -> HybridEnsembleComposition:
    """Compose and exactly decompose the deployed hybrid anomaly ranking.

    The input must be the complete scored snapshot.  Computing ranks on a
    filtered subset changes the estimand and will not reconstruct the persisted
    score; callers should verify it through :meth:`explain_record`.
    """
    families = tuple(detector_families)
    if not families:
        raise ValueError("at least one detector family is required")
    if len(set(families)) != len(families):
        raise ValueError("detector families must be unique and ordered")
    if not 0.0 < float(flag_quantile) <= 1.0:
        raise ValueError("flag_quantile must be in (0, 1]")
    if minimum_models_agreeing < 1 or minimum_models_agreeing > len(families):
        raise ValueError("minimum_models_agreeing must be within detector family count")

    score_columns = tuple(f"{family}_score" for family in families)
    raw_scores = _validated_numeric_frame(
        scored_snapshot,
        score_columns,
        label="detector score",
    )
    fixed = _validated_numeric_frame(
        scored_snapshot,
        ENSEMBLE_FIXED_COMPONENTS,
        label="fixed ensemble component",
    )
    rank_columns = tuple(detector_rank_column(family) for family in families)
    detector_ranks = raw_scores.rank(method=ENSEMBLE_RANK_METHOD, pct=True)
    detector_ranks.columns = list(rank_columns)
    component_values = pd.concat([detector_ranks, fixed], axis=1)
    component_columns = tuple(component_values.columns)
    weight = 1.0 / len(component_columns)
    weights = pd.Series(weight, index=component_columns, dtype=float)
    direct = component_values.mul(weights, axis="columns")
    ensemble_score = direct.sum(axis=1, min_count=len(component_columns)).rename("ensemble_score")
    baselines = component_values.mean(axis=0)
    baseline_score = float((baselines * weights).sum())
    centered = component_values.sub(baselines, axis="columns").mul(weights, axis="columns")
    centered_reconstruction = baseline_score + centered.sum(axis=1)
    if not np.allclose(
        centered_reconstruction.to_numpy(dtype=float),
        ensemble_score.to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-12,
    ):
        raise RuntimeError("centered ensemble decomposition is not additive")

    agreement = (detector_ranks >= flag_quantile).sum(axis=1).astype(int)
    high_confidence = (agreement >= minimum_models_agreeing).astype(int)
    return HybridEnsembleComposition(
        detector_families=families,
        detector_score_columns=score_columns,
        detector_rank_columns=rank_columns,
        component_columns=component_columns,
        detector_ranks=detector_ranks,
        component_values=component_values,
        weights=weights,
        direct_contributions=direct,
        component_baselines=baselines,
        baseline_score=baseline_score,
        centered_contributions=centered,
        ensemble_score=ensemble_score,
        model_agreement_count=agreement,
        high_confidence=high_confidence,
        flag_quantile=float(flag_quantile),
        minimum_models_agreeing=minimum_models_agreeing,
    )


def validate_ensemble_definition(
    definition: Mapping[str, Any],
    composition: HybridEnsembleComposition,
    *,
    atol: float = 1e-12,
) -> None:
    """Fail when persisted XAI metadata contradicts recomputed composition."""
    expected = composition.definition()
    numeric_scalars = {"baseline_score", "flag_quantile"}
    numeric_mappings = {"weights", "component_baselines"}
    for key, expected_value in expected.items():
        if key not in definition:
            raise ValueError(f"persisted ensemble explanation is missing {key}")
        observed = definition[key]
        if key in numeric_scalars:
            if not np.isclose(float(observed), float(expected_value), rtol=0.0, atol=atol):
                raise ValueError(f"persisted ensemble explanation has stale {key}")
        elif key in numeric_mappings:
            if not isinstance(observed, Mapping) or set(observed) != set(expected_value):
                raise ValueError(f"persisted ensemble explanation has invalid {key}")
            if any(
                not np.isclose(
                    float(observed[column]),
                    float(expected_value[column]),
                    rtol=0.0,
                    atol=atol,
                )
                for column in expected_value
            ):
                raise ValueError(f"persisted ensemble explanation has stale {key}")
        elif observed != expected_value:
            raise ValueError(f"persisted ensemble explanation is inconsistent at {key}")
    extra = sorted(set(definition).difference(expected))
    if extra:
        raise ValueError(f"persisted ensemble explanation has extra fields: {extra}")


@dataclass
class EnsembleScorer:
    """Holds several fitted scorers and produces a combined score."""

    scorers: list = field(default_factory=list)
    weights: dict[str, float] | None = None

    def add(self, scorer) -> EnsembleScorer:  # noqa: ANN001
        self.scorers.append(scorer)
        return self

    def score_each(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.scorers:
            raise RuntimeError("EnsembleScorer is empty")
        cols = [s.score(X) for s in self.scorers]
        return pd.concat(cols, axis=1)

    def score_combined(
        self,
        X: pd.DataFrame,
        rule_score: pd.Series | None = None,
        context_score: pd.Series | None = None,
    ) -> pd.DataFrame:
        per = self.score_each(X)
        if rule_score is not None:
            per["rule_score"] = rule_score.values
        if context_score is not None:
            per["context_score"] = context_score.values

        # Detector scales are estimator-specific. Convert only unsupervised
        # scores to ranks within this query snapshot before averaging; rule and
        # context retain their documented scales.
        unsup_cols = [
            c
            for c in per.columns
            if c.endswith("_score") and c not in ("rule_score", "context_score", "hgb_score")
        ]
        combined = per.copy()
        combined[unsup_cols] = per[unsup_cols].rank(
            method=ENSEMBLE_RANK_METHOD,
            pct=True,
        )

        # ensemble = weighted average over all available columns
        weights = self.weights or dict.fromkeys(per.columns, 1.0)
        cols = [c for c in per.columns if c in weights]
        if not cols:
            raise ValueError("ensemble weights do not select any score columns")
        w = np.array([weights[c] for c in cols], dtype=float)
        if not np.isfinite(w).all() or (w < 0.0).any() or float(w.sum()) <= 0.0:
            raise ValueError("ensemble weights must be finite, non-negative, and sum above zero")
        w = w / w.sum()
        values = _validated_numeric_frame(combined, cols, label="ensemble component")
        ensemble = (values.to_numpy(dtype=float) * w).sum(axis=1)

        # agreement: how many unsupervised model scores cross the per-model threshold
        agreement = (
            (combined[unsup_cols] >= HIGH_CONFIDENCE_PER_MODEL_THRESHOLD).sum(axis=1)
            if unsup_cols
            else pd.Series(0, index=per.index)
        )

        per["ensemble_score"] = ensemble
        per["model_agreement_count"] = agreement.astype(int)
        per["high_confidence"] = (
            agreement >= settings().minimum_models_agreeing_for_high_confidence
        ).astype(int)
        return per


def combine_scores(score_columns: Sequence[pd.Series]) -> pd.Series:
    """Equal-weight average of any number of [0, 1] score series."""
    if not score_columns:
        raise ValueError("at least one score series required")
    df = pd.concat(score_columns, axis=1).fillna(0.0)
    return df.mean(axis=1).rename("ensemble_score")
