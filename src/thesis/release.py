"""Atomic, hash-bound publication manifests for multi-file pipeline stages.

A stage writes all of its artifacts first and publishes its release manifest
last.  Consumers validate that commit marker and every declared file, so they
never silently combine files left behind by different stage generations.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import paths
from .config import settings
from .io.writers import write_json
from .jsonutil import json_ready, loads_json
from .lineage import file_sha256, schema_fingerprint
from .locking import active_pipeline_provenance
from .logging import get_run_id
from .provenance import (
    configuration_fingerprint,
    effective_pipeline_configuration,
    implementation_fingerprint,
    implementation_manifest,
    runtime_fingerprint,
    runtime_provenance,
)

RELEASE_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = {
    "schema_version",
    "stage",
    "release_id",
    "generation_fingerprint",
    "created_at",
    "inputs",
    "artifacts",
    "checks",
    "metadata",
}


class ReleaseIntegrityError(RuntimeError):
    """A release manifest or one of its bound files is invalid."""


@dataclass(frozen=True)
class ValidatedRelease:
    """A fully checked release plus the hash of the manifest bytes read."""

    manifest_path: Path
    manifest_sha256: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class CanonicalReleaseContract:
    """Exact primary file/check contract for one canonical stage."""

    manifest: Path
    inputs: tuple[Path, ...]
    artifacts: tuple[Path, ...]
    checks: tuple[Path, ...]


def canonical_release_contract(stage: str) -> CanonicalReleaseContract:
    """Return the exact canonical publication set for *stage*."""
    contracts = {
        "bronze": CanonicalReleaseContract(
            paths.BRONZE_RELEASE,
            (),
            (paths.RAW_GZ, paths.RAW_JSONL),
            (),
        ),
        "silver": CanonicalReleaseContract(
            paths.SILVER_RELEASE,
            (paths.BRONZE_RELEASE, paths.RAW_JSONL),
            (paths.SILVER_TENDERS, paths.SILVER_AWARDS),
            (paths.SILVER_TENDERS_RELEASE_DQ, paths.SILVER_AWARDS_RELEASE_DQ),
        ),
        "gold": CanonicalReleaseContract(
            paths.GOLD_RELEASE,
            (paths.SILVER_RELEASE, paths.SILVER_TENDERS, paths.SILVER_AWARDS),
            (
                paths.GOLD_FEATURES,
                paths.GOLD_SUPPLIERS,
                paths.GOLD_ENTITIES,
                paths.GOLD_MONTHLY,
            ),
            (
                paths.GOLD_FEATURES_RELEASE_DQ,
                paths.GOLD_SUPPLIERS_RELEASE_DQ,
                paths.GOLD_ENTITIES_RELEASE_DQ,
                paths.GOLD_MONTHLY_RELEASE_DQ,
            ),
        ),
        "benchmark": CanonicalReleaseContract(
            paths.BENCHMARK_RELEASE,
            (paths.GOLD_RELEASE, paths.GOLD_FEATURES),
            (
                paths.BENCHMARK_RESULTS,
                paths.BENCHMARK_LEADERBOARD,
                paths.BENCHMARK_LEADERBOARD_MD,
                paths.CHAMPIONS,
            ),
            (paths.BENCHMARK_RELEASE_DQ,),
        ),
        "ml": CanonicalReleaseContract(
            paths.ML_RELEASE,
            (
                paths.GOLD_RELEASE,
                paths.GOLD_FEATURES,
                paths.BENCHMARK_RELEASE,
                paths.BENCHMARK_RESULTS,
                paths.BENCHMARK_LEADERBOARD,
                paths.CHAMPIONS,
            ),
            (
                paths.CHAMPION_MODELS,
                paths.HGB_MODEL,
                paths.SHAP_VALUES,
                paths.MODEL_VALIDATION,
                paths.FEATURE_LIST,
                paths.GOLD_TENDERS,
            ),
            (paths.GOLD_TENDERS_RELEASE_DQ, paths.SHAP_VALUES_RELEASE_DQ),
        ),
    }
    try:
        return contracts[stage]
    except KeyError as exc:
        raise ReleaseIntegrityError(f"unknown canonical release stage: {stage!r}") from exc


def _data_root() -> Path:
    return paths.DATA.resolve()


def _relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(_data_root())
    except ValueError as exc:
        raise ReleaseIntegrityError(
            f"release path escapes the configured data directory: {path}"
        ) from exc
    if not relative.parts or ".." in relative.parts:
        raise ReleaseIntegrityError(f"invalid release path: {path}")
    return relative.as_posix()


def _resolve_entry_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ReleaseIntegrityError("release entry path must be a non-empty string")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or value != relative.as_posix():
        raise ReleaseIntegrityError(f"unsafe release entry path: {value!r}")
    resolved = (_data_root() / relative).resolve()
    try:
        resolved.relative_to(_data_root())
    except ValueError as exc:
        raise ReleaseIntegrityError(f"release entry escapes data directory: {value!r}") from exc
    return resolved


def _file_entry(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReleaseIntegrityError(f"release file is missing: {path}")
    return {
        "path": _relative_path(path),
        "sha256": file_sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _generation_fingerprint(
    *,
    stage: str,
    inputs: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    """Hash release content, excluding run identity and publication time."""
    material = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "stage": stage,
        "inputs": sorted(inputs, key=lambda entry: entry["path"]),
        "artifacts": sorted(artifacts, key=lambda entry: entry["path"]),
        "checks": sorted(checks, key=lambda entry: entry["path"]),
        "metadata": metadata,
    }
    canonical = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _lineage_sidecar(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lineage.json")


def _read_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        payload = loads_json(path.read_text())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ReleaseIntegrityError(f"invalid {description} JSON at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseIntegrityError(f"{description} JSON must contain an object: {path}")
    return payload


def _validate_dq_release_binding(
    check_path: Path,
    payload: Mapping[str, Any],
    declared_artifacts: set[Path],
) -> None:
    binding = payload.get("release_binding")
    expected_keys = {"artifact_path", "artifact_sha256", "artifact_size_bytes"}
    if not isinstance(binding, dict) or set(binding) != expected_keys:
        raise ReleaseIntegrityError(
            f"release DQ check lacks an exact artifact binding: {check_path}"
        )
    artifact = _resolve_entry_path(binding["artifact_path"])
    if artifact.resolve() not in declared_artifacts:
        raise ReleaseIntegrityError(f"release DQ check binds an undeclared artifact: {artifact}")
    if binding["artifact_sha256"] != file_sha256(artifact):
        raise ReleaseIntegrityError(f"release DQ artifact hash changed: {artifact}")
    if binding["artifact_size_bytes"] != artifact.stat().st_size:
        raise ReleaseIntegrityError(f"release DQ artifact size changed: {artifact}")
    if artifact.suffix == ".parquet":
        import pandas as pd

        from .dq.framework import dataframe_fingerprint

        frame = pd.read_parquet(artifact)
        if payload.get("rows") != len(frame) or payload.get("columns") != frame.shape[1]:
            raise ReleaseIntegrityError(
                f"release DQ shape does not describe bound artifact: {artifact}"
            )
        if payload.get("data_fingerprint") != dataframe_fingerprint(frame):
            raise ReleaseIntegrityError(
                f"release DQ data fingerprint does not describe bound artifact: {artifact}"
            )


def _validate_lineage_binding(
    primary: Path,
    sidecar: Path,
    *,
    expected_provenance: Mapping[str, Any],
    allowed_inputs: set[Path],
) -> None:
    payload = _read_json_object(sidecar, "lineage sidecar")
    expected_hash = file_sha256(primary)
    if payload.get("output_sha256") != expected_hash:
        raise ReleaseIntegrityError(
            f"lineage sidecar hash does not bind the current artifact: {primary}"
        )
    output_path = payload.get("output_path")
    if not isinstance(output_path, str):
        raise ReleaseIntegrityError(
            f"lineage sidecar output_path does not bind the current artifact: {primary}"
        )
    recorded_path = Path(output_path)
    if not recorded_path.is_absolute():
        recorded_path = _data_root() / recorded_path
    if recorded_path.resolve() != primary.resolve():
        raise ReleaseIntegrityError(
            f"lineage sidecar output_path does not bind the current artifact: {primary}"
        )
    if payload.get("output_size_bytes") != primary.stat().st_size:
        raise ReleaseIntegrityError(
            f"lineage sidecar size does not bind the current artifact: {primary}"
        )
    from pyarrow.parquet import ParquetFile

    parquet = ParquetFile(primary)
    if payload.get("rows") != parquet.metadata.num_rows:
        raise ReleaseIntegrityError(f"lineage row count contradicts Parquet footer: {primary}")
    if payload.get("columns") != parquet.metadata.num_columns:
        raise ReleaseIntegrityError(f"lineage column count contradicts Parquet footer: {primary}")
    empty_frame = parquet.schema_arrow.empty_table().to_pandas()
    if payload.get("schema_fingerprint") != schema_fingerprint(empty_frame):
        raise ReleaseIntegrityError(f"lineage schema contradicts Parquet schema: {primary}")
    lineage_inputs = payload.get("inputs")
    if not isinstance(lineage_inputs, list):
        raise ReleaseIntegrityError(f"lineage sidecar inputs are invalid: {sidecar}")
    if allowed_inputs and not lineage_inputs:
        raise ReleaseIntegrityError(f"lineage sidecar omits all declared inputs: {sidecar}")
    for entry in lineage_inputs:
        if not isinstance(entry, dict):
            raise ReleaseIntegrityError(f"lineage input entry is invalid: {sidecar}")
        value = entry.get("path")
        if not isinstance(value, str) or not value:
            raise ReleaseIntegrityError(f"lineage input path is invalid: {sidecar}")
        input_path = Path(value)
        if not input_path.is_absolute():
            if ".." in input_path.parts:
                raise ReleaseIntegrityError(f"unsafe lineage input path: {value!r}")
            input_path = _data_root() / input_path
        if not input_path.is_file():
            raise ReleaseIntegrityError(f"lineage input is missing: {input_path}")
        if entry.get("sha256") != file_sha256(input_path):
            raise ReleaseIntegrityError(f"lineage input hash changed: {input_path}")
        recorded_size = entry.get("size_bytes")
        if recorded_size is not None and recorded_size != input_path.stat().st_size:
            raise ReleaseIntegrityError(f"lineage input size changed: {input_path}")
        if input_path.resolve() not in allowed_inputs:
            raise ReleaseIntegrityError(
                f"lineage input is not declared by the release: {input_path}"
            )
    for key in (
        "implementation_fingerprint",
        "configuration_fingerprint",
        "runtime_fingerprint",
    ):
        if payload.get(key) != expected_provenance.get(key):
            raise ReleaseIntegrityError(f"lineage {key} contradicts release provenance: {sidecar}")
    if payload.get("runtime") != expected_provenance.get("runtime"):
        raise ReleaseIntegrityError(f"lineage runtime contradicts release provenance: {sidecar}")


def _deduplicate(paths_to_check: Iterable[Path], label: str) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths_to_check:
        canonical = _relative_path(path)
        if canonical in seen:
            raise ReleaseIntegrityError(f"duplicate {label} path: {canonical}")
        seen.add(canonical)
        result.append(path.resolve())
    return result


def publish_release(
    manifest_path: Path,
    *,
    stage: str,
    inputs: Iterable[Path],
    artifacts: Iterable[Path],
    checks: Iterable[Path] = (),
    metadata: Optional[Mapping[str, Any]] = None,
    expected_input_manifest_sha256: Optional[Mapping[Path, str]] = None,
) -> ValidatedRelease:
    """Hash all stage files and atomically publish *manifest_path* last."""
    if not stage or not isinstance(stage, str):
        raise ReleaseIntegrityError("release stage must be a non-empty string")
    _relative_path(manifest_path)
    input_paths = _deduplicate(inputs, "input")
    artifact_paths = _deduplicate(artifacts, "artifact")
    check_paths = _deduplicate(checks, "check")

    all_declared = {
        *(_relative_path(path) for path in input_paths),
        *(_relative_path(path) for path in artifact_paths),
        *(_relative_path(path) for path in check_paths),
    }
    expected_count = len(input_paths) + len(artifact_paths) + len(check_paths)
    if len(all_declared) != expected_count:
        raise ReleaseIntegrityError("a release path cannot appear in multiple sections")
    if _relative_path(manifest_path) in all_declared:
        raise ReleaseIntegrityError("a release manifest cannot declare itself")

    # Validate upstream commit markers before writing any new manifest and
    # prove that the accompanying direct inputs were actually committed by
    # them. This is repeated by ``validate_release`` for every later reader;
    # the preflight here prevents publishing a known-invalid commit marker.
    expected_manifest_hashes = {
        _relative_path(path): digest
        for path, digest in (expected_input_manifest_sha256 or {}).items()
    }
    declared_input_relatives = {_relative_path(path) for path in input_paths}
    unexpected_expectations = set(expected_manifest_hashes) - declared_input_relatives
    if unexpected_expectations:
        raise ReleaseIntegrityError(
            "expected input-manifest hashes name undeclared inputs: "
            f"{', '.join(sorted(unexpected_expectations))}"
        )
    for relative, digest in expected_manifest_hashes.items():
        if not relative.endswith(".release.json"):
            raise ReleaseIntegrityError(
                f"expected input-manifest hash is not for a release manifest: {relative}"
            )
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ReleaseIntegrityError(f"invalid expected input-manifest SHA-256: {relative}")

    upstream_artifacts: set[str] = set()
    upstream_manifests: set[str] = set()
    for input_path in input_paths:
        input_relative = _relative_path(input_path)
        if input_relative.endswith(".release.json"):
            upstream = validate_release(
                input_path,
                require_current_provenance=True,
                require_current_runtime=True,
            )
            expected_digest = expected_manifest_hashes.get(input_relative)
            if expected_digest is not None and upstream.manifest_sha256 != expected_digest:
                raise ReleaseIntegrityError(
                    f"upstream release changed during stage execution: {input_relative}"
                )
            upstream_manifests.add(input_relative)
            upstream_artifacts.update(entry["path"] for entry in upstream.payload["artifacts"])
            upstream_artifacts.update(entry["path"] for entry in upstream.payload["checks"])
    if upstream_manifests:
        unbound_inputs = (
            {_relative_path(path) for path in input_paths} - upstream_manifests - upstream_artifacts
        )
        if unbound_inputs:
            raise ReleaseIntegrityError(
                "release inputs are not committed artifacts of the declared "
                f"upstream releases: {', '.join(sorted(unbound_inputs))}"
            )

    current_runtime = runtime_provenance()
    publisher_provenance = {
        "implementation_fingerprint": implementation_fingerprint(),
        "implementation_manifest": implementation_manifest(),
        "configuration_fingerprint": configuration_fingerprint(),
        "configuration": effective_pipeline_configuration(),
        "runtime": current_runtime,
        "runtime_fingerprint": runtime_fingerprint(current_runtime),
    }
    locked_provenance = active_pipeline_provenance()
    if locked_provenance is not None:
        changed = [
            key
            for key, expected in locked_provenance.items()
            if publisher_provenance.get(key) != expected
        ]
        if changed:
            raise ReleaseIntegrityError(
                "implementation, configuration, or runtime changed after the "
                f"pipeline lock was acquired: {', '.join(sorted(changed))}"
            )

    lineage_enabled = settings().write_lineage_sidecars
    lineage_paths: list[Path] = []
    allowed_lineage_inputs = {path.resolve() for path in (*input_paths, *artifact_paths)}
    if lineage_enabled:
        for artifact in artifact_paths:
            if artifact.suffix != ".parquet":
                continue
            sidecar = _lineage_sidecar(artifact)
            if not sidecar.is_file():
                raise ReleaseIntegrityError(f"lineage sidecar is missing: {sidecar}")
            _validate_lineage_binding(
                artifact,
                sidecar,
                expected_provenance=publisher_provenance,
                allowed_inputs=allowed_lineage_inputs,
            )
            lineage_paths.append(sidecar.resolve())

    artifact_paths = _deduplicate([*artifact_paths, *lineage_paths], "artifact")
    if {_relative_path(path) for path in artifact_paths} & {
        *(_relative_path(path) for path in input_paths),
        *(_relative_path(path) for path in check_paths),
    }:
        raise ReleaseIntegrityError("an automatically included lineage path is duplicated")

    check_entries: list[dict[str, Any]] = []
    for path in check_paths:
        check_payload = _read_json_object(path, "DQ check")
        if check_payload.get("passed") is not True:
            raise ReleaseIntegrityError(f"release DQ check did not pass: {path}")
        _validate_dq_release_binding(
            path,
            check_payload,
            {
                artifact.resolve()
                for artifact in artifact_paths
                if not artifact.name.endswith(".lineage.json")
            },
        )
        check_entries.append({**_file_entry(path), "passed": True})

    release_metadata = dict(metadata or {})
    managed_metadata = {"lineage_sidecars", "provenance"}
    if managed_metadata & set(release_metadata):
        raise ReleaseIntegrityError(
            "lineage_sidecars and provenance metadata are managed by the publisher"
        )
    release_metadata["lineage_sidecars"] = lineage_enabled
    release_metadata["provenance"] = publisher_provenance
    # Match the strict writer's supported value domain before fingerprinting so
    # the verified digest covers the exact serialized semantics.
    release_metadata = json_ready(release_metadata)
    if not isinstance(release_metadata, dict):  # defensive type narrowing
        raise ReleaseIntegrityError("release metadata must serialize to an object")
    input_entries = [_file_entry(path) for path in input_paths]
    input_entry_hashes = {entry["path"]: entry["sha256"] for entry in input_entries}
    for relative, expected_digest in expected_manifest_hashes.items():
        if input_entry_hashes[relative] != expected_digest:
            raise ReleaseIntegrityError(
                f"upstream release changed during stage execution: {relative}"
            )
    artifact_entries = [_file_entry(path) for path in artifact_paths]
    payload = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "stage": stage,
        "release_id": get_run_id(),
        "generation_fingerprint": _generation_fingerprint(
            stage=stage,
            inputs=input_entries,
            artifacts=artifact_entries,
            checks=check_entries,
            metadata=release_metadata,
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": input_entries,
        "artifacts": artifact_entries,
        "checks": check_entries,
        "metadata": release_metadata,
    }
    staged_manifest = manifest_path.with_name(f".{manifest_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        canonical_target = canonical_release_contract(stage).manifest.resolve()
    except ReleaseIntegrityError:
        canonical_target = None
    is_canonical = canonical_target == manifest_path.resolve()
    try:
        write_json(payload, staged_manifest)
        # Validate the complete prospective commit marker before replacing the
        # last known-good canonical manifest.
        if is_canonical:
            validate_canonical_release(
                stage,
                manifest_path=staged_manifest,
                require_current_provenance=True,
                require_current_runtime=True,
            )
        else:
            validate_release(
                staged_manifest,
                expected_stage=stage,
                require_current_provenance=True,
                require_current_runtime=True,
            )
        os.replace(staged_manifest, manifest_path)
        if is_canonical:
            return validate_canonical_release(
                stage,
                require_current_provenance=True,
                require_current_runtime=True,
            )
        return validate_release(
            manifest_path,
            expected_stage=stage,
            require_current_provenance=True,
            require_current_runtime=True,
        )
    finally:
        staged_manifest.unlink(missing_ok=True)


def _validate_entry(entry: object, section: str) -> tuple[str, Path]:
    expected_keys = {"path", "sha256", "size_bytes"}
    if section == "checks":
        expected_keys.add("passed")
    if not isinstance(entry, dict) or set(entry) != expected_keys:
        raise ReleaseIntegrityError(f"invalid {section} entry schema")
    path_value = entry.get("path")
    path = _resolve_entry_path(path_value)
    sha256 = entry.get("sha256")
    size = entry.get("size_bytes")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        raise ReleaseIntegrityError(f"invalid SHA-256 for release entry {path_value!r}")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ReleaseIntegrityError(f"invalid size for release entry {path_value!r}")
    if section == "checks" and entry.get("passed") is not True:
        raise ReleaseIntegrityError(f"release check is not marked passed: {path_value!r}")
    if not path.is_file():
        raise ReleaseIntegrityError(f"released file is missing: {path}")
    actual_size = path.stat().st_size
    if actual_size != size:
        raise ReleaseIntegrityError(
            f"released file size changed for {path} (manifest={size}, actual={actual_size})"
        )
    actual_hash = file_sha256(path)
    if actual_hash != sha256:
        raise ReleaseIntegrityError(f"released file hash changed: {path}")
    if section == "checks":
        check_payload = _read_json_object(path, "DQ check")
        if check_payload.get("passed") is not True:
            raise ReleaseIntegrityError(f"released DQ check no longer passes: {path}")
    return str(path_value), path


def _required_relatives(required: Optional[Iterable[Path]]) -> set[str]:
    return {_relative_path(path) for path in required or ()}


def validate_release(
    manifest_path: Path,
    *,
    expected_stage: Optional[str] = None,
    required_inputs: Optional[Iterable[Path]] = None,
    required_artifacts: Optional[Iterable[Path]] = None,
    required_checks: Optional[Iterable[Path]] = None,
    require_current_provenance: bool = False,
    require_current_runtime: bool = False,
    _validation_stack: Optional[set[Path]] = None,
) -> ValidatedRelease:
    """Fully validate a release manifest and every hash-bound file."""
    _relative_path(manifest_path)
    resolved_manifest = manifest_path.resolve()
    validation_stack = set() if _validation_stack is None else _validation_stack
    if resolved_manifest in validation_stack:
        raise ReleaseIntegrityError(f"cyclic release-manifest dependency: {manifest_path}")
    validation_stack.add(resolved_manifest)
    if not manifest_path.is_file():
        raise ReleaseIntegrityError(f"release manifest is missing: {manifest_path}")
    try:
        manifest_bytes = manifest_path.read_bytes()
        payload = loads_json(manifest_bytes)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ReleaseIntegrityError(f"invalid release manifest {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != _TOP_LEVEL_KEYS:
        raise ReleaseIntegrityError(f"invalid release manifest schema: {manifest_path}")
    if payload.get("schema_version") != RELEASE_SCHEMA_VERSION:
        raise ReleaseIntegrityError(
            f"unsupported release schema version: {payload.get('schema_version')!r}"
        )
    stage = payload.get("stage")
    if not isinstance(stage, str) or not stage:
        raise ReleaseIntegrityError("release stage must be a non-empty string")
    if expected_stage is not None and stage != expected_stage:
        raise ReleaseIntegrityError(
            f"release stage mismatch (expected={expected_stage!r}, actual={stage!r})"
        )
    if not isinstance(payload.get("release_id"), str) or not payload["release_id"]:
        raise ReleaseIntegrityError("release_id must be a non-empty string")
    generation_fingerprint = payload.get("generation_fingerprint")
    if not isinstance(generation_fingerprint, str) or not _SHA256_RE.fullmatch(
        generation_fingerprint
    ):
        raise ReleaseIntegrityError("generation_fingerprint must be a SHA-256 digest")
    created_at = payload.get("created_at")
    if not isinstance(created_at, str):
        raise ReleaseIntegrityError("created_at must be an ISO-8601 string")
    try:
        timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseIntegrityError("created_at must be an ISO-8601 string") from exc
    if timestamp.tzinfo is None:
        raise ReleaseIntegrityError("created_at must include a timezone")

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("lineage_sidecars"), bool):
        raise ReleaseIntegrityError("release metadata must declare lineage_sidecars as boolean")
    provenance = metadata.get("provenance")
    if not isinstance(provenance, dict):
        raise ReleaseIntegrityError("release metadata must contain implementation provenance")
    if not isinstance(provenance.get("implementation_fingerprint"), str):
        raise ReleaseIntegrityError("release implementation fingerprint is missing")
    if not isinstance(provenance.get("implementation_manifest"), dict):
        raise ReleaseIntegrityError("release implementation manifest is missing")
    recorded_implementation_fingerprint = hashlib.sha256(
        json.dumps(
            provenance["implementation_manifest"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    if recorded_implementation_fingerprint != provenance["implementation_fingerprint"]:
        raise ReleaseIntegrityError("release implementation manifest fingerprint is inconsistent")
    if not isinstance(provenance.get("configuration_fingerprint"), str):
        raise ReleaseIntegrityError("release configuration fingerprint is missing")
    if not isinstance(provenance.get("configuration"), dict):
        raise ReleaseIntegrityError("release effective configuration is missing")
    recorded_configuration_fingerprint = hashlib.sha256(
        json.dumps(
            provenance["configuration"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    if recorded_configuration_fingerprint != provenance["configuration_fingerprint"]:
        raise ReleaseIntegrityError("release configuration fingerprint is inconsistent")
    if not isinstance(provenance.get("runtime"), dict):
        raise ReleaseIntegrityError("release runtime provenance is missing")
    if not isinstance(provenance.get("runtime_fingerprint"), str):
        raise ReleaseIntegrityError("release runtime fingerprint is missing")
    if runtime_fingerprint(provenance["runtime"]) != provenance["runtime_fingerprint"]:
        raise ReleaseIntegrityError("release runtime fingerprint is inconsistent")
    if require_current_provenance:
        if provenance["implementation_fingerprint"] != implementation_fingerprint():
            raise ReleaseIntegrityError("release was produced by a different implementation")
        if provenance["configuration_fingerprint"] != configuration_fingerprint():
            raise ReleaseIntegrityError("release was produced with a different configuration")
    if require_current_runtime and provenance["runtime_fingerprint"] != runtime_fingerprint():
        raise ReleaseIntegrityError("release was produced with a different runtime")
    sections: dict[str, dict[str, Path]] = {}
    all_paths: set[str] = set()
    for section in ("inputs", "artifacts", "checks"):
        entries = payload.get(section)
        if not isinstance(entries, list):
            raise ReleaseIntegrityError(f"release {section} must be a list")
        section_paths: dict[str, Path] = {}
        for entry in entries:
            relative, path = _validate_entry(entry, section)
            if relative in all_paths:
                raise ReleaseIntegrityError(f"duplicate path in release manifest: {relative}")
            all_paths.add(relative)
            section_paths[relative] = path
        sections[section] = section_paths

    primary_artifacts = {
        path.resolve()
        for path in sections["artifacts"].values()
        if not path.name.endswith(".lineage.json")
    }
    for check_path in sections["checks"].values():
        _validate_dq_release_binding(
            check_path,
            _read_json_object(check_path, "DQ check"),
            primary_artifacts,
        )

    expected_generation = _generation_fingerprint(
        stage=stage,
        inputs=payload["inputs"],
        artifacts=payload["artifacts"],
        checks=payload["checks"],
        metadata=metadata,
    )
    if generation_fingerprint != expected_generation:
        raise ReleaseIntegrityError("release generation_fingerprint does not match its content")

    manifest_relative = _relative_path(manifest_path)
    if manifest_relative in all_paths:
        raise ReleaseIntegrityError("a release manifest cannot declare itself")
    missing_inputs = _required_relatives(required_inputs) - set(sections["inputs"])
    if missing_inputs:
        raise ReleaseIntegrityError(
            f"release is missing required inputs: {', '.join(sorted(missing_inputs))}"
        )
    missing_artifacts = _required_relatives(required_artifacts) - set(sections["artifacts"])
    if missing_artifacts:
        raise ReleaseIntegrityError(
            f"release is missing required artifacts: {', '.join(sorted(missing_artifacts))}"
        )
    missing_checks = _required_relatives(required_checks) - set(sections["checks"])
    if missing_checks:
        raise ReleaseIntegrityError(
            f"release is missing required checks: {', '.join(sorted(missing_checks))}"
        )

    if metadata["lineage_sidecars"]:
        for relative, primary in sections["artifacts"].items():
            if primary.suffix != ".parquet":
                continue
            sidecar = _lineage_sidecar(primary)
            sidecar_relative = _relative_path(sidecar)
            if sidecar_relative not in sections["artifacts"]:
                raise ReleaseIntegrityError(
                    f"release is missing lineage sidecar for artifact: {relative}"
                )
            _validate_lineage_binding(
                primary,
                sidecar,
                expected_provenance=provenance,
                allowed_inputs={
                    *sections["inputs"].values(),
                    *sections["artifacts"].values(),
                },
            )

    # A manifest input is not merely an opaque JSON blob: recursively validate
    # the complete upstream generation that it commits. This prevents a reader
    # from accepting ML/Gold artifacts after an upstream canonical file changed
    # while the downstream manifest itself remained byte-identical.
    upstream_artifacts: set[str] = set()
    upstream_manifests: set[str] = set()
    recorded_input_hashes = {entry["path"]: entry["sha256"] for entry in payload["inputs"]}
    for relative, input_path in sections["inputs"].items():
        if relative.endswith(".release.json"):
            upstream = validate_release(
                input_path,
                require_current_provenance=require_current_provenance,
                require_current_runtime=require_current_runtime,
                _validation_stack=validation_stack,
            )
            if upstream.manifest_sha256 != recorded_input_hashes[relative]:
                raise ReleaseIntegrityError(
                    f"upstream release changed during recursive validation: {relative}"
                )
            upstream_manifests.add(relative)
            upstream_artifacts.update(entry["path"] for entry in upstream.payload["artifacts"])
            upstream_artifacts.update(entry["path"] for entry in upstream.payload["checks"])

    # When a stage declares an upstream commit marker, every accompanying
    # direct input must be an artifact committed by one of those manifests.
    # Otherwise an arbitrary sibling file could be paired with a valid marker
    # and appear generation-bound even though the upstream never published it.
    if upstream_manifests:
        unbound_inputs = set(sections["inputs"]) - upstream_manifests - upstream_artifacts
        if unbound_inputs:
            raise ReleaseIntegrityError(
                "release inputs are not committed artifacts of the declared "
                f"upstream releases: {', '.join(sorted(unbound_inputs))}"
            )

    validation_stack.remove(resolved_manifest)

    return ValidatedRelease(
        manifest_path=manifest_path.resolve(),
        # Bind the digest to the exact bytes parsed above.  Hashing the path a
        # second time would allow a concurrent os.replace to pair an old
        # payload with the digest of a newer manifest.
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        payload=payload,
    )


def validate_canonical_release(
    stage: str,
    *,
    manifest_path: Path | None = None,
    require_current_provenance: bool = False,
    require_current_runtime: bool = False,
) -> ValidatedRelease:
    """Validate the exact required input/artifact/DQ set for a stage."""
    contract = canonical_release_contract(stage)
    target = manifest_path or contract.manifest
    validated = validate_release(
        target,
        expected_stage=stage,
        required_inputs=contract.inputs,
        required_artifacts=contract.artifacts,
        required_checks=contract.checks,
        require_current_provenance=require_current_provenance,
        require_current_runtime=require_current_runtime,
    )
    payload = validated.payload
    expected_inputs = {_relative_path(path) for path in contract.inputs}
    expected_checks = {_relative_path(path) for path in contract.checks}
    expected_artifacts = {_relative_path(path) for path in contract.artifacts}
    if payload["metadata"]["lineage_sidecars"]:
        expected_artifacts.update(
            _relative_path(_lineage_sidecar(path))
            for path in contract.artifacts
            if path.suffix == ".parquet"
        )
    actual_inputs = {entry["path"] for entry in payload["inputs"]}
    actual_artifacts = {entry["path"] for entry in payload["artifacts"]}
    actual_checks = {entry["path"] for entry in payload["checks"]}
    mismatches = []
    if actual_inputs != expected_inputs:
        mismatches.append("inputs")
    if actual_artifacts != expected_artifacts:
        mismatches.append("artifacts")
    if actual_checks != expected_checks:
        mismatches.append("checks")
    if mismatches:
        raise ReleaseIntegrityError(
            f"canonical {stage} release has a non-exact file set: {', '.join(mismatches)}"
        )
    return validated


def read_released_parquet(
    manifest_path: Path,
    artifact_path: Path,
    *,
    expected_stage: str,
):
    """Read one Parquet artifact while rejecting concurrent release swaps."""
    import pandas as pd

    try:
        canonical = canonical_release_contract(expected_stage)
    except ReleaseIntegrityError:
        canonical = None
    if canonical is not None and canonical.manifest.resolve() == manifest_path.resolve():
        before = validate_canonical_release(
            expected_stage,
            require_current_provenance=True,
        )
    else:
        before = validate_release(
            manifest_path,
            expected_stage=expected_stage,
            required_artifacts=[artifact_path],
            require_current_provenance=True,
        )
    frame = pd.read_parquet(artifact_path)
    if canonical is not None and canonical.manifest.resolve() == manifest_path.resolve():
        after = validate_canonical_release(
            expected_stage,
            require_current_provenance=True,
        )
    else:
        after = validate_release(
            manifest_path,
            expected_stage=expected_stage,
            required_artifacts=[artifact_path],
            require_current_provenance=True,
        )
    if before.manifest_sha256 != after.manifest_sha256:
        raise ReleaseIntegrityError(f"release changed while reading artifact: {artifact_path}")
    return frame


def read_released_json(
    manifest_path: Path,
    artifact_path: Path,
    *,
    expected_stage: str,
) -> dict[str, Any]:
    """Read one JSON artifact while rejecting concurrent release swaps."""
    try:
        canonical = canonical_release_contract(expected_stage)
    except ReleaseIntegrityError:
        canonical = None
    if canonical is not None and canonical.manifest.resolve() == manifest_path.resolve():
        before = validate_canonical_release(
            expected_stage,
            require_current_provenance=True,
        )
    else:
        before = validate_release(
            manifest_path,
            expected_stage=expected_stage,
            required_artifacts=[artifact_path],
            require_current_provenance=True,
        )
    payload = _read_json_object(artifact_path, "released artifact")
    if canonical is not None and canonical.manifest.resolve() == manifest_path.resolve():
        after = validate_canonical_release(
            expected_stage,
            require_current_provenance=True,
        )
    else:
        after = validate_release(
            manifest_path,
            expected_stage=expected_stage,
            required_artifacts=[artifact_path],
            require_current_provenance=True,
        )
    if before.manifest_sha256 != after.manifest_sha256:
        raise ReleaseIntegrityError(f"release changed while reading artifact: {artifact_path}")
    return payload
