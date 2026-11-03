"""Smoke-test every Streamlit page renders without raising an exception.

Uses streamlit.testing.v1.AppTest which executes the page script in-process.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "streamlit_app"))

PAGES = sorted(
    [
        str(p.relative_to(ROOT))
        for p in [
            ROOT / "streamlit_app" / "Home.py",
            *(ROOT / "streamlit_app" / "pages").glob("*.py"),
        ]
    ]
)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page: str) -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / page), default_timeout=120)
    at.run()
    assert not at.exception, f"{page} raised: {at.exception}"


def test_explore_handles_literal_search_and_no_matches() -> None:
    """Punctuation in user search must not be interpreted as a regular expression."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "streamlit_app/pages/2_Explore.py"), default_timeout=120)
    at.run()
    assert not at.exception
    at.text_input[0].input("[").run()
    assert not at.exception
    at.text_input[0].input("__no_such_tender_275841963__").run()
    assert not at.exception
    assert any("Nuk u gjet asnjë tender" in notice.value for notice in at.info)
    assert next(box for box in at.selectbox if box.label == "Zgjidh nga rezultatet").disabled


def test_explore_tender_selector_changes_visible_details() -> None:
    """A visitor can open a different tender without copying an OCID by hand."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "streamlit_app/pages/2_Explore.py"), default_timeout=120)
    at.run()
    assert not at.exception
    chooser = next(box for box in at.selectbox if box.label == "Zgjidh nga rezultatet")
    previous = chooser.value
    displayed_choice = chooser.options[1]
    # AppTest select_index uses display strings; the widget's actual value is an OCID.
    chooser.set_value(displayed_choice.rsplit(" · ", 1)[-1]).run()
    assert not at.exception
    assert (
        next(box for box in at.selectbox if box.label == "Zgjidh nga rezultatet").value != previous
    )
    assert any(heading.value in displayed_choice for heading in at.subheader)


def test_explore_opens_explanations_for_the_selected_tender() -> None:
    """Opening explanations must preserve the searched tender, not show the top-ranked one."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "streamlit_app/Home.py"), default_timeout=120)
    at.switch_page("pages/2_Explore.py").run()
    assert not at.exception
    chooser = next(box for box in at.selectbox if box.label == "Zgjidh nga rezultatet")
    displayed_choice = chooser.options[1]
    selected_ocid = displayed_choice.rsplit(" · ", 1)[-1]
    chooser.set_value(selected_ocid).run()
    next(
        button for button in at.button if button.label == "Shpjego pikët e këtij tenderi →"
    ).click().run()
    assert not at.exception
    assert at.text_input(key="anomaly_manual_ocid").value == selected_ocid
    assert any(heading.value in displayed_choice for heading in at.subheader)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_shows_caveat(page: str) -> None:
    """Governance promise (review M-24/AM-01): the 'anomaly ≠ fraud' caveat
    must appear on EVERY page, including the ones naming real entities."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / page), default_timeout=120)
    at.run()
    import contextlib

    blobs = []
    for attr in ("markdown", "caption", "warning", "info"):
        with contextlib.suppress(Exception):
            blobs += [getattr(e, "value", "") or getattr(e, "body", "") for e in getattr(at, attr)]
    text = " ".join(str(b) for b in blobs).lower()
    assert "anomalia ≠ mashtrim" in text, f"{page} is missing the anomaly-is-not-fraud caveat"


def test_validation_page_omits_invalid_external_claims() -> None:
    """The dashboard must not present the removed supplier-history join as validation."""
    source = (ROOT / "streamlit_app" / "pages" / "6_Validation.py").read_text().lower()
    assert "oshp" not in source
    assert "diskualif" not in source
    assert "etiketa të pavarura" in source


def test_dimension_filters_keep_missing_values_explicit_and_selected() -> None:
    """Null and blank metadata must be a visible filter bucket, not dropped."""
    import pandas as pd
    from _bootstrap import (
        UNKNOWN_FILTER_OPTION,
        _dimension_options,
        _selected_filter_mask,
    )

    values = pd.Series(["goods", None, "", "services"])
    options = _dimension_options(values)
    assert options[-1] == UNKNOWN_FILTER_OPTION
    assert _selected_filter_mask(values, options).all()
    assert _selected_filter_mask(values, [UNKNOWN_FILTER_OPTION]).tolist() == [
        False,
        True,
        True,
        False,
    ]


def test_streamlit_cache_token_validates_current_release_before_cache(monkeypatch) -> None:
    """A prior cached frame must not conceal a changed bound artifact."""
    import _bootstrap

    calls: list[tuple[Path, bool]] = []

    class Validated:
        manifest_sha256 = "a" * 64

    def fake_contract(stage: str):
        return type("Contract", (), {"manifest": manifest})()

    def fake_validate(stage: str, *, require_current_provenance: bool):
        calls.append((Path(stage), require_current_provenance))
        return Validated()

    manifest = Path("generation.release.json")
    monkeypatch.setattr(_bootstrap, "canonical_release_contract", fake_contract)
    monkeypatch.setattr(_bootstrap, "validate_canonical_release", fake_validate)
    assert _bootstrap._release_token(manifest) == "a" * 64
    assert calls == [(Path("bronze"), True)]


def test_methodology_uses_canonical_dq_artifacts() -> None:
    source = (ROOT / "streamlit_app" / "pages" / "5_Methodology.py").read_text()
    for filename in (
        "silver_tenders.dq.md",
        "silver_awards.dq.md",
        "gold_tender_features.dq.md",
        "gold_tender_summary.dq.md",
    ):
        assert filename in source
    assert 'paths.DQ / "summary.md"' not in source
    assert 'paths.DQ / "summary_silver.md"' not in source


def test_ui_does_not_overstate_proxy_or_supplier_identity_evidence() -> None:
    benchmark = (ROOT / "streamlit_app" / "pages" / "7_Krahasimi_i_Modeleve.py").read_text().lower()
    entities = (ROOT / "streamlit_app" / "pages" / "4_Entities.py").read_text().lower()
    assert "me ndërtim" not in benchmark
    assert "identitet robust" not in entities
    assert "zgjidhje e verifikuar" in entities


def test_anomaly_page_separates_exact_ensemble_xai_from_rule_proxy_shap() -> None:
    source = (ROOT / "streamlit_app" / "pages" / "3_Anomalies.py").read_text().lower()
    home = (ROOT / "streamlit_app" / "Home.py").read_text().lower()
    assert "pse mori këtë pikë ansambli" in source
    assert "zbërthim matematikor ekzakt" in source
    assert "nuk shpjegon ensemble_score" in source
    assert "konteksti përshkrues i veçorive" in source
    assert "3/4 detektorë" not in source
    assert 'model_agreement_count"] >= 3' not in source
    assert 'model_agreement_count"] >= minimum_model_agreement' in source
    assert "katër detektorëve" not in home
    assert "{ensemble_family_count} detektorëve" in home


def test_benchmark_page_cache_is_keyed_by_release_digest() -> None:
    source = (ROOT / "streamlit_app" / "pages" / "7_Krahasimi_i_Modeleve.py").read_text()
    assert "def load_benchmark_bundle(release_sha256: str)" in source
    assert "manifest_sha256" in source
    assert "readers.load_benchmark_bundle()" in source
    assert ".__wrapped__" not in source


@pytest.mark.parametrize(
    ("page", "forbidden"),
    [
        ("Home.py", "11 rregulla"),
        ("Home.py", "pragun 0.7"),
        ("Home.py", "të gjithë tenderët publikë të kosovës"),
        ("pages/7_Krahasimi_i_Modeleve.py", "kjo simulon përdorimin real"),
        ("pages/8_Fjalori.py", "të gjithë tenderët publikë të kosovës"),
    ],
)
def test_cautious_ui_claims_do_not_regress(page: str, forbidden: str) -> None:
    source = (ROOT / "streamlit_app" / page).read_text().lower()
    assert forbidden not in source


@pytest.mark.parametrize(
    ("page", "forbidden"),
    [
        ("Home.py", "vlera totale e kontraktuar"),
        ("pages/1_Overview.py", "tenderë të kontraktuar"),
        ("pages/1_Overview.py", "vlera e kontraktuar"),
        ("pages/2_Explore.py", "detajet e kontratës"),
        ("pages/2_Explore.py", "vlera e kontraktuar"),
        ("pages/3_Anomalies.py", "kontraktuar në fund"),
        ("pages/3_Anomalies.py", "vlera e kontraktuar"),
    ],
)
def test_award_objects_are_not_presented_as_contracts(page: str, forbidden: str) -> None:
    source = (ROOT / "streamlit_app" / page).read_text().lower()
    assert forbidden not in source

    home = (ROOT / "streamlit_app" / "Home.py").read_text().lower()
    assert "vendim dhënieje" in home
    assert all(status in home for status in ("nënshkruar", "ekzekutuar", "paguar"))
