"""Multi-model exploratory anomaly ranking.

Complementary detectors are fitted on one retrospective snapshot. Each models
the observed feature distribution differently, so disagreement is useful for
model diagnostics. Agreement is not calibrated confidence and these scores do
not estimate wrongdoing or an online/forward-looking risk probability.

Detectors
---------
* **Isolation Forest** — random partitioning; cheap, robust to high dim.
* **Local Outlier Factor (LOF)** — local density; catches micro-cluster
  anomalies missed by global methods.
* **Elliptic Envelope** — Gaussian assumption; sensitive to heavy tails.
* **One-Class SVM (RBF)** — non-linear boundary; subsampled because it is
  ``O(n²)`` in training size.
* **HistGradientBoosting** classifier — *supervised* on weak rule labels;
  used only for SHAP explainability in the dashboard. It is not an
  independent detector.

Every scorer bounds its raw output to ``[0, 1]`` (higher = more unusual within
that scorer). Those min-max scales are not intrinsically comparable across
families, so the ensemble converts them to current-snapshot rank percentiles.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.covariance import EllipticEnvelope
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from ..config import settings


# =====================================================================
#  helpers
# =====================================================================
def to_model_matrix(X: pd.DataFrame) -> np.ndarray:
    """Return a dense float matrix with pandas nulls represented as ``NaN``.

    A mixed pandas frame containing a nullable numeric extension dtype (for
    example ``Int64``) is otherwise converted to an ``object`` ndarray and
    retains literal ``pd.NA`` values.  Scikit-learn cannot consistently coerce
    that ``NAType`` at fit/predict boundaries.  Converting explicitly preserves
    honest missingness while giving imputers and NaN-aware estimators their
    canonical IEEE-NaN representation.
    """
    try:
        matrix: np.ndarray = X.to_numpy(dtype=np.float64, na_value=np.nan)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "model feature matrix must contain numeric or nullable-numeric values"
        ) from exc
    if matrix.ndim != 2:
        raise ValueError("model feature matrix must be two-dimensional")
    return matrix


def _impute_scale_pipe() -> Pipeline:
    """Return canonical preprocessing while preserving missingness signals.

    Median imputation alone makes an unavailable value indistinguishable from
    a genuinely median observation.  Appended indicators let every detector
    see that distinction without converting missing awards into numeric zeroes.
    """
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
        ]
    )


def _normalise_scores(raw: np.ndarray) -> np.ndarray:
    """Min-max-normalise raw anomaly scores (already higher = more anomalous)."""
    raw = np.asarray(raw, dtype=float)
    lo, hi = raw.min(), raw.max()
    if hi - lo < 1e-12:
        return np.zeros_like(raw)
    return np.asarray((raw - lo) / (hi - lo), dtype=float)


# =====================================================================
#  Protocol for all unsupervised scorers
# =====================================================================
class UnsupervisedScorer(Protocol):
    name: str

    def fit(self, X: pd.DataFrame) -> UnsupervisedScorer: ...
    def score(self, X: pd.DataFrame) -> pd.Series: ...
    @property
    def fitted(self) -> bool: ...


# =====================================================================
#  Isolation Forest
# =====================================================================
@dataclass
class IsolationForestScorer:
    contamination: float = settings().iso_forest_contamination
    n_estimators: int = settings().iso_forest_n_estimators
    random_state: int = settings().random_seed
    name: str = "iso_forest"
    pipe: Pipeline | None = None

    def fit(self, X: pd.DataFrame) -> IsolationForestScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        iso = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        iso.fit(Xi)
        pipe.steps.append(("model", iso))
        self.pipe = pipe
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None
        Xi = self.pipe[:-1].transform(X)
        raw = -self.pipe.named_steps["model"].score_samples(Xi)
        return pd.Series(_normalise_scores(raw), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.pipe is not None


def fit_isolation_forest(X: pd.DataFrame) -> IsolationForestScorer:
    return IsolationForestScorer().fit(X)


# =====================================================================
#  Local Outlier Factor
# =====================================================================
@dataclass
class LOFScorer:
    n_neighbors: int = settings().lof_n_neighbors
    contamination: float = settings().lof_contamination
    name: str = "lof"
    pipe: Pipeline | None = None
    _train_index: pd.Index | None = None
    _train_raw: np.ndarray | None = None

    def fit(self, X: pd.DataFrame) -> LOFScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        lof = LocalOutlierFactor(
            n_neighbors=self.n_neighbors,
            contamination=self.contamination,
            novelty=True,
            n_jobs=-1,
        )
        lof.fit(Xi)
        pipe.steps.append(("model", lof))
        self.pipe = pipe
        # cache the unbiased in-sample scores sklearn computed at fit time —
        # scoring the training set through score_samples() is explicitly
        # discouraged (each point finds itself as a neighbour, dampening
        # its outlier factor).
        self._train_index = X.index.copy()
        self._train_raw = -lof.negative_outlier_factor_
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None
        if (
            self._train_index is not None
            and len(X) == len(self._train_index)
            and X.index.equals(self._train_index)
        ):
            assert self._train_raw is not None
            return pd.Series(
                _normalise_scores(self._train_raw), index=X.index, name=f"{self.name}_score"
            )
        Xi = self.pipe[:-1].transform(X)
        raw = -self.pipe.named_steps["model"].score_samples(Xi)
        return pd.Series(_normalise_scores(raw), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.pipe is not None


def fit_local_outlier_factor(X: pd.DataFrame) -> LOFScorer:
    return LOFScorer().fit(X)


# =====================================================================
#  Elliptic Envelope
# =====================================================================
@dataclass
class EllipticEnvelopeScorer:
    contamination: float = settings().elliptic_envelope_contamination
    subsample_size: int = 20_000
    variance_retained: float = 0.99
    random_state: int = settings().random_seed
    name: str = "ee"
    pipe: Pipeline | None = None

    def fit(self, X: pd.DataFrame) -> EllipticEnvelopeScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        # The canonical matrix intentionally contains related facts (for
        # example bidder count and its boolean single-bidder derivative), so a
        # raw robust covariance is rank-deficient. Fit in a full-rank PCA
        # subspace and cap the expensive MCD reference sample.
        pca = PCA(n_components=self.variance_retained, svd_solver="full")
        Xi_reduced = pca.fit_transform(Xi)
        pipe.steps.append(("pca", pca))
        if len(Xi_reduced) > self.subsample_size:
            rng = np.random.default_rng(self.random_state)
            idx = rng.choice(len(Xi_reduced), size=self.subsample_size, replace=False)
            Xi_train = Xi_reduced[idx]
        else:
            Xi_train = Xi_reduced
        ee = EllipticEnvelope(
            contamination=self.contamination,
            support_fraction=0.9,
            random_state=self.random_state,
        )
        # FastMCD can emit thousands of determinant-increase RuntimeWarnings
        # while testing candidate subsets on heavy-tailed procurement data.
        # They do not change the fitted result and would otherwise swamp the
        # benchmark log.  Suppress only that known sklearn diagnostic; all
        # other covariance warnings remain visible.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"Determinant has increased.*",
                category=RuntimeWarning,
                module=r"sklearn\.covariance\._robust_covariance",
            )
            ee.fit(Xi_train)
        pipe.steps.append(("model", ee))
        self.pipe = pipe
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None
        Xi = self.pipe[:-1].transform(X)
        raw = -self.pipe.named_steps["model"].score_samples(Xi)
        return pd.Series(_normalise_scores(raw), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.pipe is not None


def fit_elliptic_envelope(X: pd.DataFrame) -> EllipticEnvelopeScorer:
    return EllipticEnvelopeScorer().fit(X)


# =====================================================================
#  One-Class SVM (RBF, subsample-fitted, full-set scored)
# =====================================================================
@dataclass
class OCSVMScorer:
    nu: float = settings().ocsvm_nu
    subsample_size: int = settings().ocsvm_subsample_size
    random_state: int = settings().random_seed
    name: str = "ocsvm"
    pipe: Pipeline | None = None

    def fit(self, X: pd.DataFrame) -> OCSVMScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        if len(Xi) > self.subsample_size:
            rng = np.random.default_rng(self.random_state)
            idx = rng.choice(len(Xi), size=self.subsample_size, replace=False)
            Xi_train = Xi[idx]
        else:
            Xi_train = Xi
        ocsvm = OneClassSVM(kernel="rbf", gamma="scale", nu=self.nu)
        ocsvm.fit(Xi_train)
        pipe.steps.append(("model", ocsvm))
        self.pipe = pipe
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None
        Xi = self.pipe[:-1].transform(X)
        raw = -self.pipe.named_steps["model"].score_samples(Xi)
        return pd.Series(_normalise_scores(raw), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.pipe is not None


def fit_one_class_svm(X: pd.DataFrame) -> OCSVMScorer:
    return OCSVMScorer().fit(X)


# =====================================================================
#  Supervised classifier (weak labels) — for SHAP only
# =====================================================================
@dataclass
class SupervisedScorer:
    """HistGradientBoosting trained against ``rule_score >= threshold``."""

    threshold: float = settings().rule_label_threshold
    n_estimators: int = settings().hgb_n_estimators
    max_depth: int = settings().hgb_max_depth
    learning_rate: float = 0.08
    random_state: int = settings().random_seed
    name: str = "hgb"
    model: HistGradientBoostingClassifier | None = None

    def fit(self, X: pd.DataFrame, rule_score: pd.Series) -> SupervisedScorer:
        y = (rule_score >= self.threshold).astype(int)
        pos = max((y == 1).sum(), 1)
        neg = max((y == 0).sum(), 1)
        sw = np.where(y == 1, neg / pos, 1.0)
        self.model = HistGradientBoostingClassifier(
            max_depth=self.max_depth,
            max_iter=self.n_estimators,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
        )
        self.model.fit(to_model_matrix(X), y, sample_weight=sw)
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.model is not None
        proba = self.model.predict_proba(to_model_matrix(X))[:, 1]
        return pd.Series(proba, index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.model is not None


def fit_supervised_hgb(X: pd.DataFrame, rule_score: pd.Series) -> SupervisedScorer:
    return SupervisedScorer().fit(X, rule_score)
