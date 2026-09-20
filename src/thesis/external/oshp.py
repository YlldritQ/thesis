"""OSHP evidence-status audit.

The bundled ``oshp_blacklist.json`` is useful source material, but it is not a
validation label for this project's tender-level screening indicators.  Its
rows contain only an operator name and a contracting-authority name.  They do
not identify an outcome, decision/case, date, tender/OCID, or supplier business
identifier.  Expanding an operator-name match to every tender that supplier
ever won would therefore invent outcome-to-tender links that the source does
not provide.

``validate`` is retained as a backwards-compatible command entry point.  It
now writes an explicit withdrawal/status artifact and performs no scoring or
supplier-to-tender expansion.  A future external validation may be added only
from records with traceable outcomes linked to exact procurements.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

from ..io.writers import write_json
from ..jsonutil import loads_json
from ..lineage import file_sha256
from ..paths import DATA

OSHP_SNAPSHOT = DATA / "external" / "oshp_blacklist.json"
OSHP_VALIDATION = DATA / "external" / "oshp_validation.json"

# Legal-form / business-type tokens retained for descriptive source audits.
# Canonicalisation must not be used to infer a tender-level outcome.
_LEGAL_TOKENS = [
    "sh.p.k",
    "shpk",
    "sh p k",
    "sh.a",
    "sha",
    "l.l.c",
    "llc",
    "b.i",
    "bi",
    "n.t.p",
    "ntp",
    "n.t.sh",
    "ntsh",
    "n.n.p",
    "nnp",
    "o.p",
    "op",
    "gmbh",
    "d.d",
    "dd",
    "dega ne kosove",
    "dega në kosovë",
    "company",
    "group",
    "sh.p.k.",
    "sh.a.",
]


def canonical_name(name: str) -> str:
    """Canonicalise a company name for descriptive source-quality checks."""
    if not isinstance(name, str):
        return ""
    value = unicodedata.normalize("NFKD", name)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()
    value = re.sub(r"[^a-z0-9& ]+", " ", value)
    for token in sorted(_LEGAL_TOKENS, key=len, reverse=True):
        value = re.sub(rf"\b{re.escape(token)}\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_blacklist() -> pd.DataFrame:
    """Load the cached source for inspection without creating outcome labels."""
    data = loads_json(OSHP_SNAPSHOT.read_text())
    frame = pd.DataFrame(data["rows"])
    frame["operator_canonical"] = frame["operator"].map(canonical_name)
    return frame[frame["operator_canonical"].str.len() >= 3]


def validate(write: bool = True) -> dict[str, Any]:
    """Return the evidence withdrawal status; do not compute validation lift."""
    source = loads_json(OSHP_SNAPSHOT.read_text())
    rows = source.get("rows", [])
    observed_fields = sorted({field for row in rows for field in row})

    result: dict[str, Any] = {
        "status": "withdrawn",
        "usable_as_external_validation": False,
        "source": source.get("source", "OSHP cached source snapshot"),
        "url": source.get("url"),
        "cached_retrieved": source.get("retrieved"),
        "source_sha256": file_sha256(OSHP_SNAPSHOT),
        "source_rows": len(rows),
        "observed_row_fields": observed_fields,
        "reason": (
            "The cached rows contain operator and authority names only. They do "
            "not provide an adjudicated outcome or an exact link to a tender, so "
            "supplier-name matches cannot be interpreted as tender-level labels."
        ),
        "prohibited_inference": (
            "Do not label every historical tender won by a name-matched operator "
            "as adjudicated, disqualified, risky, or externally validated."
        ),
        "minimum_future_evidence": [
            "explicit decision outcome",
            "decision or case identifier",
            "decision date",
            "exact tender/procurement identifier",
            "auditable operator identifier or reviewed entity match",
        ],
        "computed_metrics": [],
    }
    if write:
        write_json(result, OSHP_VALIDATION)
    return result
