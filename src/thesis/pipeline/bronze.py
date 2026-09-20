"""Bronze layer — download the raw OCDS JSONL and extract it.

The explicit :func:`run` command remains offline-friendly: when a local dump
already exists it uses it without contacting the network. Scheduled refreshes
call :func:`check_updates`, which downloads and validates a complete staged
gzip, compares the SHA-256 of its *decompressed* JSONL content, and atomically
promotes both canonical files only after validation succeeds.
"""

from __future__ import annotations

import gzip
import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from ..config import settings
from ..jsonutil import loads_json
from ..logging import get_logger
from ..paths import BRONZE_RELEASE, RAW_GZ, RAW_JSONL, ensure_dirs
from ..release import ReleaseIntegrityError, publish_release, validate_release

log = get_logger("pipeline.bronze")


def _sibling_temp(path: Path, label: str) -> Path:
    """Return a unique, non-existent temporary sibling of *path*."""
    return path.with_name(f".{path.name}.{label}.{uuid.uuid4().hex}.tmp")


def _download_to(target: Path, url: str | None = None) -> dict[str, Any]:
    """Stream the publication into *target* (atomic: tmp + replace)."""
    cfg = settings()
    target_url = url or cfg.ocds_publication_url
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = _sibling_temp(target, "download")
    req = Request(target_url, headers={"User-Agent": "kosovo-procurement-thesis/1.0"})
    total = 0
    try:
        with urlopen(req, timeout=cfg.ocds_request_timeout_s) as resp, open(tmp, "xb") as out:
            while chunk := resp.read(cfg.ocds_chunk_bytes):
                out.write(chunk)
                total += len(chunk)
            response_metadata = {
                "source_url": target_url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "content_length": resp.headers.get("Content-Length"),
            }
        os.replace(tmp, target)
        return {"size_bytes": total, **response_metadata}
    finally:
        tmp.unlink(missing_ok=True)


