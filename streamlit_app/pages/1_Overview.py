"""Filtered, question-led overview of the published procurement records."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from _bootstrap import cached_gold, fmt_eur, fmt_number, page_header, sidebar_filters
from _charts import (
    PALETTE,
    category_bar,
    method_bar,
    monthly_summary,
    style_chart,
    time_series_value,
    time_series_volume,
    top_n_bar,
    value_histogram,
)

st.set_page_config(page_title="Përmbledhja · Prokurimi në Kosovë", page_icon="📊", layout="wide")
page_header(
    "📊 Përmbledhja e prokurimit",
    "Si ndryshojnë numri, vlera dhe konkurrenca në tenderët e përzgjedhur?",
)

gold = cached_gold()
filtered = sidebar_filters(gold)
st.caption(
    f"PËRZGJEDHJA AKTUALE · {fmt_number(len(filtered))} nga {fmt_number(len(gold))} tenderë · Të gjithë grafikët më poshtë ndjekin filtrat."
)
if filtered.empty:
    st.info(
        "Asnjë tender nuk përputhet me filtrat. Zgjidhni një periudhë më të gjerë ose përdorni «Pastro filtrat»."
    )
    st.stop()

cols = st.columns(4)
cols[0].metric("Tenderë të përzgjedhur", fmt_number(len(filtered)))
cols[1].metric("Vlera e parashikuar", fmt_eur(filtered["estimated_value_eur"].sum(min_count=1)))
cols[2].metric(
    "Vlera e vendimeve të dhënies",
    fmt_eur(filtered["total_awarded_eur"].sum(min_count=1)),
    help="Shuma në vendimet e regjistruara për dhënie të kontratës; nuk është shumë e paguar.",
)
cols[3].metric(
    "Me vendim dhënieje",
    fmt_number(filtered["n_awards"].ge(1).sum()),
    delta=f"{fmt_number(filtered['n_awards'].ge(1).mean() * 100, 1)}% e përzgjedhjes",
    delta_color="off",
)
st.caption(
    "Vendimet e dhënies nuk dëshmojnë nënshkrimin apo pagesën e kontratave. Diferenca ndaj vlerës së parashikuar nuk mat kursimin."
)

monthly = monthly_summary(filtered)
activity, competition, distribution = st.tabs(
    ["Ecuria dhe kategoritë", "Konkurrenca", "Vlerat dhe autoritetet"]
)
with activity:
    left, right = st.columns(2)
    left.plotly_chart(time_series_volume(monthly), use_container_width=True)
    right.plotly_chart(time_series_value(monthly), use_container_width=True)
    unknown_dates = int(filtered["release_date"].isna().sum())
    st.caption(
        f"Sipas datës së publikimit. Muajt pa të dhëna lihen bosh. {fmt_number(unknown_dates)} tenderë pa datë publikimi përfshihen në treguesit kryesorë, por jo në grafikët kohorë."
    )
    left, right = st.columns(2)
    left.plotly_chart(
        category_bar(filtered, "estimated_value_eur", "Për cilat kategori parashihen fondet?"),
        use_container_width=True,
    )
    right.plotly_chart(
        method_bar(filtered, "estimated_value_eur", "Cilat procedura përdoren?"),
        use_container_width=True,
    )
    st.caption(
        "Procedura përcaktohet nga kodi i prokurimit dhe përshkrimi në burim. Rastet pa klasifikim mbeten të dukshme si «E papërcaktuar»."
    )

with competition:
    observed = (
        filtered["bidder_data_observed"].fillna(False).astype(bool)
        & filtered["num_bidders"].notna()
    )
    observed_count = int(observed.sum())
    single = int(filtered.loc[observed, "num_bidders"].eq(1).sum())
    coverage = observed.mean() * 100
    cols = st.columns(3)
    cols[0].metric(
        "Me të dhëna për ofertuesit",
        fmt_number(observed_count),
        delta=f"{fmt_number(coverage, 1)}% e përzgjedhjes",
        delta_color="off",
    )
    cols[1].metric(
        "Me vetëm një ofertues",
        fmt_number(single),
        delta=f"{fmt_number(single / observed_count * 100, 1)}% e rasteve me të dhëna"
        if observed_count
        else None,
        delta_color="off",
    )
    cols[2].metric("Pa të dhëna për ofertuesit", fmt_number((~observed).sum()))
    if observed_count:
        st.subheader("Sa të shpeshtë janë tenderët me një ofertues?")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=monthly["release_date"],
                y=monthly["single_bidder_pct"],
                mode="lines+markers",
                name="Me një ofertues",
                line={"color": PALETTE["secondary"]},
                connectgaps=False,
                customdata=monthly["observed_bidders"],
                hovertemplate="%{x|%m/%Y}<br>%{y:.1f}% me një ofertues<br>Baza: %{customdata:,.0f} tenderë me të dhëna<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title=None, yaxis_title="% e tenderëve me të dhëna për ofertuesit")
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(style_chart(fig), use_container_width=True)
    else:
        st.info(
            "Për këtë përzgjedhje mungojnë të dhënat e ofertuesve. Nuk mund të llogaritet pjesëmarrja."
        )
    st.caption(
        "Përqindja përdor vetëm tenderët me të dhëna për ofertuesit. Mungesa e të dhënave nuk do të thotë se nuk pati oferta. Një ofertues është sinjal për shqyrtim, jo provë parregullsie."
    )
    coverage_fig = go.Figure(
        go.Bar(
            x=monthly["release_date"],
            y=monthly["bidder_data_coverage_pct"],
            marker_color=PALETTE["primary"],
            hovertemplate="%{x|%m/%Y}<br>%{y:.1f}% me të dhëna<extra></extra>",
        )
    )
    coverage_fig.update_layout(
        title="Sa të plota janë të dhënat e ofertuesve?",
        yaxis_title="% e të gjithë tenderëve të muajit",
    )
    coverage_fig.update_yaxes(range=[0, 100], ticksuffix="%")
    st.plotly_chart(style_chart(coverage_fig, height=280), use_container_width=True)

with distribution:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Çfarë vlerash kanë tenderët?")
        st.plotly_chart(value_histogram(filtered["estimated_value_eur"]), use_container_width=True)
        missing_values = int(filtered["estimated_value_eur"].isna().sum())
        st.caption(
            f"Intervale të vlerës së parashikuar, në euro. {fmt_number(missing_values)} tenderë pa vlerë të publikuar nuk përfshihen në këtë grafik."
        )
    with right:
        median = filtered["estimated_value_eur"].median()
        p90 = filtered["estimated_value_eur"].quantile(0.9)
        st.metric("Vlera e mesit (mediana)", fmt_eur(median))
        st.caption("Gjysma e vlerave janë më të vogla ose të barabarta me këtë shumë.")
        st.metric("90% e vlerave janë deri në", fmt_eur(p90))
        st.caption("Vetëm 10% e vlerave e kalojnë këtë kufi.")
    st.plotly_chart(
        top_n_bar(
            filtered,
            "procuring_entity_name",
            "estimated_value_eur",
            n=10,
            title="10 autoritetet me vlerën më të lartë të parashikuar",
        ),
        use_container_width=True,
    )
    st.caption(
        "Kjo renditje tregon vlerën e parashikuar në të dhënat e përzgjedhura; nuk mat performancën e institucioneve."
    )

with st.expander("Shkarko të dhënat e kësaj përzgjedhjeje"):
    export_columns = [
        "ocid",
        "title",
        "procuring_entity_name",
        "release_date",
        "category",
        "estimated_value_eur",
        "total_awarded_eur",
        "num_bidders",
        "bidder_data_observed",
    ]
    exported = filtered[[column for column in export_columns if column in filtered]].copy()
    st.download_button(
        "Shkarko tenderët (CSV)",
        exported.to_csv(index=False).encode("utf-8-sig"),
        file_name="tenderet_e_perzgjedhur.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.caption(
        "Eksporti përfshin të gjithë tenderët e përzgjedhur, përfshirë vlerat që mungojnë. Emrat teknikë të kolonave ruhen për ripërdorim në analizë."
    )
