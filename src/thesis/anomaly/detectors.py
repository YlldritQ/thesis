"""Additional unsupervised detectors + the ``build_scorer`` factory.

Extends the four core detectors in :mod:`thesis.anomaly.models` with four
more families so the benchmark compares **eight** complementary views of
normality:

* **PCA reconstruction error** — linear-subspace normality; records far
  from the principal subspace score high.
* **Gaussian Mixture (GMM)** — parametric multi-modal density; low
  log-likelihood scores high.
* **KNN distance** — distance to the k-th nearest neighbour; classic
  non-parametric global detector.
* **HBOS** — histogram-based outlier score; assumes feature
  independence, extremely fast, surprisingly competitive baseline.

Every scorer follows the same protocol as the core four: ``fit(X)``,
``score(X) -> Series in [0, 1]`` (higher = more anomalous), ``name``,
``fitted``. All share the canonical ``impute -> scale`` preprocessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline

from ..config import settings
from .models import (
    EllipticEnvelopeScorer,
    IsolationForestScorer,
    LOFScorer,
    OCSVMScorer,
    _impute_scale_pipe,
    _normalise_scores,
)


# =====================================================================
#  PCA reconstruction error
# =====================================================================
@dataclass
class PCAReconstructionScorer:
    n_components: int = 10
    random_state: int = settings().random_seed
    name: str = "pca"
    pipe: Pipeline | None = None
    pca: PCA | None = None

    def fit(self, X: pd.DataFrame) -> PCAReconstructionScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        n_comp = min(self.n_components, Xi.shape[1] - 1, max(1, Xi.shape[0] - 1))
        pca = PCA(n_components=n_comp, random_state=self.random_state)
        pca.fit(Xi)
        self.pipe = pipe
        self.pca = pca
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None and self.pca is not None
        Xi = self.pipe.transform(X)
        recon = self.pca.inverse_transform(self.pca.transform(Xi))
        err = np.square(Xi - recon).sum(axis=1)
        return pd.Series(_normalise_scores(err), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.pca is not None


# =====================================================================
#  Gaussian Mixture negative log-likelihood
# =====================================================================
@dataclass
class GMMScorer:
    n_components: int = 4
    covariance_type: str = "full"
    random_state: int = settings().random_seed
    name: str = "gmm"
    pipe: Pipeline | None = None
    gmm: GaussianMixture | None = None

    def fit(self, X: pd.DataFrame) -> GMMScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        gmm = GaussianMixture(
            n_components=max(1, min(self.n_components, len(Xi) // 2)),
            covariance_type=self.covariance_type,
            random_state=self.random_state,
            reg_covar=1e-4,
            max_iter=200,
        )
        gmm.fit(Xi)
        self.pipe = pipe
        self.gmm = gmm
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None and self.gmm is not None
        Xi = self.pipe.transform(X)
        raw = -self.gmm.score_samples(Xi)  # higher = less likely = more anomalous
        return pd.Series(_normalise_scores(raw), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.gmm is not None


# =====================================================================
#  k-th nearest-neighbour distance
# =====================================================================
@dataclass
class KNNDistanceScorer:
    n_neighbors: int = 10
    subsample_size: int = 30_000  # reference set cap; kNN query cost is O(n·log m)
    random_state: int = settings().random_seed
    name: str = "knn"
    pipe: Pipeline | None = None
    nn: NearestNeighbors | None = None
    _ref_is_subsample: bool = False
    _reference_index: pd.Index | None = None

    def fit(self, X: pd.DataFrame) -> KNNDistanceScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        if len(Xi) > self.subsample_size:
            rng = np.random.default_rng(self.random_state)
            idx = rng.choice(len(Xi), size=self.subsample_size, replace=False)
            Xi_ref = Xi[idx]
            self._reference_index = X.index[idx].copy()
            self._ref_is_subsample = True
        else:
            Xi_ref = Xi
            self._reference_index = X.index.copy()
            self._ref_is_subsample = False
        # clamp so tiny datasets (tests, quick modes) don't crash
        k_eff = max(1, min(self.n_neighbors + 1, len(Xi_ref)))
        nn = NearestNeighbors(n_neighbors=k_eff, n_jobs=-1)
        nn.fit(Xi_ref)
        self.pipe = pipe
        self.nn = nn
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None and self.nn is not None
        Xi = self.pipe.transform(X)
        dist, _ = self.nn.kneighbors(Xi)
        if dist.shape[1] == 1:
            raw = dist[:, 0]
        else:
            # k-th NON-SELF neighbour, per row.  Membership is determined from
            # the fitted reference index, not a zero distance: an unseen query
            # can legitimately duplicate a reference vector and have distance
            # zero without being the reference row itself.
            assert self._reference_index is not None
            self_hit = X.index.isin(self._reference_index)
            raw = np.where(self_hit, dist[:, -1], dist[:, -2])
        return pd.Series(_normalise_scores(raw), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return self.nn is not None


# =====================================================================
#  HBOS — histogram-based outlier score
# =====================================================================
@dataclass
class HBOSScorer:
    n_bins: int = 20
    name: str = "hbos"
    pipe: Pipeline | None = None
    edges_: list[np.ndarray] = field(default_factory=list)
    log_density_: list[np.ndarray] = field(default_factory=list)

    def fit(self, X: pd.DataFrame) -> HBOSScorer:
        pipe = _impute_scale_pipe()
        Xi = pipe.fit_transform(X)
        self.edges_, self.log_density_ = [], []
        n = Xi.shape[0]
        for j in range(Xi.shape[1]):
            col = Xi[:, j]
            edges = np.histogram_bin_edges(col, bins=self.n_bins)
            counts, _ = np.histogram(col, bins=edges)
            density = counts / max(n, 1)
            # epsilon floor so empty bins don't produce inf
            log_density = np.log(np.maximum(density, 1e-9))
            self.edges_.append(edges)
            self.log_density_.append(log_density)
        self.pipe = pipe
        return self

    def score(self, X: pd.DataFrame) -> pd.Series:
        assert self.pipe is not None and self.edges_
        Xi = self.pipe.transform(X)
        total = np.zeros(Xi.shape[0])
        for j in range(Xi.shape[1]):
            edges = self.edges_[j]
            outside_support = (Xi[:, j] < edges[0]) | (Xi[:, j] > edges[-1])
            idx = np.clip(
                np.searchsorted(edges, Xi[:, j], side="right") - 1, 0, len(self.log_density_[j]) - 1
            )
            contribution = -self.log_density_[j][idx]  # rare bin -> high score
            # A value beyond the fitted support is not evidence for the edge
            # bin's empirical density.  Assign the declared epsilon tail mass
            # instead of silently clipping an arbitrarily extreme value into a
            # potentially common boundary bin.
            contribution[outside_support] = -np.log(1e-12)
            total += contribution
        return pd.Series(_normalise_scores(total), index=X.index, name=f"{self.name}_score")

    @property
    def fitted(self) -> bool:
        return bool(self.edges_)


# =====================================================================
#  Factory
# =====================================================================

# family -> (class, whether refits vary with random seed)
FAMILY_REGISTRY: dict[str, tuple[type, bool]] = {
    "iso": (IsolationForestScorer, True),
    "lof": (LOFScorer, False),
    "ee": (EllipticEnvelopeScorer, True),
    "ocsvm": (OCSVMScorer, True),
    # PCA(svd_solver="auto") may select the randomized solver, so its seed is
    # part of the benchmark's repeatability audit even when small inputs happen
    # to select a deterministic solver.
    "pca": (PCAReconstructionScorer, True),
    "gmm": (GMMScorer, True),
    "knn": (KNNDistanceScorer, True),  # subsample choice is seeded
    "hbos": (HBOSScorer, False),
}

# Human-readable Albanian names for reports / UI
FAMILY_LABELS_SQ: dict[str, str] = {
    "iso": "Isolation Forest",
    "lof": "Local Outlier Factor (LOF)",
    "ee": "Elliptic Envelope",
    "ocsvm": "One-Class SVM",
    "pca": "Gabimi i rindërtimit PCA",
    "gmm": "Gaussian Mixture (GMM)",
    "knn": "Distanca KNN",
    "hbos": "HBOS (histogram)",
}


def build_scorer(family: str, params: dict[str, Any] | None = None):
    """Instantiate a scorer from ``family`` + hyperparameters.

    Unknown parameter keys raise immediately (typo protection), which
    matters when parameters come from ``champions.json``.
    """
    if family not in FAMILY_REGISTRY:
        raise KeyError(
            f"unknown detector family: {family!r}; expected one of {sorted(FAMILY_REGISTRY)}"
        )
    cls, _ = FAMILY_REGISTRY[family]
    return cls(**(params or {}))


def family_is_stochastic(family: str) -> bool:
    return FAMILY_REGISTRY[family][1]
