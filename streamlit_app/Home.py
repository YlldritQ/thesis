"""A question-led introduction to the procurement dataset."""

from __future__ import annotations

import streamlit as st
from _bootstrap import app_link, cached_dashboard_bundle, fmt_eur, fmt_number, page_header
from _charts import category_bar, monthly_summary, time_series_volume

st.set_page_config(
    page_title="Ballina · Prokurimi në Kosovë",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

page_header(
    "Çfarë tregojnë të dhënat e prokurimit?",
    "Shihni vlerat e parashikuara, pjesëmarrjen e ofertuesve dhe tenderët me sinjale për shqyrtim.",
)

dashboard = cached_dashboard_bundle(include_model_metadata=True)
gold = dashboard["gold"]
ensemble_definition = dashboard["feature_metadata"]["ensemble_explanation"]
ensemble_family_count = len(ensemble_definition["detector_families"])
minimum_agreement = int(ensemble_definition["minimum_models_agreeing"])

if gold.empty:
    st.info("Nuk ka të dhëna për t’u paraqitur në këtë version të analizës.")
    st.stop()

dates = gold["release_date"].dropna()
period = (
    f"{dates.min():%m/%Y} – {dates.max():%m/%Y}" if not dates.empty else "Periudhë e papërcaktuar"
)
st.caption(f"BURIMI: KRPP / Open Contracting Partnership · {period} · Publikimi 115")

cols = st.columns(4)
cols[0].metric("Tenderë në të dhëna", fmt_number(len(gold)))
cols[1].metric(
    "Autoritete kontraktuese",
    fmt_number(gold["procuring_entity_id"].nunique()),
    help="Institucionet publike që organizojnë prokurimin, sipas identifikuesve në burim.",
)
cols[2].metric(
    "Vlera e parashikuar",
    fmt_eur(gold["estimated_value_eur"].sum(min_count=1)),
    help="Shuma e vlerave të parashikuara të publikuara. Nuk është shpenzim i realizuar.",
)
flagged = int(gold["rule_score"].ge(0.5).sum())
cols[3].metric(
    "Për shqyrtim sipas rregullave",
    fmt_number(flagged),
    delta=f"{fmt_number(flagged / len(gold) * 100, 1)}% e tenderëve",
    delta_color="off",
    help="Tenderë me pikë të rregullave të paktën 0,5. Ky është prag orientues për shqyrtim, jo konstatim shkeljeje.",
)

st.markdown("### Një vështrim i parë")
left, right = st.columns([1.5, 1])
with left:
    st.plotly_chart(time_series_volume(monthly_summary(gold)), use_container_width=True)
with right:
    st.plotly_chart(
        category_bar(gold, "estimated_value_eur", "Për çfarë parashihen fondet?"),
        use_container_width=True,
    )
st.caption(
    "Grafikët përfshijnë të gjithë tenderët në këtë grup të dhënash. Për periudha ose institucione të veçanta, hapni Përmbledhjen."
)

st.markdown("### Zgjidhni çfarë dëshironi të kuptoni")
for col, heading, detail, route, button in zip(
    st.columns(3),
    ["Si ndryshon prokurimi?", "Çfarë përmban një tender?", "Cilat raste kërkojnë shqyrtim?"],
    [
        "Krahasoni numrin, vlerën dhe konkurrencën sipas periudhës, kategorisë dhe autoritetit.",
        "Kërkoni sipas titullit ose identifikuesit. Shihni vlerat, afatet dhe vendimet e dhënies.",
        "Shihni arsyet e sinjalizimit dhe si janë llogaritur pikët e çdo tenderi.",
    ],
    ["pages/1_Overview.py", "pages/2_Explore.py", "pages/3_Anomalies.py"],
    ["Hap përmbledhjen →", "Kërko tenderë →", "Shih sinjalet →"],
):
    with col, st.container(border=True):
        st.markdown(f"#### {heading}")
        st.write(detail)
        app_link(route, button)

with st.expander("Çfarë përfshijnë këto të dhëna?"):
    st.write(
        f"Analiza përfshin {fmt_number(len(gold))} tenderë të Publikimit 115 të KRPP-së, "
        "të shpërndarë nga Open Contracting Partnership. Është një version i ruajtur i të dhënave, "
        "pa përditësim automatik; nuk përfaqëson domosdoshmërisht çdo prokurim në Kosovë."
    )
    if not dates.empty:
        populated = dates.dt.strftime("%Y-%m").nunique()
        calendar = (
            (dates.max().year - dates.min().year) * 12 + dates.max().month - dates.min().month + 1
        )
        st.write(
            f"Ka të dhëna në {populated} nga {calendar} muaj të periudhës. {fmt_number(gold['release_date'].isna().sum())} tenderë nuk kanë datë publikimi dhe nuk paraqiten në grafikun kohor."
        )
    st.write(
        "Objekti `award` regjistron një vendim dhënieje, pra vendimin për dhënie të kontratës. "
        "Ai nuk dëshmon që kontrata është nënshkruar, ekzekutuar ose paguar. "
        "Vlera e parashikuar dhe vlera e vendimeve të dhënies nuk duhen interpretuar si kursim buxhetor."
    )
    st.markdown("[Burimi i të dhënave](https://data.open-contracting.org/en/publication/115)")

with st.expander("Si krijohen sinjalet për shqyrtim?"):
    st.write(
        "Rregullat kontrollojnë të dhënat e konkurrencës, vlerat dhe afatet. "
        f"Renditjet e {ensemble_family_count} detektorëve kombinohen me rregullat dhe krahasimin "
        "me tenderë të ngjashëm. Pikët janë relative ndaj të dhënave të analizuara."
    )
    st.write(
        "Pikët nuk janë probabilitet mashtrimi. Modelet janë krahasuar me etiketa të nxjerra "
        "nga rregullat; rezultatet ende nuk janë verifikuar me vlerësime të pavarura të rasteve. "
        "Te Sinjalet për shqyrtim mund të shihni kontributin e secilës pjesë në pikët përfundimtare."
    )

st.caption("Projekt diplome bachelor · Panel kërkimor; nuk është shërbim zyrtar i institucioneve.")
