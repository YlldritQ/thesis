"""Unit tests for the lineage module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from pyarrow.parquet import ParquetFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.lineage import file_sha256, schema_fingerprint


def test_file_sha256_stable(tmp_path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"hello world")
    h1 = file_sha256(p)
    h2 = file_sha256(p)
    assert h1 == h2
    assert len(h1) == 64


def test_file_sha256_missing_returns_empty(tmp_path):
    assert file_sha256(tmp_path / "nope") == ""


def test_schema_fingerprint_stable():
    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    assert schema_fingerprint(df) == schema_fingerprint(df)
    df2 = df.rename(columns={"a": "A"})
    assert schema_fingerprint(df) != schema_fingerprint(df2)


def test_write_dataframe_emits_sidecar(tmp_path, monkeypatch):
    monkeypatch.setenv("THESIS_DATA_DIR", str(tmp_path))
    # Force re-import of paths so LINEAGE points to the tmp dir
    import importlib

    from thesis import config, paths

    config.reset_settings_for_tests()
    importlib.reload(paths)
    from thesis import lineage as lin_module

    importlib.reload(lin_module)
    from thesis.lineage import write_dataframe as wdf  # re-bind

    out = tmp_path / "test.parquet"
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
    wdf(df, out, table="test", layer="silver")
    assert out.exists()
    sidecar = out.with_suffix(out.suffix + ".lineage.json")
    assert sidecar.exists()
    payload = json.loads(sidecar.read_text())
    assert payload["table"] == "test"
    assert payload["rows"] == 3
    assert payload["columns"] == 2
    assert payload["output_sha256"]  # populated post-write

    # This test reloads singleton-bearing modules; restore their process state
    # so later tests cannot inherit the temporary data root.
    monkeypatch.delenv("THESIS_DATA_DIR", raising=False)
    config.reset_settings_for_tests()
    importlib.reload(paths)
    importlib.reload(lin_module)


def test_write_dataframe_fingerprints_persisted_arrow_schema(tmp_path, monkeypatch):
    from thesis import lineage

    monkeypatch.setattr(lineage.paths, "DATA", tmp_path)
    output = tmp_path / "gold" / "canonicalized-schema.parquet"
    frame = pd.DataFrame(
        {
            "all_null_object": pd.Series([None, None], dtype=object),
            "timestamp": pd.to_datetime(["2024-01-01", None], utc=True),
        }
    )

    lineage.write_dataframe(frame, output, table="gold.schema", layer="gold")

    sidecar = json.loads(output.with_suffix(".parquet.lineage.json").read_text())
    persisted_schema = ParquetFile(output).schema_arrow.empty_table().to_pandas()
    assert sidecar["schema_fingerprint"] == lineage.schema_fingerprint(persisted_schema)


def test_track_does_not_publish_lineage_when_body_fails(tmp_path, monkeypatch):
    from thesis import lineage

    writes: list[str] = []
    monkeypatch.setattr(lineage.Lineage, "write", lambda self: writes.append(self.output_path))

    with (
        pytest.raises(RuntimeError, match="builder failed"),
        lineage.track("broken", "gold", tmp_path / "broken.parquet"),
    ):
        raise RuntimeError("builder failed")

    assert writes == []
