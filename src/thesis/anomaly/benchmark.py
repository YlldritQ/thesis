"""Rigorous multi-model benchmark for the anomaly layer.

Protokolli (dokumentuar edhe në ``leaderboard.md`` në shqip):

* **8 familje detektorësh të pambikëqyrur** × rrjeta hiperparametrash →
  për secilin konfigurim: AUC ndaj etiketave proxy të rregullave (0.4 dhe
  0.7), precision@K ndaj etiketave strikte, Spearman me ``rule_score``,
  **stabilitet bootstrap** (Jaccard i bashkësive top-5 % mbi ri-përshtatje
  në 80 % mostra), **konsistencë seed-esh** për familjet stokastike,
  dhe kohëzgjatjet e trajnimit/vlerësimit.
* **4 familje klasifikuesish të mbikëqyrur** (etiketa të dobëta nga
  rregullat) → CV e shtresëzuar k-fold × shumë seeds (ROC-AUC, PR-AUC,
  Brier) + **kontroll kohor i besnikërisë ndaj rregullave** (trajno ≤ vitin
  X, testo pas tij) +
  ECE e kalibrimit.

Praktika DE të zbatuara:

* **Checkpoint / resume** — çdo konfigurim i përfunduar shkruhet menjëherë
  në ``results.wip.jsonl``; vetëm zgjedhja e plotë kopjohet atomikisht te
  ``results.jsonl`` i publikueshëm.
* **Gjurmë e të dhënave dhe protokollit** — çdo rresht rezultati mban
  ``data_fingerprint`` mbi vlerat e veçorive, pikët e plota të rregullave,
  vitet, pragjet, rrjetat, seeds dhe parametrat e zgjedhjes; rezultate të një
  gjurme tjetër arkivohen automatikisht, kurrë nuk përzihen.
* **Dështime të izoluara** — një konfigurim që hedh përjashtim regjistrohet
  si ``failed`` me tekstin e gabimit dhe sweep-i vazhdon.
* **Determinizëm** — seeds fikse, të regjistruara në çdo rresht.

Kufizim metodologjik (i deklaruar): etiketat proxy vijnë nga shtresa e
rregullave, kështu metrikat e mbikëqyrura masin *pajtimin me rregullat*,
jo mashtrimin real. Disa veçori kontekstuale llogariten mbi gjithë
periudhën, prandaj validimi jashtë-kohor i proxy-t ka njëfarë rrjedhjeje
informacioni — kjo shënohet e qartë në raport.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import tempfile
import time
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..config import settings
from ..dq.framework import dataframe_fingerprint
from ..jsonutil import dumps_json, json_ready, loads_json
from ..lineage import file_sha256
from ..logging import get_logger, get_run_id
from ..paths import (
    BENCHMARK_LEADERBOARD,
    BENCHMARK_LEADERBOARD_MD,
    BENCHMARK_RELEASE,
    BENCHMARK_RELEASE_DQ,
    BENCHMARK_RESULTS,
    CHAMPIONS,
    GOLD_FEATURES,
    GOLD_RELEASE,
    ensure_dirs,
)
from ..provenance import implementation_fingerprint, implementation_manifest
from ..release import publish_release
from .detectors import FAMILY_LABELS_SQ, build_scorer, family_is_stochastic
from .models import to_model_matrix
from .validation import calibration_report

log = get_logger("benchmark")


# =====================================================================
#  Grids
# =====================================================================


def unsupervised_grid(quick: bool = False) -> list[dict[str, Any]]:
    """Return the (family, params) sweep for the unsupervised detectors."""
    if quick:
        return [
            {"family": "iso", "params": {"n_estimators": 100}},
            {"family": "lof", "params": {"n_neighbors": 10}},
            {"family": "pca", "params": {"n_components": 5}},
            {"family": "hbos", "params": {"n_bins": 20}},
        ]

    grid: list[dict[str, Any]] = []
    # ``contamination`` changes only the estimator's decision threshold, not
    # ``score_samples`` used by this rank benchmark. Sweeping it would create
    # exact duplicate configurations with row-order tie breaking.
    for n_est in [100, 300, 500]:
        grid.append({"family": "iso", "params": {"n_estimators": n_est}})
    for k in [10, 30, 50, 100]:
        grid.append({"family": "lof", "params": {"n_neighbors": k}})
    grid.append({"family": "ee", "params": {}})
    for nu in [0.03, 0.05, 0.10]:
        grid.append({"family": "ocsvm", "params": {"nu": nu}})
    for nc in [5, 10, 15]:
        grid.append({"family": "pca", "params": {"n_components": nc}})
    for nc in [2, 4, 8]:
        grid.append({"family": "gmm", "params": {"n_components": nc}})
    for k in [5, 10, 20]:
        grid.append({"family": "knn", "params": {"n_neighbors": k}})
    for b in [10, 20, 50]:
        grid.append({"family": "hbos", "params": {"n_bins": b}})
    return grid


def supervised_grid(quick: bool = False) -> list[dict[str, Any]]:
    """Return the (family, params) sweep for the supervised classifiers."""
    if quick:
        return [
            {"family": "hgb", "params": {"max_depth": 4, "learning_rate": 0.08, "max_iter": 100}},
            {"family": "logreg", "params": {"C": 1.0}},
        ]

    grid: list[dict[str, Any]] = []
    for depth, lr in product([3, 4, 6], [0.05, 0.08]):
        grid.append(
            {"family": "hgb", "params": {"max_depth": depth, "learning_rate": lr, "max_iter": 300}}
        )
    for rf_depth in [None, 12]:
        grid.append({"family": "rf", "params": {"n_estimators": 200, "max_depth": rf_depth}})
    for c in [0.1, 1.0, 10.0]:
        grid.append({"family": "logreg", "params": {"C": c}})
    grid.append({"family": "extratrees", "params": {"n_estimators": 300}})
    return grid


SUPERVISED_LABELS_SQ = {
    "hgb": "HistGradientBoosting",
    "rf": "Random Forest",
    "logreg": "Regresion Logjistik",
    "extratrees": "Extra Trees",
}

# Included in the benchmark fingerprint so a preprocessing/evaluation change
# cannot silently reuse results computed by older code on identical data.
BENCHMARK_PROTOCOL_VERSION = "2026-07-r6-implementation-bound-semantic-election"

# Version of the *champions artifact contract*.  It remains separate from the
# benchmark protocol even though this revision intentionally invalidates old
# rows: result provenance now binds the exact election implementation.
CHAMPIONS_SCHEMA_VERSION = 2

# The files below can change a checkpoint metric, declared grid, preprocessing,
# feature selection, or election.  Hashing this deliberately narrow set makes
# checkpoint invalidation explainable while the stage release still records the
# full-project implementation fingerprint through :mod:`thesis.release`.
_BENCHMARK_IMPLEMENTATION_PATHS = (
    "src/thesis/anomaly/benchmark.py",
    "src/thesis/anomaly/detectors.py",
    "src/thesis/anomaly/models.py",
    "src/thesis/anomaly/validation.py",
    "src/thesis/domain/features.py",
    "src/thesis/pipeline/benchmark.py",
    "src/thesis/config.py",
    "src/thesis/jsonutil.py",
    "src/thesis/provenance.py",
)

DECLARED_COMPOSITE_WEIGHTS: dict[str, float] = {
    "proxy_auc_07": 0.45,
    "stability_jaccard": 0.35,
    "seed_consistency": 0.20,
}

# These alternatives are sensitivity scenarios only.  They are intentionally
# declared in code and release provenance; none is an outcome-validated choice.
ALTERNATE_COMPOSITE_WEIGHTS: dict[str, dict[str, float]] = {
    "balanced": {
        "proxy_auc_07": 0.34,
        "stability_jaccard": 0.33,
        "seed_consistency": 0.33,
    },
    "stability_emphasis": {
        "proxy_auc_07": 0.30,
        "stability_jaccard": 0.50,
        "seed_consistency": 0.20,
    },
    "proxy_emphasis": {
        "proxy_auc_07": 0.60,
        "stability_jaccard": 0.25,
        "seed_consistency": 0.15,
    },
}


def benchmark_implementation_provenance() -> dict[str, Any]:
    """Return exact hashes for source files that can affect the election."""
    root = settings().project_root.resolve()
    files = [Path(root / relative) for relative in _BENCHMARK_IMPLEMENTATION_PATHS]
    return {
        "fingerprint": implementation_fingerprint(files),
        "manifest": implementation_manifest(files),
    }


def build_classifier(family: str, params: dict[str, Any], seed: int):
    """Instantiate a supervised classifier (with imputation where needed)."""
    if family == "hgb":
        return HistGradientBoostingClassifier(random_state=seed, **params)
    if family == "rf":
        model = RandomForestClassifier(
            random_state=seed, n_jobs=-1, class_weight="balanced", **params
        )
    elif family == "logreg":
        model = LogisticRegression(max_iter=2000, class_weight="balanced", **params)
    elif family == "extratrees":
        model = ExtraTreesClassifier(
            random_state=seed, n_jobs=-1, class_weight="balanced", **params
        )
    else:
        raise KeyError(f"unknown classifier family: {family!r}")
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
            ("scale", StandardScaler()),
            ("model", model),
        ]
    )


# =====================================================================
#  Bookkeeping
# =====================================================================


def config_key(kind: str, family: str, params: dict[str, Any]) -> str:
    payload = dumps_json({"kind": kind, "family": family, "params": params}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def declared_benchmark_contract(quick: bool = False) -> dict[str, Any]:
    """Return the exact configuration/family contract for one election mode."""
    specs = [
        *(("unsupervised", spec) for spec in unsupervised_grid(quick)),
        *(("supervised", spec) for spec in supervised_grid(quick)),
    ]
    keys = [config_key(kind, spec["family"], spec["params"]) for kind, spec in specs]
    return {
        "quick": quick,
        "expected_config_keys": sorted(keys),
        "expected_total": len(keys),
        "expected_unsupervised_total": len(unsupervised_grid(quick)),
        "expected_supervised_total": len(supervised_grid(quick)),
        "expected_unsupervised_families": sorted(
            {spec["family"] for spec in unsupervised_grid(quick)}
        ),
        "expected_supervised_families": sorted({spec["family"] for spec in supervised_grid(quick)}),
    }


def benchmark_completeness(rows: pd.DataFrame, quick: bool = False) -> dict[str, Any]:
    """Audit checkpoint rows against the exact declared election contract.

    A retry supersedes the previous row for the same configuration key.  The
    election is complete only when the latest row for every declared key has a
    valid schema and ``status == 'ok'``, with no undeclared key mixed in.
    """
    contract = declared_benchmark_contract(quick)
    expected_keys = set(contract["expected_config_keys"])

    if rows.empty or "config_key" not in rows.columns:
        latest = pd.DataFrame()
    else:
        latest = rows.drop_duplicates(subset="config_key", keep="last").copy()

    observed_keys = set(latest["config_key"].dropna().astype(str)) if not latest.empty else set()
    missing_keys = expected_keys - observed_keys
    extra_keys = observed_keys - expected_keys
    invalid_keys: set[str] = set()
    failed_keys: set[str] = set()
    successful_keys: set[str] = set()
    successful_unsup_families: set[str] = set()
    successful_sup_families: set[str] = set()
    stale_protocol_keys: set[str] = set()
    expected_provenance = benchmark_result_provenance()

    for _, row in latest.iterrows():
        key = str(row.get("config_key"))
        if key not in expected_keys:
            continue
        kind = row.get("kind")
        family = row.get("family")
        params = row.get("params")
        schema_valid = (
            kind in {"unsupervised", "supervised"}
            and isinstance(family, str)
            and isinstance(params, dict)
            and isinstance(row.get("quick"), (bool, np.bool_))
            and bool(row.get("quick")) == quick
            and config_key(kind, family, params) == key
        )
        if not schema_valid:
            invalid_keys.add(key)
            continue
        if any(row.get(field) != value for field, value in expected_provenance.items()):
            stale_protocol_keys.add(key)
            continue
        if row.get("status") != "ok":
            failed_keys.add(key)
            continue
        successful_keys.add(key)
        if kind == "unsupervised":
            successful_unsup_families.add(family)
        else:
            successful_sup_families.add(family)

    expected_unsup_families = set(contract["expected_unsupervised_families"])
    expected_sup_families = set(contract["expected_supervised_families"])
    complete = (
        not missing_keys
        and not extra_keys
        and not invalid_keys
        and not stale_protocol_keys
        and not failed_keys
        and successful_keys == expected_keys
        and successful_unsup_families == expected_unsup_families
        and successful_sup_families == expected_sup_families
    )
    return {
        **contract,
        "complete": complete,
        "observed_total": len(observed_keys),
        "successful_total": len(successful_keys),
        "successful_config_keys": sorted(successful_keys),
        "missing_config_keys": sorted(missing_keys),
        "extra_config_keys": sorted(extra_keys),
        "invalid_config_keys": sorted(invalid_keys),
        "stale_protocol_config_keys": sorted(stale_protocol_keys),
        "failed_config_keys": sorted(failed_keys),
        "unsupervised_families": sorted(successful_unsup_families),
        "supervised_families": sorted(successful_sup_families),
    }


def benchmark_protocol_provenance() -> dict[str, Any]:
    """Return every non-data input that can change the model election.

    Checkpoint reuse is safe only when the grids, thresholds, resampling
    schedule, seeds, and implementation environment are unchanged.  Keeping
    this structure both hashable and publishable makes that assumption
    auditable in every result row and in ``champions.json``.
    """
    cfg = settings()
    return {
        "protocol_version": BENCHMARK_PROTOCOL_VERSION,
        "library_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "thresholds": {
            "rule_label_threshold": cfg.rule_label_threshold,
            "rule_score_priority_threshold": cfg.rule_score_priority_threshold,
            "benchmark_flag_quantile": cfg.benchmark_flag_quantile,
            "benchmark_precision_at": cfg.benchmark_precision_at,
        },
        "election_settings": {
            "random_seed": cfg.random_seed,
            "benchmark_bootstrap_runs": cfg.benchmark_bootstrap_runs,
            "benchmark_extra_seeds": cfg.benchmark_extra_seeds,
            "benchmark_supervised_seeds": cfg.benchmark_supervised_seeds,
            "benchmark_cv_folds": cfg.benchmark_cv_folds,
            "benchmark_oot_train_max_year": cfg.benchmark_oot_train_max_year,
            "benchmark_top_k_families": cfg.benchmark_top_k_families,
            # Defaults used by grid entries that intentionally specify only
            # parameters that affect ranking rather than estimator thresholds.
            "iso_forest_contamination": cfg.iso_forest_contamination,
            "lof_contamination": cfg.lof_contamination,
            "elliptic_envelope_contamination": (cfg.elliptic_envelope_contamination),
            "ocsvm_subsample_size": cfg.ocsvm_subsample_size,
        },
        "seed_schedule": {
            "base_random_seed": cfg.random_seed,
            "bootstrap_refit_offset": 100,
            "extra_seed_refit_offset": 500,
            "supervised_fold_seed_rule": "base_random_seed + repetition_index",
        },
        "grids": {
            "unsupervised_full": unsupervised_grid(quick=False),
            "supervised_full": supervised_grid(quick=False),
            "unsupervised_quick": unsupervised_grid(quick=True),
            "supervised_quick": supervised_grid(quick=True),
        },
        "model_election": {
            "declared_composite_weights": DECLARED_COMPOSITE_WEIGHTS,
            "alternate_composite_weights": ALTERNATE_COMPOSITE_WEIGHTS,
            "family_tie_break": "config_key ascending",
            "ensemble_tie_break": "family ascending",
            "precision_rank_sensitivity": "precision_at_k descending; config_key ascending",
        },
        "implementation": benchmark_implementation_provenance(),
    }


def _stable_json(value: Any) -> str:
    return dumps_json(value, sort_keys=True)


def benchmark_protocol_fingerprint() -> str:
    """SHA-256 prefix for the complete non-data election protocol."""
    return hashlib.sha256(_stable_json(benchmark_protocol_provenance()).encode()).hexdigest()[:16]


def benchmark_result_provenance() -> dict[str, Any]:
    """Compact protocol/seed fields repeated in each checkpoint row."""
    protocol = benchmark_protocol_provenance()
    return {
        "protocol_version": protocol["protocol_version"],
        "protocol_fingerprint": benchmark_protocol_fingerprint(),
        "random_seed": protocol["election_settings"]["random_seed"],
        "thresholds_json": _stable_json(protocol["thresholds"]),
        "election_settings_json": _stable_json(protocol["election_settings"]),
        "seed_schedule_json": _stable_json(protocol["seed_schedule"]),
        "grids_sha256": hashlib.sha256(_stable_json(protocol["grids"]).encode()).hexdigest(),
        "implementation_fingerprint": protocol["implementation"]["fingerprint"],
        "implementation_manifest_sha256": hashlib.sha256(
            _stable_json(protocol["implementation"]["manifest"]).encode()
        ).hexdigest(),
        "model_election_sha256": hashlib.sha256(
            _stable_json(protocol["model_election"]).encode()
        ).hexdigest(),
    }


def _results_path(quick: bool) -> Path:
    """Return mutable resume state, never the canonical released checkpoint."""
    name = "results.quick.jsonl" if quick else "results.wip.jsonl"
    return BENCHMARK_RESULTS.with_name(name)


def _publish_checkpoint_snapshot(source: Path, target: Path) -> None:
    """Atomically snapshot a complete strict-JSONL WIP checkpoint for release."""
    _read_checkpoint_rows(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(source.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_checkpoint_rows(results_path: Path) -> list[dict[str, Any]]:
    """Parse a checkpoint fail-closed; never hide a corrupt evidence row."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        results_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            value = loads_json(line)
        except ValueError as exc:
            raise RuntimeError(
                f"invalid benchmark checkpoint JSON at {results_path}:{line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise RuntimeError(
                f"benchmark checkpoint row is not an object at {results_path}:{line_number}"
            )
        rows.append(value)
    return rows


