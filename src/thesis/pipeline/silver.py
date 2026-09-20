"""Bronze → Silver transformation.

Two normalised Parquet tables: ``tenders`` (one row per OCID) and
``awards`` (one row per award-supplier combination). Both are validated
with Pydantic, Pandera, and expectation suites before persistence. DQ errors
always abort; ``THESIS_FAIL_FAST_ON_DQ=true`` additionally blocks warnings.
"""

from __future__ import annotations

import pandas as pd

from ..config import settings
from ..domain.contracts import (
    AwardRecord,
    TenderRecord,
    validate_dataframe,
)
from ..domain.features import normalise_supplier_business_id
from ..domain.procedures import procedure_code_from_tender_id
from ..domain.schemas import validate_silver_awards, validate_silver_tenders
from ..dq.framework import run_suite
from ..dq.suites import silver_awards_suite_for, silver_tenders_suite
from ..io.readers import iter_raw_records
from ..io.writers import write_json, write_parquet
from ..logging import bind, get_logger, unbind
from ..paths import (
    BRONZE_RELEASE,
    RAW_JSONL,
    SILVER_AWARDS,
    SILVER_AWARDS_RELEASE_DQ,
    SILVER_RELEASE,
    SILVER_TENDERS,
    SILVER_TENDERS_RELEASE_DQ,
    ensure_dirs,
)
from ..release import ReleaseIntegrityError, publish_release, validate_canonical_release

log = get_logger("pipeline.silver")

AWARD_LOT_MATCH_STATUSES = frozenset(
    {"exact_unique", "exact_ambiguous", "no_exact_match", "missing_title"}
)


def _award_signature(a: dict) -> tuple:
    """Identity of one award within a tender, robust to source re-publication.

    Within a single contracting process a given lot is awarded once, to one
    supplier, for one amount. The KRPP feed nonetheless re-publishes the same
    award on a later date in ~0.8 % of tenders (an initial notice + an
    amendment/confirmation), which double-counts `total_awarded_eur` and
    triggers false "paid-above-estimate" flags (e.g. the N25 road works).

    We key on lot title, amount/currency, and a stable supplier identity. A
    valid business ID is preferred, then source party ID/UID, then normalized
    name. This keeps republications together while preventing two blank-name
    suppliers with distinct published party IDs from collapsing. Award date,
    ``award.uID`` and ``award.id`` remain deliberately ignored because they are
    row/version identifiers in this feed and change across republications.
    """
    suppliers = a.get("suppliers") or []

    def _supplier_identity(supplier: dict) -> tuple[str, str]:
        party = supplier.get("party") or {}
        identity = party.get("identity") or {}
        business_id = normalise_supplier_business_id(identity.get("identificationNumber"))
        if business_id is not None:
            return "business_id", business_id
        party_id = str(party.get("id") or supplier.get("id") or "").strip()
        if party_id:
            return "source_party_id", party_id
        party_uid = str(party.get("uID") or "").strip()
        if party_uid:
            return "source_party_uid", party_uid
        name = str(party.get("name") or supplier.get("name") or "")
        return "name", " ".join(name.casefold().split())

    supplier_identities = tuple(sorted(_supplier_identity(supplier) for supplier in suppliers))
    return (
        a.get("lotTitle"),
        (a.get("value") or {}).get("amount"),
        (a.get("value") or {}).get("currency"),
        supplier_identities,
    )


def dedup_award_list(awards: list[dict]) -> list[dict]:
    """Drop exact-duplicate award objects, preserving first-seen order."""
    seen: set = set()
    out: list[dict] = []
    for a in awards:
        sig = _award_signature(a)
        if sig in seen:
            continue
        seen.add(sig)
        out.append(a)
    return out


def _award_lot_match_status(award: dict, tender: dict) -> str:
    """Describe whether an award lot title links exactly to a tender lot.

    The feed exposes titles rather than a shared lot identifier on awards.
    Exact title equality can therefore be audited, but translated, corrected,
    or repeated titles must not be silently treated as a reliable lot join.
    """
    award_title = str(award.get("lotTitle") or "").strip()
    if not award_title:
        return "missing_title"
    tender_titles = [str(lot.get("title") or "").strip() for lot in tender.get("lots") or []]
    exact_matches = sum(title == award_title for title in tender_titles)
    if exact_matches == 1:
        return "exact_unique"
    if exact_matches > 1:
        return "exact_ambiguous"
    return "no_exact_match"


