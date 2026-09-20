"""Airflow DAG: kosovo_procurement_pipeline.

Production deployment delegates to the same Typer CLI used locally, so the
DAG stays tiny — pipeline-stage BashOperator wrappers + a DQ smoke test.

The DAG is *idempotent*: bronze checks the remote publication on every run and
promotes it only when validated content changes; downstream stages are
deterministic and safe to rebuild from the canonical snapshot.

To deploy:
1. ``pip install apache-airflow`` in the Airflow worker image (not in
   this project's pyproject — Airflow drags in 100+ deps).
2. Sym-link ``airflow_dags/`` into your Airflow ``dags_folder``.
3. Set the Airflow Variable / env var ``THESIS_PROJECT_ROOT`` to the
   repo path on the worker.

For a thesis-grade deployment the Variables can be set once via:

    airflow variables set thesis_project_root /opt/kosovo-procurement-thesis
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
except ImportError:  # pragma: no cover
    # Airflow is intentionally NOT a hard dependency of this repo.
    # The DAG file imports cleanly anywhere; it just can't be parsed
    # by Airflow itself unless Airflow is installed in the worker.
    DAG = None  # type: ignore[assignment]
    BashOperator = None  # type: ignore[assignment]

PROJECT_ROOT = os.environ.get("THESIS_PROJECT_ROOT", "/opt/kosovo-procurement-thesis")

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}


def _bash(cmd: str) -> str:
    """Run a CLI command from the project root with logging-friendly output."""
    return (
        f"set -euo pipefail; "
        f"cd {PROJECT_ROOT} && "
        f"THESIS_LOG_FORMAT=json THESIS_LOG_LEVEL=INFO "
        f"{cmd}"
    )


if DAG is not None:
    with DAG(
        dag_id="kosovo_procurement_pipeline",
        description="Kosovo OCDS bronze→silver→gold→exploratory-ranking pipeline",
        default_args=default_args,
        schedule="0 4 * * *",  # 04:00 UTC daily
        start_date=datetime(2026, 1, 1),
        catchup=False,
        max_active_runs=1,
        tags=["thesis", "ocds", "kosovo", "anomaly-ranking"],
    ) as dag:
        bronze = BashOperator(
            task_id="bronze_check_updates",
            bash_command=_bash("python -m thesis pipeline check-updates"),
        )

        silver = BashOperator(
            task_id="silver_build",
            bash_command=_bash("python -m thesis pipeline silver"),
        )

        gold = BashOperator(
            task_id="gold_build",
            bash_command=_bash("python -m thesis pipeline gold"),
        )

        benchmark = BashOperator(
            task_id="benchmark_model_selection",
            bash_command=_bash("python -m thesis pipeline benchmark"),
            # Full checkpointed election is intentionally slower than routine
            # transformation tasks; stale champions are rejected by ML.
            execution_timeout=timedelta(hours=4),
        )

        ml = BashOperator(
            task_id="ml_train_score",
            bash_command=_bash("python -m thesis pipeline ml"),
        )

        dq = BashOperator(
            task_id="dq_run",
            bash_command=_bash("python -m thesis dq run"),
        )

        validate_releases = BashOperator(
            task_id="validate_release_chain",
            bash_command=_bash("python -m thesis pipeline validate-releases"),
        )

        bronze >> silver >> gold >> benchmark >> ml >> dq >> validate_releases