def data_fingerprint(
    X: pd.DataFrame,
    rule_score: pd.Series,
    years: pd.Series,
) -> str:
    """Hash every data and protocol input used by benchmark election.

    The continuous rule score affects strict labels and Spearman metrics even
    when the binary 0.4 label is unchanged; years determine the OOT election.
    Both therefore belong in the fingerprint alongside feature values and the
    complete election protocol.
    """
    if not (len(X) == len(rule_score) == len(years)):
        raise ValueError("X, rule_score and years must have identical lengths")
    h = hashlib.sha256()
    h.update(_stable_json(benchmark_protocol_provenance()).encode())
    h.update(
        f"|{len(X)}|{'|'.join(f'{c}:{X[c].dtype}' for c in X.columns)}"
        f"|rule_score:{rule_score.dtype}|years:{years.dtype}".encode()
    )
    h.update(pd.util.hash_pandas_object(X, index=False).to_numpy().tobytes())
    h.update(
        pd.util.hash_pandas_object(rule_score.reset_index(drop=True), index=False)
        .to_numpy()
        .tobytes()
    )
    h.update(
        pd.util.hash_pandas_object(years.reset_index(drop=True), index=False).to_numpy().tobytes()
    )
    return h.hexdigest()[:16]


def _load_done_keys(fingerprint: str, quick: bool = False) -> set[str]:
    """Return config keys already completed for this data fingerprint.

    If the file contains rows for a *different* fingerprint, archive it and
    start clean — results across different data must never mix.
    """
    results_path = _results_path(quick)
    if not results_path.exists():
        return set()
    rows = _read_checkpoint_rows(results_path)
    foreign = [r for r in rows if r.get("data_fingerprint") != fingerprint]
    if foreign:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        suffix = ".quick" if quick else ".wip"
        archive = results_path.with_name(f"results{suffix}.{ts}.jsonl")
        results_path.rename(archive)
        log.info(
            "benchmark.results.archived",
            archive=str(archive),
            reason="data fingerprint changed",
            foreign_rows=len(foreign),
        )
        return set()
    latest_by_key = {
        str(row.get("config_key")): row for row in rows if row.get("config_key") is not None
    }
    expected_provenance = benchmark_result_provenance()
    done: set[str] = set()
    for key, row in latest_by_key.items():
        kind, family, params = row.get("kind"), row.get("family"), row.get("params")
        if (
            row.get("status") == "ok"
            and isinstance(row.get("quick"), bool)
            and row["quick"] == quick
            and kind in {"unsupervised", "supervised"}
            and isinstance(family, str)
            and isinstance(params, dict)
            and config_key(kind, family, params) == key
            and all(row.get(field) == value for field, value in expected_provenance.items())
        ):
            done.add(key)
    return done


