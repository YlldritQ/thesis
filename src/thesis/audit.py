"""Deterministic stratified sampling for the required human tender audit.

The model benchmark measures faithfulness to author-defined screening rules;
it is not outcome validation. This module creates a review queue across the
four possible rule×ensemble quadrants so a human can inspect source documents
without silently replacing missing ground truth with model labels. It takes
up to the requested count from each populated quadrant, records empty strata
rather than fabricating examples, and leaves every judgement field blank.
"""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import parse_qs, urlparse

import pandas as pd

from .anomaly.rules import RULES
from .config import settings
from .io import readers
from .io.writers import write_csv, write_json
from .jsonutil import loads_json
from .lineage import file_sha256
from .paths import DATA, GOLD_TENDERS, RAW_JSONL

AUDIT_DIR = DATA / "review"
AUDIT_SAMPLE = AUDIT_DIR / "manual_audit_sample.csv"
AUDIT_METADATA = AUDIT_DIR / "manual_audit_sample.metadata.json"

QUADRANTS = (
    "both_flagged",
    "rule_only",
    "ensemble_only",
    "neither",
)

_REVIEW_COLUMNS = (
    "ocid",
    "title",
    "procuring_entity_name",
    "procedure_subtype",
    "method",
    "method_details",
    "category",
    "start_date",
    "end_date",
    "estimated_value_eur",
    "total_awarded_eur",
    "num_bidders",
    "n_awards",
    "rule_score",
    "ensemble_score",
)

_EMPTY_LABEL_COLUMNS = (
    "source_document_reviewed",
    "review_relevant_concern",
    "review_data_quality_issue",
    "review_concern_type",
    "review_evidence_note",
    "reviewer_id",
    "review_date",
)

_URL_STATUS_VALID = "structurally_valid_unverified"
_URL_STATUS_MISSING = "missing_from_source"
_URL_STATUS_INVALID = "invalid_source_url"


def _document_url_status(value: object) -> tuple[str, str]:
    """Classify source URL structure without pretending to verify HTTP access."""
    url = str(value or "").strip()
    if not url:
        return _URL_STATUS_MISSING, "No document URL is published in the sampled release."
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _URL_STATUS_INVALID, "The published value is not an absolute HTTP(S) URL."
    if parsed.path.casefold().endswith("dokumentpodacifrm.aspx"):
        document_ids = parse_qs(parsed.query, keep_blank_values=True).get("id", [])
        if not any(str(document_id).strip() for document_id in document_ids):
            return _URL_STATUS_INVALID, "The published document endpoint has an empty id parameter."
    return (
        _URL_STATUS_VALID,
        "Exact URL copied from the OCDS release; structure checked, HTTP availability not verified.",
    )


def _primary_document_url(release: dict[str, Any]) -> str:
    """Choose an exact source-document URL, preferring the tender notice."""
    documents = release.get("tender", {}).get("documents", []) or []
    candidates = [
        document
        for document in documents
        if isinstance(document, dict) and str(document.get("url", "")).strip()
    ]
    notices = [
        document for document in candidates if document.get("documentType") == "tenderNotice"
    ]
    for document in [*notices, *candidates]:
        url = str(document["url"]).strip()
        status, _ = _document_url_status(url)
        if status == _URL_STATUS_VALID:
            return url
    # Preserve an invalid published value for auditable status reporting rather
    # than fabricating a substitute URL.
    fallback = notices[0] if notices else (candidates[0] if candidates else None)
    return str(fallback["url"]).strip() if fallback else ""


def _frame_content_sha256(frame: pd.DataFrame, columns: list[str]) -> str:
    """Hash a stable CSV projection without mutating or writing the frame."""
    available = [column for column in columns if column in frame]
    # Convert extension dtypes before replacing missing values.  In particular,
    # nullable integer columns reject an empty-string fill value while they are
    # still Int64, which previously made audit regeneration fail before any
    # output could be published.
    ordered = frame[available].astype("string").fillna("")
    if "audit_id" in ordered:
        ordered = ordered.sort_values("audit_id", kind="stable")
    payload = ordered.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _audit_state_metadata(sample: pd.DataFrame) -> dict[str, Any]:
    review_columns = [column for column in _EMPTY_LABEL_COLUMNS if column in sample]
    review_values = sample[review_columns].fillna("").astype(str).apply(lambda s: s.str.strip())
    any_review = review_values.ne("").any(axis=1)
    completed = sample.get("review_relevant_concern", pd.Series("", index=sample.index))
    completed = completed.fillna("").astype(str).str.strip().ne("")
    completed_count = int(completed.sum())
    any_review_count = int(any_review.sum())
    if len(sample) and completed_count == len(sample):
        completion_status = "human_review_complete"
    elif completed_count:
        completion_status = "partially_reviewed"
    elif any_review_count:
        completion_status = "review_in_progress"
    else:
        completion_status = "awaiting_human_review"
    return {
        "completion_status": completion_status,
        "completion_definition": "nonblank review_relevant_concern",
        "review_population": int(len(sample)),
        "labels_completed": completed_count,
        "labels_remaining": int(len(sample) - completed_count),
        "rows_with_any_review_data": any_review_count,
        "label_state_sha256": _frame_content_sha256(
            sample,
            ["audit_id", "ocid", *review_columns],
        ),
        "sample_definition_sha256": _frame_content_sha256(
            sample,
            [column for column in sample.columns if column not in review_columns],
        ),
    }


