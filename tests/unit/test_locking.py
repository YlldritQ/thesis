"""The canonical pipeline permits only one publishing process at a time."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from thesis.locking import pipeline_lock


def test_pipeline_lock_rejects_second_process_nonblocking(tmp_path: Path):
    script = """
import sys
from pathlib import Path
from thesis.locking import PipelineLockError, pipeline_lock
try:
    with pipeline_lock(data_root=Path(sys.argv[1]), blocking=False):
        pass
except PipelineLockError:
    raise SystemExit(23)
"""
    with pipeline_lock(data_root=tmp_path):
        result = subprocess.run(
            [sys.executable, "-c", script, str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 23, result.stderr


def test_pipeline_lock_is_reentrant_within_process(tmp_path: Path):
    with (
        pipeline_lock(data_root=tmp_path) as outer,
        pipeline_lock(data_root=tmp_path, blocking=False) as inner,
    ):
        assert inner == outer