def _append_result(row: dict[str, Any]) -> None:
    ensure_dirs()
    quick = bool(row.get("quick", False))
    results_path = _results_path(quick)
    # Preserve JSONL row boundaries if an external writer omitted the final
    # newline. Parsing remains fail-closed if the preceding row is malformed.
    needs_newline = False
    if results_path.exists() and results_path.stat().st_size > 0:
        with open(results_path, "rb") as f:
            f.seek(-1, 2)
            needs_newline = f.read(1) != b"\n"
    with open(results_path, "a", encoding="utf-8") as f:
        if needs_newline:
            f.write("\n")
        f.write(dumps_json(row, sort_keys=True) + "\n")


def _scorer_supports_seed(family: str) -> bool:
    cls = type(build_scorer(family))
    return any(f.name == "random_state" for f in dataclasses.fields(cls))


# =====================================================================
#  Unsupervised evaluation
# =====================================================================


def _top_set(scores: np.ndarray, quantile: float) -> set[int]:
    thr = np.quantile(scores, quantile)
    return set(np.where(scores >= thr)[0].tolist())


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / max(len(a | b), 1)


def evaluate_unsupervised(
    family: str,
    params: dict[str, Any],
    X: pd.DataFrame,
    y_04: pd.Series,
    y_07: pd.Series,
    rule_score: pd.Series,
) -> dict[str, Any]:
    """Full evaluation of one unsupervised configuration."""
    cfg = settings()
    rng = np.random.default_rng(cfg.random_seed)

    # ------------------------------------------------ main fit + score
    t0 = time.perf_counter()
    scorer = build_scorer(family, {**params})
    scorer.fit(X)
    fit_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    s = scorer.score(X).to_numpy()
    score_s = time.perf_counter() - t0

    # ------------------------------------------------ proxy alignment
    proxy_auc_04 = float(roc_auc_score(y_04, s))
    proxy_auc_07 = float(roc_auc_score(y_07, s))
    k = min(cfg.benchmark_precision_at, len(s))
    top_idx = np.argsort(s)[::-1][:k]
    precision_at_k = float(y_07.to_numpy()[top_idx].mean())
    spearman_rule = float(pd.Series(s).corr(rule_score.reset_index(drop=True), method="spearman"))

    # ------------------------------------------------ bootstrap stability
    n = len(X)
    sample_n = int(n * 0.8)
    flag_sets: list[set[int]] = [_top_set(s, cfg.benchmark_flag_quantile)]
    for b in range(cfg.benchmark_bootstrap_runs):
        idx = rng.choice(n, size=sample_n, replace=True)
        boot_params = {**params}
        if _scorer_supports_seed(family):
            boot_params["random_state"] = cfg.random_seed + 100 + b
        bs = build_scorer(family, boot_params)
        bs.fit(X.iloc[idx])
        flag_sets.append(_top_set(bs.score(X).to_numpy(), cfg.benchmark_flag_quantile))
    jac = [
        _jaccard(flag_sets[i], flag_sets[j])
        for i in range(len(flag_sets))
        for j in range(i + 1, len(flag_sets))
    ]
    stability_jaccard = float(np.mean(jac)) if jac else None

    # ------------------------------------------------ seed consistency
    if family_is_stochastic(family) and _scorer_supports_seed(family):
        variants = [s]
        for e in range(cfg.benchmark_extra_seeds):
            vs = build_scorer(family, {**params, "random_state": cfg.random_seed + 500 + e})
            vs.fit(X)
            variants.append(vs.score(X).to_numpy())
        rhos = [
            float(pd.Series(variants[i]).corr(pd.Series(variants[j]), method="spearman"))
            for i in range(len(variants))
            for j in range(i + 1, len(variants))
        ]
        seed_consistency = float(np.mean(rhos))
        n_fits = 1 + cfg.benchmark_bootstrap_runs + cfg.benchmark_extra_seeds
    else:
        seed_consistency = 1.0  # deterministic family
        n_fits = 1 + cfg.benchmark_bootstrap_runs

    # ------------------------------------------------ composite ranking score
    components = pd.Series(
        {
            "proxy_auc_07": proxy_auc_07,
            "stability_jaccard": stability_jaccard,
            "seed_consistency": seed_consistency,
        }
    )
    composite = _weighted_composite(components, DECLARED_COMPOSITE_WEIGHTS)

    return {
        "proxy_auc_04": round(proxy_auc_04, 4),
        "proxy_auc_07": round(proxy_auc_07, 4),
        f"precision_at_{k}": round(precision_at_k, 4),
        "precision_at_k": round(precision_at_k, 4),
        "spearman_rule": round(spearman_rule, 4),
        "stability_jaccard": round(stability_jaccard, 4) if stability_jaccard is not None else None,
        "seed_consistency": round(seed_consistency, 4),
        "composite": round(composite, 4),
        "n_fits": n_fits,
        "fit_seconds": round(fit_s, 2),
        "score_seconds": round(score_s, 2),
    }


