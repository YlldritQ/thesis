"""Single-writer lock for canonical pipeline publication.

Per-file ``os.replace`` prevents partial files, but a multi-file generation
also needs one writer across the whole stage/run. The lock is data-root scoped,
process-safe on the supported macOS/Linux deployment targets, and re-entrant
within one process so a DAG wrapper may call stage wrappers safely.
"""

from __future__ import annotations

import fcntl
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from . import paths
from .jsonutil import dumps_json


class PipelineLockError(RuntimeError):
    """Another process currently owns the canonical publication lock."""


_process_guard = threading.RLock()
_held: dict[Path, tuple[TextIO, int, dict[str, str]]] = {}


def active_pipeline_provenance() -> dict[str, str] | None:
    """Return the outermost lock's immutable execution fingerprints."""
    with _process_guard:
        if not _held:
            return None
        # One process should publish to only one data root at a time. Returning
        # a copy prevents callers from mutating the lock snapshot.
        return dict(next(iter(_held.values()))[2])


@contextmanager
def pipeline_lock(
    *,
    data_root: Path | None = None,
    blocking: bool = True,
) -> Iterator[Path]:
    """Hold the data-root publication lock for a complete run or stage."""
    root = (data_root or paths.DATA).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".pipeline.lock"
    with _process_guard:
        existing = _held.get(lock_path)
        if existing is not None:
            handle, depth, provenance = existing
            _held[lock_path] = (handle, depth + 1, provenance)
            try:
                yield lock_path
            finally:
                _held[lock_path] = (handle, depth, provenance)
            return

        handle = lock_path.open("a+", encoding="utf-8")
        operation = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        try:
            try:
                fcntl.flock(handle.fileno(), operation)
            except BlockingIOError as exc:
                raise PipelineLockError(
                    f"canonical pipeline publication is already locked: {lock_path}"
                ) from exc
            handle.seek(0)
            handle.truncate()
            handle.write(
                dumps_json(
                    {
                        "pid": os.getpid(),
                        "acquired_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
            handle.flush()
            os.fsync(handle.fileno())
            from .provenance import execution_fingerprints

            _held[lock_path] = (handle, 1, execution_fingerprints())
            try:
                yield lock_path
            finally:
                _held.pop(lock_path, None)
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