def _extract_tender(rec: dict) -> dict:
    t = rec.get("tender") or {}
    v = t.get("value") or {}
    p = t.get("tenderPeriod") or {}
    pe = (t.get("procuringEntity") or {}).get("party") or {}
    parties = rec.get("parties") or []
    roles = [set(p.get("roles") or []) for p in parties]
    tenderer_role_count = sum("tenderer" in role_set for role_set in roles)
    tenderers = t.get("tenderers")
    if isinstance(tenderers, list):
        num_bidders: int | None = len(tenderers)
        bidder_data_observed = True
    elif tenderer_role_count > 0:
        num_bidders = tenderer_role_count
        bidder_data_observed = True
    else:
        num_bidders = None
        bidder_data_observed = False
    lots = t.get("lots") or []
    lot_values = [(lot.get("value") or {}).get("valueAmount") for lot in lots]
    lot_values = [x for x in lot_values if isinstance(x, (int, float))]
    return {
        "ocid": rec.get("ocid"),
        "release_id": rec.get("id"),
        "release_date": rec.get("date"),
        "tender_id": t.get("id"),
        "procedure_code": procedure_code_from_tender_id(t.get("id")),
        "title": t.get("title"),
        "status": t.get("status"),
        "category": t.get("mainProcurementCategory"),
        "method": t.get("procurementMethod"),
        "method_details": t.get("procurementMethodDetails"),
        "award_criteria": t.get("awardCriteria"),
        "estimated_value_eur": v.get("amount"),
        "currency": v.get("currency"),
        "start_date": p.get("startDate"),
        "end_date": p.get("endDate"),
        "duration_reported_days": p.get("durationInDays"),
        "procuring_entity_id": pe.get("id"),
        "procuring_entity_uid": pe.get("uID"),
        "procuring_entity_name": pe.get("name"),
        "num_lots": len(lots),
        "lots_value_sum": sum(lot_values) if lot_values else None,
        "num_bidders": num_bidders,
        "bidder_data_observed": bidder_data_observed,
        "num_suppliers_in_parties": sum("supplier" in r for r in roles),
        "num_parties": len(parties),
        "num_awards": len(rec.get("award") or []),
    }


def _extract_awards(rec: dict) -> list[dict]:
    out: list[dict] = []
    ocid = rec.get("ocid")
    tender = rec.get("tender") or {}
    tender_id = tender.get("id")
    for a in rec.get("award") or []:
        suppliers = a.get("suppliers") or []
        common = {
            "ocid": ocid,
            "tender_id": tender_id,
            "award_id": a.get("id") or a.get("uID"),
            "award_uid": a.get("uID"),
            "award_title": a.get("title"),
            "award_description": a.get("description"),
            "award_lot_title": a.get("lotTitle"),
            "award_lot_match_status": _award_lot_match_status(a, tender),
            "award_date": a.get("date"),
            "award_status_id": a.get("statusID"),
            "awarded_value_eur": (a.get("value") or {}).get("amount"),
            "awarded_currency": (a.get("value") or {}).get("currency"),
        }
        if not suppliers:
            out.append(
                {
                    **common,
                    "supplier_party_id": None,
                    "supplier_uid": None,
                    "supplier_name": None,
                    "supplier_legal_name": None,
                    "supplier_business_id": None,
                    "supplier_business_id_raw": None,
                    "supplier_org_schema": None,
                }
            )
            continue
        for s in suppliers:
            party = s.get("party") or {}
            ident = party.get("identity") or {}
            business_id_raw = ident.get("identificationNumber")
            out.append(
                {
                    **common,
                    "supplier_party_id": party.get("id") or s.get("id"),
                    "supplier_uid": party.get("uID"),
                    "supplier_name": party.get("name") or s.get("name"),
                    "supplier_legal_name": ident.get("legalName"),
                    "supplier_business_id": normalise_supplier_business_id(business_id_raw),
                    "supplier_business_id_raw": business_id_raw,
                    "supplier_org_schema": ident.get("orgSchema"),
                }
            )
    return out


def _build_silver_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    tenders: list[dict] = []
    awards: list[dict] = []
    for n, rec in enumerate(iter_raw_records(), start=1):
        # Collapse source-duplicated award rows once, so both the tender
        # summary (num_awards, total) and the award rows agree. The guarded
        # iterator rejects a Bronze manifest swap during this full scan.
        rec["award"] = dedup_award_list(rec.get("award") or [])
        tenders.append(_extract_tender(rec))
        awards.extend(_extract_awards(rec))
        if n % 20000 == 0:
            log.info("silver.parse.progress", records_processed=n)

    tdf = pd.DataFrame(tenders)
    for col in ("release_date", "start_date", "end_date"):
        tdf[col] = pd.to_datetime(tdf[col], errors="coerce", utc=True)
    tdf["num_bidders"] = pd.to_numeric(tdf["num_bidders"], errors="coerce").astype("Int64")
    tdf["duration_computed_days"] = (
        (tdf["end_date"] - tdf["start_date"]).dt.total_seconds() / 86400
    ).round(2)
    tdf["end_before_start"] = tdf["end_date"] < tdf["start_date"]

    adf = pd.DataFrame(awards)
    if not adf.empty:
        adf["award_date"] = pd.to_datetime(adf["award_date"], errors="coerce", utc=True)

    enrich = tdf[
        [
            "ocid",
            "category",
            "method",
            "estimated_value_eur",
            "procuring_entity_id",
            "procuring_entity_name",
            "num_bidders",
            "bidder_data_observed",
            "num_awards",
        ]
    ]
    if not adf.empty:
        adf = adf.merge(enrich, on="ocid", how="left", suffixes=("", "_tender"))
        adf["num_bidders"] = pd.to_numeric(adf["num_bidders"], errors="coerce").astype("Int64")
        adf["value_ratio"] = (adf["awarded_value_eur"] / adf["estimated_value_eur"]).replace(
            [float("inf"), float("-inf")], pd.NA
        )

    return tdf, adf