# =====================================================================
#  Supervised evaluation
# =====================================================================


def evaluate_supervised(
    family: str,
    params: dict[str, Any],
    X: pd.DataFrame,
    y: pd.Series,
    years: pd.Series,
) -> dict[str, Any]:
    """CV × seeds + out-of-time validation for one classifier config."""
    cfg = settings()
    Xn = to_model_matrix(X)
    yn = y.to_numpy()

    def _fit(model, X_tr, y_tr):
        # hgb has no class_weight param — align it with the deployed
        # SupervisedScorer by passing the same balanced sample weights;
        # the other families use class_weight="balanced" internally.
        if family == "hgb":
            pos = max(int(y_tr.sum()), 1)
            neg = max(int((1 - y_tr).sum()), 1)
            sw = np.where(y_tr == 1, neg / pos, 1.0)
            model.fit(X_tr, y_tr, sample_weight=sw)
        else:
            model.fit(X_tr, y_tr)
        return model

    # ------------------------------------------------ stratified CV × seeds
    t0 = time.perf_counter()
    rocs, prs, briers = [], [], []
    n_fits = 0
    for seed in range(cfg.benchmark_supervised_seeds):
        skf = StratifiedKFold(
            n_splits=cfg.benchmark_cv_folds, shuffle=True, random_state=cfg.random_seed + seed
        )
        for tr, te in skf.split(Xn, yn):
            model = build_classifier(family, params, seed=cfg.random_seed + seed)
            _fit(model, Xn[tr], yn[tr])
            proba = model.predict_proba(Xn[te])[:, 1]
            rocs.append(float(roc_auc_score(yn[te], proba)))
            prs.append(float(average_precision_score(yn[te], proba)))
            briers.append(float(brier_score_loss(yn[te], proba)))
            n_fits += 1
    cv_s = time.perf_counter() - t0

    # ------------------------------------------------ out-of-time validation
    oot: dict[str, Any] = {
        "oot_rocauc": None,
        "oot_prauc": None,
        "oot_ece": None,
        "oot_train_n": 0,
        "oot_test_n": 0,
    }
    yr = pd.to_numeric(years, errors="coerce")
    tr_mask = (yr <= cfg.benchmark_oot_train_max_year).fillna(False).to_numpy()
    te_mask = (yr > cfg.benchmark_oot_train_max_year).fillna(False).to_numpy()
    if tr_mask.sum() > 100 and te_mask.sum() > 100 and yn[te_mask].sum() > 10:
        model = build_classifier(family, params, seed=cfg.random_seed)
        _fit(model, Xn[tr_mask], yn[tr_mask])
        proba = model.predict_proba(Xn[te_mask])[:, 1]
        calib = calibration_report(pd.Series(proba), pd.Series(yn[te_mask]))
        oot = {
            "oot_rocauc": round(float(roc_auc_score(yn[te_mask], proba)), 4),
            "oot_prauc": round(float(average_precision_score(yn[te_mask], proba)), 4),
            "oot_ece": round(calib["ece"], 4) if calib.get("ece") is not None else None,
            "oot_train_n": int(tr_mask.sum()),
            "oot_test_n": int(te_mask.sum()),
        }
        n_fits += 1

    return {
        "cv_rocauc_mean": round(float(np.mean(rocs)), 4),
        "cv_rocauc_std": round(float(np.std(rocs)), 4),
        "cv_prauc_mean": round(float(np.mean(prs)), 4),
        "cv_prauc_std": round(float(np.std(prs)), 4),
        "cv_brier_mean": round(float(np.mean(briers)), 4),
        **oot,
        "n_fits": n_fits,
        "fit_seconds": round(cv_s, 2),
    }


# =====================================================================
#  Orchestration
# =====================================================================


