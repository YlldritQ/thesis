"""Implementation/runtime provenance must describe the code actually imported."""

from __future__ import annotations

from pathlib import Path

from thesis import config, provenance


def test_project_root_override_cannot_empty_implementation_manifest(tmp_path, monkeypatch):
    expected = provenance.implementation_manifest()

    monkeypatch.setenv("THESIS_PROJECT_ROOT", str(tmp_path))
    config.reset_settings_for_tests()
    try:
        observed = provenance.implementation_manifest()
    finally:
        config.reset_settings_for_tests()

    assert observed == expected
    assert "src/thesis/release.py" in observed
    assert "src/thesis/pipeline/dag.py" in observed


def test_missing_imported_package_source_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(provenance, "_PACKAGE_ROOT", tmp_path)

    try:
        provenance.implementation_manifest()
    except RuntimeError as exc:
        assert "cannot locate required imported source files" in str(exc)
    else:  # pragma: no cover - explicit failure message is easier to diagnose
        raise AssertionError("empty implementation provenance was accepted")


def test_dockerfile_copies_every_dependency_file_in_provenance_scope():
    project_root = Path(__file__).resolve().parents[2]
    dockerfile = (project_root / "Dockerfile").read_text(encoding="utf-8")

    for filename in (
        "pyproject.toml",
        "requirements.txt",
        "requirements-lock.txt",
        "uv.lock",
    ):
        assert dockerfile.count(f"COPY {filename} ./") == 2
