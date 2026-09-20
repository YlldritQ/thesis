"""Bronze refresh tests: content hashes, validation, and atomic promotion."""

from __future__ import annotations

import gzip
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.pipeline import bronze


def _payload(rows: list[dict]) -> bytes:
    return b"".join(json.dumps(row, sort_keys=True).encode("utf-8") + b"\n" for row in rows)


def _write_gzip(path: Path, payload: bytes) -> None:
    with gzip.open(path, "wb") as out:
        out.write(payload)


def _redirect_bronze(monkeypatch, tmp_path) -> tuple[Path, Path]:
    from thesis import release

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_gz = raw_dir / "kosovo_ocds.jsonl.gz"
    raw_jsonl = raw_dir / "kosovo_ocds.jsonl"
    monkeypatch.setattr(bronze, "RAW_GZ", raw_gz)
    monkeypatch.setattr(bronze, "RAW_JSONL", raw_jsonl)
    monkeypatch.setattr(bronze, "BRONZE_RELEASE", raw_dir / "bronze.release.json")
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    monkeypatch.setattr(bronze, "ensure_dirs", lambda: None)
    return raw_gz, raw_jsonl


def _serve_file(monkeypatch, source: Path) -> None:
    def fake_download(target: Path, url=None) -> int:
        del url
        shutil.copyfile(source, target)
        return target.stat().st_size

    monkeypatch.setattr(bronze, "_download_to", fake_download)


def test_check_updates_detects_same_count_content_correction(tmp_path, monkeypatch):
    raw_gz, raw_jsonl = _redirect_bronze(monkeypatch, tmp_path)
    old_payload = _payload([{"ocid": "a", "value": 1}, {"ocid": "b"}])
    new_payload = _payload([{"ocid": "a", "value": 2}, {"ocid": "b"}])
    raw_jsonl.write_bytes(old_payload)
    _write_gzip(raw_gz, old_payload)
    remote = tmp_path / "remote.jsonl.gz"
    _write_gzip(remote, new_payload)
    _serve_file(monkeypatch, remote)

    result = bronze.check_updates(url="https://example.invalid/publication")

    assert result["old_records"] == result["new_records"] == 2
    assert result["new_delta"] == 0
    assert result["changed"] is True
    assert result["old_sha256"] != result["new_sha256"]
    assert raw_jsonl.read_bytes() == new_payload
    with gzip.open(raw_gz, "rb") as src:
        assert src.read() == new_payload
    assert not [p for p in raw_gz.parent.iterdir() if p.suffix == ".tmp"]


def test_invalid_staged_jsonl_preserves_existing_bronze(tmp_path, monkeypatch):
    raw_gz, raw_jsonl = _redirect_bronze(monkeypatch, tmp_path)
    old_payload = _payload([{"ocid": "last-known-good"}])
    raw_jsonl.write_bytes(old_payload)
    _write_gzip(raw_gz, old_payload)
    old_gzip = raw_gz.read_bytes()
    remote = tmp_path / "invalid.jsonl.gz"
    _write_gzip(remote, b'{"ocid": broken}\n')
    _serve_file(monkeypatch, remote)

    with pytest.raises(ValueError, match="invalid JSONL record"):
        bronze.check_updates()

    assert raw_jsonl.read_bytes() == old_payload
    assert raw_gz.read_bytes() == old_gzip
    assert not [p for p in raw_gz.parent.iterdir() if p.suffix == ".tmp"]


def test_invalid_staged_gzip_preserves_existing_bronze(tmp_path, monkeypatch):
    raw_gz, raw_jsonl = _redirect_bronze(monkeypatch, tmp_path)
    old_payload = _payload([{"ocid": "last-known-good"}])
    raw_jsonl.write_bytes(old_payload)
    _write_gzip(raw_gz, old_payload)
    old_gzip = raw_gz.read_bytes()
    remote = tmp_path / "invalid.jsonl.gz"
    remote.write_bytes(b"not a gzip stream")
    _serve_file(monkeypatch, remote)

    with pytest.raises(OSError):
        bronze.check_updates()

    assert raw_jsonl.read_bytes() == old_payload
    assert raw_gz.read_bytes() == old_gzip
    assert not [p for p in raw_gz.parent.iterdir() if p.suffix == ".tmp"]


