"""Regression tests for pipeline publication and scheduling safety."""

from __future__ import annotations

import sys
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly.rules import RULES
from thesis.pipeline import dag, gold, silver


class _DQResult:
    def __init__(
        self,
        *,
        passed: bool,
        errors: int = 0,
        warnings: int = 0,
        suite: str = "fixture",
    ):
        self.passed = passed
        self.error_count = errors
        self.warning_count = warnings
        self.suite = suite
        self.written = False

    def write(self):
        self.written = True

    def release_payload(self, artifact, frame):
        return {"suite": self.suite, "rows": len(frame), "artifact": str(artifact)}


def test_silver_dq_failure_does_not_publish_canonical_frames(monkeypatch):
    tenders = pd.DataFrame({"ocid": ["one"]})
    awards = pd.DataFrame({"ocid": ["one"]})
    tender_result = _DQResult(passed=False, errors=1)
    award_result = _DQResult(passed=True)
    results = iter([tender_result, award_result])
    publications: list[Path] = []

    monkeypatch.setattr(silver, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        silver,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="bronze-generation"),
    )
    monkeypatch.setattr(silver, "_build_silver_tables", lambda: (tenders, awards))
    monkeypatch.setattr(
        silver,
        "validate_dataframe",
        lambda frame, model, sample: (frame, []),
    )
    monkeypatch.setattr(silver, "validate_silver_tenders", lambda frame: frame)
    monkeypatch.setattr(silver, "validate_silver_awards", lambda frame: frame)
    monkeypatch.setattr(silver, "run_suite", lambda suite, frame: next(results))
    monkeypatch.setattr(
        silver,
        "write_parquet",
        lambda frame, path, **kwargs: publications.append(path),
    )

    with pytest.raises(ValueError, match="silver DQ ERROR"):
        silver.run()

    assert tender_result.written and award_result.written
    assert publications == []


def test_silver_row_contract_failure_always_blocks_publication(monkeypatch):
    tenders = pd.DataFrame({"ocid": ["one"]})
    awards = pd.DataFrame({"ocid": ["one"]})
    publications: list[Path] = []
    calls = iter([(1, ["row 0: invalid"]), (1, [])])

    monkeypatch.setattr(silver, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        silver,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="bronze-generation"),
    )
    monkeypatch.setattr(silver, "_build_silver_tables", lambda: (tenders, awards))
    monkeypatch.setattr(silver, "validate_dataframe", lambda frame, model, sample: next(calls))
    monkeypatch.setattr(
        silver,
        "write_parquet",
        lambda frame, path, **kwargs: publications.append(path),
    )

    with pytest.raises(ValueError, match="silver.tenders contract violation"):
        silver.run()

    assert publications == []


def test_gold_feature_dq_failure_does_not_publish_any_gold_artifact(monkeypatch):
    tenders = pd.DataFrame({"ocid": ["one"]})
    awards = pd.DataFrame({"ocid": ["one"]})
    features = pd.DataFrame(
        {
            "ocid": ["one"],
            "release_date": [pd.Timestamp("2024-01-01", tz="UTC")],
        }
    )
    rule_values = {rule.code: [False] for rule in RULES}
    rules = pd.DataFrame(
        {
            **rule_values,
            "rule_score": [0.0],
            "rule_count": [0],
            "indicator_count": [0],
            "diagnostic_count": [0],
        }
    )
    dq_failure = _DQResult(passed=False, errors=1)
    publications: list[Path] = []

    monkeypatch.setattr(gold, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        gold,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="silver-generation"),
    )
    monkeypatch.setattr(gold, "load_silver_bundle", lambda: (tenders, awards))
    monkeypatch.setattr(gold, "build_tender_features", lambda t, a: features)
    monkeypatch.setattr(gold, "apply_rules", lambda frame: rules)
    monkeypatch.setattr(gold, "run_suite", lambda suite, frame: dq_failure)
    monkeypatch.setattr(
        gold,
        "write_parquet",
        lambda frame, path, **kwargs: publications.append(path),
    )

    with pytest.raises(ValueError, match="gold feature DQ ERROR"):
        gold.run()

    assert dq_failure.written
    assert publications == []


