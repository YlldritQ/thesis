"""Bronze→Silver→Gold integration test using a synthetic OCDS fixture.

Strategy: swap ``THESIS_DATA_DIR`` to a tmp dir, write 8 synthetic OCDS
records to ``raw/``, publish Bronze, then run Silver and Gold end-to-end.
Benchmark/ML have separate release-contract tests and are rebuilt against the
full source population during acceptance, not this tiny statistically invalid
fixture.
"""

from __future__ import annotations

import gzip
import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


@pytest.fixture
def _restore_modules_after():
    """Re-reload path-dependent modules after the test so the reloaded
    tmp-dir constants don't pollute later tests in the same session.

    NB: this fixture's teardown runs *before* monkeypatch undoes the env,
    so it must clear the THESIS_* overrides itself before reloading.
    """
    yield
    import os

    for var in [
        "THESIS_DATA_DIR",
        "THESIS_FAIL_FAST_ON_DQ",
        "THESIS_OCSVM_SUBSAMPLE_SIZE",
        "THESIS_BOOTSTRAP_SAMPLES",
    ]:
        os.environ.pop(var, None)
    from thesis import config

    config.reset_settings_for_tests()
    import thesis.io.readers
    import thesis.lineage
    import thesis.paths

    importlib.reload(thesis.paths)
    importlib.reload(thesis.lineage)
    importlib.reload(thesis.io.readers)
    from thesis.pipeline import bronze, gold, ml, silver

    for m in (bronze, silver, gold, ml):
        importlib.reload(m)


@pytest.mark.integration
def test_pipeline_end_to_end(
    tmp_path: Path, monkeypatch, synthetic_ocds_records, _restore_modules_after
):
    """Bronze → Silver → Gold on 8 synthetic records, no network."""
    monkeypatch.setenv("THESIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("THESIS_FAIL_FAST_ON_DQ", "false")
    monkeypatch.setenv("THESIS_OCSVM_SUBSAMPLE_SIZE", "100")
    monkeypatch.setenv("THESIS_BOOTSTRAP_SAMPLES", "3")

    # Reload config + paths so they pick up the new data_dir
    from thesis import config

    config.reset_settings_for_tests()
    from thesis import paths

    importlib.reload(paths)
    from thesis import lineage

    importlib.reload(lineage)
    from thesis import release
    from thesis.io import readers

    importlib.reload(readers)
    from thesis.pipeline import bronze, gold, ml, silver

    for m in (bronze, silver, gold, ml):
        importlib.reload(m)

    # Drop synthetic bronze fixture into the new raw dir
    paths.ensure_dirs()
    with open(paths.RAW_JSONL, "w") as f:
        for rec in synthetic_ocds_records:
            f.write(json.dumps(rec) + "\n")
    with gzip.open(paths.RAW_GZ, "wb") as compressed:
        compressed.write(paths.RAW_JSONL.read_bytes())

    # ---- bronze ----
    res_bronze = bronze.run()
    assert res_bronze["records"] == len(synthetic_ocds_records)
    release.validate_canonical_release(
        "bronze",
        require_current_provenance=True,
        require_current_runtime=True,
    )

    # ---- silver ----
    res_silver = silver.run()
    assert res_silver["tenders"] == len(synthetic_ocds_records)
    assert paths.SILVER_TENDERS.exists()
    assert paths.SILVER_AWARDS.exists()
    release.validate_canonical_release(
        "silver",
        require_current_provenance=True,
        require_current_runtime=True,
    )
    sidecar = paths.SILVER_TENDERS.with_suffix(".parquet.lineage.json")
    assert sidecar.exists()
    sidecar_payload = json.loads(sidecar.read_text())
    assert sidecar_payload["rows"] == len(synthetic_ocds_records)

    # ---- gold ----
    res_gold = gold.run()
    assert res_gold["tender_features"] == len(synthetic_ocds_records)
    assert paths.GOLD_FEATURES.exists()
    assert paths.GOLD_RELEASE.exists()
    release.validate_canonical_release(
        "gold",
        require_current_provenance=True,
        require_current_runtime=True,
    )
    assert not paths.GOLD_TENDERS.exists()
    g = pd.read_parquet(paths.GOLD_FEATURES)
    assert "rule_score" in g.columns
    assert "ensemble_score" not in g.columns
    # Synthetic test-002 is an open procedure, so the mutually exclusive
    # open-procedure single-bidder rule must trigger.
    assert g.set_index("ocid").loc["ocds-uhzcmx-test-002", "SINGLE_BIDDER_OPEN"]
    # Synthetic test-006 must trigger RATIO_ABOVE_ESTIMATE
    assert g.set_index("ocid").loc["ocds-uhzcmx-test-006", "RATIO_ABOVE_ESTIMATE"]
    # Synthetic test-007 must trigger RATIO_BELOW_50
    assert g.set_index("ocid").loc["ocds-uhzcmx-test-007", "RATIO_BELOW_50"]
    for summary_path in [
        paths.GOLD_SUPPLIERS,
        paths.GOLD_ENTITIES,
        paths.GOLD_MONTHLY,
    ]:
        summary_lineage = json.loads(summary_path.with_suffix(".parquet.lineage.json").read_text())
        relative_features = paths.GOLD_FEATURES.relative_to(paths.DATA).as_posix()
        assert relative_features in {item["path"] for item in summary_lineage["inputs"]}
