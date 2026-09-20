"""Fail-closed tests for atomic multi-artifact release manifests."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from thesis import release
from thesis.anomaly import benchmark
from thesis.lineage import file_sha256, schema_fingerprint, track
from thesis.pipeline.dag import Task, _is_fresh
from thesis.provenance import (
    configuration_fingerprint,
    implementation_fingerprint,
    runtime_fingerprint,
    runtime_provenance,
)
from thesis.release import (
    ReleaseIntegrityError,
    publish_release,
    read_released_parquet,
    validate_canonical_release,
    validate_release,
)


@pytest.fixture
def release_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    source = tmp_path / "silver" / "source.bin"
    artifact = tmp_path / "gold" / "artifact.bin"
    check = tmp_path / "dq" / "gold.dq.json"
    manifest = tmp_path / "gold" / "gold.release.json"
    for path in (source, artifact, check):
        path.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"source-generation-1")
    artifact.write_bytes(b"artifact-generation-1")
    check.write_text(
        json.dumps(
            {
                "passed": True,
                "error_count": 0,
                "release_binding": {
                    "artifact_path": "gold/artifact.bin",
                    "artifact_sha256": file_sha256(artifact),
                    "artifact_size_bytes": artifact.stat().st_size,
                },
            }
        )
    )
    return source, artifact, check, manifest


def test_publish_and_validate_release_round_trip(release_files):
    source, artifact, check, manifest = release_files

    published = publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
        metadata={"rows": 10},
    )
    validated = validate_release(
        manifest,
        expected_stage="gold",
        required_inputs=[source],
        required_artifacts=[artifact],
        required_checks=[check],
    )

    assert published.manifest_sha256 == validated.manifest_sha256
    assert validated.payload["metadata"]["rows"] == 10
    assert len(validated.payload["generation_fingerprint"]) == 64
    assert validated.payload["checks"][0]["passed"] is True


def test_release_enforces_required_check_set(release_files):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
    )

    with pytest.raises(ReleaseIntegrityError, match="missing required checks"):
        validate_release(
            manifest,
            expected_stage="gold",
            required_checks=[check],
        )


def test_downstream_may_bind_upstream_committed_check(release_files, tmp_path):
    source, artifact, check, manifest = release_files
    upstream = publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
    )
    downstream_artifact = tmp_path / "models" / "model.bin"
    downstream_manifest = tmp_path / "models" / "ml.release.json"
    downstream_artifact.parent.mkdir(parents=True)
    downstream_artifact.write_bytes(b"model")

    publish_release(
        downstream_manifest,
        stage="ml",
        inputs=[manifest, check],
        artifacts=[downstream_artifact],
        expected_input_manifest_sha256={manifest: upstream.manifest_sha256},
    )

    validate_release(downstream_manifest, expected_stage="ml")


@pytest.mark.parametrize("changed", ["input", "artifact"])
def test_release_rejects_changed_bound_file(release_files, changed):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
    )

    target = source if changed == "input" else artifact
    target.write_bytes(target.read_bytes() + b"-mutated")

    with pytest.raises(ReleaseIntegrityError, match="changed"):
        validate_release(manifest, expected_stage="gold")


def test_release_rejects_failed_dq_evidence(release_files):
    source, artifact, check, manifest = release_files
    check.write_text(json.dumps({"passed": False, "error_count": 1}))

    with pytest.raises(ReleaseIntegrityError, match="DQ check did not pass"):
        publish_release(
            manifest,
            stage="gold",
            inputs=[source],
            artifacts=[artifact],
            checks=[check],
        )

    assert not manifest.exists()


@pytest.mark.parametrize(
    "payload",
    [
        '{"passed": true, "observed": NaN}',
        '{"passed": false, "passed": true}',
    ],
)
def test_release_rejects_non_strict_dq_json(release_files, payload):
    source, artifact, check, manifest = release_files
    check.write_text(payload)

    with pytest.raises(ReleaseIntegrityError, match="invalid DQ check JSON"):
        publish_release(
            manifest,
            stage="gold",
            inputs=[source],
            artifacts=[artifact],
            checks=[check],
        )
    assert not manifest.exists()


def _write_parquet_with_lineage(
    path: Path,
    frame: pd.DataFrame,
    output_hash: str,
    inputs: list[Path] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    sidecar = path.with_suffix(path.suffix + ".lineage.json")
    runtime = runtime_provenance()
    sidecar.write_text(
        json.dumps(
            {
                "output_path": str(path),
                "output_sha256": output_hash,
                "output_size_bytes": path.stat().st_size,
                "rows": len(frame),
                "columns": frame.shape[1],
                "schema_fingerprint": schema_fingerprint(frame),
                "inputs": [
                    {
                        "path": str(input_path),
                        "sha256": file_sha256(input_path),
                        "size_bytes": input_path.stat().st_size,
                    }
                    for input_path in inputs or []
                ],
                "implementation_fingerprint": implementation_fingerprint(),
                "configuration_fingerprint": configuration_fingerprint(),
                "runtime": runtime,
                "runtime_fingerprint": runtime_fingerprint(runtime),
            }
        )
    )
    return sidecar


def test_release_rejects_stale_lineage_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    source = tmp_path / "silver" / "source.bin"
    artifact = tmp_path / "gold" / "artifact.parquet"
    manifest = tmp_path / "gold" / "gold.release.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    _write_parquet_with_lineage(
        artifact,
        pd.DataFrame({"value": [1, 2]}),
        output_hash="0" * 64,
    )

    with pytest.raises(ReleaseIntegrityError, match="lineage sidecar hash"):
        publish_release(
            manifest,
            stage="gold",
            inputs=[source],
            artifacts=[artifact],
        )


def test_reader_rejects_manifest_swap_during_read(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    source = tmp_path / "silver" / "source.bin"
    artifact = tmp_path / "gold" / "artifact.parquet"
    manifest = tmp_path / "gold" / "gold.release.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    _write_parquet_with_lineage(
        artifact,
        pd.DataFrame({"value": [1, 2]}),
        output_hash="pending",
        inputs=[source],
    )
    sidecar = artifact.with_suffix(artifact.suffix + ".lineage.json")
    sidecar_payload = json.loads(sidecar.read_text())
    sidecar_payload["output_sha256"] = file_sha256(artifact)
    sidecar.write_text(json.dumps(sidecar_payload))
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        metadata={"revision": 1},
    )

    real_read_parquet = pd.read_parquet

    def read_then_swap(path):
        frame = real_read_parquet(path)
        publish_release(
            manifest,
            stage="gold",
            inputs=[source],
            artifacts=[artifact],
            metadata={"revision": 2},
        )
        return frame

    monkeypatch.setattr(pd, "read_parquet", read_then_swap)
    with pytest.raises(ReleaseIntegrityError, match="changed while reading"):
        read_released_parquet(
            manifest,
            artifact,
            expected_stage="gold",
        )


def test_reader_rejects_release_from_different_current_implementation(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    source = tmp_path / "silver" / "source.bin"
    artifact = tmp_path / "gold" / "artifact.parquet"
    manifest = tmp_path / "gold" / "gold.release.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    from thesis.io.writers import write_parquet

    write_parquet(
        pd.DataFrame({"value": [1, 2]}),
        artifact,
        table="gold.artifact",
        layer="gold",
        inputs=[source],
    )
    publish_release(manifest, stage="gold", inputs=[source], artifacts=[artifact])

    monkeypatch.setattr(release, "implementation_fingerprint", lambda: "f" * 64)
    with pytest.raises(ReleaseIntegrityError, match="different implementation"):
        read_released_parquet(manifest, artifact, expected_stage="gold")


def test_manifest_fingerprint_rejects_metadata_tampering(release_files):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
        metadata={"rows": 10},
    )
    payload = json.loads(manifest.read_text())
    payload["metadata"]["rows"] = 11
    manifest.write_text(json.dumps(payload))

    with pytest.raises(ReleaseIntegrityError, match="generation_fingerprint"):
        validate_release(manifest, expected_stage="gold")


def test_unbound_canonical_dq_refresh_does_not_invalidate_release(release_files):
    source, artifact, release_check, manifest = release_files
    canonical_check = release_check.with_name("canonical-gold.dq.json")
    canonical_check.write_text(json.dumps({"passed": True, "timestamp": "first"}))
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[release_check],
    )

    canonical_check.write_text(json.dumps({"passed": True, "timestamp": "later-cli-run"}))

    validate_release(manifest, expected_stage="gold")


def test_release_rejects_stale_passing_dq_bound_to_prior_artifact(release_files):
    source, artifact, check, manifest = release_files
    artifact.write_bytes(b"new-artifact-generation")

    with pytest.raises(ReleaseIntegrityError, match="DQ artifact hash changed"):
        publish_release(
            manifest,
            stage="gold",
            inputs=[source],
            artifacts=[artifact],
            checks=[check],
        )
    assert not manifest.exists()


def test_dag_freshness_rejects_uncommitted_partial_generation(release_files):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
    )
    task = Task(
        name="gold",
        fn=lambda: None,
        inputs=[source],
        outputs=[artifact, manifest],
        release_manifest=manifest,
    )
    newest = max(source.stat().st_mtime, artifact.stat().st_mtime, manifest.stat().st_mtime) + 5
    os.utime(artifact, (newest, newest))
    os.utime(manifest, (newest + 1, newest + 1))
    assert _is_fresh(task)

    # Simulate a crash after the primary was replaced but before the manifest
    # commit marker was published. Favorable mtimes must not make it skippable.
    artifact.write_bytes(b"partial-next-generation")
    newest += 10
    os.utime(artifact, (newest, newest))
    os.utime(manifest, (newest + 1, newest + 1))

    assert not _is_fresh(task)


def test_release_backed_freshness_ignores_timestamp_only_changes(release_files):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
    )
    task = Task(
        name="gold",
        fn=lambda: None,
        inputs=[source],
        outputs=[artifact, manifest],
        release_manifest=manifest,
    )
    assert _is_fresh(task)

    newer = manifest.stat().st_mtime + 60
    os.utime(source, (newer, newer))

    assert _is_fresh(task)


def test_lineage_sidecar_write_failure_propagates(tmp_path, monkeypatch):
    from thesis import lineage

    output = tmp_path / "artifact.parquet"

    def fail_write(self):
        del self
        raise OSError("x")

    monkeypatch.setattr(lineage.Lineage, "write", fail_write)

    with pytest.raises(OSError, match="x"), track("artifact", "gold", output):
        pass


def test_release_schema_does_not_change_benchmark_protocol_fingerprint(monkeypatch):
    before = benchmark.benchmark_protocol_fingerprint()

    monkeypatch.setattr(release, "RELEASE_SCHEMA_VERSION", 999)

    assert benchmark.benchmark_protocol_fingerprint() == before


def test_release_with_relative_lineage_validates_after_data_root_relocation(tmp_path, monkeypatch):
    from thesis.io.writers import write_parquet

    first_root = tmp_path / "first"
    monkeypatch.setattr(release.paths, "DATA", first_root)
    source = first_root / "silver" / "source.bin"
    artifact = first_root / "gold" / "artifact.parquet"
    manifest = first_root / "gold" / "gold.release.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    write_parquet(
        pd.DataFrame({"value": [1, 2]}),
        artifact,
        table="gold.artifact",
        layer="gold",
        inputs=[source],
    )
    publish_release(manifest, stage="gold", inputs=[source], artifacts=[artifact])
    sidecar = json.loads(artifact.with_suffix(".parquet.lineage.json").read_text())
    assert sidecar["output_path"] == "gold/artifact.parquet"

    relocated_root = tmp_path / "relocated"
    shutil.copytree(first_root, relocated_root)
    monkeypatch.setattr(release.paths, "DATA", relocated_root)
    validate_release(
        relocated_root / "gold" / "gold.release.json",
        expected_stage="gold",
        required_inputs=[relocated_root / "silver" / "source.bin"],
        required_artifacts=[relocated_root / "gold" / "artifact.parquet"],
    )


def test_dag_freshness_rejects_release_from_different_implementation(release_files, monkeypatch):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
    )
    task = Task(
        name="gold",
        fn=lambda: None,
        inputs=[source],
        outputs=[artifact, manifest],
        release_manifest=manifest,
    )
    assert _is_fresh(task)

    monkeypatch.setattr(release, "implementation_fingerprint", lambda: "f" * 64)
    assert not _is_fresh(task)


def test_release_currentness_rejects_different_runtime(release_files, monkeypatch):
    source, artifact, check, manifest = release_files
    publish_release(
        manifest,
        stage="gold",
        inputs=[source],
        artifacts=[artifact],
        checks=[check],
    )
    real_runtime_fingerprint = release.runtime_fingerprint

    def changed_current_runtime(runtime=None):
        if runtime is not None:
            return real_runtime_fingerprint(runtime)
        return "f" * 64

    monkeypatch.setattr(release, "runtime_fingerprint", changed_current_runtime)
    with pytest.raises(ReleaseIntegrityError, match="different runtime"):
        validate_release(
            manifest,
            expected_stage="gold",
            require_current_provenance=True,
            require_current_runtime=True,
        )


def test_downstream_release_recursively_validates_upstream_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    raw = tmp_path / "raw" / "source.bin"
    silver = tmp_path / "silver" / "artifact.bin"
    silver_manifest = tmp_path / "silver" / "silver.release.json"
    gold = tmp_path / "gold" / "artifact.bin"
    gold_manifest = tmp_path / "gold" / "gold.release.json"
    for path in (raw, silver, gold):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"raw")
    silver.write_bytes(b"silver")
    gold.write_bytes(b"gold")
    publish_release(
        silver_manifest,
        stage="silver",
        inputs=[raw],
        artifacts=[silver],
    )
    publish_release(
        gold_manifest,
        stage="gold",
        inputs=[silver_manifest],
        artifacts=[gold],
    )

    validate_release(gold_manifest, expected_stage="gold")
    silver.write_bytes(b"corrupted-after-downstream-publication")

    with pytest.raises(ReleaseIntegrityError, match="changed"):
        validate_release(gold_manifest, expected_stage="gold")


def test_downstream_release_rejects_input_not_committed_by_upstream(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    raw = tmp_path / "raw" / "source.bin"
    declared = tmp_path / "silver" / "declared.bin"
    undeclared = tmp_path / "silver" / "undeclared.bin"
    silver_manifest = tmp_path / "silver" / "silver.release.json"
    gold = tmp_path / "gold" / "artifact.bin"
    gold_manifest = tmp_path / "gold" / "gold.release.json"
    for path in (raw, declared, undeclared, gold):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode())
    publish_release(
        silver_manifest,
        stage="silver",
        inputs=[raw],
        artifacts=[declared],
    )
    with pytest.raises(ReleaseIntegrityError, match="not committed artifacts"):
        publish_release(
            gold_manifest,
            stage="gold",
            inputs=[silver_manifest, undeclared],
            artifacts=[gold],
        )
    assert not gold_manifest.exists()


def test_publish_rejects_upstream_manifest_swap_since_stage_read(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    raw = tmp_path / "raw" / "source.bin"
    silver = tmp_path / "silver" / "artifact.bin"
    silver_manifest = tmp_path / "silver" / "silver.release.json"
    gold = tmp_path / "gold" / "artifact.bin"
    gold_manifest = tmp_path / "gold" / "gold.release.json"
    for path in (raw, silver, gold):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode())
    first = publish_release(
        silver_manifest,
        stage="silver",
        inputs=[raw],
        artifacts=[silver],
        metadata={"revision": 1},
    )
    publish_release(
        silver_manifest,
        stage="silver",
        inputs=[raw],
        artifacts=[silver],
        metadata={"revision": 2},
    )

    with pytest.raises(ReleaseIntegrityError, match="changed during stage execution"):
        publish_release(
            gold_manifest,
            stage="gold",
            inputs=[silver_manifest, silver],
            artifacts=[gold],
            expected_input_manifest_sha256={
                silver_manifest: first.manifest_sha256,
            },
        )
    assert not gold_manifest.exists()


def test_canonical_release_requires_exact_stage_file_set(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_gz = raw_dir / "source.jsonl.gz"
    raw_jsonl = raw_dir / "source.jsonl"
    manifest = raw_dir / "bronze.release.json"
    extra = raw_dir / "undeclared.bin"
    for path in (raw_gz, raw_jsonl, extra):
        path.write_bytes(path.name.encode())
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    monkeypatch.setattr(release.paths, "RAW_GZ", raw_gz)
    monkeypatch.setattr(release.paths, "RAW_JSONL", raw_jsonl)
    monkeypatch.setattr(release.paths, "BRONZE_RELEASE", manifest)

    publish_release(
        manifest,
        stage="bronze",
        inputs=[],
        artifacts=[raw_gz, raw_jsonl],
    )
    prior = manifest.read_bytes()
    validate_canonical_release("bronze")

    with pytest.raises(ReleaseIntegrityError, match="non-exact file set"):
        publish_release(
            manifest,
            stage="bronze",
            inputs=[],
            artifacts=[raw_gz, raw_jsonl, extra],
        )
    assert manifest.read_bytes() == prior


def test_recursive_validation_rejects_manifest_swap_after_entry_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(release.paths, "DATA", tmp_path)
    raw = tmp_path / "raw" / "source.bin"
    silver = tmp_path / "silver" / "artifact.bin"
    silver_manifest = tmp_path / "silver" / "silver.release.json"
    gold = tmp_path / "gold" / "artifact.bin"
    gold_manifest = tmp_path / "gold" / "gold.release.json"
    for path in (raw, silver, gold):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode())

    publish_release(
        silver_manifest,
        stage="silver",
        inputs=[raw],
        artifacts=[silver],
        metadata={"revision": 1},
    )
    revision_one = silver_manifest.read_bytes()
    publish_release(
        gold_manifest,
        stage="gold",
        inputs=[silver_manifest, silver],
        artifacts=[gold],
    )
    publish_release(
        silver_manifest,
        stage="silver",
        inputs=[raw],
        artifacts=[silver],
        metadata={"revision": 2},
    )
    revision_two_path = tmp_path / "silver" / "revision-two.json"
    revision_two_path.write_bytes(silver_manifest.read_bytes())
    silver_manifest.write_bytes(revision_one)

    real_validate_entry = release._validate_entry
    swapped = False

    def validate_then_swap(entry, section):
        nonlocal swapped
        result = real_validate_entry(entry, section)
        if not swapped and result[1] == silver_manifest.resolve():
            os.replace(revision_two_path, silver_manifest)
            swapped = True
        return result

    monkeypatch.setattr(release, "_validate_entry", validate_then_swap)
    with pytest.raises(ReleaseIntegrityError, match="recursive validation"):
        validate_release(gold_manifest, expected_stage="gold")