def test_gold_summary_reconciliation_suites_use_live_and_persisted_sources(monkeypatch):
    tenders = pd.DataFrame({"ocid": ["one"]})
    awards = pd.DataFrame({"ocid": ["one"], "awarded_value_eur": [10.0]})
    features = pd.DataFrame(
        {
            "ocid": ["one"],
            "release_date": [pd.Timestamp("2024-01-01", tz="UTC")],
        }
    )
    rules = pd.DataFrame(
        {
            **{rule.code: [False] for rule in RULES},
            "rule_score": [0.0],
            "rule_count": [0],
            "indicator_count": [0],
            "diagnostic_count": [0],
        }
    )
    supplier_summary = pd.DataFrame({"supplier_key": ["supplier"]})
    entity_summary = pd.DataFrame({"procuring_entity_id": ["entity"]})
    monthly_summary = pd.DataFrame({"period_label": ["2024-01"]})
    persisted_features = pd.DataFrame({"ocid": ["persisted-one"]})
    persisted = {
        gold.GOLD_FEATURES: persisted_features,
        gold.GOLD_SUPPLIERS: supplier_summary.copy(),
        gold.GOLD_ENTITIES: entity_summary.copy(),
        gold.GOLD_MONTHLY: monthly_summary.copy(),
    }
    supplier_sources: list[pd.DataFrame] = []
    entity_sources: list[pd.DataFrame] = []
    monthly_sources: list[pd.DataFrame] = []
    publications: list[Path] = []
    release_payloads: list[Path] = []

    def supplier_suite_for(source):
        supplier_sources.append(source)
        return SimpleNamespace(name="gold_supplier_summary")

    def entity_suite_for(source):
        entity_sources.append(source)
        return SimpleNamespace(name="gold_entity_summary")

    def monthly_suite_for(source):
        monthly_sources.append(source)
        return SimpleNamespace(name="gold_monthly_metrics")

    monkeypatch.setattr(gold, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        gold,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="silver-generation"),
    )
    monkeypatch.setattr(gold, "load_silver_bundle", lambda: (tenders, awards))
    monkeypatch.setattr(gold, "build_tender_features", lambda t, a: features)
    monkeypatch.setattr(gold, "apply_rules", lambda frame: rules)
    monkeypatch.setattr(gold, "_supplier_summary", lambda a, f: supplier_summary)
    monkeypatch.setattr(gold, "_entity_summary", lambda a, f: entity_summary)
    monkeypatch.setattr(gold, "_monthly", lambda f: monthly_summary)
    monkeypatch.setattr(gold, "gold_supplier_summary_suite_for", supplier_suite_for)
    monkeypatch.setattr(gold, "gold_entity_summary_suite_for", entity_suite_for)
    monkeypatch.setattr(gold, "gold_monthly_metrics_suite_for", monthly_suite_for)
    monkeypatch.setattr(
        gold,
        "run_suite",
        lambda suite, frame: _DQResult(passed=True, suite=suite.name),
    )
    monkeypatch.setattr(
        gold,
        "write_parquet",
        lambda frame, path, **kwargs: publications.append(path),
    )
    monkeypatch.setattr(gold.pd, "read_parquet", lambda path: persisted[path])
    monkeypatch.setattr(gold, "write_json", lambda payload, path: release_payloads.append(path))
    monkeypatch.setattr(gold, "publish_release", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        gold,
        "settings",
        lambda: SimpleNamespace(fail_fast_on_dq=False),
    )

    result = gold.run()

    assert result == {
        "tender_features": 1,
        "supplier_summary": 1,
        "entity_summary": 1,
        "monthly_metrics": 1,
    }
    assert len(supplier_sources) == 2
    assert all(source is awards for source in supplier_sources)
    assert len(entity_sources) == 2
    assert len(monthly_sources) == 2
    assert entity_sources[0] is monthly_sources[0]
    assert entity_sources[1] is persisted_features
    assert monthly_sources[1] is persisted_features
    assert set(publications) == {
        gold.GOLD_FEATURES,
        gold.GOLD_SUPPLIERS,
        gold.GOLD_ENTITIES,
        gold.GOLD_MONTHLY,
    }
    assert set(release_payloads) == {
        gold.GOLD_FEATURES_RELEASE_DQ,
        gold.GOLD_SUPPLIERS_RELEASE_DQ,
        gold.GOLD_ENTITIES_RELEASE_DQ,
        gold.GOLD_MONTHLY_RELEASE_DQ,
    }


def test_default_dag_always_checks_remote_bronze():
    from thesis.pipeline import bronze

    bronze_task = dag.default_dag()["bronze"]
    assert bronze_task.fn is bronze.check_updates
    assert bronze_task.always_run


def test_always_run_task_is_not_skipped_when_outputs_are_fresh(tmp_path, monkeypatch):
    output = tmp_path / "ready"
    output.write_text("ready")
    calls: list[str] = []
    task = dag.Task(
        name="remote",
        fn=lambda: calls.append("remote"),
        outputs=[output],
        always_run=True,
    )
    monkeypatch.setattr(
        dag,
        "default_dag",
        lambda: OrderedDict([("remote", task)]),
    )

    result = dag.run_dag()

    assert calls == ["remote"]
    assert result["remote"]["status"] == "ok"


def test_force_runs_an_otherwise_fresh_task(tmp_path, monkeypatch):
    output = tmp_path / "ready"
    output.write_text("ready")
    calls: list[str] = []
    task = dag.Task(
        name="local",
        fn=lambda: calls.append("local"),
        outputs=[output],
    )
    monkeypatch.setattr(
        dag,
        "default_dag",
        lambda: OrderedDict([("local", task)]),
    )

    assert dag.run_dag()["local"] == "skipped"
    dag.run_dag(force=True)

    assert calls == ["local"]


def test_task_cannot_report_success_without_declared_output(tmp_path, monkeypatch):
    task = dag.Task(
        name="broken",
        fn=lambda: {"claimed": "ok"},
        outputs=[tmp_path / "never-published"],
    )
    monkeypatch.setattr(
        dag,
        "default_dag",
        lambda: OrderedDict([("broken", task)]),
    )

    with pytest.raises(RuntimeError, match="without publishing a complete"):
        dag.run_dag(force=True)
