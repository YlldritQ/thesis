"""The production DQ CLI must fail closed for Airflow and shell callers."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis import cli
from thesis.io import readers

runner = CliRunner()


class _Result:
    def __init__(self, *, passed: bool, errors: int = 0, warnings: int = 0):
        self.passed = passed
        self.error_count = errors
        self.warning_count = warnings
        self.pass_count = 1 if passed else 0
        self.fail_count = 0 if passed else 1

    def write(self) -> None:
        return None


def test_dq_run_rejects_unknown_suite_before_loading_data():
    result = runner.invoke(cli.app, ["dq", "run", "--suite", "does_not_exist"])

    assert result.exit_code == 2
    assert "unknown DQ suite" in result.output


def test_dq_run_exits_nonzero_when_artifacts_are_missing(monkeypatch):
    def missing():
        raise FileNotFoundError("fixture intentionally absent")

    for name in [
        "load_silver_tenders",
        "load_silver_awards",
        "load_gold_features",
        "load_gold_suppliers",
        "load_gold_entities",
        "load_monthly",
        "load_gold_tenders",
    ]:
        monkeypatch.setattr(readers, name, missing)

    result = runner.invoke(cli.app, ["dq", "run"])

    assert result.exit_code == 1
    assert "missing" in result.output
    assert "DQ failed" in result.output


def test_dq_run_exits_nonzero_when_an_error_expectation_fails(monkeypatch):
    monkeypatch.setattr(readers, "load_silver_tenders", lambda: pd.DataFrame())
    monkeypatch.setattr(
        cli,
        "run_suite",
        lambda suite, frame: _Result(passed=False, errors=1),
    )

    result = runner.invoke(
        cli.app,
        ["dq", "run", "--suite", "silver_tenders"],
    )

    assert result.exit_code == 1
    assert "1 ERROR expectation" in result.output


def test_dq_run_returns_zero_when_selected_suite_passes(monkeypatch):
    monkeypatch.setattr(readers, "load_silver_tenders", lambda: pd.DataFrame())
    monkeypatch.setattr(
        cli,
        "run_suite",
        lambda suite, frame: _Result(passed=True),
    )

    result = runner.invoke(
        cli.app,
        ["dq", "run", "--suite", "silver_tenders"],
    )

    assert result.exit_code == 0
    assert "True" not in result.output


@pytest.mark.parametrize(
    ("suite_name", "target_loader", "source_loader", "expectation_name"),
    [
        (
            "gold_supplier_summary",
            "load_gold_suppliers",
            "load_silver_awards",
            "source_award_reconciliation",
        ),
        (
            "gold_entity_summary",
            "load_gold_entities",
            "load_gold_features",
            "source_feature_reconciliation",
        ),
        (
            "gold_monthly_metrics",
            "load_monthly",
            "load_gold_features",
            "source_feature_reconciliation",
        ),
    ],
)
def test_dq_run_routes_gold_summaries_through_dynamic_source_suite(
    monkeypatch,
    suite_name,
    target_loader,
    source_loader,
    expectation_name,
):
    target = pd.DataFrame()
    if suite_name == "gold_supplier_summary":
        source = pd.DataFrame({"awarded_value_eur": pd.Series(dtype=float)})
    else:
        source = pd.DataFrame(
            {
                "ocid": pd.Series(dtype=str),
                "procuring_entity_id": pd.Series(dtype=str),
                "release_date": pd.Series(dtype="datetime64[ns, UTC]"),
                "estimated_value_eur": pd.Series(dtype=float),
                "total_awarded_eur": pd.Series(dtype=float),
            }
        )
    source_calls = 0
    seen_expectations: list[set[str]] = []

    def load_source():
        nonlocal source_calls
        source_calls += 1
        return source

    def capture_suite(suite, frame):
        assert frame is target
        seen_expectations.append({expectation.name for expectation in suite.expectations})
        return _Result(passed=True)

    monkeypatch.setattr(readers, target_loader, lambda: target)
    monkeypatch.setattr(readers, source_loader, load_source)
    monkeypatch.setattr(cli, "run_suite", capture_suite)

    result = runner.invoke(cli.app, ["dq", "run", "--suite", suite_name])

    assert result.exit_code == 0
    assert source_calls == 1
    assert expectation_name in seen_expectations[0]