def test_force_extract_failure_keeps_prior_jsonl(tmp_path, monkeypatch):
    raw_gz, raw_jsonl = _redirect_bronze(monkeypatch, tmp_path)
    old_payload = _payload([{"ocid": "last-known-good"}])
    raw_jsonl.write_bytes(old_payload)
    _write_gzip(raw_gz, b"not-json\n")

    with pytest.raises(ValueError, match="invalid JSONL record"):
        bronze.extract(force=True)

    assert raw_jsonl.read_bytes() == old_payload


def test_explicit_bronze_run_uses_existing_snapshot_offline(tmp_path, monkeypatch):
    raw_gz, raw_jsonl = _redirect_bronze(monkeypatch, tmp_path)
    payload = _payload([{"ocid": "offline"}])
    raw_jsonl.write_bytes(payload)
    _write_gzip(raw_gz, payload)
    monkeypatch.setattr(
        bronze,
        "_download_to",
        lambda *args, **kwargs: pytest.fail("offline run contacted the network"),
    )

    summary = bronze.run()

    assert summary["records"] == 1
    assert summary["first_keys"] == ["ocid"]


def test_forced_download_publishes_retrieval_evidence(tmp_path, monkeypatch):
    raw_gz, _ = _redirect_bronze(monkeypatch, tmp_path)
    remote = tmp_path / "remote.jsonl.gz"
    _write_gzip(remote, _payload([{"ocid": "downloaded"}]))

    def fake_download(target: Path, url=None):
        shutil.copyfile(remote, target)
        return {
            "size_bytes": target.stat().st_size,
            "source_url": url or "https://example.invalid/publication",
            "retrieved_at": "2026-07-18T12:00:00+00:00",
            "etag": '"snapshot-1"',
            "last_modified": "Sat, 18 Jul 2026 12:00:00 GMT",
            "content_length": str(target.stat().st_size),
        }

    monkeypatch.setattr(bronze, "_download_to", fake_download)
    bronze.run(force_download=True)

    manifest = json.loads((raw_gz.parent / "bronze.release.json").read_text())
    acquisition = manifest["metadata"]["acquisition"]
    assert acquisition["evidence_available"] is True
    assert acquisition["retrieved_at"] == "2026-07-18T12:00:00+00:00"
    assert acquisition["etag"] == '"snapshot-1"'


def test_provenance_only_republication_preserves_prior_acquisition(tmp_path, monkeypatch):
    raw_gz, raw_jsonl = _redirect_bronze(monkeypatch, tmp_path)
    payload = _payload([{"ocid": "offline"}])
    raw_jsonl.write_bytes(payload)
    _write_gzip(raw_gz, payload)
    bronze._publish_bronze_release(
        records=1,
        content_sha256=bronze._file_sha256(raw_jsonl),
        acquisition={
            "evidence_available": True,
            "source_url": "https://example.invalid/original",
            "retrieved_at": "2026-07-17T12:00:00+00:00",
            "etag": '"original"',
        },
    )
    real_validate = bronze.validate_release

    def stale_only_when_current(*args, **kwargs):
        if kwargs.get("require_current_provenance"):
            raise bronze.ReleaseIntegrityError("simulated source-only change")
        return real_validate(*args, **kwargs)

    monkeypatch.setattr(bronze, "validate_release", stale_only_when_current)
    monkeypatch.setattr(
        bronze,
        "_download_to",
        lambda *args, **kwargs: pytest.fail("offline run contacted the network"),
    )

    bronze.run()

    manifest = json.loads((raw_gz.parent / "bronze.release.json").read_text())
    acquisition = manifest["metadata"]["acquisition"]
    assert acquisition["evidence_available"] is True
    assert acquisition["retrieved_at"] == "2026-07-17T12:00:00+00:00"
    assert acquisition["etag"] == '"original"'
