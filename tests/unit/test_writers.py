"""Safety tests for atomic artifact publication."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pyarrow.parquet import ParquetFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.io import writers


def test_write_json_replaces_only_after_complete_serialization(tmp_path):
    target = tmp_path / "artifact.json"
    target.write_text('{"status": "old"}')

    circular: list[object] = []
    circular.append(circular)
    with pytest.raises(ValueError, match="Circular reference"):
        writers.write_json(circular, target)

    assert json.loads(target.read_text()) == {"status": "old"}
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))


def test_write_json_uses_strict_scientific_python_types(tmp_path):
    target = tmp_path / "artifact.json"

    writers.write_json(
        {
            "bool": np.bool_(True),
            "integer": np.int64(7),
            "finite": np.float64(1.25),
            "missing": np.float64(np.nan),
            "timestamp": pd.Timestamp(datetime(2026, 7, 18, tzinfo=timezone.utc)),
        },
        target,
    )

    assert json.loads(target.read_text()) == {
        "bool": True,
        "integer": 7,
        "finite": 1.25,
        "missing": None,
        "timestamp": "2026-07-18T00:00:00+00:00",
    }
    assert "NaN" not in target.read_text()


def test_write_json_rejects_unsupported_object_without_overwrite(tmp_path):
    target = tmp_path / "artifact.json"
    target.write_text('{"status": "old"}')

    with pytest.raises(TypeError, match="not JSON serializable"):
        writers.write_json({"bad": object()}, target)

    assert json.loads(target.read_text()) == {"status": "old"}


def test_write_parquet_failure_preserves_prior_canonical(tmp_path, monkeypatch):
    target = tmp_path / "artifact.parquet"
    target.write_bytes(b"last-known-good")
    frame = pd.DataFrame({"value": [1, 2, 3]})

    def fail_after_partial_write(self, path, index=False):
        del self, index
        Path(path).write_bytes(b"partial-new-file")
        raise RuntimeError("serializer failed")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_after_partial_write)
    with pytest.raises(RuntimeError, match="serializer failed"):
        writers.write_parquet(
            frame,
            target,
            table="test.atomic",
            layer="test",
        )

    assert target.read_bytes() == b"last-known-good"
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))


def test_write_parquet_lineage_fingerprints_persisted_arrow_schema(tmp_path, monkeypatch):
    from thesis import paths
    from thesis.lineage import schema_fingerprint

    # Lineage.write() also publishes a chronological audit copy. Keep that
    # secondary write inside the test sandbox instead of polluting data/_lineage.
    canonical_history = paths.DATA / "_lineage" / "test.schema"
    canonical_before = set(canonical_history.glob("*.json"))
    isolated_data = tmp_path / "data"
    monkeypatch.setattr(paths, "DATA", isolated_data)

    target = tmp_path / "canonicalized-schema.parquet"
    frame = pd.DataFrame(
        {
            "all_null_object": pd.Series([None, None], dtype=object),
            "timestamp": pd.to_datetime(["2024-01-01", None], utc=True),
        }
    )

    writers.write_parquet(frame, target, table="test.schema", layer="test")

    sidecar = json.loads(target.with_suffix(".parquet.lineage.json").read_text())
    persisted_schema = ParquetFile(target).schema_arrow.empty_table().to_pandas()
    assert sidecar["schema_fingerprint"] == schema_fingerprint(persisted_schema)
    assert len(list((isolated_data / "_lineage" / "test.schema").glob("*.json"))) == 1
    assert set(canonical_history.glob("*.json")) == canonical_before


def test_write_joblib_failure_preserves_prior_canonical(tmp_path, monkeypatch):
    target = tmp_path / "model.joblib"
    target.write_bytes(b"last-known-good")

    def fail_after_partial_write(obj, path):
        del obj
        Path(path).write_bytes(b"partial-new-model")
        raise RuntimeError("serializer failed")

    monkeypatch.setattr(writers.joblib, "dump", fail_after_partial_write)
    with pytest.raises(RuntimeError, match="serializer failed"):
        writers.write_joblib({"model": object()}, target)

    assert target.read_bytes() == b"last-known-good"
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))


def test_write_joblib_publishes_loadable_model(tmp_path):
    target = tmp_path / "model.joblib"
    payload = {"family": "test", "parameters": [1, 2, 3]}

    writers.write_joblib(payload, target)

    assert writers.joblib.load(target) == payload
    assert not list(tmp_path.glob(f".{target.name}.*.tmp"))
