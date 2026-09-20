"""Lightweight expectation framework.

Why not Great Expectations? GE is excellent but heavyweight; for thesis-scale
work the expectation set is small and explicit, and we want fast feedback
in CI without a metadata DB. This module gives us:

* A typed :class:`Expectation` with a name, a predicate, and a severity.
* :class:`ExpectationSuite` for grouping.
* :func:`run_suite` returns a structured :class:`SuiteResult` that the CLI
  prints, the dashboard renders, and CI fails on if severity ≥ ``error``.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

import pandas as pd

from .. import paths
from ..io.writers import write_json, write_markdown
from ..lineage import file_sha256
from ..logging import get_logger

log = get_logger("dq")


def dataframe_fingerprint(df: pd.DataFrame) -> str:
    """Content-and-schema hash used to bind DQ evidence to one exact table."""
    digest = hashlib.sha256()
    digest.update("|".join(f"{column}:{df[column].dtype}" for column in df.columns).encode())
    digest.update(pd.util.hash_pandas_object(df, index=False).to_numpy().tobytes())
    return digest.hexdigest()


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Expectation:
    """One DQ check.

    * ``name``: short snake_case identifier.
    * ``description``: human-readable one-liner.
    * ``predicate``: ``df -> (passed, observed_value)``.
    * ``severity``: ``info``, ``warning`` (pipeline continues unless
      ``THESIS_FAIL_FAST_ON_DQ=true``), or ``error`` (always blocking).
    """

    name: str
    description: str
    predicate: Callable[[pd.DataFrame], tuple[bool, object]]
    severity: Severity = Severity.WARNING


@dataclass
class ExpectationResult:
    name: str
    description: str
    severity: str
    passed: bool
    observed: object
    duration_ms: float


@dataclass
class SuiteResult:
    suite: str
    table: str
    passed: bool
    error_count: int
    warning_count: int
    info_count: int
    pass_count: int
    fail_count: int
    duration_ms: float
    timestamp: str
    rows: int
    columns: int
    data_fingerprint: str
    expectations: list[ExpectationResult] = field(default_factory=list)

    def write(self) -> Path:
        # Resolve through the module at call time. Tests reload ``thesis.paths``
        # after redirecting THESIS_DATA_DIR; capturing ``DQ`` at import time
        # would otherwise send their fixture evidence to the canonical data dir.
        dq_dir = paths.DQ
        out = dq_dir / f"{self.suite}.dq.json"
        write_json(asdict(self), out)
        # also write a markdown summary
        md = dq_dir / f"{self.suite}.dq.md"
        write_markdown(self._render_markdown(), md)
        return out

    def _render_markdown(self) -> str:
        head = (
            f"# DQ — {self.suite}\n\n"
            f"_Run at_: `{self.timestamp}`  ·  _table_: `{self.table}`\n\n"
            f"_shape_: `{self.rows} × {self.columns}`  ·  "
            f"_data fingerprint_: `{self.data_fingerprint}`\n\n"
            f"**Result:** {'✅ PASS' if self.passed else '❌ FAIL'}  ·  "
            f"errors={self.error_count}  warnings={self.warning_count}  "
            f"infos={self.info_count}  passed={self.pass_count}  "
            f"failed={self.fail_count}  duration_ms={self.duration_ms:.1f}\n\n"
        )
        rows = []
        rows.append("| status | severity | name | description | observed |")
        rows.append("|---|---|---|---|---|")
        for e in self.expectations:
            rows.append(
                "| {ok} | {sev} | `{n}` | {d} | `{o}` |".format(
                    ok="✅" if e.passed else "❌",
                    sev=e.severity,
                    n=e.name,
                    d=e.description.replace("|", "\\|"),
                    o=str(e.observed)[:80].replace("|", "\\|"),
                )
            )
        return head + "\n".join(rows) + "\n"

    def release_payload(self, artifact: Path, frame: pd.DataFrame) -> dict:
        """Bind this result to the exact persisted artifact it authorizes."""
        observed_fingerprint = dataframe_fingerprint(frame)
        if (
            self.rows != len(frame)
            or self.columns != frame.shape[1]
            or self.data_fingerprint != observed_fingerprint
        ):
            raise ValueError("DQ result does not describe the supplied release frame")
        if not artifact.is_file():
            raise FileNotFoundError(f"cannot bind DQ evidence to missing artifact: {artifact}")
        relative = artifact.resolve().relative_to(paths.DATA.resolve()).as_posix()
        return {
            **asdict(self),
            "release_binding": {
                "artifact_path": relative,
                "artifact_sha256": file_sha256(artifact),
                "artifact_size_bytes": artifact.stat().st_size,
            },
        }


@dataclass
class ExpectationSuite:
    """A named bundle of expectations for one table."""

    name: str
    table: str
    expectations: list[Expectation]


def run_suite(suite: ExpectationSuite, df: pd.DataFrame) -> SuiteResult:
    """Evaluate every expectation on *df* and return a structured result."""
    started = time.time()
    out: list[ExpectationResult] = []
    err = warn = info = ok = fail = 0
    for exp in suite.expectations:
        t0 = time.time()
        try:
            passed, observed = exp.predicate(df)
            # Pandas reductions commonly return ``numpy.bool_``. Preserve a
            # strict JSON/data contract instead of relying on ``default=str``,
            # which would serialize those values as misleading strings.
            passed = bool(passed)
        except Exception as e:  # noqa: BLE001
            passed, observed = False, f"exception: {e}"
        duration_ms = (time.time() - t0) * 1000
        out.append(
            ExpectationResult(
                name=exp.name,
                description=exp.description,
                severity=exp.severity.value,
                passed=passed,
                observed=observed,
                duration_ms=duration_ms,
            )
        )
        if passed:
            ok += 1
        else:
            fail += 1
            if exp.severity == Severity.ERROR:
                err += 1
            elif exp.severity == Severity.WARNING:
                warn += 1
            else:
                info += 1

    duration_ms = (time.time() - started) * 1000
    res = SuiteResult(
        suite=suite.name,
        table=suite.table,
        passed=err == 0,
        error_count=err,
        warning_count=warn,
        info_count=info,
        pass_count=ok,
        fail_count=fail,
        duration_ms=duration_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
        rows=len(df),
        columns=df.shape[1],
        data_fingerprint=dataframe_fingerprint(df),
        expectations=out,
    )

    log.info(
        "dq.suite",
        suite=suite.name,
        table=suite.table,
        passed=res.passed,
        errors=err,
        warnings=warn,
        ok=ok,
        fail=fail,
        duration_ms=round(duration_ms, 1),
    )
    return res
