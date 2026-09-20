# ADR-0006: Airflow for production orchestration; lightweight DAG runner locally

* **Status:** Accepted
* **Date:** 2026-04

## Context

The repository needs to demonstrate scheduled deployment while remaining
usable ad hoc during development, demos, and debugging. Airflow carries a
metadata DB, scheduler, and webserver; forcing it into the local loop would
add friction. The submitted system remains a static snapshot, and the full
checkpointed benchmark is materially slower than the transformation stages.

## Decision

Provide **two execution paths** that share the *same* CLI:

1. **Local: `thesis.pipeline.dag.run_dag()`** — a small custom DAG
   runner that:
   * declares each task's inputs and outputs,
   * skips tasks whose outputs are newer than every input,
   * supports `--only`, `--from`, `--force`,
   * has zero external dependencies.

2. **Production: `airflow_dags/kosovo_procurement.py`** — an Airflow
   DAG of `BashOperator`s, each running `python -m thesis pipeline …`.
   The DAG ships in this repo but Airflow is **not** a dependency of
   `pyproject.toml` — it's the worker image's responsibility.

Both paths invoke the same CLI subcommands, so local and scheduled execution
use the same stage implementations. The canonical sequence is
bronze → silver → gold/`tender_features` → benchmark → ML/`tender_summary`.
The Airflow example appends a standalone DQ evidence task; the producing
silver and ML stages already enforce their pre-publication DQ gates.

## Consequences

**Positive:**

* Local dev stays instant (no Airflow infra to spin up).
* Production gets retries, alerts, scheduling, dependency graphs.
* The CLI is the contract between the two — adding a new stage
  changes the CLI once and both paths pick it up.

**Negative:**

* Two orchestration layers must be kept in sync. Both are thin wrappers around
  the same CLI, but a new stage still requires editing both task graphs.

## Migration plan if scale outgrows the local runner

Replace `dag.run_dag()` with a Prefect or Dagster runner using the same
task definitions. The CLI stays. The Airflow DAG stays.
