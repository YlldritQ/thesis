"""Teste regresioni për dy bug-e që korruptonin flamujt:

1. Award-e të dubluara në burim → dyfishim i `total_awarded_eur` dhe raporti
   fals mbi parashikim.
2. Konsorciume ("Grup i Operatorëve Ekonomik") me `supplier_business_id` bosh
   → bashkim në një grup → winner_top_share fals 100 %.

Rasti real: ocds-uhzcmx-205-23-21-5-1-1 (zgjerimi i rrugës N25) — 5 lote,
5 konsorciume, çdo award i listuar dy herë në burim.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.domain.features import (
    per_tender_winner_concentration,
    supplier_key,
)
from thesis.pipeline.silver import _extract_awards, _extract_tender, dedup_award_list

# ------------------------------------------------------------ dedup award


def _award(
    name: str,
    amount: float,
    lot: str = "L1",
    aid=None,
    date: str = "2023-01-01",
    party_id: str | None = None,
    business_id: str | None = None,
) -> dict:
    return {
        "id": aid,
        "uID": None,
        "lotTitle": lot,
        "date": date,
        "value": {"amount": amount, "currency": "EUR"},
        "suppliers": [
            {
                "party": {
                    "id": party_id,
                    "name": name,
                    "identity": {"identificationNumber": business_id},
                }
            }
        ],
    }


def test_dedup_ignores_award_date_republication():
    """Rasti N25: i njëjti lot/fitues/vlerë i ripublikuar në një datë tjetër
    duhet të numërohet një herë, jo dy."""
    awards = [
        _award("A", 100.0, lot="Lot 0", date="2023-06-21"),
        _award("A", 100.0, lot="Lot 0", date="2023-07-06"),  # ripublikim
        _award("B", 200.0, lot="Lot 1", date="2023-06-21"),
        _award("B", 200.0, lot="Lot 1", date="2023-07-06"),  # ripublikim
    ]
    out = dedup_award_list(awards)
    assert len(out) == 2


def test_dedup_removes_exact_duplicates():
    awards = [
        _award("A", 100.0),
        _award("B", 200.0),
        _award("A", 100.0),  # dublikatë e A
        _award("B", 200.0),  # dublikatë e B
    ]
    out = dedup_award_list(awards)
    assert len(out) == 2
    names = {(a["suppliers"][0]["party"]["name"]) for a in out}
    assert names == {"A", "B"}


def test_dedup_keeps_distinct_lots_of_same_supplier():
    awards = [_award("A", 100.0, lot="L1"), _award("A", 100.0, lot="L2")]
    # lote të ndryshme → NUK janë dublikatë
    assert len(dedup_award_list(awards)) == 2


def test_dedup_ignores_row_guid_uid():
    """`uID`/`id` janë GUID rreshti që ndryshojnë në ripublikim — nuk duhet
    ta bëjnë award-in unik. I njëjti (lot, vlerë, fitues) → një award."""
    a1 = _award("A", 100.0, aid="x1")
    a2 = _award("A", 100.0, aid="x2")
    a1["uID"] = "guid-1"
    a2["uID"] = "guid-2"
    assert len(dedup_award_list([a1, a2])) == 1


def test_dedup_empty_list():
    assert dedup_award_list([]) == []


def test_dedup_keeps_blank_name_suppliers_with_distinct_source_party_ids():
    awards = [
        _award("", 100.0, party_id="party-a"),
        _award("", 100.0, party_id="party-b"),
    ]
    assert len(dedup_award_list(awards)) == 2


def test_dedup_treats_business_id_sentinel_as_missing_and_uses_party_id():
    first = _award("", 100.0, party_id="party-a", business_id="N/A")
    second = _award("", 100.0, party_id="party-b", business_id="N/A")
    assert len(dedup_award_list([first, second])) == 2


def test_missing_tenderer_publication_stays_nullable_not_zero():
    row = _extract_tender({"ocid": "x", "tender": {"id": "616-26-123-1"}})
    assert row["num_bidders"] is None
    assert row["bidder_data_observed"] is False
    assert row["procedure_code"] == "1"


def test_explicit_empty_tenderer_array_is_observed_zero():
    row = _extract_tender({"ocid": "x", "tender": {"id": "616-26-123-6", "tenderers": []}})
    assert row["num_bidders"] == 0
    assert row["bidder_data_observed"] is True
    assert row["procedure_code"] == "6"


def test_tenderer_party_roles_are_an_observed_fallback_count():
    row = _extract_tender(
        {
            "ocid": "x",
            "tender": {"id": "616-26-123-3"},
            "parties": [
                {"roles": ["tenderer"]},
                {"roles": ["buyer"]},
                {"roles": ["tenderer", "supplier"]},
            ],
        }
    )
    assert row["num_bidders"] == 2
    assert row["bidder_data_observed"] is True
    assert row["procedure_code"] == "3"


def test_award_extraction_retains_raw_business_id_and_normalizes_sentinel():
    record = {
        "ocid": "x",
        "tender": {"id": "616-26-123-1"},
        "award": [
            {
                "id": "a",
                "value": {"amount": 10, "currency": "EUR"},
                "suppliers": [
                    {
                        "party": {
                            "id": "party-a",
                            "name": "Supplier",
                            "identity": {"identificationNumber": "N/A"},
                        }
                    }
                ],
            }
        ],
    }
    row = _extract_awards(record)[0]
    assert row["supplier_business_id"] is None
    assert row["supplier_business_id_raw"] == "N/A"
    assert row["supplier_party_id"] == "party-a"
    assert row["award_lot_match_status"] == "missing_title"


@pytest.mark.parametrize(
    ("award_title", "tender_titles", "expected"),
    [
        ("Lot 1", ["Lot 1", "Lot 2"], "exact_unique"),
        ("Lot 1", ["Lot 1", "Lot 1"], "exact_ambiguous"),
        ("lot 1", ["Lot 1"], "no_exact_match"),
        (None, ["Lot 1"], "missing_title"),
    ],
)
def test_award_extraction_records_exact_lot_title_linkage(award_title, tender_titles, expected):
    record = {
        "ocid": "x",
        "tender": {
            "id": "616-26-123-1",
            "lots": [{"title": title} for title in tender_titles],
        },
        "award": [
            {
                "uID": "award-1",
                "lotTitle": award_title,
                "value": {"amount": 10, "currency": "EUR"},
                "suppliers": [{"party": {"id": "supplier-1"}}],
            }
        ],
    }

    row = _extract_awards(record)[0]

    assert row["award_lot_match_status"] == expected


# ------------------------------------------------------------ supplier key


def test_supplier_key_falls_back_to_name_for_empty_business_id():
    df = pd.DataFrame(
        {
            "supplier_business_id": ["", "", "12345"],
            "supplier_name": ["Konsorcium A", "Konsorcium B", "Firma C"],
        }
    )
    keys = supplier_key(df)
    # dy konsorciumet me id bosh marrin çelësa TË NDRYSHËM (nga emri)
    assert keys.iloc[0] != keys.iloc[1]
    assert keys.iloc[0].startswith("name::")
    # firma me id përdor id-në
    assert keys.iloc[2] == "12345"


def test_supplier_key_same_name_same_key():
    df = pd.DataFrame(
        {
            "supplier_business_id": ["", ""],
            "supplier_name": ["Konsorcium A", "konsorcium a  "],  # normalizim
        }
    )
    keys = supplier_key(df)
    assert keys.iloc[0] == keys.iloc[1]


def test_supplier_key_uses_source_party_only_when_business_id_and_name_are_missing():
    df = pd.DataFrame(
        {
            "supplier_business_id": ["N/A", "/"],
            "supplier_name": ["", ""],
            "supplier_party_id": ["party-a", "party-b"],
        }
    )
    assert supplier_key(df).tolist() == ["party::party-a", "party::party-b"]


# ------------------------------------------------------------ winner concentration


def test_five_distinct_consortiums_not_flagged_as_winner_takes_all():
    """Rasti N25: 5 konsorciume me id bosh, vlera të ndryshme →
    winner_top_share duhet të reflektojë pjesën reale (~27 %), jo 100 %."""
    vals = [9_254_811, 8_644_260, 8_447_478, 6_484_855, 1_443_784]
    names = [f"Grup i Operatorëve Ekonomik {i}" for i in range(5)]
    awards = pd.DataFrame(
        {
            "ocid": ["N25"] * 5,
            "supplier_business_id": [""] * 5,
            "supplier_name": names,
            "awarded_value_eur": vals,
        }
    )
    res = per_tender_winner_concentration(awards)
    top = res.set_index("ocid").loc["N25", "winner_top_share"]
    expected = max(vals) / sum(vals)
    assert abs(top - expected) < 1e-6
    assert top < 0.30  # larg pragut 0.95 → NUK aktivizohet flamuri


def test_implausible_estimate_not_flagged_as_overpricing():
    """Rasti €180→€178K (raport 988×): flamuri i mbiçmimit NUK duhet të
    aktivizohet; në vend të tij aktivizohet flamuri i cilësisë së të dhënave."""
    from thesis.anomaly.rules import apply_rules

    f = pd.DataFrame(
        {
            "is_single_bidder": [1, 0],
            "is_zero_bidder": [0, 0],
            "awarded_value_ratio": [988.0, 1.5],
            "days_to_first_award": [10, 10],
            "method": ["open", "open"],
            "category": ["goods", "goods"],
            "days_tender_open": [30, 30],
            "estimated_value_eur": [180, 50_000],
            "end_before_start": [0, 0],
            "lot_value_mismatch": [0, 0],
            "n_awards": [1, 1],
            "winner_top_share": [1.0, 1.0],
        }
    )
    out = apply_rules(f)
    # rekordi i prishur (988×)
    assert not out["RATIO_ABOVE_ESTIMATE"].iloc[0]
    assert out["IMPLAUSIBLE_ESTIMATE"].iloc[0]
    # mbiçmimi i besueshëm (1.5×) mbetet flamur i mbiçmimit, jo cilësie
    assert out["RATIO_ABOVE_ESTIMATE"].iloc[1]
    assert not out["IMPLAUSIBLE_ESTIMATE"].iloc[1]


def test_ratio_below_50_guards_against_zero_awarded():
    """Raport ≈ 0 (vlerë e kontraktuar që mungon) nuk duhet të llogaritet si
    'ofertë agresivisht e ulët'."""
    from thesis.anomaly.rules import apply_rules

    f = pd.DataFrame(
        {
            "is_single_bidder": [0],
            "is_zero_bidder": [0],
            "awarded_value_ratio": [0.001],  # praktikisht zero
            "days_to_first_award": [10],
            "method": ["open"],
            "category": ["goods"],
            "days_tender_open": [30],
            "estimated_value_eur": [50_000],
            "end_before_start": [0],
            "lot_value_mismatch": [0],
            "n_awards": [1],
            "winner_top_share": [1.0],
        }
    )
    out = apply_rules(f)
    assert not out["RATIO_BELOW_50"].iloc[0]


def test_single_real_winner_still_detected():
    """Kur një kompani me id reale merr gjithçka, flamuri duhet të mbetet."""
    awards = pd.DataFrame(
        {
            "ocid": ["T1", "T1"],
            "supplier_business_id": ["999", "999"],
            "supplier_name": ["Firma X", "Firma X"],
            "awarded_value_eur": [500_000, 500_000],
        }
    )
    res = per_tender_winner_concentration(awards)
    assert res.set_index("ocid").loc["T1", "winner_top_share"] == pytest.approx(1.0)
