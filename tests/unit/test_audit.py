"""Tests for the manual-audit sampling protocol."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from thesis import audit as audit_module
from thesis.audit import (
    QUADRANTS,
    _document_url_status,
    _frame_content_sha256,
    _primary_document_url,
    build_audit_sample,
)
from thesis.lineage import file_sha256


def _frame() -> pd.DataFrame:
    rows = []
    for quadrant, rule_score, ensemble_score in [
        ("both", 0.8, 0.8),
        ("rule", 0.8, 0.2),
        ("ensemble", 0.2, 0.8),
        ("neither", 0.2, 0.2),
    ]:
        for i in range(4):
            rows.append(
                {
                    "ocid": f"{quadrant}-{i}",
                    "title": f"Tender {quadrant} {i}",
                    "rule_score": rule_score,
                    "ensemble_score": ensemble_score,
                    "SINGLE_BIDDER_OPEN": quadrant in {"both", "rule"},
                }
            )
    return pd.DataFrame(rows)


def test_audit_sample_is_balanced_unlabelled_and_deterministic() -> None:
    first, metadata = build_audit_sample(_frame(), per_quadrant=2, random_state=17)
    second, _ = build_audit_sample(_frame(), per_quadrant=2, random_state=17)

    pd.testing.assert_frame_equal(first, second)
    assert first["ocid"].is_unique
    assert set(first["audit_quadrant"]) == set(QUADRANTS)
    assert set(first.groupby("audit_quadrant").size()) == {2}
    assert first.filter(like="review_").eq("").all().all()
    assert metadata["status"] == "awaiting_human_review"
    assert metadata["labels_completed"] == 0
    assert metadata["sample_by_quadrant"] == dict.fromkeys(QUADRANTS, 2)
    assert metadata["empty_quadrants"] == []
    assert "document_source_sha256" in metadata


def test_frame_content_hash_accepts_nullable_integer_missing_values() -> None:
    frame = pd.DataFrame(
        {
            "audit_id": ["b", "a"],
            "nullable_count": pd.Series([pd.NA, 3], dtype="Int64"),
        }
    )

    first = _frame_content_sha256(frame, ["audit_id", "nullable_count"])
    second = _frame_content_sha256(frame.iloc[::-1], ["audit_id", "nullable_count"])

    assert first == second
    assert len(first) == 64


def test_primary_document_url_prefers_tender_notice() -> None:
    release = {
        "tender": {
            "documents": [
                {"documentType": "other", "url": "https://example.test/other"},
                {
                    "documentType": "tenderNotice",
                    "url": "https://example.test/notice",
                },
            ]
        }
    }
    assert _primary_document_url(release) == "https://example.test/notice"


def test_document_url_requires_nonblank_id_for_known_source_endpoint() -> None:
    invalid = "https://e-prokurimi.rks-gov.net/HOME/ClanakItemNew.aspx?id="
    known_endpoint = "https://e-prokurimi.rks-gov.net/HOME/DokumentPodaciFrm.aspx?id="
    valid = "https://e-prokurimi.rks-gov.net/HOME/DokumentPodaciFrm.aspx?id=123"

    # Generic absolute URLs are structurally valid; the known document
    # endpoint additionally requires its source-published document id.
    assert _document_url_status(invalid)[0] == "structurally_valid_unverified"
    assert _document_url_status(known_endpoint)[0] == "invalid_source_url"
    assert _document_url_status(valid)[0] == "structurally_valid_unverified"


def test_primary_document_url_falls_back_to_another_valid_published_document() -> None:
    release = {
        "tender": {
            "documents": [
                {
                    "documentType": "tenderNotice",
                    "url": "https://e-prokurimi.rks-gov.net/HOME/DokumentPodaciFrm.aspx?id=",
                },
                {"documentType": "other", "url": "https://example.test/exact-source"},
            ]
        }
    }
    assert _primary_document_url(release) == "https://example.test/exact-source"


def _configure_temp_audit(monkeypatch, tmp_path, frame: pd.DataFrame) -> None:
    sample_path = tmp_path / "manual_audit_sample.csv"
    metadata_path = tmp_path / "manual_audit_sample.metadata.json"
    raw_path = tmp_path / "source.jsonl"
    raw_path.write_text(
        "".join(
            json.dumps(
                {
                    "ocid": ocid,
                    "tender": {
                        "documents": [
                            {
                                "documentType": "tenderNotice",
                                "url": f"https://example.test/doc/{ocid}",
                            }
                        ]
                    },
                }
            )
            + "\n"
            for ocid in frame["ocid"]
        )
    )
    monkeypatch.setattr(audit_module, "AUDIT_SAMPLE", sample_path)
    monkeypatch.setattr(audit_module, "AUDIT_METADATA", metadata_path)
    monkeypatch.setattr(audit_module, "RAW_JSONL", raw_path)
    monkeypatch.setattr(audit_module, "GOLD_TENDERS", tmp_path / "gold.parquet")
    monkeypatch.setattr(audit_module.readers, "load_gold_tenders", lambda: frame.copy())


def test_force_regeneration_preserves_human_fields_and_hashes(monkeypatch, tmp_path) -> None:
    frame = _frame()
    _configure_temp_audit(monkeypatch, tmp_path, frame)
    audit_module.generate_audit_sample(per_quadrant=1)
    sample = pd.read_csv(audit_module.AUDIT_SAMPLE, dtype=str, keep_default_na=False)
    reviewed_ocid = sample["ocid"].iat[0]
    sample.loc[0, "source_document_reviewed"] = "yes"
    sample.loc[0, "review_relevant_concern"] = "uncertain"
    sample.loc[0, "review_evidence_note"] = "Human-entered evidence note"
    sample.loc[0, "reviewer_id"] = "reviewer-1"
    sample.to_csv(audit_module.AUDIT_SAMPLE, index=False)

    metadata = audit_module.generate_audit_sample(per_quadrant=1, force=True)
    regenerated = pd.read_csv(audit_module.AUDIT_SAMPLE, dtype=str, keep_default_na=False)
    row = regenerated.set_index("ocid").loc[reviewed_ocid]

    assert row["review_relevant_concern"] == "uncertain"
    assert row["review_evidence_note"] == "Human-entered evidence note"
    assert metadata["status"] == "partially_reviewed"
    assert metadata["labels_completed"] == 1
    assert metadata["reviewed_rows_preserved"] == 1
    assert metadata["sample_sha256"] == file_sha256(audit_module.AUDIT_SAMPLE)
    assert len(metadata["label_state_sha256"]) == 64
    assert len(metadata["sample_definition_sha256"]) == 64
    assert metadata["source_document_url_count"] == len(regenerated)


def test_force_regeneration_refuses_to_drop_a_reviewed_ocid(monkeypatch, tmp_path) -> None:
    frame = _frame()
    _configure_temp_audit(monkeypatch, tmp_path, frame)
    audit_module.generate_audit_sample(per_quadrant=1)
    sample = pd.read_csv(audit_module.AUDIT_SAMPLE, dtype=str, keep_default_na=False)
    removed_ocid = sample["ocid"].iat[0]
    sample.loc[0, "review_relevant_concern"] = "yes"
    sample.to_csv(audit_module.AUDIT_SAMPLE, index=False)
    reduced = frame[frame["ocid"].ne(removed_ocid)].copy()
    monkeypatch.setattr(audit_module.readers, "load_gold_tenders", lambda: reduced.copy())

    with pytest.raises(ValueError, match="drop human-reviewed OCIDs"):
        audit_module.generate_audit_sample(per_quadrant=1, force=True)
