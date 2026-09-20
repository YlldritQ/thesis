"""Typer-based CLI.

Every pipeline stage and DQ-suite is exposed here. Examples::

    thesis pipeline run                # full DAG
    thesis pipeline run --only ml      # one stage, force re-run
    thesis pipeline status             # which artifacts are stale?
    thesis dq run                      # all DQ suites against current gold/silver
    thesis info                        # dataset summary
    thesis version
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, paths
from .config import settings
from .dq.framework import run_suite
from .dq.suites import (
    ALL_SUITES,
    gold_entity_summary_suite_for,
    gold_monthly_metrics_suite_for,
    gold_supplier_summary_suite_for,
    gold_tender_features_suite_for,
    silver_awards_suite_for,
)
from .jsonutil import dumps_json
from .locking import pipeline_lock
from .logging import configure as configure_logging
from .logging import get_logger
from .pipeline.dag import _is_fresh, default_dag, run_dag

console = Console()
log = get_logger("cli")

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Kosovo public-procurement heuristic-screening and exploratory-ranking pipeline.",
)
pipeline_app = typer.Typer(no_args_is_help=True, help="Run the data pipeline.")
dq_app = typer.Typer(no_args_is_help=True, help="Data-quality commands.")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(dq_app, name="dq")


# =====================================================================
#  pipeline
# =====================================================================
@pipeline_app.command("run")
def pipeline_run(
    only: Optional[list[str]] = typer.Option(
        None, "--only", help="Run only these tasks (comma- or repeated)."
    ),
    starting_from: Optional[str] = typer.Option(
        None, "--from", help="Run this task and everything after it."
    ),
    force: bool = typer.Option(False, "--force", help="Ignore freshness checks."),
) -> None:
    """Execute the pipeline DAG."""
    configure_logging()
    only_list = None
    if only:
        only_list = [t.strip() for tasks in only for t in tasks.split(",") if t.strip()]
    res = run_dag(only=only_list, force=force, starting_from=starting_from)
    console.print_json(dumps_json(res, indent=2))


@pipeline_app.command("status")
def pipeline_status() -> None:
    """Show DAG task freshness."""
    dag = default_dag()
    table = Table(title="Pipeline DAG status")
    table.add_column("task")
    table.add_column("fresh")
    table.add_column("outputs")
    for name, t in dag.items():
        outs_present = sum(1 for o in t.outputs if o.exists())
        fresh = "✓" if _is_fresh(t) else "✗"
        table.add_row(name, fresh, f"{outs_present}/{len(t.outputs)}")
    console.print(table)


# =====================================================================
#  individual stages
# =====================================================================
@pipeline_app.command("bronze")
def cmd_bronze(force: bool = typer.Option(False, "--force")) -> None:
    """Download + extract raw OCDS data."""
    configure_logging()
    from .pipeline.bronze import run

    with pipeline_lock():
        res = run(force_download=force, force_extract=force)
    console.print_json(dumps_json(res, indent=2))


@pipeline_app.command("silver")
def cmd_silver() -> None:
    """Build silver layer."""
    configure_logging()
    from .pipeline.silver import run

    with pipeline_lock():
        result = run()
    console.print_json(dumps_json(result, indent=2))


@pipeline_app.command("gold")
def cmd_gold() -> None:
    """Build gold layer."""
    configure_logging()
    from .pipeline.gold import run

    with pipeline_lock():
        result = run()
    console.print_json(dumps_json(result, indent=2))


@pipeline_app.command("ml")
def cmd_ml() -> None:
    """Fit exploratory rankers + write SHAP and diagnostic report."""
    configure_logging()
    from .pipeline.ml import run

    with pipeline_lock():
        result = run()
    console.print_json(dumps_json(result, indent=2))


@pipeline_app.command("benchmark")
def cmd_benchmark(
    quick: bool = typer.Option(
        False, "--quick", help="Tiny grid for smoke-testing (seconds instead of hours)."
    ),
) -> None:
    """Run the multi-model rule-proxy benchmark (checkpoint/resume-safe)."""
    configure_logging()
    from .pipeline.benchmark import run

    with pipeline_lock():
        result = run(quick=quick)
    console.print_json(dumps_json(result, indent=2))


@pipeline_app.command("check-updates")
def cmd_check_updates() -> None:
    """Check the upstream OCDS publication for new tender records."""
    configure_logging()
    from .pipeline.bronze import check_updates

    with pipeline_lock():
        result = check_updates()
    console.print_json(dumps_json(result, indent=2))


@pipeline_app.command("validate-releases")
def cmd_validate_releases() -> None:
    """Validate every release, its hashes, DQ evidence, and upstream chain."""
    from .release import ReleaseIntegrityError, validate_canonical_release

    table = Table(title="Release-manifest validation")
    table.add_column("stage")
    table.add_column("valid")
    table.add_column("manifest sha256")
    failures: list[str] = []
    for stage in ("bronze", "silver", "gold", "benchmark", "ml"):
        try:
            validated = validate_canonical_release(
                stage,
                require_current_provenance=True,
                require_current_runtime=True,
            )
        except ReleaseIntegrityError as exc:
            failures.append(f"{stage}: {exc}")
            table.add_row(stage, "✗", str(exc)[:80])
        else:
            table.add_row(stage, "✓", validated.manifest_sha256)
    console.print(table)
    if failures:
        raise typer.Exit(code=1)


# =====================================================================
#  DQ
# =====================================================================
@dq_app.command("run")
def dq_run(
    suite: Optional[str] = typer.Option(None, "--suite", help="Limit to one suite name."),
) -> None:
    """Run expectation suites and exit nonzero on operational/DQ failure."""
    configure_logging()
    from .io.readers import (
        load_gold_entities,
        load_gold_features,
        load_gold_suppliers,
        load_gold_tenders,
        load_monthly,
        load_silver_awards,
        load_silver_tenders,
    )

    table_loaders = {
        "silver_tenders": load_silver_tenders,
        "silver_awards": load_silver_awards,
        "gold_tender_features": load_gold_features,
        "gold_supplier_summary": load_gold_suppliers,
        "gold_entity_summary": load_gold_entities,
        "gold_monthly_metrics": load_monthly,
        "gold_tender_summary": load_gold_tenders,
    }
    known_suites = {item.name for item in ALL_SUITES}
    if suite and suite not in known_suites:
        raise typer.BadParameter(
            f"unknown DQ suite {suite!r}; expected one of {sorted(known_suites)}",
            param_hint="--suite",
        )

    rows = []
    failures: list[str] = []
    selected_suites = [item for item in ALL_SUITES if not suite or item.name == suite]
    for s in selected_suites:
        loader = table_loaders.get(s.name)
        if loader is None:
            console.print(f"[red]error[/red] {s.name} — no loader registered")
            failures.append(f"{s.name}: no loader registered")
            continue
        try:
            df = loader()
            suite_to_run = s
            if s.name == "silver_awards":
                silver_tender_source = load_silver_tenders()
                suite_to_run = silver_awards_suite_for(silver_tender_source["ocid"])
            elif s.name == "gold_tender_features":
                silver_source = load_silver_tenders()
                suite_to_run = gold_tender_features_suite_for(silver_source["ocid"])
            elif s.name == "gold_supplier_summary":
                suite_to_run = gold_supplier_summary_suite_for(load_silver_awards())
            elif s.name == "gold_entity_summary":
                suite_to_run = gold_entity_summary_suite_for(load_gold_features())
            elif s.name == "gold_monthly_metrics":
                suite_to_run = gold_monthly_metrics_suite_for(load_gold_features())
        except FileNotFoundError as e:
            console.print(f"[red]missing[/red] {s.name}: {e}")
            failures.append(f"{s.name}: missing artifact")
            continue
        result = run_suite(suite_to_run, df)
        result.write()
        if not result.passed:
            failures.append(f"{s.name}: {result.error_count} ERROR expectation(s)")
        elif settings().fail_fast_on_dq and result.warning_count:
            failures.append(
                f"{s.name}: {result.warning_count} WARNING expectation(s) "
                "with THESIS_FAIL_FAST_ON_DQ=true"
            )
        rows.append(
            (
                s.name,
                result.passed,
                result.error_count,
                result.warning_count,
                result.pass_count,
                result.fail_count,
            )
        )

    t = Table(title="DQ suites")
    for col in ["suite", "passed", "errors", "warnings", "pass", "fail"]:
        t.add_column(col)
    for r in rows:
        t.add_row(
            *[
                ("✓" if isinstance(v, bool) and v else "✗" if isinstance(v, bool) else str(v))
                for v in r
            ]
        )
    console.print(t)
    if failures:
        console.print("[red]DQ failed:[/red] " + "; ".join(failures))
        raise typer.Exit(code=1)


@dq_app.command("list")
def dq_list() -> None:
    """List every expectation in every suite."""
    t = Table(title="Expectations")
    for col in ["suite", "name", "severity", "description"]:
        t.add_column(col)
    for s in ALL_SUITES:
        for e in s.expectations:
            t.add_row(s.name, e.name, e.severity.value, e.description)
    console.print(t)


# =====================================================================
#  info / version / streamlit
# =====================================================================
report_app = typer.Typer(no_args_is_help=True, help="Generate reports from live data.")
app.add_typer(report_app, name="report")


@report_app.command("findings")
def cmd_report_findings() -> None:
    """Regenerate docs/findings.md from the current gold layer (no stale numbers)."""
    configure_logging()
    from .reporting import generate

    generate(write=True)
    console.print("[green]docs/findings.md regenerated from live gold.[/green]")


@report_app.command("external-validation")
def cmd_external_validation() -> None:
    """Write the OSHP evidence-withdrawal status (legacy command name)."""
    configure_logging()
    from .external.oshp import validate

    r = validate(write=True)
    console.print_json(dumps_json(r, indent=2))


@report_app.command("audit-sample")
def cmd_audit_sample(
    per_quadrant: int = typer.Option(
        50,
        "--per-quadrant",
        min=1,
        help="Unlabelled tenders sampled from each rule×ensemble quadrant.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Replace an existing queue; preserve any human labels first.",
    ),
) -> None:
    """Create a deterministic four-quadrant queue for human review."""
    configure_logging()
    from .audit import generate_audit_sample

    result = generate_audit_sample(per_quadrant=per_quadrant, force=force)
    console.print_json(dumps_json(result, indent=2))


@app.command()
def version() -> None:
    """Print the package version."""
    console.print(__version__)


@app.command()
def info() -> None:
    """Summarise the current data warehouse."""
    configure_logging()
    cfg = settings()
    t = Table(title="thesis info")
    t.add_column("setting")
    t.add_column("value")
    t.add_row("version", __version__)
    t.add_row("project_root", str(cfg.project_root))
    t.add_row("data_dir", str(cfg.data_dir))
    t.add_row("log_level", cfg.log_level)
    t.add_row("log_format", cfg.log_format)
    t.add_row("random_seed", str(cfg.random_seed))
    console.print(t)

    art = Table(title="artifacts on disk")
    art.add_column("path")
    art.add_column("size_mb")
    art.add_column("present")
    for p in [
        paths.RAW_JSONL,
        paths.SILVER_TENDERS,
        paths.SILVER_AWARDS,
        paths.GOLD_TENDERS,
        paths.GOLD_SUPPLIERS,
        paths.GOLD_ENTITIES,
        paths.GOLD_MONTHLY,
        paths.SHAP_VALUES,
        paths.MODEL_VALIDATION,
    ]:
        size = round(p.stat().st_size / 1e6, 2) if p.exists() else None
        art.add_row(
            str(p.relative_to(cfg.project_root)),
            str(size) if size is not None else "—",
            "✓" if p.exists() else "✗",
        )
    console.print(art)


@app.command("ui")
def cmd_ui(
    port: int = typer.Option(8501, "--port"),
    host: str = typer.Option("localhost", "--host"),
    headless: bool = typer.Option(False, "--headless"),
) -> None:
    """Launch the Streamlit dashboard."""
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(settings().project_root / "streamlit_app" / "Home.py"),
        "--server.port",
        str(port),
        "--server.address",
        host,
    ]
    if headless:
        cmd += ["--server.headless", "true"]
    os.execv(sys.executable, cmd)
