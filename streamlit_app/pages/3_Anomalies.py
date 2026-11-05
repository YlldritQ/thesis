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
    RULE_TABLE_CAPTION,
    anomaly_score_hist,
    category_label,
    ensemble_contribution_bar,
    fmt_columns,
    fmt_number,
    method_label,
    rule_table_sq,
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

st.set_page_config(
    page_title="Sinjalet për shqyrtim · Prokurimi në Kosovë", page_icon="🚨", layout="wide"
)

page_header(
    "🔎 Sinjalet për shqyrtim",
    "Shqyrtoni tenderët e sinjalizuar dhe arsyet e sinjalizimit. "
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
    raise RuntimeError(
        "Në rezultatet e publikuara mungon specifikimi për shpjegimin e pikëve të kombinuara."
    )
ensemble_families = ensemble_definition.get("detector_families")
if not isinstance(ensemble_families, list):
    raise RuntimeError("Në specifikimin XAI mungojnë familjet e modeleve që përdoren në kombinim.")
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
        raise RuntimeError(f"Përbërësi XAI nuk përputhet me skedarin e publikuar: {rank_column}")

filtered = sidebar_filters(gold)

RULE_BY_CODE = {rule.code: rule for rule in RULES}

# Defined before the tender detail section, which also uses these labels.
SCORE_LABELS = {
    "ensemble_score": "Pikët e kombinuara",
    "rule_score": "Pikët sipas rregullave",
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
DIRECTION_LABELS = {
    "high": "e lartë",
    "low": "e ulët",
    "middle": "në mes",
    "missing": "mungon",
    "no_reference": "pa bazë krahasimi",
}
BASIS_LABELS = {
    "empirical_midrank_percentile": "Percentili empirik",
    "missingness_frequency": "Shpeshtësia e mungesës",
}


def _fmt_signed(value: float, decimals: int = 3) -> str:
    return ("+" if value >= 0 else "") + fmt_number(value, decimals)


def _fmt_feature_value(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    return fmt_number(number, 0 if abs(number) >= 1000 or number.is_integer() else 3)


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
        return "sinjal për verifikim"
    if rule.score_enabled:
        return "Sinjal për shqyrtim · ndikon në pikët sipas rregullave"
    kind = (
        "cilësisë së të dhënave" if rule.signal_type == "data_quality" else "ecurisë së procedurës"
    )
    return f"Kontroll i {kind} · nuk shton pikë"


score_rules = [rule.code for rule in RULES if rule.score_enabled]
diagnostic_rules = [rule.code for rule in RULES if not rule.score_enabled]
with_signal = filtered[score_rules].fillna(False).any(axis=1)
with_diagnostic = filtered[diagnostic_rules].fillna(False).any(axis=1)
c1, c2, c3 = st.columns(3)
c1.metric("Tenderë të përzgjedhur", fmt_number(len(filtered)))
c2.metric(
    "Me të paktën një sinjal që shton pikë",
    fmt_number(int(with_signal.sum())),
    help="Tenderë me të paktën një sinjal që ndikon në pikët sipas rregullave, edhe kur ky sinjal "
    "shton pak pikë. Lista për shqyrtim në Ballinë përfshin vetëm tenderët "
    "me të paktën 0,5 pikë sipas rregullave.",
)
c3.metric("Me të dhëna për verifikim", fmt_number(int(with_diagnostic.sum())))
st.caption(
    "Një tender mund të përfshihet në të dy grupet. Filtrat ndryshojnë përzgjedhjen e shfaqur; pikët llogariten gjithmonë në raport me tërë bashkësinë e të dhënave."
)

if filtered.empty:
    st.info(
        "Asnjë tender nuk përputhet me filtrat e zgjedhur. Hiqni disa nga filtrat në menynë anësore."
    )
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
        st.success("Asnjë nga tenderët e përzgjedhur nuk ka sinjal që shton pikë.")
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
            separators=", ",
            yaxis_title=None,
            xaxis_title="Numri i tenderëve",
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
        )
        fig.update_xaxes(tickformat=",.0f")
        fig.update_traces(
            texttemplate="%{x:,.0f}",
            hovertemplate="%{y}<br>%{x:,.0f} tenderë<extra></extra>",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Grafiku paraqet sinjalet që ndikojnë në pikët sipas rregullave. Një tender mund të ketë disa sinjale, prandaj shuma e kolonave nuk përfaqëson numrin e tenderëve të veçantë."
        )

# =====================================================================
#  PJESA 1 — PËR QYTETARIN: shqyrto një tender konkret
# =====================================================================
st.subheader("Shqyrtimi i një tenderi")
st.caption(
    "Zgjidhni një nga 300 tenderët e parë ose vendosni identifikuesin OCID. Tenderët renditen "
    "sipas pikëve të llogaritura nga rregullat; kur këto janë të barabarta, përdoren pikët e kombinuara. "
    "Pikët shërbejnë për renditjen e rasteve për shqyrtim; nuk tregojnë probabilitetin e një shkeljeje."
)

# renditja për përzgjedhësin: shtresa e rregullave (baza e auditueshme) në krye
ranked = filtered.sort_values(["rule_score", "ensemble_score"], ascending=False)
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
    # A tender opened from search takes precedence over an earlier manual lookup.
    incoming_ocid = st.session_state.pop("review_ocid", None)
    if incoming_ocid is not None:
        st.session_state["anomaly_manual_ocid"] = incoming_ocid
    manual = st.text_input("Ose kërko me identifikuesin OCID", key="anomaly_manual_ocid").strip()

ocid = manual or chosen
if manual and not gold["ocid"].eq(manual).any():
    st.warning(
        "Nuk u gjet tender me këtë identifikues OCID. Kontrolloni nëse e keni kopjuar saktë dhe të plotë."
    )
elif manual and not filtered["ocid"].eq(manual).any():
    st.info(
        "Tenderi i kërkuar nuk përputhet me filtrat e zgjedhur. Të dhënat më poshtë i përkasin tenderit me OCID-in e vendosur."
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
    st.markdown("#### Treguesit kryesorë")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Vlera e parashikuar",
        fmt_eur(r.get("estimated_value_eur")),
        help=METRIC_HELP["estimated_value_eur"],
    )
    c2.metric(
        "Vlera sipas vendimeve",
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
    c3.metric("Afati për ofertim", duration, help=METRIC_HELP["days_tender_open"])
    if pd.notna(days) and days < 0:
        st.caption(
            f"Datat e regjistruara nuk përputhen: afati i fundit për ofertim është {fmt_number(abs(days))} ditë para datës së fillimit. Këto data duhen verifikuar."
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
            "Asnjë nga rregullat nuk ka sinjalizuar këtë tender. Ai mund të renditet ndër të parët "
            "për shkak të veçorive të tij statistikore. Kjo nuk vërteton as praninë, as mungesën e shkeljeve."
        )
    # ---- kush e fitoi ----
    a = awards[awards["ocid"] == ocid]
    if not a.empty:
        st.markdown("#### Furnizuesit sipas vendimeve")
        supplier_display = a["supplier_name"].fillna("").astype(str).str.strip()
        legal = a["supplier_legal_name"].fillna("").astype(str).str.strip()
        party = a["supplier_party_id"].fillna("").astype(str).str.strip()
        supplier_display = supplier_display.where(supplier_display.ne(""), legal)
        supplier_display = supplier_display.where(
            supplier_display.ne(""), "Furnizues sipas identifikuesit " + party
        ).replace("Furnizues sipas identifikuesit ", "Furnizues i paidentifikuar")
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
            "Vlerat sipas vendimeve nuk dëshmojnë se kontratat janë nënshkruar ose se janë kryer pagesa."
        )
    else:
        st.markdown("#### Furnizuesit sipas vendimeve")
        st.markdown(
            "_Në të dhënat e analizuara nuk është regjistruar vendim për dhënien e kontratës._"
        )

    # ---- shënim për kufizimin e të dhënave ----
    if pd.notna(ratio) and ratio > 1.0:
        st.warning("💡 " + DATA_LIMITATION_BIDS)

    with st.expander("Si llogariten pikët e kombinuara?"):
        # ---- shpjegimi ekzakt i rezultatit real të ansamblit ----
        st.markdown("#### Si u llogaritën pikët e kombinuara?")
        component_explanation = ensemble_composition.explain_record(
            selected_index,
            published_score=float(r["ensemble_score"]),
        )
        component_labels = {
            "rule_score": "Pikët sipas rregullave",
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
                title="Kontributi i secilit përbërës në pikët e kombinuara",
            ),
            use_container_width=True,
        )
        direct_total = float(component_explanation["direct_contribution"].sum())
        centered_total = ensemble_composition.baseline_score + float(
            component_explanation["effect_vs_baseline"].sum()
        )
        st.caption(
            f"Shuma e kontributeve = {fmt_number(direct_total, 6)}; vlera bazë e bashkësisë së të dhënave "
            f"{fmt_number(ensemble_composition.baseline_score, 6)} + ndikimet kundrejt vlerës bazë = "
            f"{fmt_number(centered_total, 6)}; pikët e kombinuara të publikuara = "
            f"{fmt_number(r['ensemble_score'], 6)}. "
            "Ky zbërthim matematikor riprodhon saktësisht pikët e publikuara. Ai tregon cilët "
            "përbërës e rritën ose e ulën vlerësimin, por nuk shpjegon shkaqet dhe nuk jep probabilitet apo provë të një shkeljeje."
        )
        explanation_table = fmt_columns(
            component_explanation[
                [
                    "component_label",
                    "value_in_formula",
                    "weight",
                    "direct_contribution",
                    "baseline",
                    "effect_vs_baseline",
                ]
            ],
            {
                "value_in_formula": 4,
                "weight": 4,
                "direct_contribution": 6,
                "baseline": 6,
                "effect_vs_baseline": 6,
            },
        ).rename(
            columns={
                "component_label": "Përbërësi",
                "value_in_formula": "Vlera në formulë",
                "weight": "Pesha",
                "direct_contribution": "Kontributi i saktë",
                "baseline": "Vlera bazë e përbërësit",
                "effect_vs_baseline": "Ndikimi kundrejt vlerës bazë",
            }
        )
        st.dataframe(explanation_table, hide_index=True, use_container_width=True)

    with st.expander("Si llogariten pikët sipas rregullave dhe krahasimit me tenderë të ngjashëm?"):
        st.caption(
            f"Pikët sipas rregullave: shuma e peshave të rregullave të aktivizuara "
            f"{fmt_number(rule_arithmetic['raw_weight_sum'], 3)} / "
            f"{fmt_number(rule_arithmetic['normaliser'], 1)} = "
            f"{fmt_number(rule_arithmetic['unclipped_score'], 3)}; pas kufizimit në intervalin "
            f"0–1 = {fmt_number(rule_arithmetic['reconstructed_score'], 3)}. Kontrollet me "
            "peshë zero shfaqen në faqe, por nuk shtojnë pikë."
        )

        context_explanation = explain_context_score(
            r,
            published_score=float(r["context_score"]),
        )
        if context_explanation.drivers:
            drivers = ", ".join(
                f"{feature} = {_fmt_signed(value)}"
                for feature, value in context_explanation.signed_z_by_driver.items()
            )
            st.caption(
                f"Krahasimi me tenderë të ngjashëm: vlera maksimale absolute z, max |z| = "
                f"{fmt_number(context_explanation.max_absolute_z, 3)}, lidhet me {drivers}; "
                f"tanh(max|z|/2) = {fmt_number(context_explanation.reconstructed_score, 3)}."
            )
        else:
            st.caption(
                "Krahasimi me tenderë të ngjashëm: nuk ka vlera z të disponueshme, ndaj pikët për këtë përbërës janë 0."
            )

    with st.expander("📐 Krahasimi i veçorive të tenderit"):
        feature_profile = feature_deviation_profile(gold, r, ML_FEATURES, top_k=8)
        profile_view = fmt_columns(
            feature_profile,
            {"missing_rate": 3, "percentile": 3, "unusualness": 3},
        )
        for column in ("observed_value", "snapshot_median"):
            profile_view[column] = feature_profile[column].map(_fmt_feature_value)
        profile_view["missing"] = feature_profile["missing"].map({True: "Po", False: "Jo"})
        profile_view["direction"] = feature_profile["direction"].map(
            lambda value: DIRECTION_LABELS.get(value, value)
        )
        profile_view["basis"] = feature_profile["basis"].map(
            lambda value: BASIS_LABELS.get(value, value)
        )
        st.dataframe(
            profile_view.rename(
                columns={
                    "feature": "Veçoria",
                    "observed_value": "Vlera",
                    "missing": "Mungon",
                    "missing_rate": "Pjesa e vlerave që mungojnë",
                    "snapshot_median": "Mediana e bashkësisë së të dhënave",
                    "percentile": "Percentili",
                    "direction": "Drejtimi",
                    "unusualness": "Largësia nga vlera e mesit",
                    "basis": "Baza e krahasimit",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "Percentilet dhe shpeshtësia e mungesave përshkruajnë veçoritë e tenderit në raport me "
            "tërë bashkësinë e të dhënave. Këto nuk janë kontribute të llogaritura nga modelet, "
            "nuk shtohen në pikët e kombinuara dhe nuk shpjegojnë shkaqet e dallimeve."
        )

    # ================================================================
    #  DETAJET TEKNIKE — të palosura, për analistët
    # ================================================================
    with st.expander("Modelet statistikore dhe shpjegimi SHAP"):
        st.write(f"Diferenca ndërmjet datave të regjistruara: {fmt_number(days)} ditë.")
        st.metric(
            "Vlera sipas vendimeve / vlera e parashikuar",
            f"{fmt_number(ratio * 100, 1)}%" if pd.notna(ratio) else "—",
        )
        st.caption(METRIC_HELP["awarded_value_ratio"])
        st.markdown(
            "**Pikët e secilit model (për kontroll)** — vlerat në shkallën 0–1 janë "
            "të normalizuara brenda secilit model. Ato ndryshojnë nga percentilet e renditjes që përdoren "
            "drejtpërdrejt në formulën e mësipërme. Vetëm familjet e përzgjedhura të modeleve ndikojnë në "
            "pikët e kombinuara, pas shndërrimit të rezultateve të tyre në renditje. Modelet e tjera dhe "
            "HistGradientBoosting nuk përfshihen në këtë llogaritje."
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
            cols[i % 6].metric(SCORE_LABELS.get(c, c), fmt_number(r[c], 3))

        st.markdown("**Sinjalet e aktivizuara dhe ndikimi i tyre në pikë:**")
        triggered = [rl for rl in RULES if r.get(rl.code, False)]
        if triggered:
            for rl in triggered:
                contribution = (
                    f"shton pikë me peshë {fmt_number(rl.weight, 2)}"
                    if rl.score_enabled
                    else "kontroll me peshë 0; nuk shton pikë"
                )
                st.markdown(
                    f"- `{rl.code}` — {FLAG_NARRATIVE[rl.code][0]} "
                    f"_({_flag_kind(rl.code)}; {contribution})_"
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
                title=f"SHAP i modelit që përafron rregullat · {ocid}",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Shpjegimi SHAP zbërthen rezultatin e klasifikuesit që përafron "
                "rregullat, në shkallën log(p/(1−p)). Ai nuk shpjegon pikët e kombinuara, nuk "
                "paraqet kontributin e modeleve të mësimit të pambikëqyrur dhe nuk përbën sinjal të pavarur."
            )
        st.caption(
            f"OCID: `{ocid}`  ·  Numri i tenderit: `{r.get('tender_id')}`  ·  "
            f"Metoda e prokurimit: {method_label(r.get('method'))}"
        )

st.markdown("---")

# =====================================================================
#  PJESA 2 — LISTA E PLOTË (analistë): filtra + tabelë
# =====================================================================
st.subheader("Krahaso tenderët sipas pikëve")
st.caption(
    "Zgjidhni kriterin e renditjes dhe pragun minimal të pikëve. Këto zgjedhje zbatohen në listën më poshtë dhe nuk ndryshojnë tenderin e hapur më sipër."
)

advanced_models = st.checkbox("Përfshi edhe rezultatet e modeleve të veçanta", value=False)
score_options = [
    c
    for c in SCORE_LABELS
    if c in gold.columns
    and (advanced_models or c in ("ensemble_score", "rule_score", "context_score"))
]

c1, c2, c3 = st.columns([1, 1, 2])
# The rule layer is the auditable baseline; the combined score stays an exploratory option.
score_type = c1.selectbox(
    "Rendit sipas",
    score_options,
    index=score_options.index("rule_score") if "rule_score" in score_options else 0,
    format_func=lambda c: SCORE_LABELS[c],
)
ensemble_half_percentile = (
    float(gold["ensemble_score"].lt(0.5).mean() * 100) if "ensemble_score" in gold else None
)
ensemble_half_note = (
    f" Për pikët e kombinuara, vlera 0,5 i përket afërsisht percentilit të "
    f"{fmt_number(ensemble_half_percentile)}-të të shpërndarjes dhe nuk është prag i përcaktuar për shqyrtim."
    if ensemble_half_percentile is not None
    else ""
)
threshold = c2.slider(
    "Pikët minimale",
    0.0,
    1.0,
    0.5,
    0.05,
    help="Përzgjedh tenderët sipas pikëve të zgjedhura. Ky prag nuk shpreh "
    "probabilitet shkeljeje dhe nuk është vërtetuar si kriter vendimmarrjeje." + ensemble_half_note,
)
rule_codes = sorted([r.code for r in RULES])
sel_rules = c3.multiselect(
    "Filtro sipas sinjalit (opsionale)",
    rule_codes,
    format_func=lambda code: FLAG_NARRATIVE[code][0],
    placeholder="Të gjitha sinjalet",
)

flagged = filtered[filtered[score_type] >= threshold].copy()
if sel_rules:
    flagged = flagged[flagged[sel_rules].any(axis=1)]
flagged = flagged.sort_values(score_type, ascending=False)

require_agreement = st.checkbox(
    "Vetëm tenderët e sinjalizuar nga disa modele: "
    f"së paku {minimum_model_agreement} nga {len(ensemble_families)} "
    f"i rendisin ndër {(1 - agreement_quantile):.0%} e tenderëve më të pazakontë",
    value=False,
    help="Veçoritë që përdorin modelet përkojnë pjesërisht. Përputhja e rezultateve të tyre nuk është "
    "garanci për saktësinë e sinjalit dhe nuk është vërtetuar se pakëson sinjalizimet e gabuara.",
)
if require_agreement and "model_agreement_count" in flagged.columns:
    flagged = flagged[flagged["model_agreement_count"] >= minimum_model_agreement]

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Tenderë që plotësojnë pragun",
    fmt_number(len(flagged)),
    help=f"{fmt_number(100 * len(flagged) / max(len(filtered), 1), 1)}% e tenderëve në përzgjedhje.",
)
c2.metric("Vlera totale e parashikuar", fmt_eur(flagged["estimated_value_eur"].sum(min_count=1)))
c3.metric("Mediana e pikëve", fmt_number(flagged[score_type].median(), 3) if len(flagged) else "—")
c4.metric("Autoritete kontraktuese", fmt_number(flagged["procuring_entity_id"].nunique()))

st.plotly_chart(
    anomaly_score_hist(filtered[score_type], threshold=threshold), use_container_width=True
)

with st.expander("Të gjitha sinjalet në listën e përzgjedhur"):
    st.caption(
        "Sinjalet për shqyrtim ndikojnë në pikët sipas rregullave. Kontrollet e cilësisë "
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
        fig.update_layout(
            height=540,
            showlegend=False,
            separators=", ",
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
        )
        fig.update_xaxes(tickformat=",.0f")
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
        "Asnjë tender nuk i plotëson kushtet e zgjedhura. Ulni pragun e pikëve ose hiqni filtrin sipas sinjalit."
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
        {True: "Me vendim të regjistruar", False: "Pa vendim të regjistruar"}
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
        "release_date": st.column_config.DateColumn("Data e publikimit", format="DD.MM.YYYY"),
        "procuring_entity_name": st.column_config.TextColumn("Autoriteti kontraktues"),
        "category": st.column_config.TextColumn("Kategoria"),
        "method": st.column_config.TextColumn("Metoda e prokurimit"),
        "estimated_value_eur": st.column_config.NumberColumn(
            "Vlera e parashikuar (€)", format="localized"
        ),
        "total_awarded_eur": st.column_config.NumberColumn(
            "Vlera sipas vendimeve (€)", format="localized"
        ),
        "award_status": st.column_config.TextColumn("Vendimi për kontratën"),
        "title": st.column_config.TextColumn("Titulli i tenderit", width="large"),
        "model_agreement_count": st.column_config.NumberColumn(
            f"Modele që e rendisin ndër {(1 - agreement_quantile):.0%} e tenderëve më të pazakontë",
            help="Numri i modeleve që e rendisin tenderin ndër më të pazakontët. Nuk përfaqëson probabilitetin e një shkeljeje.",
        ),
    }
)
st.dataframe(
    table, use_container_width=True, hide_index=True, column_config=score_col_config, height=420
)
if len(flagged) > 500:
    st.caption(
        f"Shfaqen 500 nga {fmt_number(len(flagged))} tenderë. Përdorni filtra më të hollësishëm për të gjetur rastet që ju interesojnë."
    )

with st.expander("Çfarë tregojnë pikët?"):
    for key in ("ensemble_score", "rule_score", "context_score"):
        st.markdown(f"**{SCORE_LABELS[key]}** — {METRIC_HELP[key]}")

with st.expander("Përkufizimet teknike të rregullave"):
    st.caption(
        "Përkufizimet origjinale të rregullave, peshat dhe kufijtë e interpretimit, për verifikimin e metodologjisë."
    )
    st.caption(RULE_TABLE_CAPTION)
    st.dataframe(rule_table_sq(rule_descriptions()), hide_index=True, use_container_width=True)
