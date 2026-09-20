"""Source-aware procurement procedure taxonomy.

The OCDS ``procurementMethod`` field is too coarse for legal or statistical
comparisons in this dataset: both ordinary open procedures and the low-value
price-quotation procedure are encoded as ``open``.  Rules and reports must use
``procurementMethodDetails`` as well.

The taxonomy is deliberately descriptive.  It does not infer urgency,
corrigenda, contract-value class, or a legal breach when those facts are not in
the publication extract.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

PRICE_QUOTATION = "price_quotation"
STANDARD_OPEN = "standard_open"
DESIGN_CONTEST = "design_contest"
MINIMUM_VALUE = "minimum_value"
NEGOTIATED_WITHOUT_NOTICE = "negotiated_without_notice"
NEGOTIATED_WITH_NOTICE = "negotiated_with_notice"
FRAMEWORK_MINI_TENDER = "framework_mini_tender"
RESTRICTED = "restricted"
SELECTIVE = "selective"
UNKNOWN = "unknown"

# KRPP encodes the procedure type as the final component of the published
# tender identifier. The consolidated Regulation No. 001/2022 as amended by
# Regulation No. 002/2024, Article 12.3, defines these values. The predecessor
# 2016 Rules and Operational Guidelines annex independently documents codes
# 1--7 for the historical part of this snapshot. The source code is more
# precise than the coarse OCDS ``method`` and avoids treating code-3 design
# contests as ordinary open/restricted tenders.
PROCEDURE_CODE_MAP = {
    "1": STANDARD_OPEN,
    "2": RESTRICTED,
    "3": DESIGN_CONTEST,
    "4": NEGOTIATED_WITH_NOTICE,
    "5": NEGOTIATED_WITHOUT_NOTICE,
    "6": PRICE_QUOTATION,
    "7": MINIMUM_VALUE,
    "8": FRAMEWORK_MINI_TENDER,
}


def normalise_procedure_text(value: object) -> str:
    """Return a stable ASCII/lower-case representation of source detail."""
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", text).strip()


def procedure_code_from_tender_id(tender_id: object) -> str | None:
    """Return the official terminal KRPP procedure code when available."""
    if not isinstance(tender_id, str):
        return None
    match = re.search(r"-([1-8])\s*$", tender_id)
    return match.group(1) if match else None


def classify_procedure(
    method: object,
    method_details: object,
    tender_id: object = None,
) -> str:
    """Map one OCDS method/detail pair to a source-aware subtype."""
    meth = normalise_procedure_text(method)
    detail = normalise_procedure_text(method_details)

    procedure_code = procedure_code_from_tender_id(tender_id)
    if procedure_code is not None:
        return PROCEDURE_CODE_MAP[procedure_code]

    if "bagatelne nabave" in detail and "javna objava" in detail:
        return PRICE_QUOTATION
    if "natjecaj" in detail:
        return DESIGN_CONTEST
    if detail == "otvoreni postupak":
        return STANDARD_OPEN
    if "minimalne vrednosti" in detail:
        return MINIMUM_VALUE
    if "mini tender" in detail:
        return FRAMEWORK_MINI_TENDER
    if "bez prethodne objave" in detail:
        return NEGOTIATED_WITHOUT_NOTICE
    if "s prethodnom objavom" in detail:
        return NEGOTIATED_WITH_NOTICE
    if "ograniceni" in detail:
        return RESTRICTED
    if meth == "selective":
        return SELECTIVE
    # A missing/novel detail must not be promoted to ordinary open merely
    # because the coarse OCDS value says ``open``.
    return UNKNOWN


def classify_procedure_series(df: pd.DataFrame) -> pd.Series:
    """Vector-friendly taxonomy for a tender DataFrame."""
    method = df.get("method", pd.Series(index=df.index, dtype=object))
    details = df.get("method_details", pd.Series(index=df.index, dtype=object))
    tender_ids = df.get("tender_id", pd.Series(index=df.index, dtype=object))
    return pd.Series(
        (
            classify_procedure(m, d, tender_id)
            for m, d, tender_id in zip(method, details, tender_ids)
        ),
        index=df.index,
        name="procedure_subtype",
        dtype="object",
    )
