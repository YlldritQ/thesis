"""Tests for the OSHP evidence-status module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.external.oshp import OSHP_SNAPSHOT, canonical_name


def test_canonical_strips_legal_forms_and_diacritics():
    # different legal-form spellings of the same firm collapse to one key
    assert canonical_name("Pro Medical SH.P.K.") == canonical_name("pro medical shpk")
    assert canonical_name("ARCHI TIME Sh.p.k") == canonical_name("archi time SHPK")
    # diacritics removed
    assert "ë" not in canonical_name("Gëzime Gashi B.I")
    # empty / non-string safe
    assert canonical_name(None) == ""
    assert canonical_name("") == ""


def test_canonical_keeps_distinct_firms_distinct():
    assert canonical_name("Leicon Sh.P.K") != canonical_name("Ida Auto Group Sh.P.K")


def test_snapshot_exists_and_parses():
    import json

    if not OSHP_SNAPSHOT.exists():
        pytest.skip("OSHP snapshot not present")
    data = json.loads(OSHP_SNAPSHOT.read_text())
    assert data["rows"]
    assert all("operator" in r for r in data["rows"])


@pytest.mark.skipif(
    not OSHP_SNAPSHOT.exists(),
    reason="OSHP snapshot not present",
)
def test_validate_withdraws_invalid_tender_level_inference():
    from thesis.external.oshp import validate

    r = validate(write=False)
    assert r["status"] == "withdrawn"
    assert r["usable_as_external_validation"] is False
    assert r["observed_row_fields"] == ["authority", "operator"]
    assert r["computed_metrics"] == []
    assert "exact link to a tender" in r["reason"]
