"""Plain Albanian glossary for first-time users of the procurement dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from _bootstrap import SOURCE_TZ, app_link, cached_dashboard_bundle, page_header
from _charts import fmt_number
from _narrative import DATA_LIMITATION_BIDS, FLAG_NARRATIVE, METRIC_HELP, contract_severity

st.set_page_config(
    page_title="Fjalori i termave · Prokurimi në Kosovë", page_icon="📚", layout="wide"
)
page_header(
    "📚 Fjalori i termave",
    "Shpjegime të termave, treguesve dhe sinjaleve që përdoren në panel.",
)

dashboard = cached_dashboard_bundle(include_model_metadata=True)
gold = dashboard["gold"]
feature_metadata = dashboard.get("feature_metadata") or {}
ensemble_definition = feature_metadata.get("ensemble_explanation") or {}
# Show the covered period in the source's published +01:00 offset, as on the other pages.
release_dates = (
    pd.to_datetime(
        gold.get("release_date", pd.Series(dtype="datetime64[ns]")), errors="coerce", utc=True
    )
    .dt.tz_convert(SOURCE_TZ)
    .dropna()
)

st.markdown(
    "**Filloni me faqen Përmbledhja** për një pamje të përgjithshme të të dhënave. Përdorni **Kërko tenderë** "
    "për një rast të caktuar dhe **Sinjalet për shqyrtim** për të kuptuar pse ai "
    "rast është veçuar. Kjo faqe shpjegon termat që hasni gjatë analizës."
)
if not release_dates.empty:
    populated_months = release_dates.dt.strftime("%Y-%m").nunique()
    start_date, end_date = release_dates.min(), release_dates.max()
    calendar_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    st.caption(
        f"Bashkësia e analizuar: {fmt_number(len(gold))} tenderë · {start_date:%m/%Y}–{end_date:%m/%Y} · "
        f"Të dhëna për {populated_months} nga {calendar_months} muajt e këtij intervali. "
        "Ky është një version i ruajtur i të dhënave, jo monitorim në kohë reale."
    )
else:
    st.info("Nuk ka data publikimi për të përcaktuar periudhën e mbuluar.")

tab_terms, tab_values, tab_signals = st.tabs(
    ["Termat kryesorë", "Si interpretohen shifrat", "Si interpretohen sinjalet"]
)

with tab_terms:
    terms = {
        "Autoriteti kontraktues": "Institucioni ose organizata që zhvillon prokurimin, "
        "për shembull një komunë, ministri ose ndërmarrje publike. Në panel quhet edhe autoritet.",
        "Operatori ekonomik": "Personi ose organizata që ofron mallra, shërbime apo punë. "
        "Mund të marrë pjesë vetë ose në grup me operatorë të tjerë.",
        "Ofertuesi": "Operatori ekonomik ose grupi i operatorëve që ka dorëzuar ofertë. "
        "Paneli numëron ofertuesit e regjistruar në burimin e të dhënave.",
        "Furnizuesi": "Operatori ekonomik i shënuar në një vendim për dhënien e kontratës. "
        "Mungesa e identifikuesve ose përdorimi i emrave të ndryshëm mund të ndikojë në numërim.",
        "Tenderi": "Në këtë panel, një aktivitet prokurimi i identifikuar në të dhëna. "
        "Një tender mund të ketë disa pjesë (lote) dhe disa vendime për dhënien e kontratës.",
        "Loti": "Një pjesë e veçantë e një tenderi, për shembull furnizimi i një lloji "
        "pajisjeje. Tenderi mund të ndahet në lote me fitues të ndryshëm.",
        "Procedura e hapur": "Procedurë ku operatorët ekonomikë mund të dorëzojnë oferta "
        "sipas kushteve të publikuara. Në analizë, nënlloji i procedurës ruhet kur "
        "burimi e dallon nga kuotimi i çmimit ose procedurat e tjera.",
        "Vlera e parashikuar": "Vlera që autoriteti kontraktues ka parashikuar për "
        "prokurimin. Nuk tregon shumën e paguar.",
        "Vendimi për dhënien e kontratës": "Rezultati i regjistruar i përzgjedhjes së "
        "operatorit ekonomik. Në formatin OCDS quhet award. Nuk provon se kontrata "
        "është nënshkruar apo zbatuar, ose se janë kryer pagesa.",
        "FPP / CPV": "Fjalori i Përbashkët i Prokurimit: sistemi i kodeve që përshkruan "
        "mallrat, shërbimet ose punët që prokurohen. CPV është shkurtesa në anglisht.",
        "OCDS": "Standard për publikimin e të dhënave të kontraktimit në format të hapur. Përdor fusha të "
        "përbashkëta për njoftimet e prokurimit, palët dhe rezultatet, që të dhënat "
        "të mund të përpunohen e të krahasohen.",
        "Anomalia": "Një vlerë ose kombinim të dhënash që dallon nga të tjerat. "
        "Mund të ketë shpjegim të ligjshëm ose të vijë nga një gabim në të dhëna.",
        "Sinjali për shqyrtim": "Një situatë që sistemi e shënon për verifikim, si pjesëmarrja e një "
        "ofertuesi të vetëm. Sinjali tregon çfarë duhet shqyrtuar; nuk vërteton shkelje.",
        "Pikët e kombinuara": "Vlerë nga 0 në 1 që bashkon renditjen e modeleve, rregullat "
        "dhe krahasimin me tenderë të ngjashëm. Shërben për të renditur rastet për "
        "shqyrtim brenda bashkësisë së analizuar; nuk mat probabilitetin e mashtrimit.",
        "Etiketa sipas rregullave": "Vlerë po/jo e përcaktuar nga pikët sipas rregullave. "
        "Përdoret për krahasimin e modeleve. Nuk është etiketë e një shkeljeje të konfirmuar.",
        "Modeli statistikor": "Metodë që mëson rregullsi nga të dhënat "
        "dhe veçon raste që dallojnë. Modele të ndryshme mund të veçojnë raste të ndryshme.",
        "Mësimi makinerik": "Fushë e shkencës kompjuterike që zhvillon metoda për të mësuar "
        "nga të dhënat. Në këtë projekt përdoret për krahasimin dhe renditjen e tenderëve.",
        "Mësimi i mbikëqyrur": "Trajnimi i një modeli me raste për të cilat janë dhënë etiketa. "
        "Në këtë projekt etiketat nxirren nga rregullat; ato nuk janë shkelje të konfirmuara.",
        "Mësimi i pambikëqyrur": "Analiza e të dhënave pa etiketa paraprake për rezultatin. "
        "Në këtë projekt modelet përkatëse identifikojnë tenderë me karakteristika të pazakonta.",
        "Klasifikimi": "Caktimi i rasteve në kategori. Klasifikuesi i këtij projekti mëson "
        "të riprodhojë etiketat sipas rregullave; nuk përcakton nëse është kryer një shkelje.",
        "Parapërpunimi": "Përgatitja e të dhënave për analizë, përmes pastrimit, "
        "unifikimit të formateve dhe trajtimit të vlerave që mungojnë.",
        "Shpjegueshmëria": "Mundësia për të treguar si është llogaritur një rezultat. "
        "Paneli paraqet kontributin e modeleve, rregullave dhe kontekstit në pikët e kombinuara. "
        "Ky shpjegim nuk provon shkakun e një parregullsie.",
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
        st.info("Nuk u gjet asnjë term. Provoni një fjalë tjetër ose fshini tekstin e kërkimit.")
    for term, explanation in matches.items():
        st.markdown(f"**{term}**  \n{explanation}")

    with st.expander("Burimet për terminologjinë shqipe"):
        st.markdown(
            "Emërtimet e prokurimit ndjekin përdorimin e portalit zyrtar të Kosovës: "
            "autoriteti kontraktues, operatori ekonomik, vlera e parashikuar dhe "
            "njoftimi për dhënien e kontratës. "
            "[Shembull në e-Prokurimi](https://e-prokurimi.rks-gov.net/SPIN_PROD/application/ipn/DocumentManagement/DokumentPodaciFrm.aspx?id=2577669)."
        )
        st.markdown(
            "Në të njëjtën procedurë, portali i paraqet veçmas **B08 — Njoftimin për "
            "dhënien e kontratës** dhe **B52 — Njoftimin për nënshkrimin e kontratës**. "
            "Ky dallim ruhet edhe në panel."
        )
        st.markdown(
            "Termat statistikorë **mesatarja** dhe **mediana** përdoren edhe në "
            "[Raportin e Stabilitetit Financiar të BQK-së, nr. 21](https://bqk-kos.org/wp-content/uploads/2025/08/BQK_FSR_21.pdf). "
            "Shpjegimet këtu janë përshtatur për përdoruesin e panelit."
        )
        st.markdown(
            "Për terminologjinë e informatikës janë konsultuar programi mësimor "
            "[Mësimi Makinerik i FIEK-ut, Universiteti i Prishtinës](https://fiek.uni-pr.edu/desk/inc/media/BB0C5A0F-4D25-4099-9274-C7D71E7E3A82.pdf) "
            "dhe [disertacioni i Erind Bedallit, Departamenti i Informatikës, Universiteti i Tiranës](https://www.unitir.edu.al/wp-content/uploads/2015/01/Doktoratura-Erind-Bedalli-Fakulteti-i-Shkencave-i-Natyrore-Departamenti-i-Informatikes.pdf). "
            "Këto burime përdoren si referenca për termat, ndërsa përkufizimet janë përshtatur për këtë panel."
        )

with tab_values:
    st.subheader("Tri dallime që ndihmojnë në interpretimin e shifrave")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**Mungon ≠ zero**\n\nShenja **—** do të thotë se vlera mungon ose nuk mund "
        "të llogaritet. **0** është vlerë e regjistruar. Një muaj pa të dhëna nuk "
        "provon se nuk u zhvillua prokurim."
    )
    c2.markdown(
        "**Mesatarja dhe mediana**\n\nMesatarja është shuma pjesëtuar me numrin e "
        "vlerave. Mediana është vlera në mes të listës së renditur; ndikohet më pak "
        "nga tenderët me vlera shumë të mëdha."
    )
    c3.markdown(
        "**Përqindja dhe baza e saj**\n\nPërqindja llogaritet mbi një grup të caktuar. "
        "Për shembull, tenderët me një ofertues krahasohen vetëm me tenderët ku "
        "numri i ofertuesve është i njohur."
    )
    st.markdown(
        "**Percentili** tregon pozicionin në një renditje. Një tender rreth percentilit "
        "95 është pranë 5% të rasteve në krye të renditjes. Ky është një pozicion relativ, "
        "jo probabilitet 95% që të ketë shkelje. Filtrat nuk i rillogaritin pikët e ruajtura."
    )
    metric_labels = {
        "estimated_value_eur": "Vlera e parashikuar",
        "total_awarded_eur": "Vlera sipas vendimeve",
        "awarded_value_ratio": "Raporti ndërmjet vlerave",
        "num_bidders": "Numri i ofertuesve",
        "n_awards": "Numri i vendimeve për dhënien e kontratës",
        "winner_top_share": "Pjesa e furnizuesit kryesor",
        "days_tender_open": "Afati për ofertim",
        "days_to_first_award": "Ditët deri te vendimi i parë për dhënien e kontratës",
        "ensemble_score": "Pikët e kombinuara",
        "rule_score": "Pikët sipas rregullave",
        "context_score": "Dallimi nga tenderët e ngjashëm",
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
                "Tregon përputhje ndërmjet modeleve; nuk është matje e sigurisë se ka shkelje."
            )

with tab_signals:
    st.subheader("Çfarë kuptimi kanë ngjyrat?")
    st.caption(
        "Ngjyrat përmbledhin sinjalet e evidentuara dhe renditjen statistikore. "
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
    st.caption(
        "Hapni shpjegimin e një sinjali për të lexuar arsyen e sinjalizimit dhe rrethanat e mundshme."
    )
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
        "Nëse vlera sipas vendimeve për dhënien e kontratës është më e lartë se parashikimi, "
        "duhen kontrolluar lotet dhe përmbajtja e secilës vlerë. Vetëm ky dallim "
        "nuk dëshmon tejkalim të shpenzimeve apo pagesë të tepërt."
    )
    with st.expander("Llogaritja e pikëve në këtë shembull"):
        st.markdown(
            "Rregulli për një ofertues në procedurë të hapur shton **0,375 pikë** "
            "(pesha 0,75 pjesëtohet me 2). Vetëm ky kusht mbetet nën pragun 0,5 "
            "të pikëve sipas rregullave. Ngjyra e shpjegimit dhe pragu i pikëve janë "
            "dy mënyra të ndryshme për të përmbledhur rezultatet. Kontrolli i dallimit ndërmjet vlerave shton "
            "**0 pikë** dhe shërben vetëm për verifikim të të dhënave."
        )
    st.warning(DATA_LIMITATION_BIDS)

st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    app_link("pages/1_Overview.py", "📊 Përmbledhja")
with c2:
    app_link("pages/2_Explore.py", "🔍 Kërko tenderë")
with c3:
    app_link("pages/5_Methodology.py", "📖 Si funksionon analiza")
