"""Anomalitë (shqip) — shpjegim qytetar në krye, detaje teknike të palosura."""

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
    show_caveat,
    sidebar_filters,
)
from _charts import (
    PALETTE,
    anomaly_score_hist,
    category_label,
    ensemble_contribution_bar,
    fmt_number,
    method_label,
    shap_waterfall,
)
from _narrative import (
    DATA_LIMITATION_BIDS,
    FLAG_NARRATIVE,
    METRIC_HELP,
    contract_severity,
    explain_flags,
    plain_summary,
)

from thesis.anomaly import (
    RULES,
    compose_hybrid_ensemble,
    explain_context_score,
    explain_rule_score,
    feature_deviation_profile,
    rule_descriptions,
)
from thesis.anomaly.detectors import FAMILY_LABELS_SQ
from thesis.anomaly.ensemble import validate_ensemble_definition
from thesis.domain.features import ML_FEATURES

st.set_page_config(page_title="Sinjalet për shqyrtim · OCDS Kosova", page_icon="🚨", layout="wide")

page_header(
    "🔎 Sinjalet për shqyrtim",
    "Shiko cilët tenderë kërkojnë verifikim dhe kupto arsyen. "
    "Sinjalet ndihmojnë në përzgjedhjen e rasteve; nuk provojnë shkelje.",
    caveat=False,
)
show_caveat()

dashboard = cached_dashboard_bundle(include_shap=True, include_model_metadata=True)
gold = dashboard["gold"]
awards = dashboard["awards"]
shap_df = dashboard["shap"]
feature_metadata = dashboard["feature_metadata"]
ensemble_definition = feature_metadata.get("ensemble_explanation")
if not isinstance(ensemble_definition, dict):
    raise RuntimeError("Mungon kontrata e shpjegimit të ansamblit në gjeneratën ML.")
ensemble_families = ensemble_definition.get("detector_families")
if not isinstance(ensemble_families, list):
    raise RuntimeError("Familjet e ansamblit mungojnë në kontratën XAI.")
agreement_quantile = float(ensemble_definition["flag_quantile"])
minimum_model_agreement = int(ensemble_definition["minimum_models_agreeing"])
ensemble_composition = compose_hybrid_ensemble(
    gold,
    ensemble_families,
    flag_quantile=agreement_quantile,
    minimum_models_agreeing=minimum_model_agreement,
)
validate_ensemble_definition(ensemble_definition, ensemble_composition)
for rank_column in ensemble_composition.detector_rank_columns:
    if rank_column not in gold or not gold[rank_column].equals(
        ensemble_composition.detector_ranks[rank_column]
    ):
        raise RuntimeError(f"Komponenti XAI nuk përputhet me artefaktin e publikuar: {rank_column}")

filtered = sidebar_filters(gold)

RULE_BY_CODE = {rule.code: rule for rule in RULES}


def _has_recorded_award(row: pd.Series | dict) -> bool:
    """Return whether the snapshot contains at least one recorded award decision."""
    was_awarded = row.get("was_awarded")
    if pd.notna(was_awarded):
        return bool(was_awarded)
    n_awards = row.get("n_awards", 0)
    return bool(pd.notna(n_awards) and float(n_awards) >= 1)


def _flag_kind(code: str) -> str:
    rule = RULE_BY_CODE.get(code)
    if rule is None:
        return "sinjal"
    if rule.score_enabled:
        return "Sinjal për shqyrtim · ndikon në pikët e rregullave"
    kind = "cilësinë e të dhënave" if rule.signal_type == "data_quality" else "ecurinë e procedurës"
    return f"Kontroll për {kind} · nuk shton pikë"


score_rules = [rule.code for rule in RULES if rule.score_enabled]
diagnostic_rules = [rule.code for rule in RULES if not rule.score_enabled]
with_signal = filtered[score_rules].fillna(False).any(axis=1)
with_diagnostic = filtered[diagnostic_rules].fillna(False).any(axis=1)
c1, c2, c3 = st.columns(3)
c1.metric("Tenderë në përzgjedhje", fmt_number(len(filtered)))
c2.metric("Me sinjal për shqyrtim", fmt_number(int(with_signal.sum())))
c3.metric("Me të dhëna për verifikim", fmt_number(int(with_diagnostic.sum())))
st.caption(
    "Një tender mund të jetë në të dy grupet. Filtrat kufizojnë pamjen; pikët mbeten të llogaritura kundrejt të gjithë grupit të të dhënave."
)

