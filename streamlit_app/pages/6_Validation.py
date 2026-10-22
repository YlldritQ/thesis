"""Internal checks with an explicit separation from real-world detection accuracy."""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from _bootstrap import cached_validation_report, page_header
from _charts import fmt_columns, fmt_number

from thesis.viz import PALETTE

st.set_page_config(
    page_title="Kontrollet e modeleve · Prokurimi në Kosovë", page_icon="🧪", layout="wide"
)
page_header(
    "🧪 Kontrollet e modeleve",
    "Kontrolle të modeleve: përsëritshmëria, ngjashmëria e renditjeve dhe lidhja me rregullat.",
)

report = cached_validation_report()
if not report:
    st.info("Raporti i kontrolleve të modeleve nuk është i disponueshëm.")
    with st.expander("Udhëzim për mirëmbajtësin"):
        st.code("thesis pipeline run --only ml --force", language="bash")
    st.stop()


def _metric_text(value: object, digits: int = 3) -> str:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return fmt_number(value, digits)
    return "—"


family_labels = {
    "iso": "Isolation Forest",
    "lof": "LOF",
    "ee": "Elliptic Envelope",
    "ocsvm": "One-Class SVM",
    "pca": "PCA",
    "gmm": "Gaussian Mixture",
    "knn": "KNN",
    "hbos": "HBOS",
}
cv = report.get("cross_validation") or {}
stability_by_family = report.get("stability_by_ensemble_family") or {}
if not stability_by_family:
    stability_by_family = {
        family: values
        for family, values in {
            "iso": report.get("stability_isolation_forest") or {},
            "lof": report.get("stability_lof") or {},
        }.items()
        if values
    }
agree = report.get("inter_model_agreement") or {}
calib = report.get("supervised_calibration") or {}
baseline = report.get("rule_only_baseline_and_confusion") or {}

st.warning(
    "Nuk ka etiketa të pavarura që tregojnë cilët tenderë kanë shkelje të konfirmuara. "
    "Këto kontrolle tregojnë si sillen modelet në të dhënat e analizuara; "
    "nuk matin sa saktë zbulohet mashtrimi."
)
c1, c2, c3 = st.columns(3)
c1.metric("Tenderë të vlerësuar", fmt_number(report.get("n_records")))
c2.metric(
    "Veçori hyrëse të modeleve",
    str(report.get("n_features", "—")),
    help="Variablat numerike që marrin modelet statistikore për çdo tender. "
    "Nuk janë të njëjtat me treguesit e rregullave të paraqitur te Sinjalet për shqyrtim.",
)
c3.metric("Modele në kombinim", str(len(report.get("ensemble_models", []))))

tab_agreement, tab_stability, tab_details = st.tabs(
    ["Rregullat dhe modelet", "Qëndrueshmëria e rezultateve", "Kontrolle teknike"]
)

