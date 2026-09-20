"""Validation framework for the anomaly layer.

Internal diagnostics, all written into the JSON report:

1. **Cross-validation** of the supervised classifier (ROC-AUC + PR-AUC
   over k-fold splits).
2. **Stability bootstrap** for unsupervised scorers — fit the model on
   80 % bootstraps repeatedly and measure how often the same OCID stays
   above the review threshold (``stability ∈ [0, 1]``).
3. **Inter-model rank agreement** — Spearman correlation between every pair
   of unsupervised score columns. Correlation describes similarity; without
   outcome labels it cannot show that diversity improves detection.
4. **Calibration** for the supervised model — reliability diagram bins.
5. **Feature-family ablation** — refit deployed detector families on declared
   lower-derived and pre-outcome-field subsets, then compare ranks/top-5 sets.
6. **Vote-quantile sensitivity** — compare review-flag membership at the
   declared 0.90/0.95/0.99 rank cut-offs.

Output lives in ``data/models/validation_report.json`` and is rendered
in the Streamlit "Validation" page.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from ..config import settings
from ..logging import get_logger
from .models import to_model_matrix

log = get_logger("validation")


# =====================================================================
#  cross-validation of the supervised classifier
# =====================================================================
def cross_validate_supervised(
    X: pd.DataFrame,
    rule_score: pd.Series,
    n_splits: int | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stratified k-fold ROC-AUC + PR-AUC.

    ``params`` lets the caller validate the *deployed* hyperparameters
    (e.g. the benchmark's explainer champion) instead of the config
    defaults — the report must describe the model that actually ships.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    cfg = settings()
    p = params or {}
    n_splits = n_splits or cfg.cv_folds
    y = (rule_score >= cfg.rule_label_threshold).astype(int).to_numpy()
    Xn = to_model_matrix(X)

    if y.sum() < n_splits or (1 - y).sum() < n_splits:
        return {
            "n_splits": n_splits,
            "rocauc_mean": None,
            "prauc_mean": None,
            "note": "insufficient class balance for CV",
        }

    effective = {
        "max_depth": p.get("max_depth", cfg.hgb_max_depth),
        "max_iter": p.get("max_iter", cfg.hgb_n_estimators),
        "learning_rate": p.get("learning_rate", 0.08),
    }
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=cfg.random_seed)
    rocs, prs = [], []
    for fold, (tr, te) in enumerate(skf.split(Xn, y)):
        sw = np.where(y[tr] == 1, max((y[tr] == 0).sum() / max((y[tr] == 1).sum(), 1), 1.0), 1.0)
        m = HistGradientBoostingClassifier(
            random_state=cfg.random_seed,
            **effective,
        )
        m.fit(Xn[tr], y[tr], sample_weight=sw)
        proba = m.predict_proba(Xn[te])[:, 1]
        rocs.append(float(roc_auc_score(y[te], proba)))
        prs.append(float(average_precision_score(y[te], proba)))
        log.info("cv.fold", fold=fold, rocauc=rocs[-1], prauc=prs[-1])

    return {
        "n_splits": n_splits,
        "params": effective,
        "rocauc_mean": float(np.mean(rocs)),
        "rocauc_std": float(np.std(rocs)),
        "prauc_mean": float(np.mean(prs)),
        "prauc_std": float(np.std(prs)),
        "rocauc_per_fold": rocs,
        "prauc_per_fold": prs,
    }


# =====================================================================
#  stability bootstrap
# =====================================================================
def stability_bootstrap(
    X: pd.DataFrame,
    scorer_factory,
    n_runs: int | None = None,
    sample_frac: float = 0.8,
    flag_quantile: float | None = None,
) -> dict[str, Any]:
    """Fit *scorer_factory* on bootstraps and report flag stability.

    Flags are the **top-(1-q) quantile set** of each refit's scores, not a
    fixed absolute threshold: every ``score()`` output is min-max-rescaled
    per refit, so an absolute cut like 0.7 would measure renormalisation
    drift rather than model stability.

    Args:
        X: feature matrix.
        scorer_factory: zero-arg factory returning an ``UnsupervisedScorer``.
        n_runs: bootstraps.
        sample_frac: fraction of rows in each bootstrap (with replacement).
        flag_quantile: quantile above which a record counts as flagged
            (default from ``benchmark_flag_quantile``).

    Returns:
        Dict with ``mean_jaccard``, ``mean_top_overlap`` and per-run flag
        counts.
    """
    cfg = settings()
    n_runs = n_runs or cfg.bootstrap_samples
    q = flag_quantile if flag_quantile is not None else cfg.benchmark_flag_quantile
    rng = np.random.default_rng(cfg.random_seed)

    n = len(X)
    sample_n = int(n * sample_frac)
    flagged_sets: list[set[int]] = []

    started = time.time()
    for run in range(n_runs):
        idx = rng.choice(n, size=sample_n, replace=True)
        Xb = X.iloc[idx]
        try:
            scorer = scorer_factory()
            scorer.fit(Xb)
            s = scorer.score(X).to_numpy()
            thr = np.quantile(s, q)
            flagged = set(np.where(s >= thr)[0].tolist())
            flagged_sets.append(flagged)
        except Exception as e:  # noqa: BLE001
            log.warning("bootstrap.run.failed", run=run, error=str(e))

    if len(flagged_sets) < 2:
        return {"runs": len(flagged_sets), "mean_jaccard": None}

    pairs = []
    overlaps = []
    for i in range(len(flagged_sets)):
        for j in range(i + 1, len(flagged_sets)):
            a, b = flagged_sets[i], flagged_sets[j]
            if not a and not b:
                pairs.append(1.0)
                overlaps.append(1.0)
                continue
            inter = len(a & b)
            union = len(a | b)
            pairs.append(inter / max(union, 1))
            overlaps.append(inter / max(min(len(a), len(b)), 1))

    return {
        "runs": len(flagged_sets),
        "sample_frac": sample_frac,
        "flag_quantile": q,
        "mean_flagged_count": float(np.mean([len(s) for s in flagged_sets])),
        "mean_jaccard": float(np.mean(pairs)),
        "mean_top_overlap": float(np.mean(overlaps)),
        "duration_seconds": round(time.time() - started, 2),
    }


# =====================================================================
#  inter-model agreement
# =====================================================================
def inter_model_agreement(scores: pd.DataFrame) -> dict[str, Any]:
    """Spearman correlation matrix + average pairwise correlation."""
    cols = [c for c in scores.columns if c.endswith("_score")]
    if len(cols) < 2:
        return {"models": cols, "mean_spearman": None}
    corr = scores[cols].corr(method="spearman")
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            pairs.append(float(corr.iat[i, j]))
    return {
        "models": cols,
        "spearman_matrix": corr.round(3).to_dict(),
        "mean_pairwise": float(np.mean(pairs)),
        "min_pairwise": float(np.min(pairs)),
        "max_pairwise": float(np.max(pairs)),
        "note": (
            "Pairwise Spearman describes rank similarity among detectors. "
            "Low correlation is diversity, not evidence that the ensemble "
            "reduces false positives or improves detection."
        ),
    }


def rank_vote_quantile_sensitivity(
    member_ranks: pd.DataFrame,
    *,
    minimum_agreement: int,
    declared_quantile: float,
    quantiles: tuple[float, ...] = (0.90, 0.95, 0.99),
) -> dict[str, Any]:
    """Compare rank-vote review sets without treating them as labels."""
    if member_ranks.empty:
        return {
            "status": "not_computable",
            "reason": "no deployed detector ranks",
            "quantiles": {},
        }
    if minimum_agreement < 1 or minimum_agreement > member_ranks.shape[1]:
        return {
            "status": "not_computable",
            "reason": (
                "minimum agreement exceeds the deployed detector count"
                if minimum_agreement > member_ranks.shape[1]
                else "minimum agreement must be positive"
            ),
            "minimum_models_agreeing": minimum_agreement,
            "deployed_model_count": member_ranks.shape[1],
            "quantiles": {},
        }
    declared_votes = (member_ranks >= declared_quantile).sum(axis=1)
    declared_set = set(member_ranks.index[declared_votes >= minimum_agreement].tolist())
    scenarios: dict[str, Any] = {}
    for quantile in quantiles:
        votes = (member_ranks >= quantile).sum(axis=1)
        flagged = set(member_ranks.index[votes >= minimum_agreement].tolist())
        union = declared_set | flagged
        scenarios[f"q{quantile:.2f}"] = {
            "quantile": quantile,
            "flagged_count": len(flagged),
            "flagged_share": round(len(flagged) / max(len(member_ranks), 1), 6),
            "membership_jaccard_vs_declared": (
                round(len(declared_set & flagged) / len(union), 4) if union else 1.0
            ),
        }
    return {
        "status": "rank_membership_sensitivity_only",
        "minimum_models_agreeing": minimum_agreement,
        "declared_quantile": declared_quantile,
        "declared_flagged_count": len(declared_set),
        "quantiles": scenarios,
        "interpretation": (
            "This reports sensitivity of an unlabeled review-set definition. "
            "It is not confidence calibration or detection validation."
        ),
    }


def _top_rank_set(scores: pd.Series, quantile: float = 0.95) -> set[Any]:
    ranks = scores.rank(pct=True, method="average")
    return set(ranks.index[ranks >= quantile].tolist())


def _rank_comparison(reference: pd.Series, candidate: pd.Series) -> dict[str, Any]:
    reference_top = _top_rank_set(reference)
    candidate_top = _top_rank_set(candidate)
    union = reference_top | candidate_top
    correlation = (
        float(reference.corr(candidate, method="spearman")) if len(reference) > 1 else float("nan")
    )
    return {
        "spearman_rank_correlation": (round(correlation, 4) if np.isfinite(correlation) else None),
        "top_5pct_reference_count": len(reference_top),
        "top_5pct_ablation_count": len(candidate_top),
        "top_5pct_overlap_count": len(reference_top & candidate_top),
        "top_5pct_jaccard": (
            round(len(reference_top & candidate_top) / len(union), 4) if union else 1.0
        ),
    }


def deployed_feature_family_ablation(
    X: pd.DataFrame,
    *,
    ensemble_families: list[str],
    family_params: dict[str, dict[str, Any]],
    full_family_scores: pd.DataFrame,
    full_ensemble_score: pd.Series,
    fixed_ensemble_components: pd.DataFrame,
    feature_subsets: dict[str, list[str]],
) -> dict[str, Any]:
    """Refit deployed detectors on declared subsets and compare only ranks.

    This deliberately produces no AUC, precision, or accuracy statistic: the
    snapshot has no independent outcome labels.  The comparison asks only how
    much the deployed review ordering depends on feature families.
    """
    from .detectors import build_scorer

    results: dict[str, Any] = {}
    for subset_name, declared_features in feature_subsets.items():
        features = [feature for feature in declared_features if feature in X.columns]
        missing = sorted(set(declared_features) - set(features))
        subset_result: dict[str, Any] = {
            "declared_features": declared_features,
            "features_used": features,
            "missing_features": missing,
            "families": {},
        }
        if len(features) < 2:
            subset_result.update(
                {
                    "status": "not_computable",
                    "reason": "fewer than two declared features are available",
                }
            )
            results[subset_name] = subset_result
            continue

        ablated_scores: dict[str, pd.Series] = {}
        for family in ensemble_families:
            try:
                scorer = build_scorer(family, family_params[family])
                scorer.fit(X[features])
                score = scorer.score(X[features])
                ablated_scores[family] = score
                subset_result["families"][family] = {
                    "status": "ok",
                    **_rank_comparison(full_family_scores[f"{family}_score"], score),
                }
            except Exception as exc:  # noqa: BLE001 - report feasibility honestly
                subset_result["families"][family] = {
                    "status": "failed",
                    "error": str(exc)[:300],
                }

        if len(ablated_scores) != len(ensemble_families):
            subset_result.update(
                {
                    "status": "partial",
                    "ensemble_comparison": None,
                    "reason": "one or more deployed family refits failed",
                }
            )
        else:
            ablated_frame = pd.DataFrame(ablated_scores, index=X.index)
            detector_ranks = ablated_frame.rank(pct=True)
            ensemble_input = pd.concat([detector_ranks, fixed_ensemble_components], axis=1)
            ablated_ensemble = ensemble_input.mean(axis=1, skipna=False)
            subset_result.update(
                {
                    "status": "ok",
                    "ensemble_comparison": _rank_comparison(full_ensemble_score, ablated_ensemble),
                }
            )
        results[subset_name] = subset_result

    return {
        "status": "rank_stability_only",
        "top_set_definition": "rank percentile >= 0.95",
        "subsets": results,
        "interpretation": (
            "Models were refit on declared feature subsets. Spearman and top-5% "
            "overlap measure ranking dependence on feature families, not model "
            "accuracy, causal importance, or external validation. The "
            "pre-outcome-field subset is still computed on a static full-period "
            "snapshot and therefore does not establish temporal generalization."
        ),
    }


# =====================================================================
#  calibration
# =====================================================================
def calibration_report(
    proba: pd.Series,
    y_true: pd.Series,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Reliability diagram bins for a probabilistic model."""
    p = proba.to_numpy()
    y = y_true.to_numpy()
    edges = np.quantile(p, np.linspace(0, 1, n_bins + 1))
    edges[0] = -1e-9
    edges[-1] = 1.0 + 1e-9
    bins = []
    for i in range(n_bins):
        m = (p > edges[i]) & (p <= edges[i + 1])
        if m.sum() == 0:
            continue
        bins.append(
            {
                "low": float(edges[i]),
                "high": float(edges[i + 1]),
                "n": int(m.sum()),
                "mean_pred": float(p[m].mean()),
                "mean_actual": float(y[m].mean()),
                "abs_gap": abs(float(p[m].mean()) - float(y[m].mean())),
            }
        )
    if not bins:
        return {"bins": [], "ece": None}
    total = sum(b["n"] for b in bins)
    ece = sum(b["abs_gap"] * b["n"] for b in bins) / total
    return {"bins": bins, "ece": ece, "n_bins_used": len(bins)}