def run_benchmark(
    X: pd.DataFrame,
    rule_score: pd.Series,
    years: pd.Series,
    quick: bool = False,
    expected_gold_release_sha256: str | None = None,
) -> dict[str, Any]:
    """Run the full sweep with checkpoint/resume. Returns a summary."""
    if not quick and expected_gold_release_sha256 is None:
        raise RuntimeError("full benchmark execution requires the captured gold release SHA-256")
    cfg = settings()
    ensure_dirs()

    y_04 = (rule_score >= cfg.rule_label_threshold).astype(int)
    y_07 = (rule_score >= cfg.rule_score_priority_threshold).astype(int)
    fp = data_fingerprint(X, rule_score, years)
    result_provenance = benchmark_result_provenance()
    done = _load_done_keys(fp, quick=quick)

    u_grid = unsupervised_grid(quick)
    s_grid = supervised_grid(quick)
    log.info(
        "benchmark.start",
        fingerprint=fp,
        quick=quick,
        unsupervised_configs=len(u_grid),
        supervised_configs=len(s_grid),
        already_done=len(done),
    )

    total_fits = 0
    started = time.perf_counter()

    for i, spec in enumerate(u_grid, 1):
        key = config_key("unsupervised", spec["family"], spec["params"])
        if key in done:
            log.info(
                "benchmark.skip", family=spec["family"], params=spec["params"], reason="resume"
            )
            continue
        base = {
            "kind": "unsupervised",
            "family": spec["family"],
            "family_label_sq": FAMILY_LABELS_SQ[spec["family"]],
            "params": spec["params"],
            "config_key": key,
            "data_fingerprint": fp,
            "quick": quick,
            "run_id": get_run_id(),
            "completed_at": None,
            **result_provenance,
        }
        log.info(
            "benchmark.unsup.config",
            i=i,
            total=len(u_grid),
            family=spec["family"],
            params=spec["params"],
        )
        try:
            metrics = evaluate_unsupervised(
                spec["family"], spec["params"], X, y_04, y_07, rule_score
            )
            total_fits += metrics["n_fits"]
            row = {
                **base,
                **metrics,
                "status": "ok",
                "error": None,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:  # noqa: BLE001 — isolate failures, keep sweeping
            log.warning(
                "benchmark.unsup.failed", family=spec["family"], params=spec["params"], error=str(e)
            )
            row = {
                **base,
                "status": "failed",
                "error": str(e)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        _append_result(row)

    for i, spec in enumerate(s_grid, 1):
        key = config_key("supervised", spec["family"], spec["params"])
        if key in done:
            log.info(
                "benchmark.skip", family=spec["family"], params=spec["params"], reason="resume"
            )
            continue
        base = {
            "kind": "supervised",
            "family": spec["family"],
            "family_label_sq": SUPERVISED_LABELS_SQ[spec["family"]],
            "params": spec["params"],
            "config_key": key,
            "data_fingerprint": fp,
            "quick": quick,
            "run_id": get_run_id(),
            "completed_at": None,
            **result_provenance,
        }
        log.info(
            "benchmark.sup.config",
            i=i,
            total=len(s_grid),
            family=spec["family"],
            params=spec["params"],
        )
        try:
            metrics = evaluate_supervised(spec["family"], spec["params"], X, y_04, years)
            total_fits += metrics["n_fits"]
            row = {
                **base,
                **metrics,
                "status": "ok",
                "error": None,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:  # noqa: BLE001
            log.warning(
                "benchmark.sup.failed",
                family=spec["family"],
                params=spec["params"],
                error=str(e)[:200],
            )
            row = {
                **base,
                "status": "failed",
                "error": str(e)[:500],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        _append_result(row)

    duration = time.perf_counter() - started
    summary = build_leaderboard(
        fp,
        quick=quick,
        expected_gold_release_sha256=expected_gold_release_sha256,
    )
    summary.update(
        {
            "fits_this_run": total_fits,
            "duration_seconds": round(duration, 1),
            "quick": quick,
        }
    )
    log.info(
        "benchmark.done", **{k: v for k, v in summary.items() if not isinstance(v, (list, dict))}
    )
    return summary


# =====================================================================
#  Leaderboard + champions
# =====================================================================


def load_results(
    fingerprint: str | None = None,
    quick: bool | None = None,
) -> pd.DataFrame:
    results_path = BENCHMARK_RESULTS if quick is None else _results_path(quick)
    if not results_path.exists():
        return pd.DataFrame()
    df = pd.DataFrame(_read_checkpoint_rows(results_path))
    if df.empty:
        return df
    if fingerprint:
        df = df[df["data_fingerprint"] == fingerprint]
    if quick is not None:
        quick_col = df["quick"] if "quick" in df.columns else False
        if isinstance(quick_col, bool):
            df = df if quick_col == quick else df.iloc[0:0]
        else:
            df = df[quick_col.fillna(False).astype(bool).eq(quick)]
    return df


def _normalise_results(rows: pd.DataFrame) -> pd.DataFrame:
    """Normalise JSON-backed and Parquet-backed benchmark rows identically."""
    normalised = rows.copy()
    if "params" not in normalised:
        return normalised

    def parse_params(value: Any) -> Any:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = loads_json(value)
            except ValueError as exc:
                raise RuntimeError("invalid strict JSON in benchmark params") from exc
            return parsed
        return value

    normalised["params"] = normalised["params"].map(parse_params)
    return normalised


def _finite_metric(row: pd.Series, name: str) -> float:
    value = row.get(name)
    if value is None or not pd.notna(value):
        return 0.0
    return float(value)


def _weighted_composite(row: pd.Series, weights: dict[str, float]) -> float:
    """Calculate a declared rank score from persisted component metrics."""
    return float(sum(_finite_metric(row, metric) * weight for metric, weight in weights.items()))


def _family_election(
    unsup: pd.DataFrame,
    *,
    weights: dict[str, float] | None,
    metric: str | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Elect one configuration per family and then rank the families."""
    elected: dict[str, dict[str, Any]] = {}
    for family, sub in unsup.groupby("family", sort=True):
        ranked = sub.copy()
        if metric is None:
            assert weights is not None
            ranked["election_score"] = ranked.apply(
                lambda row: _weighted_composite(row, weights), axis=1
            )
        else:
            ranked["election_score"] = pd.to_numeric(ranked[metric], errors="coerce").fillna(
                float("-inf")
            )
        best = ranked.sort_values(["election_score", "config_key"], ascending=[False, True]).iloc[0]
        elected[str(family)] = {
            "config_key": str(best["config_key"]),
            "params": best["params"],
            "election_score": round(float(best["election_score"]), 8),
            "composite": _finite_metric(best, "composite"),
            "proxy_auc_07": _finite_metric(best, "proxy_auc_07"),
            "precision_at_k": _finite_metric(best, "precision_at_k"),
            "stability_jaccard": (
                _finite_metric(best, "stability_jaccard")
                if pd.notna(best.get("stability_jaccard"))
                else None
            ),
            "seed_consistency": _finite_metric(best, "seed_consistency"),
        }
    ranked_families = sorted(
        elected,
        key=lambda family: (-elected[family]["election_score"], family),
    )
    return elected, ranked_families


def _set_jaccard(left: list[str], right: list[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    return round(len(a & b) / max(len(a | b), 1), 4)


def model_election_sensitivity(
    rows: pd.DataFrame,
    declared_ensemble: list[str],
) -> dict[str, Any]:
    """Report rank sensitivity; this is explicitly not outcome validation."""
    latest = _normalise_results(rows).drop_duplicates(subset="config_key", keep="last")
    unsup = latest[(latest["kind"] == "unsupervised") & (latest["status"] == "ok")].copy()
    top_k = settings().benchmark_top_k_families
    declared_elected, _ = _family_election(unsup, weights=None, metric="composite")
    scenarios: dict[str, Any] = {}
    for name, weights in ALTERNATE_COMPOSITE_WEIGHTS.items():
        elected, ranking = _family_election(unsup, weights=weights)
        ensemble = ranking[:top_k]
        scenarios[name] = {
            "weights": weights,
            "ensemble_families": ensemble,
            "top_k_jaccard_vs_declared": _set_jaccard(declared_ensemble, ensemble),
            "changed_family_configuration_count": sum(
                elected[family]["config_key"] != declared_elected[family]["config_key"]
                for family in sorted(declared_elected)
            ),
            "family_config_keys": {
                family: elected[family]["config_key"] for family in sorted(elected)
            },
        }

    precision_elected, precision_ranking = _family_election(
        unsup, weights=None, metric="precision_at_k"
    )
    precision_ensemble = precision_ranking[:top_k]
    declared_positions = {family: index for index, family in enumerate(declared_ensemble)}
    precision_positions = {family: index for index, family in enumerate(precision_ranking)}
    common = sorted(set(declared_positions) & set(precision_positions))
    rank_conflicts = sum(
        (declared_positions[left] - declared_positions[right])
        * (precision_positions[left] - precision_positions[right])
        < 0
        for index, left in enumerate(common)
        for right in common[index + 1 :]
    )
    return {
        "status": "rank_sensitivity_only",
        "declared_ensemble_families": declared_ensemble,
        "alternate_weight_scenarios": scenarios,
        "precision_at_k_ranking": {
            "ensemble_families": precision_ensemble,
            "top_k_jaccard_vs_declared": _set_jaccard(declared_ensemble, precision_ensemble),
            "pairwise_rank_conflicts_within_declared_top_k": int(rank_conflicts),
            "family_config_keys": {
                family: precision_elected[family]["config_key"]
                for family in sorted(precision_elected)
            },
        },
        "interpretation": (
            "Sensitivity of the proxy/stability rank election on this snapshot; "
            "it is not validation against fraud, corruption, or external outcomes."
        ),
    }


def derive_benchmark_election(rows: pd.DataFrame, quick: bool = False) -> dict[str, Any]:
    """Recompute the complete deterministic election from checkpoint rows."""
    normalised = _normalise_results(rows)
    completeness = benchmark_completeness(normalised, quick=quick)
    if not completeness["complete"]:
        raise RuntimeError(
            "Benchmark election is incomplete; champions were not published "
            f"(successful={completeness['successful_total']}/"
            f"{completeness['expected_total']}, "
            f"missing={len(completeness['missing_config_keys'])}, "
            f"failed={len(completeness['failed_config_keys'])}, "
            f"extra={len(completeness['extra_config_keys'])}, "
            f"invalid={len(completeness['invalid_config_keys'])}, "
            f"stale_protocol={len(completeness['stale_protocol_config_keys'])}). "
            "Rerun `thesis pipeline benchmark` to resume failed or missing configs."
        )
    latest = normalised.drop_duplicates(subset="config_key", keep="last").copy()
    unsup = latest[latest["kind"] == "unsupervised"].copy()
    sup = latest[latest["kind"] == "supervised"].copy()

    unsupervised, family_ranking = _family_election(unsup, weights=None, metric="composite")
    ensemble_families = family_ranking[: settings().benchmark_top_k_families]

    supervised_champion: dict[str, Any] = {}
    explainer: dict[str, Any] = {}
    if not sup.empty:
        sup["oot_rank"] = pd.to_numeric(sup["oot_rocauc"], errors="coerce").fillna(
            pd.to_numeric(sup["cv_rocauc_mean"], errors="coerce")
        )
        best = sup.sort_values(
            ["oot_rank", "cv_rocauc_mean", "config_key"],
            ascending=[False, False, True],
        ).iloc[0]
        supervised_champion = {
            "family": str(best["family"]),
            "config_key": str(best["config_key"]),
            "params": best["params"],
            "oot_rocauc": (float(best["oot_rocauc"]) if pd.notna(best["oot_rocauc"]) else None),
            "cv_rocauc_mean": float(best["cv_rocauc_mean"]),
            "cv_prauc_mean": float(best["cv_prauc_mean"]),
        }
        hgb = sup[sup["family"] == "hgb"]
        if not hgb.empty:
            best_hgb = hgb.sort_values(
                ["oot_rank", "cv_rocauc_mean", "config_key"],
                ascending=[False, False, True],
            ).iloc[0]
            explainer = {
                "family": "hgb",
                "config_key": str(best_hgb["config_key"]),
                "params": best_hgb["params"],
                "oot_rocauc": (
                    float(best_hgb["oot_rocauc"]) if pd.notna(best_hgb["oot_rocauc"]) else None
                ),
            }
    sensitivity = model_election_sensitivity(latest, ensemble_families)
    return {
        "completeness": completeness,
        "unsupervised": unsupervised,
        "ensemble_families": ensemble_families,
        "supervised_champion": supervised_champion,
        "explainer": explainer,
        "model_election_sensitivity": sensitivity,
    }


def _champion_semantics(champions: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "schema_version",
        "data_fingerprint",
        "protocol_fingerprint",
        "implementation_fingerprint",
        "quick",
        "completeness",
        "unsupervised",
        "ensemble_families",
        "supervised_champion",
        "explainer",
        "composite_weights",
        "composite_formula",
        "model_election_sensitivity",
    )
    return {field: champions.get(field) for field in fields}


def _result_bundle_fingerprint(rows: pd.DataFrame) -> str:
    """Hash the canonical latest-row table independent of storage encoding."""
    normalised = _normalise_results(rows)
    if normalised.empty:
        return hashlib.sha256(b"[]").hexdigest()
    latest = normalised.drop_duplicates(subset="config_key", keep="last").copy()
    latest = latest.drop(columns=["error"], errors="ignore")
    latest = latest.reindex(sorted(latest.columns), axis=1).sort_values("config_key")
    return hashlib.sha256(_stable_json(latest.to_dict(orient="records")).encode()).hexdigest()


def benchmark_semantic_check(
    rows: pd.DataFrame,
    champions: dict[str, Any],
    *,
    quick: bool = False,
    leaderboard: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Fail-closed semantic check for the released result/election bundle."""
    errors: list[str] = []
    protocol = benchmark_protocol_provenance()
    expected_protocol_fingerprint = benchmark_protocol_fingerprint()
    expected_impl = protocol["implementation"]["fingerprint"]
    normalised = _normalise_results(rows)
    result_bundle_fingerprint = _result_bundle_fingerprint(normalised)
    leaderboard_bundle_fingerprint = (
        _result_bundle_fingerprint(leaderboard) if leaderboard is not None else None
    )
    if (
        leaderboard_bundle_fingerprint is not None
        and leaderboard_bundle_fingerprint != result_bundle_fingerprint
    ):
        errors.append("released leaderboard is not the canonical latest-row checkpoint table")
    if not normalised.empty and {"kind", "composite"}.issubset(normalised.columns):
        latest_unsup = normalised.drop_duplicates(subset="config_key", keep="last").query(
            "kind == 'unsupervised'"
        )
        formula_mismatches = [
            str(row["config_key"])
            for _, row in latest_unsup.iterrows()
            if abs(
                _finite_metric(row, "composite")
                - _weighted_composite(row, DECLARED_COMPOSITE_WEIGHTS)
            )
            > 0.0002
        ]
        if formula_mismatches:
            errors.append(
                "persisted composite scores do not match the declared formula: "
                + ", ".join(formula_mismatches)
            )
    try:
        election = derive_benchmark_election(normalised, quick=quick)
    except RuntimeError as exc:
        election = None
        errors.append(str(exc))

    data_fingerprints = (
        sorted(normalised["data_fingerprint"].dropna().astype(str).unique().tolist())
        if "data_fingerprint" in normalised
        else []
    )
    if len(data_fingerprints) != 1:
        errors.append(f"expected exactly one result data fingerprint, found {data_fingerprints}")
    elif champions.get("data_fingerprint") != data_fingerprints[0]:
        errors.append("champion data fingerprint does not match leaderboard/results")
    if champions.get("schema_version") != CHAMPIONS_SCHEMA_VERSION:
        errors.append("unsupported champions schema version")
    if champions.get("quick") is not quick:
        errors.append("champions quick/full mode does not match the checked contract")
    if champions.get("protocol_fingerprint") != expected_protocol_fingerprint:
        errors.append("champions protocol fingerprint is not current")
    if champions.get("implementation_fingerprint") != expected_impl:
        errors.append("champions implementation fingerprint is not current")
    if json_ready(champions.get("benchmark_protocol")) != json_ready(protocol):
        errors.append("champions benchmark protocol payload is not current")

    expected_semantics: dict[str, Any] | None = None
    if election is not None and data_fingerprints:
        expected_semantics = {
            "schema_version": CHAMPIONS_SCHEMA_VERSION,
            "data_fingerprint": data_fingerprints[0],
            "protocol_fingerprint": expected_protocol_fingerprint,
            "implementation_fingerprint": expected_impl,
            "quick": quick,
            **election,
            "composite_weights": DECLARED_COMPOSITE_WEIGHTS,
            "composite_formula": (
                "0.45×proxy_auc_07 + 0.35×stability_jaccard + 0.20×seed_consistency"
            ),
        }
        if json_ready(_champion_semantics(champions)) != json_ready(expected_semantics):
            errors.append("champions are not the deterministic election from released rows")

    material = {
        "check": "benchmark_release_semantics",
        "protocol_fingerprint": expected_protocol_fingerprint,
        "implementation_fingerprint": expected_impl,
        "data_fingerprints": data_fingerprints,
        "result_bundle_fingerprint": result_bundle_fingerprint,
        "leaderboard_bundle_fingerprint": leaderboard_bundle_fingerprint,
        "expected_champion_semantics": expected_semantics,
    }
    semantic_fingerprint = hashlib.sha256(_stable_json(material).encode()).hexdigest()
    return {
        "schema_version": 1,
        "check": "benchmark_release_semantics",
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": 0,
        "fail_count": len(errors),
        "errors": errors,
        "protocol_fingerprint": expected_protocol_fingerprint,
        "implementation_fingerprint": expected_impl,
        "data_fingerprints": data_fingerprints,
        "result_bundle_fingerprint": result_bundle_fingerprint,
        "leaderboard_bundle_fingerprint": leaderboard_bundle_fingerprint,
        "semantic_fingerprint": semantic_fingerprint,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def build_leaderboard(
    fingerprint: str,
    quick: bool = False,
    expected_gold_release_sha256: str | None = None,
) -> dict[str, Any]:
    """Rank results, elect champions, persist leaderboard + champions.json.

    ``quick=True`` writes to ``*.quick`` sibling paths and never touches the
    canonical champions — a smoke run must not hijack model selection or
    satisfy the DAG's freshness check.
    """
    from ..io.writers import write_json, write_markdown, write_parquet

    if not quick and expected_gold_release_sha256 is None:
        raise RuntimeError("full benchmark publication requires the captured gold release SHA-256")

    df = _normalise_results(load_results(fingerprint, quick=quick))
    try:
        election = derive_benchmark_election(df, quick=quick)
    except RuntimeError:
        completeness = benchmark_completeness(df, quick=quick)
        log.error(
            "benchmark.election.incomplete",
            quick=quick,
            expected=completeness["expected_total"],
            successful=completeness["successful_total"],
            missing=len(completeness["missing_config_keys"]),
            failed=len(completeness["failed_config_keys"]),
            extra=len(completeness["extra_config_keys"]),
            invalid=len(completeness["invalid_config_keys"]),
            stale_protocol=len(completeness["stale_protocol_config_keys"]),
        )
        raise

    # Completeness guarantees every latest declared row is successful.
    ok = df.drop_duplicates(subset="config_key", keep="last").copy()
    completeness = election["completeness"]
    failed = 0

    champions_path = CHAMPIONS.with_suffix(".quick.json") if quick else CHAMPIONS
    leaderboard_path = (
        BENCHMARK_LEADERBOARD.with_suffix(".quick.parquet") if quick else BENCHMARK_LEADERBOARD
    )
    md_path = (
        BENCHMARK_LEADERBOARD_MD.with_suffix(".quick.md") if quick else BENCHMARK_LEADERBOARD_MD
    )

    unsup = ok[ok["kind"] == "unsupervised"].copy()
    sup = ok[ok["kind"] == "supervised"].copy()

    protocol = benchmark_protocol_provenance()
    champions = {
        "schema_version": CHAMPIONS_SCHEMA_VERSION,
        "data_fingerprint": fingerprint,
        "benchmark_protocol": protocol,
        "protocol_fingerprint": benchmark_protocol_fingerprint(),
        "implementation_fingerprint": protocol["implementation"]["fingerprint"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quick": quick,
        **election,
        "composite_weights": DECLARED_COMPOSITE_WEIGHTS,
        "composite_formula": ("0.45×proxy_auc_07 + 0.35×stability_jaccard + 0.20×seed_consistency"),
    }
    lb = ok.drop(columns=["error"], errors="ignore").copy()
    lb["params"] = lb["params"].apply(lambda value: dumps_json(value, sort_keys=True))
    results_path = _results_path(quick)
    semantic_precheck = benchmark_semantic_check(df, champions, quick=quick, leaderboard=lb)
    if not semantic_precheck["passed"]:
        raise RuntimeError(
            "Benchmark semantic election check failed: " + "; ".join(semantic_precheck["errors"])
        )
    # Keep the previous canonical generation valid during the expensive sweep.
    # Only a complete, semantically checked full WIP checkpoint can replace the
    # released JSONL snapshot, and the replacement itself is atomic.
    if not quick:
        _publish_checkpoint_snapshot(results_path, BENCHMARK_RESULTS)
    lineage_results_path = results_path if quick else BENCHMARK_RESULTS
    write_parquet(
        lb,
        leaderboard_path,
        table="models.benchmark_leaderboard",
        layer="model",
        inputs=[GOLD_FEATURES, lineage_results_path],
        parameters={"fingerprint": fingerprint, "quick": quick},
    )

    _write_leaderboard_md(unsup, sup, champions, failed, md_path, writer=write_markdown)
    write_json(champions, champions_path)
    persisted_leaderboard = pd.read_parquet(leaderboard_path)
    semantic_check = benchmark_semantic_check(
        df,
        champions,
        quick=quick,
        leaderboard=persisted_leaderboard,
    )
    if not semantic_check["passed"]:
        raise RuntimeError(
            "Persisted benchmark semantic election check failed: "
            + "; ".join(semantic_check["errors"])
        )
    if not quick:
        semantic_check.update(
            {
                "rows": len(persisted_leaderboard),
                "columns": persisted_leaderboard.shape[1],
                "data_fingerprint": dataframe_fingerprint(persisted_leaderboard),
                "release_binding": {
                    "artifact_path": BENCHMARK_LEADERBOARD.resolve()
                    .relative_to(settings().data_dir.resolve())
                    .as_posix(),
                    "artifact_sha256": file_sha256(BENCHMARK_LEADERBOARD),
                    "artifact_size_bytes": BENCHMARK_LEADERBOARD.stat().st_size,
                },
            }
        )
        write_json(semantic_check, BENCHMARK_RELEASE_DQ)
        publish_release(
            BENCHMARK_RELEASE,
            stage="benchmark",
            inputs=[GOLD_RELEASE, GOLD_FEATURES],
            artifacts=[
                BENCHMARK_RESULTS,
                CHAMPIONS,
                BENCHMARK_LEADERBOARD,
                BENCHMARK_LEADERBOARD_MD,
            ],
            checks=[BENCHMARK_RELEASE_DQ],
            metadata={
                "data_fingerprint": fingerprint,
                "protocol_fingerprint": champions["protocol_fingerprint"],
                "implementation_fingerprint": champions["implementation_fingerprint"],
                "semantic_fingerprint": semantic_check["semantic_fingerprint"],
            },
            expected_input_manifest_sha256=(
                {GOLD_RELEASE: expected_gold_release_sha256}
                if expected_gold_release_sha256 is not None
                else None
            ),
        )
    return {
        "configs_ok": len(ok),
        "configs_failed": failed,
        "unsupervised_configs": len(unsup),
        "supervised_configs": len(sup),
        "ensemble_families": election["ensemble_families"],
        "supervised_champion": election["supervised_champion"].get("family"),
        "total_fits_recorded": int(ok["n_fits"].sum()) if "n_fits" in ok else None,
    }


def _write_leaderboard_md(
    unsup: pd.DataFrame, sup: pd.DataFrame, champions: dict, failed: int, md_path=None, writer=None
) -> None:
    """Raporti i renditjes në shqip."""
    md_path = md_path or BENCHMARK_LEADERBOARD_MD
    lines: list[str] = []
    cfg = settings()
    p = lines.append
    p("# Krahasimi i Modeleve — Leaderboard")
    p("")
    p(
        f"_Gjeneruar_: `{champions['created_at']}`  ·  "
        f"_gjurma e të dhënave_: `{champions['data_fingerprint']}`  ·  "
        f"konfigurime të dështuara: {failed}"
    )
    p("")
    p("## Protokolli")
    p("")
    p(
        "* **Të pambikëqyrur**: AUC proxy ndaj etiketave të rregullave "
        "(pragje 0.4 dhe 0.7), precision@500 ndaj etiketave strikte, "
        "Spearman me `rule_score`, stabilitet bootstrap (Jaccard i "
        "bashkësive top-5 % mbi ri-përshtatje në 80 % mostra), konsistencë "
        "seed-esh për familjet stokastike."
    )
    p(f"* **Formula e renditjes**: `{champions['composite_formula']}`.")
    p(
        f"* **Përsëritjet**: {cfg.benchmark_bootstrap_runs} ri-përshtatje "
        f"bootstrap dhe {cfg.benchmark_extra_seeds} seeds shtesë për familjet "
        "stokastike; këto janë kontrolle të kufizuara përsëritshmërie, jo "
        "intervale pasigurie."
    )
    p(
        "* **Të mbikëqyrur**: CV e shtresëzuar 5-fold × 2 seeds "
        "(ROC-AUC, PR-AUC, Brier) + kontroll kohor i besnikërisë ndaj rregullave "
        "(trajnim ≤ 2023, test ≥ 2024) + ECE e kalibrimit."
    )
    p("")
    p("## ⚠️ Kufizime metodologjike (lexo para përdorimit)")
    p("")
    p(
        "1. Etiketat proxy vijnë nga shtresa e rregullave — metrikat masin "
        "**pajtimin me rregullat**, jo mashtrimin real. Asnjë model këtu "
        "nuk 'zbulon mashtrim'; ato renditin rekorde tenderi për **rishikim njerëzor**."
    )
    p(
        "2. Ndarja kohore përdor të njëjtat etiketa proxy të derivuara nga "
        "rregullat dhe veçori që mbivendosen fort me to. Prandaj OOT mat vetëm "
        "besnikëri kohore ndaj proxy-t; nuk mat gjeneralizim të zbulimit. Disa "
        "statistika kontekstuale llogariten mbi snapshot-in e plotë."
    )
    p(
        "3. Stabiliteti dhe konsistenca e seed-eve ndihmojnë të vlerësohet "
        "riprodhueshmëria e renditjes në këtë snapshot; ato nuk tregojnë "
        "saktësi rezultati ose gatishmëri për përdorim operacional."
    )
    p(
        "4. Skenarët alternativë të peshave dhe renditja precision@K më poshtë "
        "janë ndjeshmëri e renditjes ndaj proxy-ve, jo validim ndaj rezultateve "
        "të jashtme."
    )
    p("")

    if not unsup.empty:
        p("## Detektorët e pambikëqyrur (renditur sipas pikës së përbërë)")
        p("")
        cols = [
            "family_label_sq",
            "params",
            "composite",
            "proxy_auc_07",
            "proxy_auc_04",
            "precision_at_k",
            "stability_jaccard",
            "seed_consistency",
            "spearman_rule",
            "fit_seconds",
        ]
        view = unsup.sort_values("composite", ascending=False)[cols].copy()
        view["params"] = view["params"].apply(
            lambda d: dumps_json(d, sort_keys=True) if isinstance(d, dict) else d
        )
        view.columns = [
            "Modeli",
            "Parametrat",
            "Pika e përbërë",
            "AUC(0.7)",
            "AUC(0.4)",
            "Prec@500",
            "Stabiliteti",
            "Konsist. seed",
            "Spearman(rregulla)",
            "Koha e trajnimit (s)",
        ]
        p(view.to_markdown(index=False))
        p("")

    if not sup.empty:
        p("## Klasifikuesit proxy (renditur sipas besnikërisë kohore ROC-AUC)")
        p("")
        cols = [
            "family_label_sq",
            "params",
            "oot_rocauc",
            "oot_prauc",
            "oot_ece",
            "cv_rocauc_mean",
            "cv_rocauc_std",
            "cv_prauc_mean",
            "cv_brier_mean",
            "fit_seconds",
        ]
        view = sup.copy()
        view["oot_sort"] = view["oot_rocauc"].fillna(view["cv_rocauc_mean"])
        view = view.sort_values("oot_sort", ascending=False)[cols]
        view["params"] = view["params"].apply(
            lambda d: dumps_json(d, sort_keys=True) if isinstance(d, dict) else d
        )
        view.columns = [
            "Modeli",
            "Parametrat",
            "OOT ROC-AUC",
            "OOT PR-AUC",
            "OOT ECE",
            "CV ROC-AUC",
            "±std",
            "CV PR-AUC",
            "CV Brier",
            "Koha (s)",
        ]
        p(view.to_markdown(index=False))
        p("")

    p("## Kampionët")
    p("")
    for fam, info in champions.get("unsupervised", {}).items():
        star = " ⭐ (në ansambël)" if fam in champions["ensemble_families"] else ""
        p(
            f"* **{FAMILY_LABELS_SQ.get(fam, fam)}**{star} — "
            f"parametrat `{dumps_json(info['params'], sort_keys=True)}` · "
            f"pikë e përbërë {info['composite']:.3f}"
        )
    if champions.get("supervised_champion"):
        sc = champions["supervised_champion"]
        p(
            f"* **Klasifikuesi kampion**: {SUPERVISED_LABELS_SQ.get(sc['family'], sc['family'])} "
            f"`{dumps_json(sc['params'], sort_keys=True)}` · OOT ROC-AUC "
            f"{sc['oot_rocauc'] if sc['oot_rocauc'] is not None else '—'}"
        )
    if champions.get("explainer"):
        p(
            f"* **Shpjeguesi (SHAP)**: HistGradientBoosting "
            f"`{dumps_json(champions['explainer']['params'], sort_keys=True)}` — përdoret vetëm "
            f"për shpjegime, jo si detektor i pavarur."
        )
    p("")

    sensitivity = champions.get("model_election_sensitivity") or {}
    scenarios = sensitivity.get("alternate_weight_scenarios") or {}
    if scenarios:
        p("## Ndjeshmëria e zgjedhjes (jo validim)")
        p("")
        sensitivity_rows = [
            {
                "skenari": name,
                "peshat": _stable_json(values.get("weights", {})),
                "familjet top-K": ", ".join(values.get("ensemble_families", [])),
                "Jaccard vs deklaruara": values.get("top_k_jaccard_vs_declared"),
                "konfigurime të ndryshuara": values.get("changed_family_configuration_count"),
            }
            for name, values in scenarios.items()
        ]
        precision = sensitivity.get("precision_at_k_ranking") or {}
        sensitivity_rows.append(
            {
                "skenari": "precision@K proxy",
                "peshat": "—",
                "familjet top-K": ", ".join(precision.get("ensemble_families", [])),
                "Jaccard vs deklaruara": precision.get("top_k_jaccard_vs_declared"),
                "konfigurime të ndryshuara": "—",
            }
        )
        p(pd.DataFrame(sensitivity_rows).to_markdown(index=False))
        p("")
    p(
        f"**Ansambli përfundimtar**: "
        f"{', '.join(FAMILY_LABELS_SQ.get(f, f) for f in champions['ensemble_families'])} "
        f"+ shtresa e rregullave + pika kontekstuale."
    )

    payload = "\n".join(lines)
    if writer is None:
        from ..io.writers import write_markdown

        writer = write_markdown
    writer(payload, md_path)
