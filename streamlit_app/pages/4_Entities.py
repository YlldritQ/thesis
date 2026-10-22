"""Entities page (Albanian) — authorities and documented supplier groupings."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st
from _bootstrap import (
    cached_dashboard_bundle,
    fmt_eur,
    page_header,
)
from _charts import (
    PALETTE,
    category_label,
    fmt_columns,
    fmt_number,
    lorenz_curve,
    method_label,
)
from _narrative import METRIC_HELP

from thesis.domain.features import (
    normalise_supplier_business_id,
)
from thesis.domain.features import (
    supplier_key as supplier_group_key,
)

st.set_page_config(
    page_title="Autoritetet dhe furnizuesit · Prokurimi në Kosovë", page_icon="🏢", layout="wide"
)

page_header(
    "🏢 Autoritetet dhe furnizuesit",
    "Krahasoni aktivitetin e institucioneve dhe shihni si ndahet vlera e vendimeve të dhënies mes furnizuesve.",
)

dashboard = cached_dashboard_bundle()
gold = dashboard["gold"]
awards = dashboard["awards"]
entities = dashboard["entities"].copy()
suppliers = dashboard["suppliers"].copy()


def _mode_or_none(values: pd.Series) -> str | None:
    clean = values.dropna().astype(str).str.strip()
    clean = clean[clean.ne("")]
    return clean.mode().iat[0] if not clean.empty else None


def _with_supplier_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["supplier_key"] = supplier_group_key(out)
    business_id = out["supplier_business_id"].map(normalise_supplier_business_id)
    names = out["supplier_name"].fillna("").astype(str).str.strip()
    party_ids = out.get("supplier_party_id", pd.Series(index=out.index, dtype=object))
    party_uids = out.get("supplier_uid", pd.Series(index=out.index, dtype=object))
    source_party = party_ids.fillna("").astype(str).str.strip()
    source_party = source_party.where(
        source_party.ne(""), party_uids.fillna("").astype(str).str.strip()
    )
    out["identity_source"] = "unidentified"
    out.loc[source_party.ne(""), "identity_source"] = "source_party_id_fallback"
    out.loc[names.ne(""), "identity_source"] = "name_fallback"
    out.loc[business_id.notna(), "identity_source"] = "business_id"
    out.loc[out["supplier_key"].isna(), "identity_source"] = "unidentified"
    return out


def _fallback_supplier_summary(award_rows: pd.DataFrame, tender_rows: pd.DataFrame) -> pd.DataFrame:
    """Compatibility view for a pre-migration gold artifact.

    Newly generated gold data already contains these columns. This branch
    keeps the page honest while an older local artifact awaits rebuilding.
    """
    keyed = _with_supplier_keys(award_rows)
    keyed["awarded_value_eur"] = pd.to_numeric(keyed["awarded_value_eur"], errors="coerce").fillna(
        0.0
    )
    total_value = float(keyed["awarded_value_eur"].sum())
    keyed = keyed.dropna(subset=["supplier_key"]).copy()
    competition_columns = ["ocid", "is_single_bidder"]
    if "bidder_data_observed" not in keyed:
        if "bidder_data_observed" in tender_rows:
            competition_columns.append("bidder_data_observed")
        else:
            # A legacy artifact encoded unknown counts as zero. Do not reuse
            # that field as observed competition; keep the derived rate blank.
            keyed["bidder_data_observed"] = False
    keyed = keyed.merge(
        tender_rows[competition_columns].drop_duplicates("ocid"), on="ocid", how="left"
    )
    keyed["single_bidder_observed"] = keyed["is_single_bidder"].where(keyed["bidder_data_observed"])
    grouped = keyed.groupby("supplier_key")
    out = grouped.agg(
        tenders_won=("ocid", "nunique"),
        award_rows=("ocid", "size"),
        total_awarded_eur=("awarded_value_eur", "sum"),
        median_awarded_eur=("awarded_value_eur", "median"),
        max_awarded_eur=("awarded_value_eur", "max"),
        first_award=("award_date", "min"),
        last_award=("award_date", "max"),
        distinct_procuring_entities=("procuring_entity_id", "nunique"),
        distinct_categories=("category", "nunique"),
        distinct_methods=("method", "nunique"),
        distinct_names=("supplier_name", "nunique"),
        primary_name=("supplier_name", _mode_or_none),
        supplier_business_id=("supplier_business_id", _mode_or_none),
        identity_source=("identity_source", _mode_or_none),
        single_bidder_win_pct=("single_bidder_observed", "mean"),
    ).reset_index()
    identified_value = float(out["total_awarded_eur"].sum())
    out["share_of_total_awarded_pct"] = out["total_awarded_eur"] / max(total_value, 1.0) * 100
    out["share_of_identified_value_pct"] = (
        out["total_awarded_eur"] / max(identified_value, 1.0) * 100
    )
    out["identity_value_coverage_pct"] = identified_value / max(total_value, 1.0) * 100
    out["single_bidder_win_pct"] *= 100
    return out.sort_values("total_awarded_eur", ascending=False)


awards_keyed = _with_supplier_keys(awards)
if "supplier_key" not in suppliers.columns:
    suppliers = _fallback_supplier_summary(awards, gold)
if "supplier_party_id" not in suppliers.columns:
    suppliers["supplier_party_id"] = pd.NA
if "distinct_source_identity_keys" not in suppliers.columns:
    suppliers["distinct_source_identity_keys"] = pd.NA

# A legacy entity artifact cannot support a defensible sensitivity comparison.
# Keep the fields unavailable until gold is rebuilt instead of relabelling the
# old blank-ID-collapsing HHI as the ID-or-name grouping measure.
for concentration_col in (
    "bidder_data_coverage_pct",
    "supplier_hhi_name_fallback",
    "supplier_hhi_source_party_fallback",
    "supplier_hhi_id_only",
    "supplier_identity_value_coverage_pct",
    "supplier_source_party_identity_value_coverage_pct",
    "supplier_business_id_value_coverage_pct",
):
    if concentration_col not in entities.columns:
        entities[concentration_col] = float("nan")

IDENTITY_LABELS = {
    "business_id": "Identifikuesi i biznesit",
    "name_fallback": "Emri i furnizuesit",
    "source_party_id_fallback": "Identifikuesi i palës në burim",
    "unidentified": "I paidentifikuar",
}
ENTITY_SORT_LABELS = {
    "total_estimated_eur": "Vlera e parashikuar",
    "tenders": "Numri i tenderëve",
    "single_bidder_pct": "Pjesa me një ofertues",
    "rule_score_avg": "Mesatarja e pikëve të rregullave",
}
SUPPLIER_SORT_LABELS = {
    "total_awarded_eur": "Vlera e vendimeve të dhënies",
    "tenders_won": "Tenderë me vendim në favor të furnizuesit",
    "distinct_procuring_entities": "Numri i autoriteteve kontraktuese",
    "single_bidder_win_pct": "Pjesa e vendimeve me një ofertues",
}


def _percent(value: float) -> str:
    return f"{value:.1f}%".replace(".", ",") if pd.notna(value) else "—"


def _name_labels(frame: pd.DataFrame, name: str, identity: str) -> pd.Series:
    """Keep equal display names distinct when the recorded identities differ."""
    names = frame[name].fillna("").astype(str).str.strip().replace("", "Pa emër të publikuar")
    duplicates = names.duplicated(keep=False)
    return names.where(~duplicates, names + " · " + frame[identity].astype(str))


def _value_bar(frame: pd.DataFrame, label: str, value: str, title: str, axis: str):
    view = frame.nlargest(10, value).sort_values(value).copy()
    view["short_name"] = view[label].str.slice(0, 58)
    # Use a unique positional axis so names that share a prefix never merge.
    view["row"] = range(len(view))
    is_eur = value.endswith("_eur")
    x_column = value
    if is_eur:
        x_column = "value_million_eur"
        view[x_column] = view[value] / 1e6
        axis = axis.replace("(€)", "(milionë €)")
    fig = px.bar(
        view,
        x=x_column,
        y="row",
        orientation="h",
        custom_data=[label, value],
        color_discrete_sequence=[PALETTE["primary"]],
    )
    fig.update_yaxes(tickvals=view["row"], ticktext=view["short_name"], title=None)
    fig.update_xaxes(title=axis, rangemode="tozero")
    if value == "rule_score_avg":
        value_hover = "%{x:.3f} pikë nga 1"
        fig.update_xaxes(tickformat=".2f")
    elif value.endswith("_pct"):
        value_hover = "%{x:.1f}%"
        fig.update_xaxes(ticksuffix="%")
    elif is_eur:
        value_hover = "%{customdata[1]:,.0f} €"
        fig.update_xaxes(tickformat=",~f")
    else:
        value_hover = "%{x:,.0f}"
    fig.update_traces(hovertemplate="%{customdata[0]}<br>" + value_hover + "<extra></extra>")
    fig.update_layout(separators=", ")
    fig.update_layout(
        title=title,
        height=max(280, 29 * len(view) + 95),
        margin={"l": 20, "r": 25, "t": 55, "b": 20},
        showlegend=False,
    )
    return fig


st.caption(
    "Kjo faqe përdor të gjithë periudhën e të dhënave. Përzgjedhjet e filtrave në faqet e tjera nuk zbatohen këtu."
)
entity_names = entities.set_index("procuring_entity_id")["name"]
entities["display_name"] = _name_labels(entities, "name", "procuring_entity_id")
suppliers["display_name"] = _name_labels(suppliers, "primary_name", "supplier_key")
coverage_values = suppliers["identity_value_coverage_pct"].dropna()
coverage = float(coverage_values.iloc[0]) if not coverage_values.empty else float("nan")
c1, c2, c3 = st.columns(3)
known_entity_ids = entities["procuring_entity_id"].notna() & entities["procuring_entity_id"].astype(
    "string"
).str.strip().ne("")
c1.metric(
    "Autoritete kontraktuese",
    fmt_number(entities.loc[known_entity_ids, "procuring_entity_id"].nunique()),
)
c2.metric(
    "Grupe furnizuesish",
    fmt_number(len(suppliers)),
    help="Grupohen sipas identifikuesit të biznesit; kur mungon, përdoret emri ose identifikuesi i palës. Numri nuk është numër i verifikuar i kompanive.",
)
c3.metric(
    "Vlerë me furnizues të identifikuar",
    _percent(coverage),
    help="Pjesa e vlerës së vendimeve që mund të lidhet me një grup furnizuesi sipas të dhënave në burim.",
)

missing_identity_tenders = entities.loc[~known_entity_ids, "tenders"].sum()
if missing_identity_tenders:
    st.caption(
        f"Tenderë pa identifikues të autoritetit: {fmt_number(missing_identity_tenders)}. Rreshtat pa identifikues nuk numërohen si autoritet më vete."
    )

tab_entity, tab_supplier = st.tabs(["Autoritetet kontraktuese", "Furnizuesit"])

with tab_entity:
    st.subheader("Cilat institucione kanë më shumë aktivitet?")
    sort_by = st.selectbox(
        "Krahaso autoritetet sipas",
        list(ENTITY_SORT_LABELS),
        format_func=lambda c: ENTITY_SORT_LABELS[c],
    )
    chart_entities = entities.copy()
    if sort_by == "single_bidder_pct":
        min_tenders = st.number_input(
            "Së paku sa tenderë për autoritet?",
            min_value=1,
            value=20,
            step=1,
            help="Një përqindje nga pak tenderë është më pak përfaqësuese.",
        )
        chart_entities = chart_entities[chart_entities["tenders"] >= min_tenders]
        st.caption(
            "Përqindja llogaritet vetëm ndër tenderët me numër të publikuar ofertuesish. Shihni edhe mbulimin e të dhënave në profil."
        )
    if chart_entities[sort_by].notna().any():
        axis = {
            "total_estimated_eur": "Vlera e parashikuar (€)",
            "tenders": "Numri i tenderëve",
            "single_bidder_pct": "Tenderë me një ofertues (%)",
            "rule_score_avg": "Mesatarja e pikëve (0–1)",
        }[sort_by]
        st.plotly_chart(
            _value_bar(
                chart_entities,
                "display_name",
                sort_by,
                "10 autoritetet me vlerat më të larta",
                axis,
            ),
            use_container_width=True,
        )
    else:
        st.info("Nuk ka të dhëna të mjaftueshme për këtë krahasim.")
    st.caption(
        "Renditja përshkruan të dhënat e publikuara. Vëllimi i lartë i prokurimit ose një sinjal statistikor nuk nënkupton shkelje."
    )

    st.divider()
    st.subheader("Profili i autoritetit kontraktues")
    eid = st.selectbox(
        "Zgjidh një autoritet",
        entities.loc[known_entity_ids].sort_values("name")["procuring_entity_id"].tolist(),
        format_func=lambda key: f"{entity_names.get(key, 'Pa emër')} · {key}",
    )
    if eid is not None:
        e = entities.set_index("procuring_entity_id").loc[eid]
        sub = gold[gold["procuring_entity_id"] == eid]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tenderë të publikuar", fmt_number(e["tenders"]))
        c2.metric(
            "Vlera e parashikuar",
            fmt_eur(e["total_estimated_eur"]),
            help=METRIC_HELP["estimated_value_eur"],
        )
        c3.metric(
            "Tenderë me një ofertues",
            _percent(e["single_bidder_pct"]),
            help=METRIC_HELP["single_bidder_pct"],
        )
        c4.metric("Me vendim dhënieje", fmt_number(e["awarded_tenders"]))
        st.caption(
            f"Numri i ofertuesve është i publikuar për {_percent(e['bidder_data_coverage_pct'])} të tenderëve të këtij autoriteti. Shenja «—» te treguesit tregon se vlera mungon."
        )

        yearly = (
            sub.dropna(subset=["year"])
            .groupby("year")
            .agg(
                tenders=("ocid", "size"),
                value=("estimated_value_eur", lambda values: values.sum(min_count=1)),
            )
            .reset_index()
        )
        yearly["year_label"] = yearly["year"].astype(int).astype(str)
        yearly["million_eur"] = yearly["value"] / 1e6
        c1, c2 = st.columns(2)
        for column, key, title, axis in (
            (c1, "tenders", "Sa tenderë publikohen çdo vit?", "Numri i tenderëve"),
            (
                c2,
                "million_eur",
                "Sa është vlera e parashikuar çdo vit?",
                "Vlera e parashikuar (milionë €)",
            ),
        ):
            with column:
                fig = px.bar(
                    yearly, x="year_label", y=key, color_discrete_sequence=[PALETTE["primary"]]
                )
                fig.update_layout(
                    title=title,
                    xaxis_title="Viti i publikimit",
                    yaxis_title=axis,
                    height=320,
                    separators=", ",
                    margin={"l": 20, "r": 20, "t": 60, "b": 20},
                    showlegend=False,
                )
                fig.update_xaxes(type="category")
                st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Vitet me të dhëna të pjesshme mund të kenë më pak tenderë; shihni mbulimin kohor në faqen Përmbledhja."
        )

        all_entity_awards = awards_keyed[awards_keyed["procuring_entity_id"] == eid]
        entity_awards = all_entity_awards[all_entity_awards["supplier_key"].notna()]
        if entity_awards.empty:
            st.info("Nuk ka vendime dhënieje me furnizues të identifikueshëm për këtë autoritet.")
        else:
            top_suppliers = (
                entity_awards.groupby("supplier_key")
                .agg(
                    awarded_value_eur=("awarded_value_eur", "sum"),
                    primary_name=("supplier_name", _mode_or_none),
                )
                .reset_index()
            )
            top_suppliers["supplier_label"] = _name_labels(
                top_suppliers, "primary_name", "supplier_key"
            )
            st.plotly_chart(
                _value_bar(
                    top_suppliers,
                    "supplier_label",
                    "awarded_value_eur",
                    "Cilët furnizues kanë vlerën më të lartë në vendime?",
                    "Vlera e vendimeve të dhënies (€)",
                ),
                use_container_width=True,
            )
            identified_total = entity_awards["awarded_value_eur"].sum()
            total_value = all_entity_awards["awarded_value_eur"].sum()
            top_ten = top_suppliers.nlargest(10, "awarded_value_eur")["awarded_value_eur"].sum()
            share = top_ten / total_value * 100 if total_value > 0 else float("nan")
            identity_coverage = (
                identified_total / total_value * 100 if total_value > 0 else float("nan")
            )
            st.caption(
                f"10 furnizuesit kryesorë (ose më pak, kur ka më pak) mbulojnë {_percent(share)} të vlerës së vendimeve të këtij autoriteti. Gjithsej, {_percent(identity_coverage)} e vlerës mund të lidhet me një furnizues."
            )

        with st.expander("Si matet përqendrimi te furnizuesit? (HHI)"):
            st.write(METRIC_HELP["supplier_hhi"])
            st.caption(
                "Rezultati ndryshon kur mungojnë identifikuesit. Tri llogaritjet më poshtë tregojnë ndikimin e mënyrës së grupimit. Ky grupim nuk është zgjidhje e verifikuar e identitetit të subjekteve ose matje e një tregu kombëtar."
            )
            scenarios = pd.DataFrame(
                [
                    {
                        "Grupimi i furnizuesve": "ID biznesi → emër → ID e palës",
                        "HHI (0–10 000)": e["supplier_hhi_name_fallback"],
                        "Vlera e mbuluar (%)": e["supplier_identity_value_coverage_pct"],
                    },
                    {
                        "Grupimi i furnizuesve": "ID biznesi → ID e palës → emër",
                        "HHI (0–10 000)": e["supplier_hhi_source_party_fallback"],
                        "Vlera e mbuluar (%)": e[
                            "supplier_source_party_identity_value_coverage_pct"
                        ],
                    },
                    {
                        "Grupimi i furnizuesve": "Vetëm ID biznesi",
                        "HHI (0–10 000)": e["supplier_hhi_id_only"],
                        "Vlera e mbuluar (%)": e["supplier_business_id_value_coverage_pct"],
                    },
                ]
            )
            st.dataframe(
                fmt_columns(scenarios, {"HHI (0–10 000)": 0, "Vlera e mbuluar (%)": 1}),
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "ID-ja e palës identifikon një palë në publikim; nuk është identifikues juridik i verifikuar. Edhe emrat e njëjtë mund t'u përkasin subjekteve të ndryshme."
            )

    with st.expander("Tabela krahasuese e të gjitha autoriteteve"):
        view = entities.sort_values(sort_by, ascending=False).copy()
        view.loc[view["awarded_tenders"].fillna(0).eq(0), "total_awarded_eur"] = float("nan")
        columns = {
            "name": "Autoriteti kontraktues",
            "tenders": "Tenderë",
            "total_estimated_eur": "Vlera e parashikuar (€)",
            "total_awarded_eur": "Vendimet e dhënies (€)",
            "single_bidder_pct": "Me një ofertues (%)",
            "bidder_data_coverage_pct": "Numër i publikuar ofertuesish (%)",
            "procuring_entity_id": "Identifikuesi",
        }
        st.dataframe(
            view[list(columns)].rename(columns=columns), hide_index=True, use_container_width=True
        )
    with st.expander("Të gjithë treguesit teknikë të autoriteteve"):
        st.caption(
            "Fushat origjinale ruhen për analizë dhe verifikim. Shënimi HHI këtu i përket vlerës së vendimeve, jo një tregu të përkufizuar."
        )
        st.dataframe(
            entities.drop(columns="display_name"), hide_index=True, use_container_width=True
        )

with tab_supplier:
    st.subheader("Cilët furnizues shfaqen në vendimet e dhënies?")
    st.caption(
        "Furnizues mund të jetë një operator ekonomik ose grup operatorësh. Grupet formohen sipas identifikuesit të biznesit, pastaj emrit dhe, kur të dy mungojnë, identifikuesit të palës në burim. Kjo nuk është verifikim juridik i identitetit."
    )
    sort_by = st.selectbox(
        "Krahaso furnizuesit sipas",
        list(SUPPLIER_SORT_LABELS),
        format_func=lambda c: SUPPLIER_SORT_LABELS[c],
        key="supplier_sort",
    )
    chart_suppliers = suppliers.copy()
    if sort_by == "single_bidder_win_pct":
        minimum = st.number_input(
            "Së paku sa tenderë për furnizues?", min_value=1, value=10, step=1
        )
        chart_suppliers = chart_suppliers[chart_suppliers["tenders_won"] >= minimum]
        st.caption(
            "Kjo përqindje llogaritet mbi rreshtat e vendimeve me të dhëna të njohura për ofertuesit. Një tender me disa vendime mund të numërohet disa herë."
        )
    if chart_suppliers[sort_by].notna().any():
        axis = {
            "total_awarded_eur": "Vlera e vendimeve të dhënies (€)",
            "tenders_won": "Numri i tenderëve",
            "distinct_procuring_entities": "Numri i autoriteteve",
            "single_bidder_win_pct": "Vendime me një ofertues (%)",
        }[sort_by]
        st.plotly_chart(
            _value_bar(
                chart_suppliers,
                "display_name",
                sort_by,
                "10 furnizuesit me vlerat më të larta",
                axis,
            ),
            use_container_width=True,
        )
    else:
        st.info("Nuk ka të dhëna të mjaftueshme për këtë krahasim.")

    st.divider()
    st.subheader("Profili i furnizuesit")
    supplier_lookup = suppliers.set_index("supplier_key")

    def _supplier_label(key: str) -> str:
        row = supplier_lookup.loc[key]
        name = row.get("primary_name")
        name = str(name) if pd.notna(name) and str(name).strip() else "Pa emër të publikuar"
        return f"{name} · {key}"

    selected_key = st.selectbox(
        "Zgjidh një furnizues", suppliers["supplier_key"].tolist(), format_func=_supplier_label
    )
    if selected_key is not None:
        supplier = supplier_lookup.loc[selected_key]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Tenderë me vendim dhënieje",
            fmt_number(supplier["tenders_won"]),
            help="Numri i tenderëve të ndryshëm ku ky furnizues shfaqet në një vendim dhënieje.",
        )
        c2.metric(
            "Vlera e vendimeve",
            fmt_eur(supplier["total_awarded_eur"]),
            help=METRIC_HELP["total_awarded_eur"],
        )
        c3.metric("Autoritete kontraktuese", fmt_number(supplier["distinct_procuring_entities"]))
        c4.metric(
            "Vendime me një ofertues",
            _percent(supplier["single_bidder_win_pct"]),
            help="Llogaritet mbi rreshtat e vendimeve ku numri i ofertuesve është i njohur. Një tender me disa vendime mund të numërohet disa herë.",
        )
        identity_label = IDENTITY_LABELS.get(
            supplier["identity_source"], "Identitet i papërcaktuar"
        )
        st.caption(
            f"Grupuar sipas: {identity_label.lower()}. Identifikuesi i grupit: {selected_key}."
        )

        supplier_awards = awards_keyed[awards_keyed["supplier_key"] == selected_key]
        if supplier_awards.empty:
            st.info("Nuk ka vendime të regjistruara për këtë grup furnizuesi.")
        else:
            buyers = (
                supplier_awards.groupby("procuring_entity_id")
                .agg(
                    awarded_value_eur=("awarded_value_eur", "sum"),
                    name=("procuring_entity_name", _mode_or_none),
                )
                .reset_index()
            )
            buyers["buyer_label"] = _name_labels(buyers, "name", "procuring_entity_id")
            st.plotly_chart(
                _value_bar(
                    buyers,
                    "buyer_label",
                    "awarded_value_eur",
                    "Nga cilat autoritete vjen vlera e vendimeve?",
                    "Vlera e vendimeve të dhënies (€)",
                ),
                use_container_width=True,
            )
            st.caption(
                "Shfaqen deri në 10 autoritete. Vlera lidhet me vendimet e regjistruara dhe nuk dëshmon pagesa të kryera."
            )
            award_records = (
                supplier_awards[
                    [
                        "ocid",
                        "award_date",
                        "awarded_value_eur",
                        "procuring_entity_name",
                        "category",
                        "method",
                    ]
                ]
                .sort_values("award_date", ascending=False)
                .head(200)
                .copy()
            )
            award_records["category"] = award_records["category"].map(category_label)
            award_records["method"] = award_records["method"].map(method_label)
            st.markdown("**Vendimet më të fundit të regjistruara**")
            st.dataframe(
                award_records,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "ocid": st.column_config.TextColumn("Identifikuesi i tenderit (OCID)"),
                    "award_date": st.column_config.DateColumn(
                        "Data e vendimit", format="DD.MM.YYYY"
                    ),
                    "awarded_value_eur": st.column_config.NumberColumn(
                        "Vlera e vendimit (€)", format="localized"
                    ),
                    "procuring_entity_name": st.column_config.TextColumn("Autoriteti kontraktues"),
                    "category": st.column_config.TextColumn("Kategoria"),
                    "method": st.column_config.TextColumn("Metoda në burim"),
                },
            )
            if len(supplier_awards) > 200:
                st.caption(
                    f"Shfaqen 200 nga {fmt_number(len(supplier_awards))} vendime të regjistruara."
                )

    with st.expander("Sa e përqendruar është vlera mes furnizuesve?"):
        positive = suppliers.loc[suppliers["total_awarded_eur"] > 0, "total_awarded_eur"]
        if positive.empty:
            st.info("Nuk ka vlera pozitive për këtë krahasim.")
        else:
            st.plotly_chart(
                lorenz_curve(positive, "furnizuesit me vlerë të regjistruar"),
                use_container_width=True,
            )
            st.caption(
                "Furnizuesit renditen nga vlera më e ulët te vlera më e lartë. Sa më larg vijës së barazisë të jetë kurba, aq më shumë vlerë përqendrohet te pak furnizues. Kjo përshkruan vetëm të dhënat e analizuara; nuk mat pjesë tregu."
            )

    with st.expander("Tabela krahasuese e të gjithë furnizuesve"):
        columns = {
            "primary_name": "Furnizuesi",
            "tenders_won": "Tenderë me vendim",
            "total_awarded_eur": "Vendimet e dhënies (€)",
            "distinct_procuring_entities": "Autoritete",
            "share_of_total_awarded_pct": "Pjesa e vlerës së përgjithshme (%)",
            "single_bidder_win_pct": "Vendime me një ofertues (%)",
            "supplier_business_id": "Identifikuesi i biznesit",
        }
        st.dataframe(
            suppliers.sort_values(sort_by, ascending=False)[list(columns)].rename(columns=columns),
            hide_index=True,
            use_container_width=True,
        )
    with st.expander("Të gjithë treguesit teknikë të furnizuesve"):
        st.caption(
            "Fushat origjinale, përfshirë identifikuesit dhe mënyrën e grupimit, ruhen për verifikim."
        )
        st.dataframe(
            suppliers.drop(columns="display_name"), hide_index=True, use_container_width=True
        )
