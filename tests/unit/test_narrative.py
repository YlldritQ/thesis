"""Teste për shtresën narrative (shpjegimet qytetare në shqip)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly import RULES
from thesis.narrative import (
    FLAG_NARRATIVE,
    METRIC_HELP,
    contract_severity,
    explain_flags,
    plain_summary,
    why_flagged_headline,
)


def test_every_rule_has_a_narrative():
    """Çdo kod rregulli duhet të ketë shpjegim qytetar."""
    rule_codes = {r.code for r in RULES}
    narrative_codes = set(FLAG_NARRATIVE)
    missing = rule_codes - narrative_codes
    assert not missing, f"rregulla pa narrativë: {missing}"


def test_severity_bands_ordered_bare_score():
    # prapambetje: kur kalohet vetëm një numër
    assert contract_severity(0.9)["emoji"] == "🔴"
    assert contract_severity(0.6)["emoji"] == "🟠"
    assert contract_severity(0.4)["emoji"] == "🟡"
    assert contract_severity(0.1)["emoji"] == "🟢"


def test_severity_handles_none_and_nan():
    import math

    assert contract_severity(None)["score"] == 0.0
    assert contract_severity(math.nan)["score"] == 0.0


def test_severity_explainable_first_high_ensemble_no_flags_is_blue():
    """Rasti N25: ensemble i lartë POR pa flamuj → blu 'i pazakontë pa
    arsye', JO i kuq."""
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row["ensemble_score"] = 0.86
    sev = contract_severity(row)
    assert sev["emoji"] == "🔵"
    assert "pazakont" in sev["label"].lower()


def test_severity_red_requires_real_flags():
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row.update({"SINGLE_BIDDER_OPEN": True, "HIGH_VALUE_SINGLE": True, "ensemble_score": 0.9})
    sev = contract_severity(row)
    assert sev["emoji"] == "🔴"


def test_severity_one_medium_flag_is_orange():
    # WINNER_TAKES_ALL_LARGE ka ashpërsi 2
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row.update({"WINNER_TAKES_ALL_LARGE": True, "ensemble_score": 0.3})
    sev = contract_severity(row)
    assert sev["emoji"] == "🟠"


def test_severity_only_minor_flag_is_yellow_not_red():
    """Rasti N25 pas rregullimit: vetëm LOT_VALUE_MISMATCH (minor) +
    ensemble i lartë → 🟡, JO 🔴."""
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row.update({"LOT_VALUE_MISMATCH": True, "ensemble_score": 0.86})
    sev = contract_severity(row)
    assert sev["emoji"] == "🟡"


def test_one_standard_open_signal_is_orange_not_red():
    # Kuqja kërkon kombinim sinjalesh; një sinjal i vetëm nuk mjafton.
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row.update({"SINGLE_BIDDER_OPEN": True, "ensemble_score": 0.3})
    sev = contract_severity(row)
    assert sev["emoji"] == "🟠"


def test_single_bidder_open_supersedes_generic():
    """Kur SINGLE_BIDDER_OPEN është aktiv, karta e përgjithshme SINGLE_BIDDER
    nuk shfaqet dy herë."""
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row.update({"SINGLE_BIDDER": True, "SINGLE_BIDDER_OPEN": True})
    codes = [f["code"] for f in explain_flags(row)]
    assert "SINGLE_BIDDER_OPEN" in codes
    assert "SINGLE_BIDDER" not in codes


def test_minimum_single_bidder_alone_is_light():
    """Ofertues i vetëm pa variantin 'open' → sinjal i lehtë (blerje e vogël)."""
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    row.update({"SINGLE_BIDDER": True, "ensemble_score": 0.2})
    sev = contract_severity(row)
    assert sev["emoji"] == "🟡"


def test_explain_flags_sorted_by_severity():
    row = {"SINGLE_BIDDER": True, "LOT_VALUE_MISMATCH": True}
    flags = explain_flags(row)
    assert len(flags) == 2
    # Renditja mbetet stabile kur të dy sinjalet janë diagnostike/kontekstuale.
    assert flags[0]["code"] == "SINGLE_BIDDER"
    assert flags[0]["severity"] >= flags[1]["severity"]


def test_explain_flags_empty_when_none_triggered():
    row = dict.fromkeys(FLAG_NARRATIVE, False)
    assert explain_flags(row) == []


def test_plain_summary_mentions_entity_and_flags():
    row = {
        "procuring_entity_name": "KOMUNA E TESTIT",
        "title": "Furnizim me pajisje",
        "estimated_value_eur": 100_000.0,
        "total_awarded_eur": 120_000.0,
        "num_bidders": 1,
        "SINGLE_BIDDER": True,
        "RATIO_ABOVE_ESTIMATE": True,
    }
    s = plain_summary(row)
    assert "KOMUNA E TESTIT" in s
    assert "1 kompani" in s
    assert "tregues" in s.lower()


def test_plain_summary_zero_bidders():
    row = {"procuring_entity_name": "X", "title": "y", "num_bidders": 0, "ZERO_BIDDER": True}
    s = plain_summary(row)
    assert "asnjë ofertues" in s.lower()


def test_plain_summary_missing_bidder_publication_is_not_zero():
    row = {"procuring_entity_name": "X", "title": "y", "num_bidders": pd.NA}
    summary = plain_summary(row).lower()
    assert "nuk publikon numrin e ofertuesve" in summary
    assert "asnjë ofertues" not in summary


def test_plain_summary_unawarded_is_not_a_zero_euro_award():
    row = {
        "procuring_entity_name": "X",
        "title": "y",
        "estimated_value_eur": 25_000,
        "total_awarded_eur": 0.0,
        "was_awarded": 0,
        "n_awards": 0,
        "num_bidders": 2,
    }
    summary = plain_summary(row)
    assert "nuk ka vendim dhënieje të regjistruar" in summary.lower()
    assert "0 €" not in summary


def test_award_language_does_not_claim_signed_executed_or_paid_contract():
    help_text = METRIC_HELP["total_awarded_eur"].lower()
    assert "vendim dhënieje" in help_text
    for status in ("nënshkruar", "ekzekutuar", "paguar"):
        assert status in help_text

    summary = plain_summary(
        {
            "procuring_entity_name": "X",
            "title": "y",
            "estimated_value_eur": 25_000,
            "total_awarded_eur": 20_000,
            "was_awarded": 1,
            "n_awards": 1,
            "num_bidders": 2,
        }
    ).lower()
    assert "vlera e dhënieve të regjistruara" in summary
    assert "u kontraktua" not in summary


def test_why_flagged_headline_returns_detail():
    row = {"SINGLE_BIDDER": True}
    h = why_flagged_headline(row)
    assert "1 kompani" in h


def test_why_flagged_headline_no_flags():
    row = {"ensemble_score": 0.2}
    h = why_flagged_headline(row)
    assert "shenjua" in h.lower() or "rregull" in h.lower()


def test_metric_help_covers_key_columns():
    for key in [
        "estimated_value_eur",
        "awarded_value_ratio",
        "num_bidders",
        "ensemble_score",
        "rule_score",
    ]:
        assert key in METRIC_HELP
        assert len(METRIC_HELP[key]) > 20  # shpjegim i mirëfilltë, jo bosh
