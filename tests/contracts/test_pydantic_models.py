"""Contract tests — Pydantic row-validation."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.domain.contracts import (
    AwardRecord,
    TenderRecord,
    validate_dataframe,
)


def test_tender_record_accepts_minimal():
    t = TenderRecord(
        ocid="ocds-test-001",
        num_lots=1,
        num_bidders=2,
        bidder_data_observed=True,
        num_suppliers_in_parties=1,
        num_parties=3,
        num_awards=1,
    )
    assert t.ocid == "ocds-test-001"


def test_tender_record_rejects_negative_value():
    with pytest.raises(Exception):
        TenderRecord(
            ocid="x",
            num_lots=0,
            num_bidders=0,
            bidder_data_observed=True,
            num_suppliers_in_parties=0,
            num_parties=0,
            num_awards=0,
            estimated_value_eur=-10.0,
        )


def test_tender_record_rejects_negative_count():
    with pytest.raises(Exception):
        TenderRecord(
            ocid="x",
            num_lots=-1,
            num_bidders=0,
            bidder_data_observed=True,
            num_suppliers_in_parties=0,
            num_parties=0,
            num_awards=0,
        )


def test_validate_dataframe_passes_clean_input():
    df = pd.DataFrame(
        [
            {
                "ocid": f"ocid-{i}",
                "num_lots": 1,
                "num_bidders": 2,
                "bidder_data_observed": True,
                "num_suppliers_in_parties": 1,
                "num_parties": 3,
                "num_awards": 1,
            }
            for i in range(5)
        ]
    )
    rows, errs = validate_dataframe(df, TenderRecord, sample=5)
    assert rows == 5
    assert errs == []


def test_validate_dataframe_collects_errors():
    df = pd.DataFrame(
        [
            {
                "ocid": "",  # empty -> validation error
                "num_lots": 0,
                "num_bidders": 0,
                "bidder_data_observed": True,
                "num_suppliers_in_parties": 0,
                "num_parties": 0,
                "num_awards": 0,
            }
        ]
    )
    rows, errs = validate_dataframe(df, TenderRecord)
    assert rows == 1
    assert len(errs) >= 1


def test_award_record_accepts_minimum_enriched_row():
    a = AwardRecord(
        ocid="x",
        awarded_value_eur=10_000.0,
        award_lot_match_status="missing_title",
        num_awards=1,
        bidder_data_observed=False,
    )
    assert a.awarded_value_eur == 10_000.0


def test_validate_dataframe_checks_all_rows_by_default():
    rows = [
        {
            "ocid": f"ocid-{i}",
            "num_lots": 1,
            "num_bidders": 2,
            "bidder_data_observed": True,
            "num_suppliers_in_parties": 1,
            "num_parties": 3,
            "num_awards": 1,
        }
        for i in range(205)
    ]
    rows[-1]["ocid"] = ""

    checked, errors = validate_dataframe(pd.DataFrame(rows), TenderRecord)

    assert checked == 205
    assert errors and errors[0].startswith("row 204:")


def test_row_contract_rejects_undeclared_columns():
    with pytest.raises(Exception):
        TenderRecord(
            ocid="x",
            num_lots=0,
            num_bidders=None,
            bidder_data_observed=False,
            num_suppliers_in_parties=0,
            num_parties=0,
            num_awards=0,
            silently_unvalidated_field="bad",
        )