def _file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Return a SHA-256 digest for *path*, or an empty string if absent."""
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as src:
        while chunk := src.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, "rb") as src:
        return sum(1 for _ in src)


def _extract_validated(source: Path, target: Path) -> tuple[int, str]:
    """Validate *source* fully while extracting it to staged JSONL.

    Reading to EOF verifies the gzip CRC. Every line must also be a non-empty
    JSON document. The returned digest covers the exact decompressed bytes, so
    corrected records are detected even when the row count is unchanged.
    """
    digest = hashlib.sha256()
    records = 0
    with gzip.open(source, "rb") as src, open(target, "xb") as out:
        for line_number, line in enumerate(src, 1):
            if not line.strip():
                raise ValueError(f"blank JSONL record at line {line_number}")
            try:
                value = loads_json(line)
                if not isinstance(value, dict):
                    raise ValueError("JSONL record must contain an object")
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(f"invalid JSONL record at line {line_number}") from exc
            out.write(line)
            digest.update(line)
            records += 1
        if records == 0:
            raise ValueError("downloaded publication contains no JSONL records")
        out.flush()
        os.fsync(out.fileno())
    return records, digest.hexdigest()


def _validate_local_pair() -> tuple[int, str]:
    """Prove that canonical gzip inflates to the exact canonical JSONL bytes."""
    if not RAW_GZ.is_file() or not RAW_JSONL.is_file():
        raise FileNotFoundError("both canonical bronze gzip and JSONL are required")
    staged = _sibling_temp(RAW_JSONL, "pair-validation")
    try:
        records, digest = _extract_validated(RAW_GZ, staged)
        if digest != _file_sha256(RAW_JSONL) or staged.stat().st_size != RAW_JSONL.stat().st_size:
            raise ValueError("canonical bronze gzip does not match the extracted JSONL")
        return records, digest
    finally:
        staged.unlink(missing_ok=True)


def _publish_bronze_release(
    *,
    records: int,
    content_sha256: str,
    acquisition: dict[str, Any] | None,
) -> None:
    cfg = settings()
    recorded_source_url = acquisition.get("source_url") if isinstance(acquisition, dict) else None
    publish_release(
        BRONZE_RELEASE,
        stage="bronze",
        inputs=[],
        artifacts=[RAW_GZ, RAW_JSONL],
        metadata={
            "records": records,
            "decompressed_content_sha256": content_sha256,
            "source_url": recorded_source_url or cfg.ocds_publication_url,
            "source_url_basis": (
                "retrieval_evidence" if recorded_source_url else "configured_expected_source"
            ),
            "acquisition": acquisition
            or {
                "evidence_available": False,
                "reason": (
                    "Historical local snapshot: original retrieval timestamp and HTTP "
                    "headers are unavailable and were not inferred."
                ),
            },
        },
    )


def _normalise_acquisition(value: object, source_url: str | None) -> dict[str, Any]:
    """Accept the structured downloader result and legacy test doubles safely."""
    if isinstance(value, dict):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return {
            "size_bytes": value,
            "source_url": source_url or settings().ocds_publication_url,
            "retrieved_at": None,
            "etag": None,
            "last_modified": None,
            "content_length": None,
        }
    raise TypeError("downloader must return acquisition metadata")


def _download_with_metadata(
    url: str | None = None, force: bool = False
) -> tuple[Path, dict[str, Any] | None]:
    """Download a validated gzip and retain its HTTP acquisition evidence."""
    ensure_dirs()
    if RAW_GZ.exists() and not force:
        log.info(
            "bronze.download.skip",
            path=str(RAW_GZ),
            size_mb=round(RAW_GZ.stat().st_size / 1e6, 1),
            reason="already present",
        )
        return RAW_GZ, None

    log.info("bronze.download.start", dest=str(RAW_GZ))
    staged_gz = _sibling_temp(RAW_GZ, "staged")
    staged_jsonl = _sibling_temp(RAW_JSONL, "validation")
    try:
        acquisition = _normalise_acquisition(_download_to(staged_gz, url=url), url)
        records, digest = _extract_validated(staged_gz, staged_jsonl)
        os.replace(staged_gz, RAW_GZ)
        log.info(
            "bronze.download.done",
            size_mb=round(int(acquisition["size_bytes"]) / 1e6, 1),
            records=records,
            content_sha256=digest,
        )
        return RAW_GZ, acquisition
    finally:
        staged_gz.unlink(missing_ok=True)
        staged_jsonl.unlink(missing_ok=True)


def download(url: str | None = None, force: bool = False) -> Path:
    """Download a validated gzip, preserving the prior canonical on failure."""
    return _download_with_metadata(url=url, force=force)[0]


def check_updates(url: str | None = None) -> dict:
    """Validate the latest publication and compare decompressed content hashes.

    A new or corrected publication is fully downloaded, decompressed, and JSON
    validated before either canonical artifact changes. Record counts remain in
    the result for observability, but SHA-256 is the change detector.
    """
    ensure_dirs()
    staged_gz = _sibling_temp(RAW_GZ, "fresh")
    staged_jsonl = _sibling_temp(RAW_JSONL, "fresh")
    old_records = _count_jsonl_records(RAW_JSONL)
    old_digest = _file_sha256(RAW_JSONL)
    try:
        log.info("bronze.check_updates.download", dest=str(staged_gz))
        acquisition = _normalise_acquisition(_download_to(staged_gz, url=url), url)
        new_records, new_digest = _extract_validated(staged_gz, staged_jsonl)
        changed = not old_digest or new_digest != old_digest
        needs_promotion = changed or not RAW_GZ.exists() or not RAW_JSONL.exists()
        log.info(
            "bronze.check_updates.compare",
            old_records=old_records,
            new_records=new_records,
            new_delta=new_records - old_records,
            old_sha256=old_digest,
            new_sha256=new_digest,
            changed=changed,
        )

        if needs_promotion:
            # Each replacement is atomic because its stage is a sibling. Gzip is
            # the source artifact; JSONL is its validated, derived extraction.
            os.replace(staged_gz, RAW_GZ)
            os.replace(staged_jsonl, RAW_JSONL)
            log.info("bronze.check_updates.swapped", records=new_records)
        else:
            log.info("bronze.check_updates.unchanged")

        records, canonical_digest = _validate_local_pair()
        release_needs_publication = needs_promotion
        if not release_needs_publication:
            try:
                current_release = validate_release(
                    BRONZE_RELEASE,
                    expected_stage="bronze",
                    required_artifacts=[RAW_GZ, RAW_JSONL],
                    require_current_provenance=True,
                    require_current_runtime=True,
                )
                prior_acquisition = current_release.payload["metadata"].get("acquisition", {})
                release_needs_publication = prior_acquisition.get("evidence_available") is not True
            except ReleaseIntegrityError:
                release_needs_publication = True
        if release_needs_publication:
            _publish_bronze_release(
                records=records,
                content_sha256=canonical_digest,
                acquisition={"evidence_available": True, **acquisition},
            )

        return {
            "old_records": old_records,
            "new_records": new_records,
            "new_delta": new_records - old_records,
            "old_sha256": old_digest,
            "new_sha256": new_digest,
            "changed": changed,
        }
    finally:
        staged_gz.unlink(missing_ok=True)
        staged_jsonl.unlink(missing_ok=True)


def extract(force: bool = False) -> Path:
    """Validate and atomically extract the local gzip to canonical JSONL."""
    if RAW_JSONL.exists() and not force:
        log.info(
            "bronze.extract.skip",
            path=str(RAW_JSONL),
            size_mb=round(RAW_JSONL.stat().st_size / 1e6, 1),
        )
        return RAW_JSONL
    log.info("bronze.extract.start", src=str(RAW_GZ), dest=str(RAW_JSONL))
    staged_jsonl = _sibling_temp(RAW_JSONL, "extract")
    try:
        records, digest = _extract_validated(RAW_GZ, staged_jsonl)
        os.replace(staged_jsonl, RAW_JSONL)
        log.info(
            "bronze.extract.done",
            size_mb=round(RAW_JSONL.stat().st_size / 1e6, 1),
            records=records,
            content_sha256=digest,
        )
        return RAW_JSONL
    finally:
        staged_jsonl.unlink(missing_ok=True)


def quick_summary() -> dict:
    """Return a ``{records, first_keys}`` rollup of the extracted file."""
    if not RAW_JSONL.exists():
        return {"records": 0, "first_keys": []}
    n = 0
    sample: dict | None = None
    with open(RAW_JSONL) as f:
        for line in f:
            if sample is None:
                value = loads_json(line)
                if not isinstance(value, dict):
                    raise ValueError("JSONL record must contain an object")
                sample = value
            n += 1
    return {"records": n, "first_keys": list((sample or {}).keys())}


def run(force_download: bool = False, force_extract: bool = False) -> dict:
    """Use the local bronze snapshot, downloading only when absent/forced.

    This is the explicit offline-friendly command. The scheduled DAG uses
    :func:`check_updates` so it always checks the remote publication.
    """
    _, acquisition = _download_with_metadata(force=force_download)
    extract(force=force_extract or force_download)
    summary = quick_summary()
    records, digest = _validate_local_pair()
    try:
        existing = validate_release(
            BRONZE_RELEASE,
            expected_stage="bronze",
            required_artifacts=[RAW_GZ, RAW_JSONL],
            require_current_provenance=True,
            require_current_runtime=True,
        )
        metadata = existing.payload["metadata"]
        if (
            metadata.get("records") != records
            or metadata.get("decompressed_content_sha256") != digest
        ):
            raise ReleaseIntegrityError("bronze release metadata does not match local snapshot")
    except ReleaseIntegrityError:
        preserved_acquisition: dict[str, Any] | None = None
        if acquisition is None and BRONZE_RELEASE.is_file():
            try:
                prior = validate_release(
                    BRONZE_RELEASE,
                    expected_stage="bronze",
                    required_artifacts=[RAW_GZ, RAW_JSONL],
                )
                prior_value = prior.payload["metadata"].get("acquisition")
                if isinstance(prior_value, dict):
                    preserved_acquisition = prior_value
            except ReleaseIntegrityError:
                pass
        if acquisition is not None:
            preserved_acquisition = {"evidence_available": True, **acquisition}
        _publish_bronze_release(
            records=records,
            content_sha256=digest,
            acquisition=preserved_acquisition,
        )
    summary["content_sha256"] = digest
    log.info("bronze.summary", **summary)
    return summary
