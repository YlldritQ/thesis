"""Pydantic data contracts for the silver and gold layers.

Used both as documentation *and* as run-time validators. The pipeline calls
:func:`validate_dataframe` on its output before persisting Parquet.

Two-tier validation strategy:
* **Pydantic** for row-level type validation (this module).
* **Pandera** for DataFrame-level invariants and per-column constraints
  (see :mod:`thesis.domain.schemas`).

When either tier finds a violation we surface it as a DQ failure rather
than silently dropping rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TenderRecord(BaseModel):
    """One row of ``silver.tenders``."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    ocid: str = Field(..., min_length=1)
    release_id: Optional[str] = None
    release_date: Optional[datetime] = None
    tender_id: Optional[str] = None
    procedure_code: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    method: Optional[str] = None
    method_details: Optional[str] = None
    award_criteria: Optional[str] = None
    estimated_value_eur: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_reported_days: Optional[float] = None
    procuring_entity_id: Optional[str] = None
    procuring_entity_uid: Optional[str] = None
    procuring_entity_name: Optional[str] = None
    num_lots: int = Field(ge=0)
    lots_value_sum: Optional[float] = None
    num_bidders: Optional[int] = Field(default=None, ge=0)
    bidder_data_observed: bool
    num_suppliers_in_parties: int = Field(ge=0)
    num_parties: int = Field(ge=0)
    num_awards: int = Field(ge=0)
    duration_computed_days: Optional[float] = None
    end_before_start: Optional[bool] = None


class AwardRecord(BaseModel):
    """One row of ``silver.awards``."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    ocid: str = Field(..., min_length=1)
    tender_id: Optional[str] = None
    award_id: Optional[str] = None
    award_uid: Optional[str] = None
    award_title: Optional[str] = None
    award_description: Optional[str] = None
    award_lot_title: Optional[str] = None
    award_lot_match_status: Literal[
        "exact_unique", "exact_ambiguous", "no_exact_match", "missing_title"
    ]
    award_date: Optional[datetime] = None
    award_status_id: Optional[str] = None
    awarded_value_eur: Optional[float] = Field(default=None, ge=0)
    awarded_currency: Optional[str] = None
    supplier_party_id: Optional[str] = None
    supplier_uid: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_legal_name: Optional[str] = None
    supplier_business_id: Optional[str] = None
    supplier_business_id_raw: Optional[str] = None
    supplier_org_schema: Optional[str] = None
    category: Optional[str] = None
    method: Optional[str] = None
    estimated_value_eur: Optional[float] = Field(default=None, ge=0)
    procuring_entity_id: Optional[str] = None
    procuring_entity_name: Optional[str] = None
    num_bidders: Optional[int] = Field(default=None, ge=0)
    bidder_data_observed: bool
    num_awards: int = Field(ge=0)
    value_ratio: Optional[float] = None


def validate_dataframe(
    df: pd.DataFrame,
    model: type[BaseModel],
    sample: int | None = None,
    raise_on_error: bool = False,
) -> tuple[int, list[str]]:
    """Validate rows of *df* against *model* (all rows by default).

    Args:
        df: DataFrame to validate.
        model: Pydantic model class.
        sample: How many rows to check (None = all).
        raise_on_error: If True, the first error raises ValueError.

    Returns:
        ``(rows_checked, error_messages)``. Empty error list = pass.
    """
    sub = df.head(sample) if sample is not None and len(df) > sample else df
    errors: list[str] = []
    for i, row in enumerate(sub.to_dict("records")):
        clean = {
            k: (None if pd.isna(v) else v)
            for k, v in row.items()
            if not (isinstance(v, list) and len(v) == 0)
        }
        try:
            model(**clean)
        except ValidationError as e:
            msg = f"row {i}: {e.errors()[0]}"
            errors.append(msg)
            if raise_on_error:
                raise ValueError(msg) from e
            if len(errors) >= 10:
                break
    return len(sub), errors