with tab_agreement:
    st.subheader("A veçojnë rregullat dhe modelet të njëjtët tenderë?")
    st.caption(
        "Tabela krahason sinjalizimin sipas pikëve të rregullave me pikët e kombinuara. "
        "Rregullat janë edhe pjesë e kombinimit, ndaj ky krahasim nuk është verifikim i pavarur."
    )
    confusion = baseline.get("confusion") or {}
    if not confusion:
        st.info("Krahasimi me rregullat nuk është i disponueshëm.")
    else:
        comparison = pd.DataFrame(
            [
                {"Grupi": "Të dyja mënyrat", "Tenderë": confusion.get("both_flagged", 0)},
                {
                    "Grupi": "Vetëm rregullat",
                    "Tenderë": confusion.get("rule_only_demoted_by_ensemble", 0),
                },
                {
                    "Grupi": "Vetëm pikët e kombinuara",
                    "Tenderë": confusion.get("ensemble_only_ml_unvalidated", 0),
                },
                {"Grupi": "Asnjëra", "Tenderë": confusion.get("neither", 0)},
            ]
        )
        fig = px.bar(
            comparison,
            x="Tenderë",
            y="Grupi",
            orientation="h",
            text="Tenderë",
            color_discrete_sequence=[PALETTE["primary"]],
        )
        fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=300,
            xaxis_title="Numri i tenderëve",
            yaxis_title=None,
            yaxis_autorange="reversed",
            xaxis_rangemode="tozero",
            margin={"l": 10, "r": 65, "t": 15, "b": 15},
            showlegend=False,
        )
        fig.update_layout(separators=", ")
        fig.update_xaxes(tickformat=",~f")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Pragu i pikëve të rregullave: {fmt_number(baseline.get('rule_flag_threshold'), 1)} · "
            f"Pragu i pikëve të kombinuara: {fmt_number(baseline.get('ensemble_flag_threshold'), 1)}. "
            "Këto pragje janë zgjedhje të analizës, jo kufij ligjorë."
        )
        ensemble_only_share = baseline.get("pct_ensemble_that_is_ml_only")
        if isinstance(ensemble_only_share, (int, float)):
            total = int(comparison["Tenderë"].sum())
            ensemble_set = confusion.get("both_flagged", 0) + confusion.get(
                "ensemble_only_ml_unvalidated", 0
            )
            rule_set = confusion.get("both_flagged", 0) + confusion.get(
                "rule_only_demoted_by_ensemble", 0
            )
            nested = (
                " Të gjithë tenderët e sinjalizuar nga rregullat janë edhe mbi pragun e pikëve "
                "të kombinuara; grupet nuk kundërshtojnë njëri-tjetrin, por ndryshojnë shumë në madhësi."
                if confusion.get("rule_only_demoted_by_ensemble", 0) == 0
                else ""
            )
            st.info(
                f"{fmt_number(ensemble_only_share * 100, 1)}% e tenderëve mbi pragun e pikëve të kombinuara "
                "nuk e kalojnë pragun e rregullave. Kjo tregon dallim në përzgjedhje, "
                "jo shkelje të reja të zbuluara. Pragu 0,5 i pikëve të kombinuara përfshin "
                f"{fmt_number(100 * ensemble_set / max(total, 1), 1)}% të tenderëve, ndërsa pragu "
                f"i rregullave {fmt_number(100 * rule_set / max(total, 1), 1)}%." + nested
            )
        with st.expander("Shifrat e krahasimit"):
            st.dataframe(
                fmt_columns(comparison, {"Tenderë": 0}), hide_index=True, use_container_width=True
            )
    st.subheader("Çfarë duhet për verifikim të mëtejshëm?")
    st.markdown(
        "Një shqyrtues duhet të lexojë dokumentet e një mostre tenderësh, duke përfshirë "
        "edhe raste pa sinjale. Përfundimet e këtij shqyrtimi duhen mbajtur veç "
        "nga rregullat që prodhuan sinjalet. Një rast i pashqyrtuar nuk llogaritet "
        "si rast pa shkelje."
    )
    with st.expander("Protokolli për shqyrtimin manual"):
        st.markdown(
            "Mostra përfshin katër grupe: sinjalizim nga të dyja mënyrat, vetëm nga "
            "rregullat, vetëm nga pikët e kombinuara dhe nga asnjëra."
        )
        st.code("thesis report audit-sample", language="bash")
        st.caption("Protokolli i plotë: docs/manual_audit_protocol.md")

