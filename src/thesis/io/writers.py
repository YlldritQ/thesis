"""Writers — every persistent artifact passes through here.

Parquet publication emits a lineage sidecar through
:func:`thesis.lineage.track`. Every writer stages a complete sibling file and
uses :func:`os.replace`, so readers see either the prior artifact or the new
complete artifact, never a partially-written canonical file.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from pyarrow.parquet import ParquetFile

from ..jsonutil import dumps_json
from ..lineage import Lineage, schema_fingerprint, track


def _sibling_temp(path: Path) -> Path:
    """Return a unique, non-existent temporary sibling of *path*.

    Keeping the staged file in the destination directory guarantees that
    :func:`os.replace` stays on one filesystem and is therefore atomic.
    """
    return path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text completely before atomically publishing it at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _sibling_temp(path)
    try:
        tmp.write_text(text)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def write_parquet(
    df: pd.DataFrame,
    path: Path,
    table: str,
    layer: str,
    inputs: list[Path] | None = None,
    parameters: dict[str, Any] | None = None,
) -> Lineage:
    """Atomically persist a DataFrame to Parquet with a lineage sidecar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _sibling_temp(path)
    try:
        # Build the complete parquet beside the canonical destination. A failed
        # serializer therefore cannot truncate the last known-good artifact.
        df.to_parquet(tmp, index=False)
        # Parquet/Arrow may canonicalize an in-memory dtype (for example an
        # all-null object column). Record the schema of the bytes that will be
        # published, not the pre-serialization frame, so lineage validation
        # compares like with like.
        persisted_schema_frame = ParquetFile(tmp).schema_arrow.empty_table().to_pandas()
        with track(
            table,
            layer,
            path,
            inputs=inputs,
            parameters=parameters,
        ) as lineage:
            lineage.rows = len(df)
            lineage.columns = df.shape[1]
            lineage.schema_fingerprint = schema_fingerprint(persisted_schema_frame)
            os.replace(tmp, path)
        return lineage
    finally:
        tmp.unlink(missing_ok=True)


def write_json(
    obj: Any,
    path: Path,
    indent: int = 2,
) -> None:
    payload = dumps_json(obj, indent=indent)
    _atomic_write_text(path, payload)


def write_csv(
    df: pd.DataFrame,
    path: Path,
    **kwargs: Any,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _sibling_temp(path)
    try:
        df.to_csv(tmp, index=kwargs.pop("index", False), **kwargs)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def write_markdown(text: str, path: Path) -> None:
    _atomic_write_text(path, text)


def write_joblib(obj: Any, path: Path) -> None:
    """Atomically persist a joblib artifact beside its canonical target.

    Model serialization can fail after writing part of the destination.  A
    unique sibling staging file keeps the last known-good model readable until
    serialization has completed and :func:`os.replace` publishes it in one
    operation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _sibling_temp(path)
    try:
        joblib.dump(obj, tmp)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
