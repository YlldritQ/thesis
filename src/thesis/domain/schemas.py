"""Pandera DataFrame-level schemas.

Pandera complements the row-by-row Pydantic models with **DataFrame-wide**
checks: column presence, dtype enforcement, nullability, value ranges,
custom predicates. Pipeline stages call :func:`validate_silver_tenders`,
``validate_silver_awards``, and ``validate_gold_tender_summary`` before
persisting.
"""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

# =====================================================================
#  Silver
# =====================================================================

silver_tenders_schema = pa.DataFrameSchema(
    {
        "ocid": pa.Column(str, nullable=False, unique=True),
        "release_id": pa.Column(str, nullable=True),
        "release_date": pa.Column(pa.DateTime, nullable=True),
        "tender_id": pa.Column(str, nullable=True, unique=True),
        "procedure_code": pa.Column(
            str,
            nullable=True,
            checks=pa.Check.isin([str(value) for value in range(1, 9)]),
        ),
        "title": pa.Column(str, nullable=True),
        "status": pa.Column(str, nullable=True),
        "category": pa.Column(
            str, nullable=True, checks=pa.Check.isin(["goods", "services", "works"])
        ),
        "method": pa.Column(str, nullable=True),
        "method_details": pa.Column(str, nullable=True),
        "award_criteria": pa.Column(str, nullable=True),
        "estimated_value_eur": pa.Column(float, nullable=True, checks=pa.Check.ge(0)),
        "currency": pa.Column(str, nullable=True),
        "start_date": pa.Column(pa.DateTime, nullable=True),
        "end_date": pa.Column(pa.DateTime, nullable=True),
        "duration_reported_days": pa.Column(float, nullable=True),
        "procuring_entity_id": pa.Column(str, nullable=True),
        "procuring_entity_uid": pa.Column(str, nullable=True),
        "procuring_entity_name": pa.Column(str, nullable=True),
        "num_lots": pa.Column(int, checks=pa.Check.ge(0)),
        "lots_value_sum": pa.Column(float, nullable=True),
        "num_bidders": pa.Column(pd.Int64Dtype(), nullable=True, checks=pa.Check.ge(0)),
        "bidder_data_observed": pa.Column(bool, nullable=False),
        "num_suppliers_in_parties": pa.Column(int, checks=pa.Check.ge(0)),
        "num_parties": pa.Column(int, checks=pa.Check.ge(0)),
        "num_awards": pa.Column(int, checks=pa.Check.ge(0)),
        "duration_computed_days": pa.Column(float, nullable=True),
        "end_before_start": pa.Column(bool, nullable=True),
    },
    coerce=True,
    checks=[
        pa.Check(
            lambda df: (
                (df["bidder_data_observed"] & df["num_bidders"].notna())
                | (~df["bidder_data_observed"] & df["num_bidders"].isna())
            ).all(),
            name="bidder_observation_matches_nullable_count",
        )
    ],
    strict=False,
)

silver_awards_schema = pa.DataFrameSchema(
    {
        "ocid": pa.Column(str, nullable=False),
        "tender_id": pa.Column(str, nullable=True),
        "award_id": pa.Column(str, nullable=True),
        "award_lot_match_status": pa.Column(
            str,
            nullable=False,
            checks=pa.Check.isin(
                ["exact_unique", "exact_ambiguous", "no_exact_match", "missing_title"]
            ),
        ),
        "awarded_value_eur": pa.Column(float, nullable=True, checks=pa.Check.ge(0)),
        "supplier_party_id": pa.Column(str, nullable=True),
        "supplier_business_id": pa.Column(str, nullable=True),
        "supplier_business_id_raw": pa.Column(str, nullable=True),
        "supplier_name": pa.Column(str, nullable=True),
        "num_bidders": pa.Column(pd.Int64Dtype(), nullable=True, checks=pa.Check.ge(0)),
        "bidder_data_observed": pa.Column(bool, nullable=False),
        "num_awards": pa.Column(int, checks=pa.Check.ge(0)),
    },
    checks=[
        pa.Check(
            lambda df: (
                (df["bidder_data_observed"] & df["num_bidders"].notna())
                | (~df["bidder_data_observed"] & df["num_bidders"].isna())
            ).all(),
            name="bidder_observation_matches_nullable_count",
        )
    ],
    coerce=True,
    strict=False,
)


def validate_silver_tenders(df: pd.DataFrame) -> pd.DataFrame:
    return silver_tenders_schema.validate(df, lazy=True)


def validate_silver_awards(df: pd.DataFrame) -> pd.DataFrame:
    return silver_awards_schema.validate(df, lazy=True)