if filtered.empty:
    st.info("Nuk ka tenderë për filtrat e zgjedhur. Zgjeroni përzgjedhjen në anën e majtë.")
else:
    signal_counts = pd.DataFrame(
        [
            {"Sinjali": FLAG_NARRATIVE[rule.code][0], "Tenderë": int(filtered[rule.code].sum())}
            for rule in RULES
            if rule.score_enabled
        ]
    ).sort_values("Tenderë")
    signal_counts = signal_counts[signal_counts["Tenderë"] > 0]
    if signal_counts.empty:
        st.success("Asnjë tender në përzgjedhje nuk ka sinjal që shton pikë për shqyrtim.")
    else:
        fig = px.bar(
            signal_counts,
            x="Tenderë",
            y="Sinjali",
            orientation="h",
            text="Tenderë",
            color_discrete_sequence=[PALETTE["primary"]],
        )
        fig.update_layout(
            title="Cilat sinjale shfaqen më shpesh?",
            height=280,
            yaxis_title=None,
            xaxis_title="Numri i tenderëve",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
        )
        fig.update_traces(hovertemplate="%{y}<br>%{x:,.0f} tenderë<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Shfaqen sinjalet që ndikojnë në pikët e rregullave. I njëjti tender mund të aktivizojë disa sinjale, ndaj kolonat nuk mblidhen në një total."
        )

# =====================================================================
#  PJESA 1 — PËR QYTETARIN: shqyrto një tender konkret
# =====================================================================
st.subheader("Shqyrto një tender")
st.caption(
    "Zgjidh nga 300 tenderët e parë sipas pikëve të kombinuara ose vendos një OCID. "
    "Pikët janë mjet për renditje, jo probabilitet shkeljeje."
)

# renditja për përzgjedhësin: më të shenjuarit në krye
ranked = filtered.sort_values("ensemble_score", ascending=False)
top_choices = ranked.head(300)


def _label(ocid: str) -> str:
    row = gold.loc[gold["ocid"] == ocid].iloc[0]
    sev = contract_severity(row.to_dict())
    title = (row.get("title") or "")[:60]
    ent = (row.get("procuring_entity_name") or "")[:35]
    return f"{sev['emoji']} {ent} — {title}"


c_sel, c_search = st.columns([3, 2])
with c_sel:
    chosen = st.selectbox(
        "Zgjidh një tender për shqyrtim",
        top_choices["ocid"].tolist(),
        format_func=_label,
        disabled=top_choices.empty,
        placeholder="Nuk ka tenderë në përzgjedhje" if top_choices.empty else "Zgjidh një tender",
    )
with c_search:
    manual = st.text_input("Ose kërko me identifikuesin OCID", value="").strip()

ocid = manual or chosen
if manual and not gold["ocid"].eq(manual).any():
    st.warning("Ky identifikues OCID nuk u gjet. Kontrolloni nëse e keni kopjuar të plotë.")
elif manual and not filtered["ocid"].eq(manual).any():
    st.info(
        "Tenderi i kërkuar është jashtë filtrave të zgjedhur; detajet më poshtë i përkasin OCID-it të vendosur."
    )

