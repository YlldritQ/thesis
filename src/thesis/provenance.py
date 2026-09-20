"""Deterministic implementation, configuration, and runtime provenance.

The project directory does not necessarily contain Git metadata.  A release
therefore cannot rely on a commit id alone to prove which implementation built
an artifact.  This module hashes the actual source files and the effective
pipeline configuration, while still recording a Git id when one exists.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .config import settings

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REQUIRED_PACKAGE_FILES = {
    "__init__.py",
    "provenance.py",
    "release.py",
    "pipeline/dag.py",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _source_checkout_root() -> Path | None:
    """Return the checkout containing this imported package, if present.

    This intentionally does not trust ``THESIS_PROJECT_ROOT``: that setting
    controls operational paths and must not be able to redirect code
    provenance to an empty or unrelated directory.
    """
    candidate = _PACKAGE_ROOT.parent.parent
    if (candidate / "pyproject.toml").is_file() and (
        candidate / "src" / "thesis"
    ).resolve() == _PACKAGE_ROOT:
        return candidate.resolve()
    return None


def source_files() -> list[Path]:
    """Return actual imported package files and dependency declarations."""
    package_files = sorted(path.resolve() for path in _PACKAGE_ROOT.rglob("*.py"))
    observed = {path.relative_to(_PACKAGE_ROOT).as_posix() for path in package_files}
    missing = _REQUIRED_PACKAGE_FILES - observed
    if not package_files or missing:
        raise RuntimeError(
            "implementation provenance cannot locate required imported source files: "
            f"{', '.join(sorted(missing)) or 'package is empty'}"
        )
    candidates = list(package_files)
    checkout = _source_checkout_root()
    if checkout is not None:
        candidates.extend(
            path.resolve()
            for name in (
                "pyproject.toml",
                "requirements.txt",
                "requirements-lock.txt",
                "uv.lock",
            )
            if (path := checkout / name).is_file()
        )
    return sorted(set(candidates), key=_logical_source_name)


def _logical_source_name(path: Path) -> str:
    resolved = path.resolve()
    try:
        return f"src/thesis/{resolved.relative_to(_PACKAGE_ROOT).as_posix()}"
    except ValueError:
        checkout = _source_checkout_root()
        if checkout is not None:
            try:
                return resolved.relative_to(checkout).as_posix()
            except ValueError:
                pass
        return resolved.as_posix()


def implementation_manifest(files: Iterable[Path] | None = None) -> dict[str, str]:
    """Map project-relative implementation paths to their exact SHA-256."""
    selected = (
        source_files()
        if files is None
        else sorted({path.resolve() for path in files}, key=lambda p: p.as_posix())
    )
    manifest: dict[str, str] = {}
    for path in selected:
        if not path.is_file():
            raise FileNotFoundError(f"implementation provenance file is missing: {path}")
        name = _logical_source_name(path)
        if name in manifest:
            raise RuntimeError(f"duplicate logical implementation path: {name}")
        manifest[name] = _sha256(path)
    if not manifest:
        raise RuntimeError("implementation provenance manifest is empty")
    return manifest


def implementation_fingerprint(files: Iterable[Path] | None = None) -> str:
    """SHA-256 over exact source paths and bytes."""
    encoded = json.dumps(
        implementation_manifest(files),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


_CONFIG_EXCLUDE = {
    "project_root",
    "data_dir",
    "docs_dir",
    "pipeline_run_id",
    "log_level",
    "log_format",
    "streamlit_default_page_size",
    "streamlit_max_search_results",
}


def effective_pipeline_configuration() -> dict[str, Any]:
    """Return effective settings that can affect acquired or derived artifacts."""
    raw = settings().model_dump(exclude=_CONFIG_EXCLUDE)
    return {key: raw[key] for key in sorted(raw)}


def configuration_fingerprint() -> str:
    """SHA-256 over the effective artifact-affecting configuration."""
    payload = json.dumps(
        effective_pipeline_configuration(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _installed_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "not-installed"


def runtime_provenance() -> dict[str, Any]:
    """Compact execution-environment identity for release metadata."""
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": sys.platform,
        "package": _installed_version("kosovo-procurement-thesis"),
        "libraries": {
            name: _installed_version(distribution)
            for name, distribution in {
                "numpy": "numpy",
                "pandas": "pandas",
                "pyarrow": "pyarrow",
                "scipy": "scipy",
                "scikit_learn": "scikit-learn",
                "shap": "shap",
                "joblib": "joblib",
            }.items()
        },
    }


def runtime_fingerprint(runtime: dict[str, Any] | None = None) -> str:
    """SHA-256 over the exact artifact-affecting runtime identity."""
    payload = runtime_provenance() if runtime is None else runtime
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def execution_fingerprints() -> dict[str, str]:
    """Capture source, configuration, and runtime at stage/run start."""
    return {
        "implementation_fingerprint": implementation_fingerprint(),
        "configuration_fingerprint": configuration_fingerprint(),
        "runtime_fingerprint": runtime_fingerprint(),
    }
