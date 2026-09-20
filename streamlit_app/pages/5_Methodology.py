"""Explain the analysis first; keep reproducibility material available on demand."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from _bootstrap import page_header
from _charts import fmt_number
from _narrative import FLAG_NARRATIVE
from pyarrow.parquet import ParquetFile

from thesis import paths
from thesis.anomaly import rule_descriptions
from thesis.anomaly.rules import RULE_SCORE_NORMALISER, RULES
from thesis.domain.features import CONTEXT_FEATURES, ML_FEATURES
from thesis.jsonutil import loads_json

st.set_page_config(page_title="Metodologjia · OCDS Kosova", page_icon="📖", layout="wide")
page_header(
    "📖 Si bëhet analiza",
    "Nga njoftimet e prokurimit te sinjalet për shqyrtim: burimi, hapat dhe kufizimet.",
)

DOCS = paths.DOCS


def _render_document(filename: str) -> None:
    document = DOCS / filename
    if document.exists():
        st.markdown(document.read_text())
    else:
        st.info("Dokumenti shpjegues nuk është i disponueshëm në këtë instalim.")


def _render_dq_artifact(report_path: Path, parquet_path: Path) -> None:
    """Show freshness alongside the canonical DQ report, including unknown states."""
    if not report_path.exists():
        st.info("Raporti i kontrollit nuk është gjeneruar ende.")
        with st.expander("Udhëzim për mirëmbajtësin"):
            st.code("thesis dq run", language="bash")
        return

    metadata_path = report_path.with_suffix(".json")
    metadata = loads_json(metadata_path.read_text()) if metadata_path.exists() else {}
    run_at = metadata.get("timestamp")
    row_count = ParquetFile(parquet_path).metadata.num_rows if parquet_path.exists() else None
    artifact_updated = (
        datetime.fromtimestamp(parquet_path.stat().st_mtime, tz=timezone.utc)
        if parquet_path.exists()
        else None
    )
    passed = metadata.get("passed")
    result = "Kaloi" if passed is True else "Nuk kaloi" if passed is False else "Pa rezultat"
    c1, c2, c3 = st.columns(3)
    c1.metric("Rreshta të të dhënave", fmt_number(row_count))
    c2.metric("Kontrolli i cilësisë", result)
    c3.metric("Paralajmërime", str(metadata.get("warning_count", "—")))
    st.caption("Kalimi i kontrollit vërteton rregullat e kontrolluara, jo plotësinë e burimit.")

    if run_at and artifact_updated is not None:
        try:
            dq_time = datetime.fromisoformat(str(run_at).replace("Z", "+00:00"))
            if dq_time.tzinfo is None:
                dq_time = dq_time.replace(tzinfo=timezone.utc)
        except ValueError:
            dq_time = None
        if dq_time is not None and dq_time < artifact_updated:
            st.warning(
                "Ky raport është më i vjetër se skedari aktual i të dhënave. "
                "Kontrolli duhet përsëritur përpara se raporti të përdoret si rezultat aktual."
            )

    with st.expander("Raporti i plotë dhe koha e kontrollit"):
        st.caption(
            f"Kontrolluar: {run_at or '—'} · Të dhënat përditësuar: "
            f"{artifact_updated.isoformat() if artifact_updated else '—'}"
        )
        st.caption(f"Skedari: {report_path.relative_to(paths.ROOT)}")
        st.markdown(report_path.read_text())


tab_steps, tab_rules, tab_quality, tab_technical = st.tabs(
    ["Si funksionon", "Rregullat e shqyrtimit", "Cilësia e të dhënave", "Dokumentacioni teknik"]
)

with tab_steps:
    st.subheader("Çfarë bën ky projekt?")
    st.markdown(
        "Projekti i ndihmon përdoruesit të kuptojnë të dhënat e publikuara të prokurimit "
        "dhe të zgjedhin tenderë për shqyrtim të mëtejshëm. Analiza përdor një grup të "
        "ruajtur të të dhënave; nuk përditësohet drejtpërdrejt nga portali i prokurimit."
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**1 · Përgatiten të dhënat**\n\n"
        "Njoftimet e publikuara në formatin OCDS organizohen sipas tenderit, "
        "autoritetit kontraktues dhe vendimit për dhënie të kontratës. "
        "Kontrollohen identifikuesit, datat dhe vlerat që mungojnë."
    )
    c2.markdown(
        "**2 · Kërkohen sinjale**\n\n"
        "Rregullat e shpjegueshme gjejnë kushte të caktuara, si një ofertues i vetëm. "
        "Modelet statistikore gjejnë tenderë që dallojnë nga të tjerët në të dhëna."
    )
    c3.markdown(
        "**3 · Shqyrtohet konteksti**\n\n"
        "Paneli paraqet arsyen, shifrat dhe kufizimet. Për të arritur në një përfundim "
        "duhen lexuar dokumentet burimore dhe rrethanat e procedurës."
    )
    st.subheader("Si duhen kuptuar pikët?")
    st.markdown(
        "**Pikët e rregullave** përmbledhin sinjalet me peshat e zgjedhura nga autori. "
        "**Pikët e kombinuara** bashkojnë renditjet e modeleve, rregullat dhe krahasimin "
        "me tenderë të ngjashëm. Vlerat janë nga 0 në 1: një vlerë më e lartë rrit "
        "përparësinë për shqyrtim, por nuk tregon probabilitetin e një shkeljeje."
    )
    st.info(
        "Pikët krahasojnë tenderët brenda grupit të analizuar. Ato mund të ndryshojnë "
        "kur ndryshon ky grup. Rezultatet nuk janë verifikuar kundrejt një liste "
        "të pavarur të shkeljeve të konfirmuara."
    )
    st.subheader("Çfarë nuk mund të tregojnë këto të dhëna?")
    st.markdown(
        "- Një vendim për dhënie të kontratës nuk provon se kontrata është "
        "nënshkruar, zbatuar ose paguar.\n"
        "- Pa çmimet e secilës ofertë, nuk mund të përcaktohet nëse u zgjodh "
        "oferta më e lirë.\n"
        "- Një diferencë mes vlerës së parashikuar dhe vlerës së vendimeve të "
        "dhënies mund të vijë nga lote ose publikime të paplota; ajo nuk mat "
        "vetvetiu kursimin apo tejkalimin e shpenzimeve.\n"
        "- Mungesa e një sinjali nuk vërteton se një procedurë është pa probleme."
    )
    with st.expander("Parimet e përdorimit të përgjegjshëm"):
        _render_document("responsible_use.md")

with tab_rules:
    st.subheader("Cilat kushte kontrollohen?")
    enabled_count = sum(rule.score_enabled for rule in RULES)
    st.caption(
        f"Kontrollohen {len(RULES)} kushte. Vetëm {enabled_count} prej tyre ndikojnë "
        "në pikët e rregullave; të tjerat shërbejnë për kontroll të të dhënave "
        "ose ndjekje të procedurës. Asnjëri nuk përbën konstatim ligjor."
    )
    signal_types = {
        "review": "Shqyrtim i tenderit",
        "data_quality": "Cilësia e të dhënave",
        "operational": "Ndjekja e procedurës",
    }
    rows = []
    for rule in RULES:
        title, explanation, _ = FLAG_NARRATIVE.get(rule.code, (rule.code, rule.description, 1))
        rows.append(
            {
                "Sinjali": title,
                "Qëllimi": signal_types.get(rule.signal_type, rule.signal_type),
                "Pikët që shton": rule.weight / RULE_SCORE_NORMALISER if rule.score_enabled else 0,
                "Shpjegimi": explanation,
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Pikët që shton": st.column_config.NumberColumn(format="%.3f"),
            "Shpjegimi": st.column_config.TextColumn(width="large"),
        },
    )
    st.caption(
        "Pikët e aktivizuara mblidhen dhe kufizohen në 1. Kushti me një ofertues "
        "në procedurë të hapur zëvendëson kushtin e përgjithshëm për një ofertues, "
        "që i njëjti fakt të mos numërohet dy herë."
    )
    with st.expander("Peshat, pragjet dhe referencat e plota"):
        st.code("rule_score = clip(sum(weight × triggered) / 2, 0, 1)", language="text")
        st.dataframe(rule_descriptions(), hide_index=True, use_container_width=True)

with tab_quality:
    st.subheader("A i kanë kaluar të dhënat kontrollet?")
    st.caption(
        "Zgjidh grupin që dëshiron të kontrollosh. Paralajmërimet tregojnë fusha "
        "që kërkojnë kujdes edhe kur kontrollet kryesore kanë kaluar."
    )
    quality_groups = {
        "Tenderët e përgatitur": (paths.DQ / "silver_tenders.dq.md", paths.SILVER_TENDERS),
        "Vendimet për dhënie të kontratës": (paths.DQ / "silver_awards.dq.md", paths.SILVER_AWARDS),
        "Treguesit e llogaritur": (paths.DQ / "gold_tender_features.dq.md", paths.GOLD_FEATURES),
        "Tenderët me rezultate të analizës": (
            paths.DQ / "gold_tender_summary.dq.md",
            paths.GOLD_TENDERS,
        ),
    }
    chosen_quality_group = st.selectbox("Grupi i të dhënave", list(quality_groups))
    _render_dq_artifact(*quality_groups[chosen_quality_group])

with tab_technical:
    st.caption("Material për riprodhimin e analizës dhe shqyrtimin akademik të projektit.")
    for label, filename in (
        ("Arkitektura e sistemit", "architecture.md"),
        ("Udhëzuesi i ekzekutimit dhe mirëmbajtjes", "operations.md"),
        ("Metodologjia e plotë", "methodology.md"),
    ):
        with st.expander(label):
            _render_document(filename)
    with st.expander("Treguesit që përdorin modelet"):
        c1, c2 = st.columns(2)
        c1.markdown(f"**Tregues numerikë ({len(ML_FEATURES)})**")
        c1.code("\n".join(ML_FEATURES), language="text")
        c2.markdown(f"**Tregues për krahasim me tenderë të ngjashëm ({len(CONTEXT_FEATURES)})**")
        c2.code("\n".join(CONTEXT_FEATURES), language="text")
        st.caption(
            "Emrat teknikë lidhen me kolonat e ruajtura. Percentilet dhe pikët "
            "llogariten kundrejt të gjithë grupit të analizuar."
        )
        if paths.FEATURE_LIST.exists():
            st.json(loads_json(paths.FEATURE_LIST.read_text()))
    with st.expander("Vendimet për ndërtimin e sistemit"):
        adrs = sorted((DOCS / "adr").glob("*.md"))
        if not adrs:
            st.info("Nuk ka dokumente të vendimeve teknike në këtë instalim.")
        for document in adrs:
            st.markdown(document.read_text())
            st.divider()