if ocid and (gold["ocid"] == ocid).any():
    selected_row = gold.loc[gold["ocid"] == ocid].iloc[0]
    selected_index = selected_row.name
    r = selected_row.to_dict()
    sev = contract_severity(r)

    st.subheader(str(r.get("title") or "Tender pa titull"))
    st.markdown(f"{sev['emoji']} **{sev['label']}**")
    st.write(plain_summary(r))

    # ---- vlerat kryesore, secila e shpjeguar ----
    st.markdown("#### Shifrat kryesore")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Vlera e parashikuar",
        fmt_eur(r.get("estimated_value_eur")),
        help=METRIC_HELP["estimated_value_eur"],
    )
    c2.metric(
        "Vendimet e dhënies",
        (fmt_eur(r.get("total_awarded_eur")) if _has_recorded_award(r) else "—"),
        help=METRIC_HELP["total_awarded_eur"],
    )
    ratio = r.get("awarded_value_ratio")
    days = r.get("days_tender_open")
    duration = (
        "Për verifikim"
        if pd.notna(days) and days < 0
        else (f"{fmt_number(days)} ditë" if pd.notna(days) else "—")
    )
    c3.metric("Periudha për oferta", duration, help=METRIC_HELP["days_tender_open"])
    if pd.notna(days) and days < 0:
        st.caption(
            f"Datat në burim nuk përputhen: afati për oferta është {fmt_number(abs(days))} ditë para datës së fillimit. Periudha kërkon verifikim."
        )
    bidder_count = r.get("num_bidders")
    c4.metric(
        "Ofertues të regjistruar",
        f"{int(bidder_count)}" if pd.notna(bidder_count) else "—",
        help=METRIC_HELP["num_bidders"],
    )

    # ---- pse u shenjua: flamujt si karta ----
    st.markdown("#### Çfarë kërkon verifikim?")
    flags = explain_flags(r)
    rule_arithmetic = explain_rule_score(r, published_score=float(r["rule_score"]))
    if flags:
        for flag in flags:
            st.markdown(f"**{flag['title']}**  \n{flag['detail']}")
            st.caption(_flag_kind(flag["code"]))
    else:
        st.info(
            "Nuk është aktivizuar asnjë sinjal nga rregullat. Tenderi mund të dalë lart në renditje "
            "për shkak të dallimeve statistikore. Kjo nuk vërteton shkelje ose mungesë shkeljesh."
        )
    # ---- kush e fitoi ----
    a = awards[awards["ocid"] == ocid]
    if not a.empty:
        st.markdown("#### Furnizuesit në vendimet e dhënies")
        supplier_display = a["supplier_name"].fillna("").astype(str).str.strip()
        legal = a["supplier_legal_name"].fillna("").astype(str).str.strip()
        party = a["supplier_party_id"].fillna("").astype(str).str.strip()
        supplier_display = supplier_display.where(supplier_display.ne(""), legal)
        supplier_display = supplier_display.where(
            supplier_display.ne(""), "Palë burimore " + party
        ).replace("Palë burimore ", "E paidentifikuar")
        winners = (
            a.assign(supplier_display=supplier_display)
            .groupby("supplier_display")["awarded_value_eur"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        for _, w in winners.head(5).iterrows():
            st.markdown(f"- **{w['supplier_display']}** — {fmt_eur(w['awarded_value_eur'])}")
        if len(winners) > 5:
            st.caption(
                f"Shfaqen 5 nga {fmt_number(len(winners))} furnizues të regjistruar për këtë tender."
            )
        st.caption(
            "Vlerat në vendime nuk dëshmojnë se kontratat janë nënshkruar ose se pagesat janë kryer."
        )
    else:
        st.markdown("#### Furnizuesit në vendimet e dhënies")
        st.markdown("_Nuk ka vendim dhënieje të regjistruar në të dhënat e analizuara._")

    # ---- shënim për kufizimin e të dhënave ----
    if pd.notna(ratio) and ratio > 1.0:
        st.warning("💡 " + DATA_LIMITATION_BIDS)

    with st.expander("Si llogariten pikët e kombinuara?"):
        # ---- shpjegimi ekzakt i rezultatit real të ansamblit ----
        st.markdown("#### Pse mori këtë pikë ansambli?")
        component_explanation = ensemble_composition.explain_record(
            selected_index,
            published_score=float(r["ensemble_score"]),
        )
        component_labels = {
            "rule_score": "Indikatorët e rregullave",
            "context_score": "Dallimet nga tenderët e ngjashëm",
            **{
                f"ensemble_rank_{family}": FAMILY_LABELS_SQ.get(family, family)
                for family in ensemble_families
            },
        }
        component_explanation["component_label"] = component_explanation["component"].map(
            component_labels
        )
        st.plotly_chart(
            ensemble_contribution_bar(
                component_explanation,
                title="Kontributi i secilës pjesë në pikët e kombinuara",
            ),
            use_container_width=True,
        )
        direct_total = float(component_explanation["direct_contribution"].sum())
        centered_total = ensemble_composition.baseline_score + float(
            component_explanation["effect_vs_baseline"].sum()
        )
        st.caption(
            f"Σ e kontributeve = {direct_total:.6f}; baza e grupit të të dhënave "
            f"{ensemble_composition.baseline_score:.6f} + efektet ndaj bazës = "
            f"{centered_total:.6f}; ensemble_score i publikuar = {r['ensemble_score']:.6f}. "
            "Ky është zbërthim matematikor ekzakt i pikës së publikuar. Tregon cilat "
            "shtresa e ngritën ose e ulën renditjen, jo shkak, probabilitet apo provë shkeljeje."
        )
        explanation_table = component_explanation[
            [
                "component_label",
                "value_in_formula",
                "weight",
                "direct_contribution",
                "baseline",
                "effect_vs_baseline",
            ]
        ].rename(
            columns={
                "component_label": "përbërësi",
                "value_in_formula": "vlera në formulë",
                "weight": "pesha",
                "direct_contribution": "kontributi ekzakt",
                "baseline": "baza e komponentit",
                "effect_vs_baseline": "efekti ndaj bazës",
            }
        )
        st.dataframe(explanation_table, hide_index=True, use_container_width=True)

    with st.expander("Si llogariten pikët e rregullave dhe kontekstit?"):
        st.caption(
            f"Aritmetika e rule_score: Σ peshave të aktivizuara "
            f"{rule_arithmetic['raw_weight_sum']:.3f} / "
            f"{rule_arithmetic['normaliser']:.1f} = "
            f"{rule_arithmetic['unclipped_score']:.3f}; pas kufizimit [0,1] = "
            f"{rule_arithmetic['reconstructed_score']:.3f}. Diagnostikët me peshë zero "
            "mbeten të dukshëm, por nuk ndikojnë në pikë."
        )

        context_explanation = explain_context_score(
            r,
            published_score=float(r["context_score"]),
        )
        if context_explanation.drivers:
            drivers = ", ".join(
                f"{feature}={value:+.3f}z"
                for feature, value in context_explanation.signed_z_by_driver.items()
            )
            st.caption(
                f"Konteksti: max |z| = {context_explanation.max_absolute_z:.3f} nga {drivers}; "
                f"tanh(max|z|/2) = {context_explanation.reconstructed_score:.3f}."
            )
        else:
            st.caption("Konteksti: asnjë z-score i vëzhguar; context_score rindërtohet si 0.")

    with st.expander("📐 Konteksti përshkrues i veçorive hyrëse"):
        feature_profile = feature_deviation_profile(gold, r, ML_FEATURES, top_k=8)
        st.dataframe(
            feature_profile.rename(
                columns={
                    "feature": "veçoria",
                    "observed_value": "vlera",
                    "missing": "mungon",
                    "missing_rate": "pjesa që mungon",
                    "snapshot_median": "mediana e grupit të të dhënave",
                    "percentile": "percentili",
                    "direction": "drejtimi",
                    "unusualness": "largësia nga mesi",
                    "basis": "baza e krahasimit",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "Këto percentile dhe frekuenca mungese përshkruajnë hyrjet kundrejt "
            "grupit të plotë të të dhënave. Nuk janë kontribute të matura të detektorëve, "
            "nuk hyjnë sërish në ensemble_score dhe nuk janë shpjegim shkakësor."
        )

    # ================================================================
    #  DETAJET TEKNIKE — të palosura, për analistët
    # ================================================================
    with st.expander("Modelet statistikore dhe shpjegimi SHAP"):
        st.write(f"Dallimi ndërmjet datave në burim: {fmt_number(days)} ditë.")
        st.metric("Vendimet kundrejt parashikimit", f"{ratio:.1%}" if pd.notna(ratio) else "—")
        st.caption(METRIC_HELP["awarded_value_ratio"])
        st.markdown(
            "**Pikët bruto të modeleve (diagnostikë)** — këto shkallë 0–1 janë "
            "normalizime brenda secilit detektor, jo rank-percentilet që hyjnë "
            "drejtpërdrejt në formulën sipër. Vetëm familjet e zgjedhura hyjnë në "
            "ensemble_score pas rank-transformimit; detektorët e tjerë dhe HGB nuk hyjnë."
        )
        sc_cols = [
            c
            for c in [
                "rule_score",
                "context_score",
                "iso_score",
                "lof_score",
                "ee_score",
                "ocsvm_score",
                "pca_score",
                "gmm_score",
                "knn_score",
                "hbos_score",
                "hgb_score",
            ]
            if c in r
        ]
        cols = st.columns(min(len(sc_cols), 6))
        for i, c in enumerate(sc_cols):
            cols[i % 6].metric(c.replace("_score", ""), f"{r[c]:.3f}")

        st.markdown("**Indikatorët e aktivizuar (me statusin e pikëzimit):**")
        triggered = [rl for rl in RULES if r.get(rl.code, False)]
        if triggered:
            for rl in triggered:
                contribution = (
                    f"hyn në pikë me peshë {rl.weight}"
                    if rl.score_enabled
                    else "diagnostik; peshë 0 dhe nuk hyn në pikë"
                )
                st.markdown(
                    f"- `{rl.code}` — {rl.description} _({_flag_kind(rl.code)}; {contribution})_"
                )
        else:
            st.markdown("_Asnjë rregull nuk u aktivizua._")

        sv_row = shap_df[shap_df["ocid"] == ocid]
        if not sv_row.empty:
            base_value = float(sv_row["base_value"].iat[0])
            values = sv_row[ML_FEATURES].iloc[0].astype(float).values
            x_value = base_value + float(values.sum())
            fig = shap_waterfall(
                ML_FEATURES,
                values,
                base_value,
                x_value,
                title=f"SHAP i modelit proxy të rregullave · {ocid}",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Ky SHAP shpjegon daljen log-odds të klasifikuesit që përafron "
                "rregullat. Nuk shpjegon ensemble_score, nuk është kontribut i "
                "detektorëve unsupervised dhe nuk është sinjal i pavarur."
            )
        st.caption(
            f"OCID: `{ocid}`  ·  Tender ID: `{r.get('tender_id')}`  ·  Metoda: {r.get('method')}"
        )

st.markdown("---")

# =====================================================================
#  PJESA 2 — LISTA E PLOTË (analistë): filtra + tabelë
# =====================================================================
st.subheader("Krahaso tenderët sipas pikëve")
st.caption(
    "Zgjidh mënyrën e renditjes dhe kufirin minimal. Këto zgjedhje ndryshojnë listën më poshtë, jo tenderin e hapur më sipër."
)

SCORE_LABELS = {
    "ensemble_score": "Pikët e kombinuara",
    "rule_score": "Pikët e rregullave",
    "context_score": "Dallimet nga tenderët e ngjashëm",
    "iso_score": "Isolation Forest",
    "lof_score": "Local Outlier Factor (LOF)",
    "ee_score": "Elliptic Envelope",
    "ocsvm_score": "One-Class SVM",
    "pca_score": "Gabimi i rindërtimit PCA",
    "gmm_score": "Gaussian Mixture (GMM)",
    "knn_score": "Distanca KNN",
    "hbos_score": "HBOS (histogram)",
    "hgb_score": "HistGradientBoosting (vetëm shpjegim)",
}
advanced_models = st.checkbox("Përfshi edhe modelet individuale në renditje", value=False)
score_options = [
    c
    for c in SCORE_LABELS
    if c in gold.columns
    and (advanced_models or c in ("ensemble_score", "rule_score", "context_score"))
]

c1, c2, c3 = st.columns([1, 1, 2])
score_type = c1.selectbox("Rendit sipas", score_options, format_func=lambda c: SCORE_LABELS[c])
threshold = c2.slider(
    "Pikët minimale",
    0.0,
    1.0,
    0.5,
    0.05,
    help="Filtër në shkallën e renditjes së zgjedhur; nuk është prag "
    "probabiliteti ose vendim i validuar.",
)
rule_codes = sorted([r.code for r in RULES])
sel_rules = c3.multiselect(
    "Kërko një sinjal të caktuar (opsionale)",
    rule_codes,
    format_func=lambda code: FLAG_NARRATIVE[code][0],
)

flagged = filtered[filtered[score_type] >= threshold].copy()
if sel_rules:
    flagged = flagged[flagged[sel_rules].any(axis=1)]
flagged = flagged.sort_values(score_type, ascending=False)

require_agreement = st.checkbox(
    "Vetëm tenderët ku modelet pajtohen: "
    f"së paku {minimum_model_agreement} nga {len(ensemble_families)} "
    f"i rendisin mes {(1 - agreement_quantile):.0%} më të pazakontëve",
    value=False,
    help="Ky është filtër për përputhje modelesh me veçori të mbivendosura; nuk është "
    "masë besueshmërie dhe nuk është provuar se redukton falsë pozitivët.",
)
if require_agreement and "model_agreement_count" in flagged.columns:
    flagged = flagged[flagged["model_agreement_count"] >= minimum_model_agreement]

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Tenderë mbi kufirin",
    f"{len(flagged):,}",
    help=f"{len(flagged) / max(len(filtered), 1):.1%} e tenderëve në përzgjedhje.",
)
c2.metric("Vlera totale e parashikuar", fmt_eur(flagged["estimated_value_eur"].sum(min_count=1)))
c3.metric("Mediana e pikëve", f"{flagged[score_type].median():.3f}" if len(flagged) else "—")
c4.metric("Autoritete kontraktuese", f"{flagged['procuring_entity_id'].nunique():,}")

st.plotly_chart(
    anomaly_score_hist(filtered[score_type], threshold=threshold), use_container_width=True
)

with st.expander("Të gjitha sinjalet në listën e përzgjedhur"):
    st.caption(
        "Sinjalet për shqyrtim ndikojnë në pikët e rregullave. Kontrollet e cilësisë "
        "së të dhënave dhe ecurisë së procedurës shfaqen gjithashtu, por nuk shtojnë pikë."
    )
    if len(flagged):
        rc = pd.Series(
            {FLAG_NARRATIVE[r.code][0]: int(flagged[r.code].sum()) for r in RULES}
        ).sort_values()
        fig = px.bar(
            rc,
            orientation="h",
            color_discrete_sequence=[PALETTE["bad"]],
            labels={"value": "Numri i tenderëve", "index": "Sinjali"},
        )
        fig.update_layout(height=540, showlegend=False, margin={"l": 20, "r": 20, "t": 30, "b": 20})
        st.plotly_chart(fig, use_container_width=True)

display_cols = [
    c
    for c in [
        "title",
        "procuring_entity_name",
        "release_date",
        "category",
        "method",
        "ocid",
        "estimated_value_eur",
        "total_awarded_eur",
        "was_awarded",
        "rule_score",
        "context_score",
        "ensemble_score",
        "model_agreement_count",
    ]
    if c in gold.columns
]
if flagged.empty:
    st.info(
        "Asnjë tender nuk i plotëson këto kushte. Ulni kufirin e pikëve ose hiqni kufizimin sipas sinjalit."
    )

table = flagged[display_cols].head(500).copy()
table = table.drop(columns=["was_awarded"], errors="ignore") if table.empty else table
if len(table):
    table["release_date"] = pd.to_datetime(table["release_date"]).dt.date
    table["category"] = table["category"].map(category_label)
    table["method"] = table["method"].map(method_label)
    has_award = table.apply(_has_recorded_award, axis=1)
    if "total_awarded_eur" in table:
        table.loc[~has_award, "total_awarded_eur"] = float("nan")
    table["award_status"] = has_award.map(
        {True: "dhënie e regjistruar", False: "— pa dhënie të regjistruar"}
    )
    table = table.drop(columns=["was_awarded"], errors="ignore")

score_col_config = {
    c: st.column_config.ProgressColumn(SCORE_LABELS[c], min_value=0.0, max_value=1.0, format="%.2f")
    for c in display_cols
    if c.endswith("_score")
}
score_col_config.update(
    {
        "ocid": st.column_config.TextColumn("OCID"),
        "release_date": st.column_config.DateColumn("data"),
        "procuring_entity_name": st.column_config.TextColumn("autoriteti kontraktues"),
        "category": st.column_config.TextColumn("kategoria"),
        "method": st.column_config.TextColumn("Metoda në burim"),
        "estimated_value_eur": st.column_config.NumberColumn(
            "vlera e parashikuar €", format="%.0f"
        ),
        "total_awarded_eur": st.column_config.NumberColumn("Vendimet e dhënies (€)", format="%.0f"),
        "award_status": st.column_config.TextColumn("statusi i dhënies"),
        "title": st.column_config.TextColumn("titulli", width="large"),
        "model_agreement_count": st.column_config.NumberColumn(
            f"Modele në {(1 - agreement_quantile):.0%} më të lartët",
            help="Numri i modeleve që e rendisin tenderin ndër më të pazakontët; nuk është masë sigurie.",
        ),
    }
)
st.dataframe(
    table, use_container_width=True, hide_index=True, column_config=score_col_config, height=420
)
if len(flagged) > 500:
    st.caption(
        f"Shfaqen 500 nga {fmt_number(len(flagged))} tenderë. Ngushtoni filtrat për të parë pjesën tjetër."
    )

with st.expander("Çfarë tregojnë pikët?"):
    for key in ("ensemble_score", "rule_score", "context_score"):
        st.markdown(f"**{SCORE_LABELS[key]}** — {METRIC_HELP[key]}")

with st.expander("Përkufizimet teknike të rregullave"):
    st.caption("Përkufizimet origjinale, peshat dhe kufizimet për verifikim metodologjik.")
    st.dataframe(rule_descriptions(), hide_index=True, use_container_width=True)
