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
    "Si ndryshojnë numri dhe vlera e tenderëve të përzgjedhur dhe sa konkurrencë ka mes ofertuesve?",
)

gold = cached_gold()
filtered = sidebar_filters(gold)
st.caption(
    f"REZULTATET E FILTRIMIT · {fmt_number(len(filtered))} nga {fmt_number(len(gold))} tenderë · Të gjithë grafikët më poshtë pasqyrojnë filtrat e zgjedhur."
)
if filtered.empty:
    st.info(
        "Asnjë tender nuk përputhet me filtrat e zgjedhur. Zgjidhni një periudhë më të gjerë ose përdorni «Hiq filtrat»."
    )
    st.stop()

cols = st.columns(4)
cols[0].metric("Tenderë pas filtrimit", fmt_number(len(filtered)))
cols[1].metric("Vlera e parashikuar", fmt_eur(filtered["estimated_value_eur"].sum(min_count=1)))
cols[2].metric(
    "Vlera sipas vendimeve",
    fmt_eur(filtered["total_awarded_eur"].sum(min_count=1)),
    help="Shuma e vlerave të shënuara në vendimet për dhënien e kontratës. Nuk përfaqëson pagesa të kryera.",
)
cols[3].metric(
    "Me vendim për dhënien e kontratës",
    fmt_number(filtered["n_awards"].ge(1).sum()),
    delta=f"{fmt_number(filtered['n_awards'].ge(1).mean() * 100, 1)}% e tenderëve të filtruar",
    delta_color="off",
)
st.caption(
    "Vendimet për dhënien e kontratës nuk dëshmojnë se kontratat janë nënshkruar apo zbatuar, ose se janë kryer pagesa. Dallimi krahasuar me vlerën e parashikuar nuk tregon domosdoshmërisht kursim."
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
        f"Grafikët bazohen në datën e publikimit; muajt pa të dhëna shfaqen bosh. {fmt_number(unknown_dates)} tenderë pa datë publikimi përfshihen në treguesit kryesorë, por jo në grafikët kohorë."
    )
    left, right = st.columns(2)
    left.plotly_chart(
        category_bar(
            filtered, "estimated_value_eur", "Si ndahet vlera e parashikuar sipas kategorive?"
        ),
        use_container_width=True,
    )
    right.plotly_chart(
        method_bar(filtered, "estimated_value_eur", "Cilat procedura përdoren?"),
        use_container_width=True,
    )
    st.caption(
        "Procedura përcaktohet sipas kodit të prokurimit dhe përshkrimit në burim. Tenderët pa klasifikim paraqiten me shënimin «E papërcaktuar»."
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
        delta=f"{fmt_number(coverage, 1)}% e tenderëve të filtruar",
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
                hovertemplate="%{x|%m/%Y}<br>%{y:.1f}% me një ofertues<br>Llogaritur mbi %{customdata:,.0f} tenderë me të dhëna<extra></extra>",
            )
        )
        fig.update_layout(xaxis_title=None, yaxis_title="% e tenderëve me të dhëna për ofertuesit")
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(style_chart(fig), use_container_width=True)
    else:
        st.info(
            "Për tenderët e filtruar mungojnë të dhënat për ofertuesit. Pjesëmarrja nuk mund të llogaritet."
        )
    st.caption(
        "Përqindja llogaritet vetëm për tenderët me të dhëna për ofertuesit. Mungesa e këtyre të dhënave nuk do të thotë se nuk janë dorëzuar oferta. Pjesëmarrja e vetëm një ofertuesi është arsye për shqyrtim, por nuk provon parregullsi."
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
        title="Sa të plota janë të dhënat për ofertuesit?",
        yaxis_title="% e të gjithë tenderëve të muajit",
    )
    coverage_fig.update_yaxes(range=[0, 100], ticksuffix="%")
    st.plotly_chart(style_chart(coverage_fig, height=280), use_container_width=True)

with distribution:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Si shpërndahen vlerat e tenderëve?")
        st.plotly_chart(value_histogram(filtered["estimated_value_eur"]), use_container_width=True)
        missing_values = int(filtered["estimated_value_eur"].isna().sum())
        st.caption(
            f"Tenderët grupohen sipas intervaleve të vlerës së parashikuar, në euro. {fmt_number(missing_values)} tenderë pa vlerë të publikuar nuk përfshihen në grafik."
        )
    with right:
        median = filtered["estimated_value_eur"].median()
        p90 = filtered["estimated_value_eur"].quantile(0.9)
        st.metric("Vlera mediane", fmt_eur(median))
        st.caption("Të paktën gjysma e vlerave janë më të vogla ose të barabarta me këtë shumë.")
        st.metric("Kufiri i 90% të vlerave", fmt_eur(p90))
        st.caption("Rreth 90% e vlerave nuk e kalojnë këtë kufi.")
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
        "Renditja bazohet në vlerën e parashikuar të tenderëve të filtruar; nuk mat performancën e institucioneve."
    )

with st.expander("Shkarko të dhënat e filtruara"):
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
        "Skedari përfshin të gjithë tenderët e filtruar, edhe ata me vlera të munguara. Emrat teknikë të kolonave ruhen, që të dhënat të mund të përdoren në analiza të tjera."
    )
