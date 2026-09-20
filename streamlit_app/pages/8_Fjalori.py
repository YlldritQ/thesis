"""Plain Albanian glossary for first-time users of the procurement dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from _bootstrap import app_link, cached_dashboard_bundle, page_header
from _charts import fmt_number
from _narrative import DATA_LIMITATION_BIDS, FLAG_NARRATIVE, METRIC_HELP, contract_severity

st.set_page_config(page_title="Fjalori · OCDS Kosova", page_icon="📚", layout="wide")
page_header(
    "📚 Fjalori dhe udhëzuesi",
    "Shpjegime të shkurtra për fjalët, shifrat dhe sinjalet që shfaqen në panel.",
)

dashboard = cached_dashboard_bundle(include_model_metadata=True)
gold = dashboard["gold"]
feature_metadata = dashboard.get("feature_metadata") or {}
ensemble_definition = feature_metadata.get("ensemble_explanation") or {}
release_dates = pd.to_datetime(
    gold.get("release_date", pd.Series(dtype="datetime64[ns]")), errors="coerce", utc=True
).dropna()

st.markdown(
    "**Filloni nga Përmbledhja** për pamjen e përgjithshme. Përdorni **Kërko tenderë** "
    "për një rast të caktuar dhe **Sinjalet për shqyrtim** për të kuptuar pse ai "
    "rast është veçuar. Kjo faqe shpjegon termat që hasni gjatë analizës."
)
if not release_dates.empty:
    populated_months = release_dates.dt.strftime("%Y-%m").nunique()
    start_date, end_date = release_dates.min(), release_dates.max()
    calendar_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    st.caption(
        f"Grupi i analizuar: {fmt_number(len(gold))} tenderë · {start_date:%m/%Y}–{end_date:%m/%Y} · "
        f"{populated_months} muaj me të dhëna nga {calendar_months} muaj në këtë interval. "
        "Ky është një version i ruajtur i të dhënave, jo monitorim në kohë reale."
    )
else:
    st.info("Nuk ka data publikimi për të përcaktuar periudhën e mbuluar.")

tab_terms, tab_values, tab_signals = st.tabs(
    ["Fjalët kryesore", "Si lexohen shifrat", "Si lexohen sinjalet"]
)

with tab_terms:
    terms = {
        "Autoriteti kontraktues": "Institucioni ose organizata që zhvillon prokurimin, "
        "për shembull një komunë, ministri ose ndërmarrje publike. Në panel quhet edhe autoritet.",
        "Operatori ekonomik": "Personi ose organizata që ofron mallra, shërbime apo punë. "
        "Mund të marrë pjesë vetë ose në grup me operatorë të tjerë.",
        "Ofertuesi": "Operatori ekonomik ose grupi i operatorëve që ka dorëzuar ofertë. "
        "Në këtë panel numërohen ofertuesit e regjistruar në burimin e të dhënave.",
        "Furnizuesi": "Operatori ekonomik i shënuar në një vendim për dhënie të kontratës. "
        "Identitetet që mungojnë ose emrat e ndryshëm mund të ndikojnë në numërim.",
        "Tenderi": "Në këtë panel, një aktivitet prokurimi i identifikuar në të dhëna. "
        "Një tender mund të ketë disa pjesë (lote) dhe disa vendime dhënieje.",
        "Loti": "Një pjesë e veçantë e një tenderi, për shembull furnizimi i një lloji "
        "pajisjeje. Tenderi mund të ndahet në lote me fitues të ndryshëm.",
        "Procedura e hapur": "Procedurë ku operatorët ekonomikë mund të dorëzojnë oferta "
        "sipas kushteve të publikuara. Në analizë, nënlloji i procedurës ruhet kur "
        "burimi e dallon nga kuotimi i çmimit ose procedurat e tjera.",
        "Vlera e parashikuar": "Vlera që autoriteti kontraktues ka parashikuar për "
        "prokurimin. Nuk është shumë e paguar.",
        "Vendimi për dhënie të kontratës": "Rezultati i regjistruar i përzgjedhjes së "
        "operatorit ekonomik. Në formatin OCDS quhet award. Nuk provon se kontrata "
        "është nënshkruar, zbatuar ose paguar.",
        "FPP / CPV": "Fjalori i Përbashkët i Prokurimit: sistemi i kodeve që përshkruan "
        "mallrat, shërbimet ose punët që prokurohen. CPV është shkurtesa në anglisht.",
        "OCDS": "Standardi i të dhënave të hapura për kontraktimin. Përdor fusha të "
        "përbashkëta për njoftimet e prokurimit, palët dhe rezultatet, që të dhënat "
        "të mund të përpunohen e të krahasohen.",
        "Anomalia": "Një vlerë ose kombinim të dhënash që dallon nga të tjerat. "
        "Mund të ketë shpjegim të ligjshëm ose të vijë nga një gabim në të dhëna.",
        "Sinjali për shqyrtim": "Një kusht që sistemi e veçon për verifikim, si një "
        "ofertues i vetëm. Sinjali tregon çfarë të shqyrtohet; nuk jep vendim për shkelje.",
        "Pikët e kombinuara": "Vlerë nga 0 në 1 që bashkon renditjen e modeleve, rregullat "
        "dhe krahasimin me tenderë të ngjashëm. Shërben për të renditur rastet për "
        "shqyrtim brenda grupit të analizuar; nuk mat probabilitetin e mashtrimit.",
        "Etiketa e rregullave": "Përgjigje po/jo e llogaritur nga pikët e rregullave. "
        "Përdoret për krahasimin e modeleve. Nuk është etiketë e një shkeljeje të konfirmuar.",
        "Modeli statistikor": "Metodë që mëson modele të përsëritura nga të dhënat "
        "dhe veçon raste që dallojnë. Modele të ndryshme mund të veçojnë raste të ndryshme.",
    }
    query = (
        st.text_input("Kërko një term", placeholder="P.sh. loti, ofertuesi, pikët…")
        .strip()
        .casefold()
    )
    matches = {
        term: explanation
        for term, explanation in terms.items()
        if not query or query in f"{term} {explanation}".casefold()
    }
    if not matches:
        st.info("Nuk u gjet asnjë term. Provoni një fjalë tjetër ose hiqni kërkimin.")
    for term, explanation in matches.items():
        st.markdown(f"**{term}**  \n{explanation}")

    with st.expander("Burimet për terminologjinë shqipe"):
        st.markdown(
            "Emërtimet e prokurimit ndjekin përdorimin e portalit zyrtar të Kosovës: "
            "autoriteti kontraktues, operatori ekonomik, vlera e parashikuar dhe "
            "njoftimi për dhënie të kontratës. "
            "[Shembull në e-Prokurimi](https://e-prokurimi.rks-gov.net/SPIN_PROD/application/ipn/DocumentManagement/DokumentPodaciFrm.aspx?id=2577669)."
        )
        st.markdown(
            "Në të njëjtën procedurë, portali i paraqet veçmas **B08 — Njoftimin për "
            "dhënie të kontratës** dhe **B52 — Njoftimin për nënshkrimin e kontratës**. "
            "Ky dallim ruhet edhe në panel."
        )
        st.markdown(
            "Termat statistikorë **mesatarja** dhe **mediana** përdoren edhe në "
            "[Raportin e Stabilitetit Financiar të BQK-së, nr. 21](https://bqk-kos.org/wp-content/uploads/2025/08/BQK_FSR_21.pdf). "
            "Shpjegimet këtu janë përshtatur për përdoruesin e panelit."
        )

with tab_values:
    st.subheader("Tri dallime që ndihmojnë në lexim")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**Mungon ≠ zero**\n\nShenja **—** do të thotë se vlera mungon ose nuk mund "
        "të llogaritet. **0** është vlerë e regjistruar. Një muaj pa të dhëna nuk "
        "provon se nuk pati prokurim."
    )
    c2.markdown(
        "**Mesatarja dhe mediana**\n\nMesatarja është shuma pjesëtuar me numrin e "
        "vlerave. Mediana është vlera në mes të listës së renditur; ndikohet më pak "
        "nga tenderët me vlera shumë të mëdha."
    )
    c3.markdown(
        "**Përqindja dhe baza e saj**\n\nPërqindja llogaritet mbi një grup të caktuar. "
        "Për shembull, tenderët me një ofertues krahasohen vetëm me tenderët ku "
        "numri i ofertuesve dihet."
    )
    st.markdown(
        "**Percentili** tregon pozicionin në një renditje. Një tender rreth percentilit "
        "95 është afër 5% të rasteve në krye. Kjo tregon pozicion relativ, jo 95% "
        "mundësi për shkelje. Kur përdorni filtrat, pikët e ruajtura nuk rillogariten."
    )
    metric_labels = {
        "estimated_value_eur": "Vlera e parashikuar",
        "total_awarded_eur": "Vlera e vendimeve të dhënies",
        "awarded_value_ratio": "Raporti ndërmjet vlerave",
        "num_bidders": "Numri i ofertuesve",
        "n_awards": "Numri i vendimeve të dhënies",
        "winner_top_share": "Pjesa e furnizuesit kryesor",
        "days_tender_open": "Afati për dorëzimin e ofertave",
        "days_to_first_award": "Ditët deri te vendimi i parë i dhënies",
        "ensemble_score": "Pikët e kombinuara",
        "rule_score": "Pikët e rregullave",
        "context_score": "Dallimi nga tenderë të ngjashëm",
        "supplier_hhi": "Përqendrimi te furnizuesit (HHI)",
        "single_bidder_pct": "Tenderët me një ofertues (%)",
    }
    st.subheader("Çfarë tregon secila shifër?")
    for key, explanation in METRIC_HELP.items():
        st.markdown(f"**{metric_labels.get(key, key)}**  \n{explanation}")
    with st.expander("Emrat teknikë të treguesve në skedarët e shkarkuar"):
        st.dataframe(
            pd.DataFrame(
                [{"Treguesi": label, "Emri në skedar": key} for key, label in metric_labels.items()]
            ),
            hide_index=True,
            use_container_width=True,
        )
        families = ensemble_definition.get("detector_families") or []
        minimum_agreement = ensemble_definition.get("minimum_models_agreeing")
        flag_quantile = ensemble_definition.get("flag_quantile")
        if families and minimum_agreement is not None and flag_quantile is not None:
            st.markdown(
                f"**high_confidence** është emërtim teknik historik. Në këtë version "
                f"do të thotë se të paktën **{minimum_agreement} nga {len(families)} modele** "
                f"e vendosin tenderin në pjesën e sipërme prej "
                f"**{(1 - flag_quantile):.0%}** të renditjes. "
                "Tregon pajtim mes modeleve, jo siguri të matur për një shkelje."
            )

with tab_signals:
    st.subheader("Çfarë kuptimi kanë ngjyrat?")
    st.caption(
        "Ngjyrat përmbledhin sinjalet dhe renditjen statistikore. "
        "Nuk tregojnë fajësi dhe nuk zëvendësojnë shqyrtimin e dokumenteve."
    )
    examples = [
        (
            {"SINGLE_BIDDER_OPEN": True, "HIGH_VALUE_SINGLE": True},
            "Të paktën dy sinjale që rrisin përparësinë e shqyrtimit.",
        ),
        ({"SINGLE_BIDDER_OPEN": True}, "Një sinjal që rrit përparësinë e shqyrtimit."),
        ({"ensemble_score": 0.8}, "Pikë të kombinuara të larta, pa sinjal nga rregullat."),
        (
            {"ZERO_BIDDER": True},
            "Sinjal për verifikim ose pikë të kombinuara mesatarisht të larta.",
        ),
        (
            {"ensemble_score": 0.1},
            "Nuk ka sinjale të dukshme; kjo nuk vërteton mungesën e problemeve.",
        ),
    ]
    for example, explanation in examples:
        band = contract_severity(example)
        st.markdown(f"{band['emoji']} **{band['label']}** — {explanation}")

    st.subheader("Cilat sinjale mund të shfaqen?")
    st.caption("Hapni një sinjal për të lexuar arsyen dhe shpjegimet e mundshme.")
    for _, (title, detail, _) in sorted(FLAG_NARRATIVE.items(), key=lambda item: -item[1][2]):
        with st.expander(title):
            st.markdown(detail)

    st.subheader("Shembull: vetëm një ofertues")
    st.markdown(
        "Në një procedurë të hapur standarde është regjistruar vetëm **një ofertues**. "
        "Paneli e veçon për shqyrtim sepse pjesëmarrja është e ulët. "
        "Shqyrtuesi kontrollon kushtet e tenderit, tregun dhe dokumentet: "
        "mund të ketë pak operatorë të kualifikuar ose arsye të tjera të ligjshme."
    )
    st.info(
        "Nëse vlera e vendimeve të dhënies është më e lartë se parashikimi, "
        "kontrollohen lotet dhe çfarë përfshin secila vlerë. Vetëm kjo diferencë "
        "nuk tregon shpenzim mbi plan apo pagesë të tepërt."
    )
    with st.expander("Llogaritja e pikëve në këtë shembull"):
        st.markdown(
            "Rregulli për një ofertues në procedurë të hapur shton **0,375 pikë** "
            "(pesha 0,75 pjesëtohet me 2). Vetëm ky kusht mbetet nën pragun 0,5 "
            "të pikëve të rregullave. Ngjyra e shpjegimit dhe pragu i pikëve janë "
            "dy përmbledhje të ndryshme. Kontrolli i diferencës së vlerave shton "
            "**0 pikë** dhe shërben vetëm për verifikim të të dhënave."
        )
    st.warning(DATA_LIMITATION_BIDS)

st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    app_link("pages/1_Overview.py", "📊 Përmbledhja")
with c2:
    app_link("pages/2_Explore.py", "🔎 Kërko tenderë")
with c3:
    app_link("pages/5_Methodology.py", "📖 Si bëhet analiza")