def run() -> dict:
    """Build silver tables and write them. Returns row counts."""
    bind(stage="silver")
    try:
        ensure_dirs()
        log.info("silver.start")
        bronze_release = validate_canonical_release(
            "bronze",
            require_current_provenance=True,
            require_current_runtime=True,
        )

        tdf, adf = _build_silver_tables()
        bronze_after_parse = validate_canonical_release(
            "bronze",
            require_current_provenance=True,
            require_current_runtime=True,
        )
        if bronze_after_parse.manifest_sha256 != bronze_release.manifest_sha256:
            raise ReleaseIntegrityError("Bronze release changed while building Silver")

        # Full row-contract validation is a publication gate. Sampling can hide
        # a late invalid record and ``fail_fast_on_dq`` governs warnings only;
        # Pydantic contract violations always block canonical publication.
        _, terr = validate_dataframe(tdf, TenderRecord, sample=None)
        if terr:
            log.warning("silver.contract.tender_errors", errors=terr[:3])
            raise ValueError(f"silver.tenders contract violation: {terr[0]}")
        _, aerr = validate_dataframe(adf, AwardRecord, sample=None)
        if aerr:
            log.warning("silver.contract.award_errors", errors=aerr[:3])
            raise ValueError(f"silver.awards contract violation: {aerr[0]}")

        # pandera dataframe-level validation
        validate_silver_tenders(tdf)
        validate_silver_awards(adf)

        # DQ expectation suites. ERROR-severity failures are contract
        # violations and ALWAYS abort (per-severity gating, review H-7);
        # fail_fast_on_dq additionally makes WARNINGs blocking. Evaluate and
        # persist the general evidence before promoting either canonical
        # parquet. Release-bound evidence is recomputed from the persisted
        # Parquet bytes below.
        tres = run_suite(silver_tenders_suite, tdf)
        ares = run_suite(silver_awards_suite_for(tdf["ocid"]), adf)
        tres.write()
        ares.write()
        if not tres.passed or not ares.passed:
            raise ValueError(
                "silver DQ ERROR — contract violation, aborting "
                f"(tenders errors={tres.error_count}, awards errors={ares.error_count})"
            )
        if settings().fail_fast_on_dq and (tres.warning_count or ares.warning_count):
            raise ValueError("silver DQ warnings present and THESIS_FAIL_FAST_ON_DQ=true")

        # Publish only validated frames. ``write_parquet`` stages each complete
        # file beside its destination and atomically replaces the canonical
        # artifact, so a serialization failure cannot truncate the prior run.
        write_parquet(
            tdf,
            SILVER_TENDERS,
            table="silver.tenders",
            layer="silver",
            inputs=[BRONZE_RELEASE, RAW_JSONL],
        )
        write_parquet(
            adf,
            SILVER_AWARDS,
            table="silver.awards",
            layer="silver",
            inputs=[BRONZE_RELEASE, RAW_JSONL],
        )

        persisted_tenders = pd.read_parquet(SILVER_TENDERS)
        persisted_awards = pd.read_parquet(SILVER_AWARDS)
        persisted_tres = run_suite(silver_tenders_suite, persisted_tenders)
        persisted_ares = run_suite(
            silver_awards_suite_for(persisted_tenders["ocid"]),
            persisted_awards,
        )
        if not persisted_tres.passed or not persisted_ares.passed:
            raise ValueError("persisted Silver artifacts fail release DQ")
        if settings().fail_fast_on_dq and (
            persisted_tres.warning_count or persisted_ares.warning_count
        ):
            raise ValueError("persisted Silver DQ warnings and THESIS_FAIL_FAST_ON_DQ=true")
        write_json(
            persisted_tres.release_payload(SILVER_TENDERS, persisted_tenders),
            SILVER_TENDERS_RELEASE_DQ,
        )
        write_json(
            persisted_ares.release_payload(SILVER_AWARDS, persisted_awards),
            SILVER_AWARDS_RELEASE_DQ,
        )

        publish_release(
            SILVER_RELEASE,
            stage="silver",
            inputs=[BRONZE_RELEASE, RAW_JSONL],
            artifacts=[SILVER_TENDERS, SILVER_AWARDS],
            checks=[SILVER_TENDERS_RELEASE_DQ, SILVER_AWARDS_RELEASE_DQ],
            metadata={"tenders": len(tdf), "awards": len(adf)},
            expected_input_manifest_sha256={
                BRONZE_RELEASE: bronze_release.manifest_sha256,
            },
        )

        return {
            "tenders": len(tdf),
            "awards": len(adf),
            "tenders_dq_passed": tres.passed,
            "awards_dq_passed": ares.passed,
        }
    finally:
        unbind("stage")
