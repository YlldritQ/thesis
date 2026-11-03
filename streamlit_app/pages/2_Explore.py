"""Search and understand individual procurement records."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from _bootstrap import cached_dashboard_bundle, fmt_eur, page_header, sidebar_filters
from _charts import category_label, fmt_number, method_label, procedure_label
from _narrative import METRIC_HELP, contract_severity, explain_flags, plain_summary

from thesis.anomaly import RULES

RULE_BY_CODE = {rule.code: rule for rule in RULES}


def _has_recorded_award(row: pd.Series | dict) -> bool:
    was_awarded = row.get("was_awarded")
    if pd.notna(was_awarded):
        return bool(was_awarded)
    n_awards = row.get("n_awards", 0)
    return bool(pd.notna(n_awards) and float(n_awards) >= 1)


def _flag_kind(code: str) -> str:
    rule = RULE_BY_CODE.get(code)
    if rule is None:
        return "sinjal për verifikim"
    return "ndikon në pikët e rregullave" if rule.score_enabled else "kontroll pa pikë shtesë"


st.set_page_config(page_title="Kërko tenderë · Prokurimi në Kosovë", page_icon="🔍", layout="wide")
page_header(
    "🔍 Kërko tenderë",
    "Gjeni një tender, shihni vlerat dhe ofertuesit e regjistruar, pastaj shqyrtoni sinjalet që kërkojnë verifikim.",
)

dashboard = cached_dashboard_bundle()
gold = dashboard["gold"]
awards = dashboard["awards"]
filtered = sidebar_filters(gold)

q = st.text_input(
    "Kërko sipas titullit, autoritetit ose furnizuesit",
    placeholder="P.sh. furnizim me pajisje ose emri i një komune",
    help="Mund të përdorni edhe identifikuesin e tenderit (OCID), numrin e tenderit ose ID-në e furnizuesit.",
).strip()

if q:
    mask = pd.Series(False, index=filtered.index)
    for field in ("title", "ocid", "procuring_entity_name", "tender_id"):
        mask |= filtered[field].astype("string").str.contains(q, case=False, regex=False, na=False)
    supplier_mask = pd.Series(False, index=awards.index)
    for field in (
        "supplier_name",
        "supplier_legal_name",
        "supplier_business_id",
        "supplier_party_id",
    ):
        supplier_mask |= (
            awards[field].astype("string").str.contains(q, case=False, regex=False, na=False)
        )
    mask |= filtered["ocid"].isin(awards.loc[supplier_mask, "ocid"])
    result = filtered.loc[mask].copy()
else:
    result = filtered.copy()

SORT_LABELS = {
    "Më të rinjtë": ("release_date", False),
    "Më të vjetrit": ("release_date", True),
    "Vlera më e lartë": ("estimated_value_eur", False),
    "Vlera më e ulët": ("estimated_value_eur", True),
    "Më shumë pikë nga sinjalet": ("rule_score", False),
    "Pikët e kombinuara, nga më të lartat": ("ensemble_score", False),
    "Isolation Forest, nga më të lartat": ("iso_score", False),
}
sort_by = st.selectbox("Rendit rezultatet", list(SORT_LABELS))
sort_col, ascending = SORT_LABELS[sort_by]
result = result.sort_values(sort_col, ascending=ascending)

c1, c2, c3 = st.columns(3)
c1.metric("Tenderë të gjetur", fmt_number(len(result)))
c2.metric("Vlera e parashikuar", fmt_eur(result["estimated_value_eur"].sum(min_count=1)))
c3.metric("Autoritete kontraktuese", fmt_number(result["procuring_entity_id"].nunique()))

if result.empty:
    st.info(
        "Nuk u gjet asnjë tender. Provoni një fjalë më të shkurtër ose zgjeroni filtrat në anën e majtë."
    )
else:
    technical_columns = st.checkbox("Shfaq edhe identifikuesit dhe pikët teknike", value=False)
    display_cols = [
        "title",
        "procuring_entity_name",
        "release_date",
        "estimated_value_eur",
        "total_awarded_eur",
        "num_bidders",
        "category",
        "method",
    ]
    if technical_columns:
        display_cols += ["ocid", "n_awards", "rule_score", "iso_score", "ensemble_score"]
    table = result[[*display_cols, "was_awarded"]].head(500).copy()
    table["release_date"] = pd.to_datetime(table["release_date"]).dt.date
    has_award = table.apply(_has_recorded_award, axis=1)
    table.loc[~has_award, "total_awarded_eur"] = float("nan")
    table["category"] = table["category"].map(category_label)
    table["method"] = table["method"].map(method_label)
    table = table.drop(columns="was_awarded")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        height=350,
        column_config={
            "title": st.column_config.TextColumn("Titulli i tenderit", width="large"),
            "ocid": st.column_config.TextColumn("Identifikuesi (OCID)"),
            "release_date": st.column_config.DateColumn("Data e publikimit", format="DD.MM.YYYY"),
            "procuring_entity_name": st.column_config.TextColumn("Autoriteti kontraktues"),
            "category": st.column_config.TextColumn("Kategoria"),
            "method": st.column_config.TextColumn("Metoda në burim"),
            "estimated_value_eur": st.column_config.NumberColumn(
                "Vlera e parashikuar (€)",
                format="localized",
                help=METRIC_HELP["estimated_value_eur"],
            ),
            "total_awarded_eur": st.column_config.NumberColumn(
                "Vendimet e dhënies (€)", format="localized", help=METRIC_HELP["total_awarded_eur"]
            ),
            "num_bidders": st.column_config.NumberColumn(
                "Ofertues", help=METRIC_HELP["num_bidders"]
            ),
            "n_awards": st.column_config.NumberColumn(
                "Vendime / rreshta dhënieje", help=METRIC_HELP["n_awards"]
            ),
            "rule_score": st.column_config.ProgressColumn(
                "Pikët e rregullave", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "iso_score": st.column_config.ProgressColumn(
                "Isolation Forest", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "ensemble_score": st.column_config.ProgressColumn(
                "Pikët e kombinuara",
                min_value=0.0,
                max_value=1.0,
                format="%.2f",
                help=METRIC_HELP["ensemble_score"],
            ),
        },
    )
    st.caption(
        "— tregon vlerë të munguar ose mungesë vendimi të regjistruar. Nuk do të thotë zero. Vlerat e vendimeve nuk dëshmojnë pagesa të kryera."
    )
    if len(result) > 500:
        st.caption(
            f"Tabela shfaq 500 nga {fmt_number(len(result))} rezultate. Përdorni kërkimin ose filtrat për ta ngushtuar listën."
        )

st.divider()
st.subheader("Shqyrto një tender")
lookup = gold.set_index("ocid")


def _tender_label(value: str) -> str:
    row = lookup.loc[value]
    return f"{row['title']} · {row['procuring_entity_name']} · {value}"


selected = st.selectbox(
    "Zgjidh nga rezultatet",
    result["ocid"].head(500).tolist(),
    format_func=_tender_label,
    disabled=result.empty,
    placeholder="Nuk ka rezultate" if result.empty else "Zgjidh një tender",
)
with st.expander("Gjej drejtpërdrejt me identifikuesin OCID"):
    manual = st.text_input("Identifikuesi OCID", placeholder="ocds-…").strip()
    st.caption("Ky kërkim kontrollon të gjithë grupin e të dhënave, pavarësisht filtrave.")
ocid = manual or selected

if ocid:
    rec = gold[gold["ocid"] == ocid]
    if rec.empty:
        st.warning("Ky identifikues OCID nuk u gjet. Kontrolloni nëse e keni kopjuar të plotë.")
    else:
        r = rec.iloc[0]
        rd = r.to_dict()
        sev = contract_severity(rd)
        st.subheader(str(r["title"]))
        st.markdown(f"{sev['emoji']} **{sev['label']}**")
        st.write(plain_summary(rd))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Vlera e parashikuar",
            fmt_eur(r["estimated_value_eur"]),
            help=METRIC_HELP["estimated_value_eur"],
        )
        c2.metric(
            "Vendimet e dhënies",
            fmt_eur(r["total_awarded_eur"]) if _has_recorded_award(r) else "—",
            help=METRIC_HELP["total_awarded_eur"],
        )
        c3.metric(
            "Ofertues të regjistruar",
            fmt_number(r["num_bidders"]) if pd.notna(r["num_bidders"]) else "—",
            help=METRIC_HELP["num_bidders"],
        )
        days = r["days_tender_open"]
        duration = (
            "Për verifikim"
            if pd.notna(days) and days < 0
            else (f"{fmt_number(days)} ditë" if pd.notna(days) else "—")
        )
        c4.metric("Periudha për oferta", duration, help=METRIC_HELP["days_tender_open"])
        if pd.notna(days) and days < 0:
            st.caption(
                f"Datat në burim nuk përputhen: afati për oferta është {fmt_number(abs(days))} ditë para datës së fillimit. Periudha kërkon verifikim."
            )
        st.caption(
            f"{category_label(r['category'])} · {procedure_label(r['procedure_subtype'])} · OCID: {ocid}"
        )

        st.markdown("#### Çfarë kërkon verifikim?")
        flags = explain_flags(rd)
        if flags:
            for flag in flags:
                st.markdown(f"**{flag['title']}**  \n{flag['detail']}")
                st.caption(_flag_kind(flag["code"]))
        else:
            st.info(
                "Nuk është aktivizuar asnjë sinjal nga rregullat. Kjo nuk vërteton mungesën e parregullsive."
            )

        st.markdown("#### Furnizuesit në vendimet e dhënies")
        a = awards[awards["ocid"] == ocid].copy()
        if a.empty:
            st.info("Nuk ka vendim dhënieje të regjistruar për këtë tender.")
        else:
            names = a["supplier_name"].fillna("").astype(str).str.strip()
            legal = a["supplier_legal_name"].fillna("").astype(str).str.strip()
            a["supplier_display"] = names.where(names.ne(""), legal).replace(
                "", "Furnizues i paidentifikuar"
            )
            st.dataframe(
                a[
                    [
                        "supplier_display",
                        "award_date",
                        "awarded_value_eur",
                        "supplier_business_id",
                        "award_id",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "supplier_display": st.column_config.TextColumn("Furnizuesi"),
                    "award_date": st.column_config.DateColumn(
                        "Data e vendimit", format="DD.MM.YYYY"
                    ),
                    "awarded_value_eur": st.column_config.NumberColumn(
                        "Vlera e vendimit (€)", format="localized"
                    ),
                    "supplier_business_id": st.column_config.TextColumn("Identifikuesi i biznesit"),
                    "award_id": st.column_config.TextColumn("Identifikuesi i vendimit"),
                },
            )
            st.caption(
                "Furnizuesi është operatori ekonomik ose grupi i operatorëve i shënuar në burim. Një vendim nuk dëshmon kontratë të nënshkruar, të ekzekutuar ose të paguar."
            )

        with st.expander("Krahasimi i vlerave dhe pikët teknike"):
            st.write(f"Dallimi ndërmjet datave në burim: {fmt_number(days)} ditë.")
            ratio = r["awarded_value_ratio"]
            st.metric(
                "Vendimet kundrejt parashikimit",
                f"{fmt_number(ratio * 100, 1)}%" if pd.notna(ratio) else "—",
                help=METRIC_HELP["awarded_value_ratio"],
            )
            st.caption(METRIC_HELP["awarded_value_ratio"])
            c1, c2, c3 = st.columns(3)
            for column, key, label in (
                (c1, "rule_score", "Pikët e rregullave"),
                (c2, "iso_score", "Isolation Forest"),
                (c3, "ensemble_score", "Pikët e kombinuara"),
            ):
                column.metric(label, fmt_number(r[key], 2))
            st.caption(METRIC_HELP["ensemble_score"])
            st.write(f"Numri i tenderit në burim: {r['tender_id']}")
            if st.button("Shpjego pikët e këtij tenderi →", use_container_width=True):
                st.session_state["review_ocid"] = str(ocid)
                st.switch_page(Path(__file__).with_name("3_Anomalies.py"))
