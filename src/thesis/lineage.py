"""Data lineage — every output gets a JSON sidecar describing its provenance.

Sidecar location: ``<output_path>.lineage.json`` next to the artifact, plus a
copy in ``data/_lineage/<table>/<run_id>.json`` for chronological audit.

Sidecar contents:
    table, layer, rows, columns, schema_fingerprint,
    inputs ([{path, sha256, rows, size_bytes}]),
    output_path, output_sha256, output_size_bytes,
    build_started_at, build_completed_at, duration_seconds,
    git_sha, code_version, pipeline_run_id, parameters
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import pandas as pd
from pyarrow.parquet import ParquetFile

from . import paths
from .config import settings
from .jsonutil import dumps_json
from .logging import get_logger, get_run_id
from .provenance import (
    configuration_fingerprint,
    implementation_fingerprint,
    runtime_fingerprint,
    runtime_provenance,
)


def _atomic_write_text(path: Path, payload: str) -> None:
    """Publish lineage JSON atomically beside its canonical destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(payload)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(settings().project_root),
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _code_version() -> str:
    try:
        return version("kosovo-procurement-thesis")
    except PackageNotFoundError:
        return "unknown"


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    """SHA-256 of a file's bytes."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(chunk):
            h.update(data)
    return h.hexdigest()


def schema_fingerprint(df: pd.DataFrame) -> str:
    """Stable hash of column names + dtypes (order-sensitive)."""
    spec = "|".join(f"{c}:{df[c].dtype}" for c in df.columns)
    return hashlib.sha256(spec.encode()).hexdigest()[:16]


def _portable_path(path: Path) -> str:
    """Use a data-root-relative path when possible, retaining external paths."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(paths.DATA.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_portable_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else paths.DATA.resolve() / path


@dataclass
class LineageInput:
    path: str
    sha256: str
    rows: int | None = None
    size_bytes: int | None = None


@dataclass
class Lineage:
    table: str
    layer: str
    rows: int
    columns: int
    schema_fingerprint: str
    inputs: list[LineageInput]
    output_path: str
    output_sha256: str = ""
    output_size_bytes: int = 0
    build_started_at: str = field(default_factory=lambda: _now_iso())
    build_completed_at: str = ""
    duration_seconds: float = 0.0
    git_sha: str = field(default_factory=_git_sha)
    code_version: str = field(default_factory=_code_version)
    implementation_fingerprint: str = field(default_factory=implementation_fingerprint)
    configuration_fingerprint: str = field(default_factory=configuration_fingerprint)
    runtime: dict[str, Any] = field(default_factory=runtime_provenance)
    runtime_fingerprint: str = field(default_factory=runtime_fingerprint)
    pipeline_run_id: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)

    def write(self) -> None:
        out_path = _resolve_portable_path(self.output_path)
        # finalise output stats
        if out_path.exists():
            self.output_sha256 = file_sha256(out_path)
            self.output_size_bytes = out_path.stat().st_size
        sidecar = out_path.with_suffix(out_path.suffix + ".lineage.json")
        payload = dumps_json(asdict(self), indent=2)
        _atomic_write_text(sidecar, payload)

        # also drop into chronological log
        run_dir = paths.DATA / "_lineage" / self.table
        run_dir.mkdir(parents=True, exist_ok=True)
        ts_clean = self.build_completed_at.replace(":", "").replace("-", "")
        rid = self.pipeline_run_id.replace("/", "_") or "norun"
        _atomic_write_text(
            run_dir / f"{ts_clean or 'unknown'}_{rid}.json",
            payload,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def track(
    table: str,
    layer: str,
    output_path: Path,
    inputs: list[Path] | None = None,
    parameters: dict[str, Any] | None = None,
) -> Iterator[Lineage]:
    """Context manager that produces a :class:`Lineage` ready to be written.

    Caller is responsible for setting ``rows`` / ``columns`` /
    ``schema_fingerprint`` on the yielded object once the dataframe is
    available, then calling ``.write()`` after the file has been persisted.
    For convenience, ``write_with_lineage`` does both in one call.
    """
    log = get_logger("lineage")
    started = time.time()
    in_objs = []
    for p in inputs or []:
        size = p.stat().st_size if p.exists() else None
        in_objs.append(LineageInput(path=_portable_path(p), sha256=file_sha256(p), size_bytes=size))
    lin = Lineage(
        table=table,
        layer=layer,
        rows=0,
        columns=0,
        schema_fingerprint="",
        inputs=in_objs,
        output_path=_portable_path(output_path),
        pipeline_run_id=get_run_id(),
        parameters=parameters or {},
    )
    log.info("build.start", table=table, layer=layer, output=str(output_path))
    try:
        yield lin
    except BaseException as exc:
        log.error(
            "build.failed",
            table=table,
            layer=layer,
            output=str(output_path),
            error=f"{type(exc).__name__}: {exc}",
        )
        raise
    else:
        finished = time.time()
        lin.build_completed_at = _now_iso()
        lin.duration_seconds = round(finished - started, 3)
        if settings().write_lineage_sidecars:
            # Lineage is part of the published artifact contract.  A failed
            # sidecar must abort the stage instead of leaving an apparently
            # successful primary file with missing or stale provenance.
            lin.write()
        log.info(
            "build.end",
            table=table,
            rows=lin.rows,
            cols=lin.columns,
            duration_s=lin.duration_seconds,
            output_sha256=lin.output_sha256[:12],
        )


def write_dataframe(
    df: pd.DataFrame,
    output_path: Path,
    table: str,
    layer: str,
    inputs: list[Path] | None = None,
    parameters: dict[str, Any] | None = None,
) -> Lineage:
    """Write a DataFrame to Parquet *with* a lineage sidecar.

    Returns the :class:`Lineage` object after writing.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        df.to_parquet(tmp, index=False)
        # Arrow can canonicalize pandas dtypes while writing (notably an
        # all-null object column).  Lineage must describe the persisted bytes,
        # because release validation independently fingerprints the Parquet
        # footer rather than the pre-serialization DataFrame.
        persisted_schema_frame = ParquetFile(tmp).schema_arrow.empty_table().to_pandas()
        with track(
            table,
            layer,
            output_path,
            inputs=inputs,
            parameters=parameters,
        ) as lin:
            lin.rows = len(df)
            lin.columns = df.shape[1]
            lin.schema_fingerprint = schema_fingerprint(persisted_schema_frame)
            os.replace(tmp, output_path)
        return lin
    finally:
        tmp.unlink(missing_ok=True)
