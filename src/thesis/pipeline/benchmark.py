"""Pipeline stage: rigorous multi-model benchmark.

Runs the full sweep defined in :mod:`thesis.anomaly.benchmark` over the
gold feature matrix and persists:

* ``data/models/benchmark/results.wip.jsonl``  — mutable resume checkpoint
* ``data/models/benchmark/results.jsonl``      — atomic completed release snapshot
* ``data/models/benchmark/leaderboard.parquet``— ranked results + lineage
* ``data/models/benchmark/leaderboard.md``     — raport në shqip
* ``data/models/benchmark/champions.json``     — konfigurimet fituese që
  i konsumon :mod:`thesis.pipeline.ml`
"""

from __future__ import annotations

from typing import Any

from ..anomaly.benchmark import run_benchmark
from ..domain.features import ML_FEATURES
from ..io.readers import load_gold_features
from ..logging import bind, get_logger, unbind
from ..paths import ensure_dirs
from ..release import validate_canonical_release

log = get_logger("pipeline.benchmark")


def run(quick: bool = False) -> dict[str, Any]:
    bind(stage="benchmark")
    try:
        ensure_dirs()
        gold_release = validate_canonical_release(
            "gold",
            require_current_provenance=True,
            require_current_runtime=True,
        )
        gold = load_gold_features()
        X = gold[ML_FEATURES].copy()
        log.info("benchmark.stage.start", rows=len(X), features=len(ML_FEATURES), quick=quick)
        return run_benchmark(
            X=X,
            rule_score=gold["rule_score"],
            years=gold["year"],
            quick=quick,
            expected_gold_release_sha256=gold_release.manifest_sha256,
        )
    finally:
        unbind("stage")