with tab_stability:
    st.subheader("A përzgjidhen të njëjtët tenderë kur analiza përsëritet?")
    st.caption(
        "Modelet trajnohen sërish në mostra të të dhënave. Matësi Jaccard krahason "
        "grupet e tenderëve të përzgjedhur: 0 = asnjë tender i përbashkët; "
        "1 = grupe të njëjta. Qëndrueshmëria nuk tregon nëse sinjalet janë të sakta."
    )
    stability_rows = [
        {
            "Modeli": family_labels.get(family, family),
            "Ngjashmëria e grupeve (Jaccard)": values.get("mean_jaccard"),
            "Pjesa e përbashkët në krye": values.get("mean_top_overlap"),
            "Përsëritje": values.get("runs"),
            "Pjesa e mostrës": values.get("sample_frac"),
            "Pragu i percentilit": values.get("flag_quantile", values.get("threshold")),
        }
        for family, values in stability_by_family.items()
    ]
    if not stability_rows:
        st.info("Matjet e qëndrueshmërisë nuk janë të disponueshme.")
    else:
        stability_frame = pd.DataFrame(stability_rows)
        plot_frame = stability_frame.dropna(subset=["Ngjashmëria e grupeve (Jaccard)"])
        if not plot_frame.empty:
            fig = px.bar(
                plot_frame.sort_values("Ngjashmëria e grupeve (Jaccard)"),
                x="Ngjashmëria e grupeve (Jaccard)",
                y="Modeli",
                orientation="h",
                text_auto=".3f",
                color_discrete_sequence=[PALETTE["primary"]],
            )
            fig.update_layout(
                height=max(260, 55 * len(plot_frame)),
                xaxis_range=[0, 1],
                yaxis_title=None,
                margin={"l": 10, "r": 20, "t": 15, "b": 15},
            )
            fig.update_layout(separators=", ")
            st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Ky është kontroll me pak përsëritje në të njëjtin grup të të dhënave. "
            "Nuk jep intervale të pasigurisë dhe nuk vërteton rezultatet në të dhëna të reja."
        )
        with st.expander("Parametrat dhe matjet e përsëritjeve"):
            st.dataframe(
                fmt_columns(
                    stability_frame,
                    {
                        "Ngjashmëria e grupeve (Jaccard)": 3,
                        "Pjesa e përbashkët në krye": 3,
                        "Përsëritje": 0,
                        "Pjesa e mostrës": 2,
                        "Pragu i percentilit": 2,
                    },
                ),
                hide_index=True,
                use_container_width=True,
            )

    vote_sensitivity = report.get("rank_agreement_quantile_sensitivity") or {}
    quantiles = vote_sensitivity.get("quantiles") or {}
    if quantiles:
        st.subheader("Sa tenderë përzgjidhen kur ndryshon pragu?")
        st.caption(
            "Një prag më i lartë e ngushton listën për shqyrtim. Përzgjedhja kërkon "
            "pajtim mes modeleve sipas të njëjtit rregull; ndryshon vetëm pragu i renditjes."
        )
        sensitivity_rows = [
            {
                "Pragu i renditjes": f"{scenario.get('quantile', 0):.0%}",
                "Tenderë": scenario.get("flagged_count"),
                "Pjesa e tenderëve": scenario.get("flagged_share"),
                "Ngjashmëria me përzgjedhjen bazë": scenario.get("membership_jaccard_vs_declared"),
            }
            for scenario in sorted(quantiles.values(), key=lambda value: value.get("quantile", 0))
        ]
        st.dataframe(
            fmt_columns(
                pd.DataFrame(sensitivity_rows),
                {"Tenderë": 0, "Pjesa e tenderëve": 4, "Ngjashmëria me përzgjedhjen bazë": 3},
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "Pjesa e tenderëve shprehet nga 0 në 1; 0,05 do të thotë 5%. "
            "Pragu 95% përzgjedh kryesisht 5% e tenderëve në krye të renditjes së secilit model."
        )

with tab_details:
    st.caption(
        "Këto matje ndihmojnë shqyrtimin akademik. Një etiketë e rregullave është "
        "një rezultat i llogaritur nga vetë sistemi, jo një shkelje e verifikuar."
    )
    with st.expander("Sa mirë i riprodhon klasifikuesi etiketat e rregullave?"):
        st.markdown(
            "Validimi i kryqëzuar e ndan grupin në pjesë për trajnim dhe testim. "
            "ROC-AUC dhe PR-AUC krahasohen me etiketat e rregullave. Vlerat e larta "
            "tregojnë se klasifikuesi riprodhon rregullat; nuk matin zbulimin e mashtrimit. "
            "Ky klasifikues përdoret për shpjegimin SHAP të rregullave."
        )
        st.caption(
            f"Pragu i etiketës së rregullave: {_metric_text(report.get('rule_label_threshold'), 1)}"
        )
        if cv.get("rocauc_mean") is None:
            st.info("Validimi i kryqëzuar nuk është i disponueshëm.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("ROC-AUC mesatare", _metric_text(cv.get("rocauc_mean"), 4))
            c2.metric("PR-AUC mesatare", _metric_text(cv.get("prauc_mean"), 4))
            c3.metric("Ndarje për testim", str(cv.get("n_splits", "—")))
            fig = go.Figure()
            for key, label, color in (
                ("rocauc_per_fold", "ROC-AUC", PALETTE["primary"]),
                ("prauc_per_fold", "PR-AUC", PALETTE["secondary"]),
            ):
                values = cv.get(key) or []
                fig.add_trace(
                    go.Bar(
                        name=label,
                        x=[str(i + 1) for i in range(len(values))],
                        y=values,
                        marker_color=color,
                        hovertemplate="Ndarja %{x}<br>%{y:.4f}<extra>%{fullData.name}</extra>",
                    )
                )
            fig.update_layout(
                barmode="group",
                height=300,
                xaxis_title="Ndarja për testim",
                yaxis_title="Matja kundrejt etiketave të rregullave",
                yaxis_range=[0, 1],
                legend={"orientation": "h", "y": 1.15},
                margin={"l": 10, "r": 15, "t": 40, "b": 15},
            )
            fig.update_layout(separators=", ")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Devijimi standard: ROC-AUC = {_metric_text(cv.get('rocauc_std'), 4)}; "
                f"PR-AUC = {_metric_text(cv.get('prauc_std'), 4)}."
            )

    with st.expander("Sa ngjajnë renditjet e modeleve me njëra-tjetrën?"):
        st.markdown(
            "Korrelacioni Spearman është 1 për renditje të njëjta dhe −1 për renditje "
            "të kundërta. Vlera pranë 0 tregon pak lidhje mes renditjeve. "
            "Dallimet nuk provojnë se kombinimi i modeleve është më i saktë."
        )
        if agree.get("spearman_matrix"):
            mat = pd.DataFrame(agree["spearman_matrix"]).round(2)
            labels = {name: family_labels.get(name.removesuffix("_score"), name) for name in mat}
            mat = mat.rename(index=labels, columns=labels)
            fig = px.imshow(
                mat, text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto"
            )
            fig.update_layout(
                height=480,
                coloraxis_colorbar_title="Spearman",
                margin={"l": 10, "r": 20, "t": 20, "b": 20},
            )
            fig.update_layout(separators=", ")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Mesatarja mes çifteve: {_metric_text(agree.get('mean_pairwise'))} · "
                f"Më e ulëta: {_metric_text(agree.get('min_pairwise'))} · "
                f"Më e larta: {_metric_text(agree.get('max_pairwise'))}"
            )
        else:
            st.info("Matrica e ngjashmërisë nuk është e disponueshme.")

    with st.expander("Sa ndryshojnë rezultatet kur hiqen disa tregues?"):
        st.markdown(
            "Modelet ritrajnohen me më pak tregues dhe krahasohen renditjet. "
            "Krahasimi i fushave para rezultatit të procedurës përdor sërish të njëjtin "
            "grup historik; nuk provon se modeli do të funksionojë në të ardhmen."
        )
        subsets = (report.get("deployed_score_feature_ablation") or {}).get("subsets") or {}
        subset_labels = {
            "raw_fact_only": "Vetëm treguesit bazë",
            "pre_outcome_fields_snapshot": "Pa fushat e rezultatit të procedurës",
        }
        if not subsets:
            st.info("Ky kontroll nuk është i disponueshëm.")
        for subset_name, subset in subsets.items():
            st.markdown(f"**{subset_labels.get(subset_name, subset_name)}**")
            family_rows = [
                {
                    "Modeli": family_labels.get(family, family),
                    "Korrelacioni i renditjeve": values.get("spearman_rank_correlation"),
                    "Jaccard për 5% në krye": values.get("top_5pct_jaccard"),
                    "Tenderë të përbashkët në krye": values.get("top_5pct_overlap_count"),
                }
                for family, values in (subset.get("families") or {}).items()
            ]
            if family_rows:
                st.dataframe(
                    fmt_columns(
                        pd.DataFrame(family_rows),
                        {
                            "Korrelacioni i renditjeve": 3,
                            "Jaccard për 5% në krye": 3,
                            "Tenderë të përbashkët në krye": 0,
                        },
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
            ensemble_comparison = subset.get("ensemble_comparison") or {}
            if ensemble_comparison:
                st.caption(
                    "Pikët e kombinuara · Korrelacioni: "
                    f"{_metric_text(ensemble_comparison.get('spearman_rank_correlation'))} · "
                    "Jaccard për 5% në krye: "
                    f"{_metric_text(ensemble_comparison.get('top_5pct_jaccard'))}"
                )
            st.caption("Treguesit teknikë: " + ", ".join(subset.get("features_used", [])))

    with st.expander("Kalibrimi kundrejt etiketës së rregullave"):
        st.markdown(
            "Vija krahason parashikimin e klasifikuesit me shpeshtësinë e etiketës së "
            "rregullave. ECE afër zeros tregon përputhje me këtë etiketë. "
            "As parashikimi dhe as ECE nuk janë probabilitet i një shkeljeje reale."
        )
        bins_df = pd.DataFrame(calib.get("bins") or [])
        if bins_df.empty or not {"mean_pred", "mean_actual"}.issubset(bins_df):
            st.info("Matjet e kalibrimit nuk janë të disponueshme.")
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=bins_df["mean_pred"],
                    y=bins_df["mean_actual"],
                    mode="lines+markers",
                    name="Klasifikuesi",
                    line={"color": PALETTE["primary"]},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[0, 1],
                    y=[0, 1],
                    mode="lines",
                    name="Përputhje e plotë",
                    line={"color": PALETTE["accent"], "dash": "dash"},
                )
            )
            fig.update_layout(
                height=360,
                xaxis_title="Parashikimi mesatar për etiketën e rregullave",
                yaxis_title="Pjesa me etiketë pozitive të rregullave",
                xaxis_range=[0, 1],
                yaxis_range=[0, 1],
                legend={"orientation": "h", "y": 1.15},
                margin={"l": 10, "r": 20, "t": 40, "b": 20},
            )
            fig.update_layout(separators=", ")
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Gabimi i kalibrimit (ECE)", _metric_text(calib.get("ece"), 4))

    with st.expander("Raporti i plotë i kontrolleve (JSON)"):
        st.json(report)
