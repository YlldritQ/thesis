"""DAG runner — declarative task graph + freshness-aware execution.

Why a custom runner instead of Airflow locally?
* Airflow needs a metadata DB, a scheduler, a webserver — overkill for a
  single-machine thesis pipeline.
* The same task definitions are re-exposed as Airflow ``BashOperator``
  tasks under ``airflow_dags/`` for production deployments. This runner
  stays the local-development entrypoint.

Each task declares its outputs. ``run()`` skips a task when **every** output
exists *and* is newer than every input — unless ``--force`` is set or the task
is a remote-source check marked ``always_run``.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .. import paths
from ..locking import pipeline_lock
from ..logging import bind, get_logger, unbind
from ..release import (
    ReleaseIntegrityError,
    canonical_release_contract,
    validate_canonical_release,
    validate_release,
)

log = get_logger("dag")


@dataclass
class Task:
    name: str
    fn: Callable[[], object]
    inputs: list[Path] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    release_manifest: Optional[Path] = None
    # Remote-source checks cannot be decided from local mtimes. They still
    # expose output freshness in ``pipeline status``, but execute on every DAG
    # run so an upstream correction with unchanged cardinality is discovered.
    always_run: bool = False


def _is_fresh(t: Task) -> bool:
    if not t.outputs:
        return False
    for o in t.outputs:
        if not o.exists():
            return False
    if t.release_manifest is not None:
        if t.release_manifest not in t.outputs:
            return False
        try:
            contract = canonical_release_contract(t.name)
            if contract.manifest.resolve() == t.release_manifest.resolve():
                validate_canonical_release(
                    t.name,
                    require_current_provenance=True,
                    require_current_runtime=True,
                )
            else:
                validate_release(
                    t.release_manifest,
                    expected_stage=t.name,
                    required_inputs=t.inputs,
                    required_artifacts=[
                        output for output in t.outputs if output != t.release_manifest
                    ],
                    require_current_provenance=True,
                    require_current_runtime=True,
                )
        except ReleaseIntegrityError as exc:
            log.warning(
                "task.release_invalid",
                task=t.name,
                manifest=str(t.release_manifest),
                error=str(exc),
            )
            return False
        # The release validator has checked exact input/output bytes,
        # provenance and the recursive upstream chain. Timestamps add no
        # information and would make a mere ``touch`` spuriously stale.
        return True
    output_mtime = min(o.stat().st_mtime for o in t.outputs)
    return all(not (i.exists() and i.stat().st_mtime > output_mtime) for i in t.inputs)


def default_dag() -> OrderedDict[str, Task]:
    """The canonical task graph. Edit here when adding pipeline stages.

    ``gold`` publishes an immutable unscored feature table. ``benchmark`` reads
    that table and publishes model-selection artifacts; ``ml`` is the sole
    writer of the scored tender summary. This gives freshness checks one clear
    producer for every canonical output.
    """
    from . import benchmark, bronze, gold, ml, silver

    tasks = OrderedDict()
    tasks["bronze"] = Task(
        name="bronze",
        fn=bronze.check_updates,
        outputs=[paths.RAW_GZ, paths.RAW_JSONL, paths.BRONZE_RELEASE],
        release_manifest=paths.BRONZE_RELEASE,
        always_run=True,
    )
    tasks["silver"] = Task(
        name="silver",
        fn=silver.run,
        inputs=[paths.BRONZE_RELEASE, paths.RAW_JSONL],
        outputs=[
            paths.SILVER_TENDERS,
            paths.SILVER_AWARDS,
            paths.SILVER_TENDERS_RELEASE_DQ,
            paths.SILVER_AWARDS_RELEASE_DQ,
            paths.SILVER_RELEASE,
        ],
        depends_on=["bronze"],
        release_manifest=paths.SILVER_RELEASE,
    )
    tasks["gold"] = Task(
        name="gold",
        fn=gold.run,
        inputs=[paths.SILVER_RELEASE, paths.SILVER_TENDERS, paths.SILVER_AWARDS],
        outputs=[
            paths.GOLD_FEATURES,
            paths.GOLD_SUPPLIERS,
            paths.GOLD_ENTITIES,
            paths.GOLD_MONTHLY,
            paths.GOLD_FEATURES_RELEASE_DQ,
            paths.GOLD_SUPPLIERS_RELEASE_DQ,
            paths.GOLD_ENTITIES_RELEASE_DQ,
            paths.GOLD_MONTHLY_RELEASE_DQ,
            paths.GOLD_RELEASE,
        ],
        depends_on=["silver"],
        release_manifest=paths.GOLD_RELEASE,
    )
    tasks["benchmark"] = Task(
        name="benchmark",
        fn=benchmark.run,
        inputs=[paths.GOLD_RELEASE, paths.GOLD_FEATURES],
        outputs=[
            paths.BENCHMARK_RESULTS,
            paths.CHAMPIONS,
            paths.BENCHMARK_LEADERBOARD,
            paths.BENCHMARK_LEADERBOARD_MD,
            paths.BENCHMARK_RELEASE_DQ,
            paths.BENCHMARK_RELEASE,
        ],
        depends_on=["gold"],
        release_manifest=paths.BENCHMARK_RELEASE,
    )
    tasks["ml"] = Task(
        name="ml",
        fn=ml.run,
        inputs=[
            paths.GOLD_RELEASE,
            paths.GOLD_FEATURES,
            paths.BENCHMARK_RELEASE,
            paths.BENCHMARK_RESULTS,
            paths.BENCHMARK_LEADERBOARD,
            paths.CHAMPIONS,
        ],
        outputs=[
            paths.CHAMPION_MODELS,
            paths.HGB_MODEL,
            paths.SHAP_VALUES,
            paths.MODEL_VALIDATION,
            paths.FEATURE_LIST,
            paths.GOLD_TENDERS,
            paths.GOLD_TENDERS_RELEASE_DQ,
            paths.SHAP_VALUES_RELEASE_DQ,
            paths.ML_RELEASE,
        ],
        depends_on=["benchmark"],
        release_manifest=paths.ML_RELEASE,
    )
    return tasks


def _run_dag_unlocked(
    only: list[str] | None = None,
    force: bool = False,
    starting_from: str | None = None,
) -> dict[str, dict | str]:
    """Execute (a subset of) the DAG in topological order.

    Args:
        only: If given, run *only* these tasks (and assume their deps are fresh).
        force: If True, ignore freshness and run every task in scope. Task
            functions still keep their own safety checks; in particular the
            bronze refresh validates the staged remote snapshot before swap.
        starting_from: If given, run this task and everything after it.
    """
    dag = default_dag()
    order = list(dag.keys())

    if only:
        unknown = sorted(set(only) - set(dag))
        if unknown:
            raise KeyError(f"unknown task(s): {', '.join(unknown)} (known: {', '.join(order)})")
        scope = [t for t in order if t in only]
    elif starting_from:
        if starting_from not in dag:
            raise KeyError(f"unknown task: {starting_from}")
        scope = order[order.index(starting_from) :]
    else:
        scope = order

    log.info("dag.run", tasks=scope, force=force)
    results: dict[str, dict | str] = {}
    for name in scope:
        t = dag[name]
        if not force and not t.always_run and _is_fresh(t):
            log.info("task.skip", task=name, reason="outputs fresh")
            results[name] = "skipped"
            continue
        bind(task=name)
        try:
            log.info(
                "task.start",
                task=name,
                inputs=[str(p) for p in t.inputs],
                outputs=[str(p) for p in t.outputs],
            )
            started = time.time()
            res = t.fn()
            if not _is_fresh(t):
                raise RuntimeError(
                    f"task {name!r} returned without publishing a complete, "
                    "current, hash-valid output generation"
                )
            duration = round(time.time() - started, 2)
            log.info("task.done", task=name, duration_s=duration)
            results[name] = {"status": "ok", "duration_s": duration, "result": res}
        finally:
            unbind("task")
    return results


def run_dag(
    only: list[str] | None = None,
    force: bool = False,
    starting_from: str | None = None,
) -> dict[str, dict | str]:
    """Execute the DAG while holding the canonical single-writer lock."""
    with pipeline_lock():
        return _run_dag_unlocked(
            only=only,
            force=force,
            starting_from=starting_from,
        )
