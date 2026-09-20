"""Readers must not mix or retain obsolete release generations."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from thesis.io import readers
from thesis.release import ReleaseIntegrityError


def test_no_argument_reader_does_not_cache_prior_generation(monkeypatch):
    generations = iter([1, 2])

    def fake_read(*args, **kwargs):
        del args, kwargs
        return pd.DataFrame({"generation": [next(generations)]})

    monkeypatch.setattr(readers, "read_released_parquet", fake_read)

    assert readers.load_silver_tenders().at[0, "generation"] == 1
    assert readers.load_silver_tenders().at[0, "generation"] == 2


def test_silver_bundle_rejects_release_swap_between_tables(monkeypatch):
    validations = iter(
        [
            SimpleNamespace(manifest_sha256="a" * 64),
            SimpleNamespace(manifest_sha256="b" * 64),
        ]
    )
    monkeypatch.setattr(
        readers,
        "validate_canonical_release",
        lambda *args, **kwargs: next(validations),
    )
    monkeypatch.setattr(
        readers.pd,
        "read_parquet",
        lambda path: pd.DataFrame({"path": [str(path)]}),
    )

    with pytest.raises(ReleaseIntegrityError, match="changed while reading"):
        readers.load_silver_bundle()


def test_dashboard_bundle_rejects_cross_stage_manifest_swap(monkeypatch):
    calls = {"silver": 0, "gold": 0, "ml": 0}

    def validate(stage, **kwargs):
        del kwargs
        calls[stage] += 1
        suffix = "new" if stage == "silver" and calls[stage] > 1 else "old"
        return SimpleNamespace(manifest_sha256=f"{stage}-{suffix}")

    monkeypatch.setattr(readers, "validate_canonical_release", validate)
    monkeypatch.setattr(
        readers.pd,
        "read_parquet",
        lambda path: pd.DataFrame({"source": [str(path)]}),
    )

    with pytest.raises(ReleaseIntegrityError, match="dashboard bundle: silver"):
        readers.load_dashboard_bundle(include_shap=True)


def test_dashboard_bundle_reads_optional_shap_and_metadata_under_one_guard(monkeypatch, tmp_path):
    monkeypatch.setattr(
        readers,
        "validate_canonical_release",
        lambda stage, **kwargs: SimpleNamespace(manifest_sha256=f"{stage}-stable"),
    )
    monkeypatch.setattr(
        readers.pd,
        "read_parquet",
        lambda path: pd.DataFrame({"source": [path.name]}),
    )
    feature_metadata = tmp_path / "feature_list.json"
    feature_metadata.write_text('{"ensemble_explanation": {"schema_version": 1}}')
    monkeypatch.setattr(readers.paths, "FEATURE_LIST", feature_metadata)

    without_shap = readers.load_dashboard_bundle()
    with_shap = readers.load_dashboard_bundle(include_shap=True)
    with_all = readers.load_dashboard_bundle(
        include_shap=True,
        include_model_metadata=True,
    )

    assert set(without_shap) == {"gold", "awards", "suppliers", "entities"}
    assert set(with_shap) == {*without_shap, "shap"}
    assert set(with_all) == {*with_shap, "feature_metadata"}
    assert with_all["feature_metadata"]["ensemble_explanation"]["schema_version"] == 1
