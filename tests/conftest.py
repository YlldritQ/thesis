"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import json

# Make sure src/ is importable regardless of how pytest is invoked.
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _ts(s: str) -> str:
    return s


@pytest.fixture
def synthetic_ocds_records() -> list[dict]:
    """Eight synthetic OCDS-shaped records covering the main code paths.

    * 1 plain awarded tender (open, multiple bidders)
    * 1 single-bidder open tender
    * 1 zero-bidder cancelled tender
    * 1 minimum-method tender (end_before_start by design)
    * 1 multi-lot tender with mismatched sums
    * 1 framework agreement with multiple awards / one supplier dominant
    * 1 awarded > estimated tender
    * 1 ratio < 50 % tender
    """
    base = {
        "ocid": "ocds-uhzcmx-test-001",
        "id": "ocds-uhzcmx-test-001-1",
        "date": "2024-06-01T10:00:00+00:00",
        "tag": ["compiled"],
        "initiationType": "tender",
        "tender": {
            "id": "test-001",
            "uID": "uid-001",
            "title": "Plain awarded tender",
            "description": "",
            "status": "active",
            "mainProcurementCategory": "goods",
            "procurementMethod": "open",
            "procurementMethodDetails": "otvoreni postupak",
            "awardCriteria": "priceOnly",
            "awardCriteriaDetails": "lowest price",
            "submissionMethodDetails": "x",
            "value": {"amount": 100_000.0, "currency": "EUR"},
            "minValue": {"currency": "EUR"},
            "tenderPeriod": {
                "startDate": "2024-05-01T00:00:00+00:00",
                "endDate": "2024-05-31T12:00:00+00:00",
                "durationInDays": 30,
            },
            "procuringEntity": {
                "id": "pe-001",
                "party": {
                    "id": "pe-001",
                    "uID": "u-pe-001",
                    "name": "ENTITY ALPHA",
                    "role": "procuringEntity",
                },
            },
            "lots": [
                {
                    "id": "lot-1",
                    "title": "main",
                    "value": {"valueAmount": 100_000.0, "valueCurrency": "EUR", "uID": "u-lot-1"},
                    "description": "main lot",
                }
            ],
            "documents": [
                {
                    "id": "d1",
                    "url": "x",
                    "format": "x",
                    "language": "sq",
                    "documentType": "tenderNotice",
                }
            ],
            "tenderers": [
                {"id": "p-001", "name": "Supplier One"},
                {"id": "p-002", "name": "Supplier Two"},
                {"id": "p-003", "name": "Supplier Three"},
            ],
        },
        "parties": [
            {"id": "p-001", "name": "Supplier One", "roles": ["tenderer"]},
            {"id": "p-002", "name": "Supplier Two", "roles": ["tenderer"]},
            {"id": "p-003", "name": "Supplier Three", "roles": ["tenderer", "supplier"]},
        ],
        "award": [
            {
                "id": "a-1",
                "uID": "u-a-1",
                "title": "award",
                "description": "",
                "lotTitle": "lot-1",
                "date": "2024-06-15T00:00:00+00:00",
                "tenderNumber": "test-001",
                "statusID": "active",
                "value": {"amount": 95_000.0, "currency": "EUR"},
                "suppliers": [
                    {
                        "id": "p-003",
                        "name": "Supplier Three",
                        "party": {
                            "id": "p-003",
                            "uID": "u-p-003",
                            "name": "Supplier Three",
                            "role": "Tenderer",
                            "identity": {
                                "identificationNumber": "12345",
                                "legalName": "Supplier Three SH.P.K.",
                                "orgSchema": "XK",
                                "url": "",
                            },
                        },
                    }
                ],
            }
        ],
    }

    records = [base]
    # Single-bidder open tender
    sb = json.loads(json.dumps(base))
    sb["ocid"] = "ocds-uhzcmx-test-002"
    sb["tender"]["id"] = "test-002"
    sb["tender"]["title"] = "Single-bidder open"
    sb["tender"]["tenderers"] = [{"id": "p-001", "name": "Supplier One"}]
    sb["parties"] = [
        {"id": "p-001", "name": "Supplier One", "roles": ["tenderer", "supplier"]},
    ]
    sb["award"][0]["suppliers"] = [
        {
            "id": "p-001",
            "name": "Supplier One",
            "party": {
                "id": "p-001",
                "uID": "u-p-001",
                "name": "Supplier One",
                "role": "Tenderer",
                "identity": {
                    "identificationNumber": "12345",
                    "legalName": "Supplier One SH.P.K.",
                    "orgSchema": "XK",
                    "url": "",
                },
            },
        }
    ]
    records.append(sb)

    # Zero-bidder cancelled tender
    zb = json.loads(json.dumps(base))
    zb["ocid"] = "ocds-uhzcmx-test-003"
    zb["tender"]["id"] = "test-003"
    zb["tender"]["title"] = "Cancelled / no bidders"
    zb["tender"]["tenderers"] = []
    zb["parties"] = []
    zb["award"] = []
    records.append(zb)

    # minimum-method, end_before_start
    mm = json.loads(json.dumps(base))
    mm["ocid"] = "ocds-uhzcmx-test-004"
    mm["tender"]["id"] = "test-004"
    mm["tender"]["title"] = "Minimum-method tender"
    mm["tender"]["procurementMethod"] = "minimum"
    mm["tender"]["tenderPeriod"]["startDate"] = "2024-06-15T00:00:00+00:00"
    mm["tender"]["tenderPeriod"]["endDate"] = "2024-06-10T12:00:00+00:00"
    mm["tender"]["tenderPeriod"]["durationInDays"] = -5
    records.append(mm)

    # Multi-lot mismatched
    ml = json.loads(json.dumps(base))
    ml["ocid"] = "ocds-uhzcmx-test-005"
    ml["tender"]["id"] = "test-005"
    ml["tender"]["title"] = "Multi-lot mismatch"
    ml["tender"]["lots"] = [
        {
            "id": "lot-1",
            "title": "a",
            "value": {"valueAmount": 60_000.0, "valueCurrency": "EUR", "uID": "u-l1"},
            "description": "a",
        },
        {
            "id": "lot-2",
            "title": "b",
            "value": {"valueAmount": 30_000.0, "valueCurrency": "EUR", "uID": "u-l2"},
            "description": "b",
        },
    ]
    records.append(ml)

    # Awarded > estimated
    ratio_high = json.loads(json.dumps(base))
    ratio_high["ocid"] = "ocds-uhzcmx-test-006"
    ratio_high["tender"]["id"] = "test-006"
    ratio_high["tender"]["title"] = "Awarded > estimated"
    ratio_high["award"][0]["value"]["amount"] = 150_000.0
    records.append(ratio_high)

    # Ratio < 50 %
    ratio_low = json.loads(json.dumps(base))
    ratio_low["ocid"] = "ocds-uhzcmx-test-007"
    ratio_low["tender"]["id"] = "test-007"
    ratio_low["tender"]["title"] = "Aggressive low bid"
    ratio_low["award"][0]["value"]["amount"] = 30_000.0
    records.append(ratio_low)

    # Framework agreement with multiple awards
    fw = json.loads(json.dumps(base))
    fw["ocid"] = "ocds-uhzcmx-test-008"
    fw["tender"]["id"] = "test-008"
    fw["tender"]["title"] = "Framework agreement"
    fw["award"] = [
        {
            **fw["award"][0],
            "id": f"a-{i}",
            "uID": f"u-a-{i}",
            "value": {"amount": 50_000.0 + i * 1_000, "currency": "EUR"},
        }
        for i in range(5)
    ]
    records.append(fw)

    return records


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Redirect THESIS_DATA_DIR to a fresh tmp_path and reset settings.

    Yields the path; tests can write fixtures into it.
    """
    monkeypatch.setenv("THESIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("THESIS_FAIL_FAST_ON_DQ", "false")

    # Reset cached settings + paths
    from thesis import config

    config.reset_settings_for_tests()

    # Force re-import of paths to pick up the new data_dir
    import importlib

    from thesis import paths as paths_module

    importlib.reload(paths_module)

    return tmp_path