def _source_document_urls(ocids: set[str]) -> dict[str, str]:
    """Stream raw OCDS once and return source links for the sampled tenders."""
    if not ocids or not RAW_JSONL.exists():
        return {}
    remaining = set(ocids)
    urls: dict[str, str] = {}
    with RAW_JSONL.open(encoding="utf-8") as source:
        for line in source:
            try:
                release = loads_json(line)
            except (ValueError, TypeError):
                continue
            ocid = str(release.get("ocid", ""))
            if ocid not in remaining:
                continue
            urls[ocid] = _primary_document_url(release)
            remaining.remove(ocid)
            if not remaining:
                break
    return urls


def build_audit_sample(
    frame: pd.DataFrame,
    *,
    per_quadrant: int = 50,
    random_state: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a deterministic, stratified audit queue and its provenance.

    ``review_*`` fields are always empty.  Generating this sample is therefore
    not evidence that any tender has been reviewed or that either detector is
    correct.
    """
    if per_quadrant < 1:
        raise ValueError("per_quadrant must be at least 1")
    required = {"ocid", "rule_score", "ensemble_score"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"gold table is missing audit fields: {sorted(missing)}")

    cfg = settings()
    seed = cfg.random_seed if random_state is None else random_state
    work = frame.copy()
    rule_flag = work["rule_score"].ge(cfg.rule_score_review_threshold)
    ensemble_flag = work["ensemble_score"].ge(cfg.ensemble_score_review_threshold)
    work["audit_quadrant"] = "neither"
    work.loc[rule_flag & ensemble_flag, "audit_quadrant"] = "both_flagged"
    work.loc[rule_flag & ~ensemble_flag, "audit_quadrant"] = "rule_only"
    work.loc[~rule_flag & ensemble_flag, "audit_quadrant"] = "ensemble_only"

    rule_columns = [rule.code for rule in RULES if rule.code in work.columns]
    samples: list[pd.DataFrame] = []
    population: dict[str, int] = {}
    for offset, quadrant in enumerate(QUADRANTS):
        pool = work[work["audit_quadrant"].eq(quadrant)]
        population[quadrant] = int(len(pool))
        n_take = min(per_quadrant, len(pool))
        chosen = pool.sample(n=n_take, random_state=seed + offset).copy()
        chosen = chosen.sort_values("ocid", kind="stable").reset_index(drop=True)
        chosen.insert(
            0,
            "audit_id",
            [f"{quadrant}-{i:03d}" for i in range(1, len(chosen) + 1)],
        )
        if rule_columns:
            chosen["active_indicators"] = chosen[rule_columns].apply(
                lambda row: ";".join(code for code in rule_columns if bool(row.get(code, False))),
                axis=1,
            )
        else:
            chosen["active_indicators"] = ""
        samples.append(chosen)

    sample = pd.concat(samples, ignore_index=True)
    keep = [
        "audit_id",
        "audit_quadrant",
        *[column for column in _REVIEW_COLUMNS if column in sample.columns],
        "active_indicators",
    ]
    sample = sample[keep]
    sample["source_document_url"] = ""
    sample["source_document_url_status"] = "not_resolved"
    sample["source_document_url_note"] = ""
    for column in _EMPTY_LABEL_COLUMNS:
        sample[column] = ""

    metadata: dict[str, Any] = {
        "status": "awaiting_human_review",
        "labels_completed": 0,
        "source_artifact": str(GOLD_TENDERS),
        "source_sha256": file_sha256(GOLD_TENDERS) if GOLD_TENDERS.exists() else None,
        "document_source_artifact": str(RAW_JSONL),
        "document_source_sha256": file_sha256(RAW_JSONL) if RAW_JSONL.exists() else None,
        "random_seed": seed,
        "requested_per_quadrant": per_quadrant,
        "rule_threshold": cfg.rule_score_review_threshold,
        "ensemble_threshold": cfg.ensemble_score_review_threshold,
        "population_by_quadrant": population,
        "sample_by_quadrant": {
            quadrant: int(sample["audit_quadrant"].eq(quadrant).sum()) for quadrant in QUADRANTS
        },
        "empty_quadrants": [quadrant for quadrant in QUADRANTS if population[quadrant] == 0],
        "warning": (
            "This file is an unlabeled stratified review queue. Empty review "
            "fields must not be interpreted as negative labels; empty source "
            "quadrants are reported as zero and are not synthetically filled."
        ),
    }
    metadata.update(_audit_state_metadata(sample))
    return sample, metadata


def generate_audit_sample(
    *,
    per_quadrant: int = 50,
    force: bool = False,
) -> dict[str, Any]:
    """Build and atomically publish the unlabeled audit queue.

    Refuse a routine overwrite. With ``force=True``, preserve all human fields
    by OCID and fail rather than drop reviewed rows that are absent from the new
    deterministic sample.
    """
    existing: pd.DataFrame | None = None
    previous_sample_sha256: str | None = None
    previous_label_state_sha256: str | None = None
    if AUDIT_SAMPLE.exists() and not force:
        raise FileExistsError(
            f"{AUDIT_SAMPLE} already exists; pass --force to regenerate with label preservation"
        )
    if AUDIT_SAMPLE.exists():
        previous_sample_sha256 = file_sha256(AUDIT_SAMPLE)
        existing = pd.read_csv(AUDIT_SAMPLE, dtype=str, keep_default_na=False)
        required_existing = {"ocid", *_EMPTY_LABEL_COLUMNS}
        missing_existing = required_existing.difference(existing.columns)
        if missing_existing:
            raise ValueError(
                "existing audit sample cannot be safely preserved; missing columns: "
                f"{sorted(missing_existing)}"
            )
        if existing["ocid"].duplicated().any():
            raise ValueError("existing audit sample has duplicate OCIDs; refusing overwrite")
        previous_label_state_sha256 = _audit_state_metadata(existing)["label_state_sha256"]

    frame = readers.load_gold_tenders()
    sample, metadata = build_audit_sample(frame, per_quadrant=per_quadrant)

    labels_preserved = 0
    rows_preserved = 0
    if existing is not None:
        review_values = existing[list(_EMPTY_LABEL_COLUMNS)].apply(lambda s: s.str.strip())
        rows_with_review = existing[review_values.ne("").any(axis=1)]
        dropped_reviewed = sorted(set(rows_with_review["ocid"]) - set(sample["ocid"].astype(str)))
        if dropped_reviewed:
            raise ValueError(
                "regeneration would drop human-reviewed OCIDs; refusing overwrite: "
                f"{dropped_reviewed[:10]}"
            )
        rows_preserved = int(sample["ocid"].astype(str).isin(rows_with_review["ocid"]).sum())
        by_ocid = existing.set_index("ocid")
        for column in _EMPTY_LABEL_COLUMNS:
            preserved = sample["ocid"].astype(str).map(by_ocid[column]).fillna("")
            labels_preserved += int(preserved.astype(str).str.strip().ne("").sum())
            sample[column] = preserved

    urls = _source_document_urls(set(sample["ocid"].astype(str)))
    sample["source_document_url"] = sample["ocid"].map(urls).fillna("")
    statuses = sample["source_document_url"].map(_document_url_status)
    sample["source_document_url_status"] = statuses.map(lambda status: status[0])
    sample["source_document_url_note"] = statuses.map(lambda status: status[1])
    status_counts = sample["source_document_url_status"].value_counts().to_dict()
    metadata["source_document_url_status_counts"] = {
        str(status): int(count) for status, count in status_counts.items()
    }
    metadata["source_document_url_nonblank_count"] = int(
        sample["source_document_url"].astype(str).str.strip().ne("").sum()
    )
    metadata["source_document_url_count"] = int(
        sample["source_document_url_status"].eq(_URL_STATUS_VALID).sum()
    )
    metadata["source_document_url_coverage_pct"] = round(
        100 * metadata["source_document_url_count"] / max(len(sample), 1), 2
    )
    state = _audit_state_metadata(sample)
    metadata.update(state)
    metadata["status"] = state["completion_status"]
    metadata["labels_preserved_field_count"] = labels_preserved
    metadata["reviewed_rows_preserved"] = rows_preserved
    metadata["previous_sample_sha256"] = previous_sample_sha256
    metadata["previous_label_state_sha256"] = previous_label_state_sha256
    write_csv(sample, AUDIT_SAMPLE)
    metadata["sample_sha256"] = file_sha256(AUDIT_SAMPLE)
    write_json(metadata, AUDIT_METADATA)
    return metadata
