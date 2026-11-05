"""Model selection shown as an internal comparison, never as fraud accuracy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st
from _bootstrap import page_header
from _charts import fmt_columns, fmt_datetime, fmt_number

from thesis import paths
from thesis.anomaly.detectors import FAMILY_LABELS_SQ
from thesis.io import readers
from thesis.release import validate_canonical_release
from thesis.viz import PALETTE

st.set_page_config(
    page_title="Krahasimi i modeleve · Prokurimi në Kosovë", page_icon="🏁", layout="wide"
)
page_header(
    "🏁 Krahasimi i modeleve",
    "Modelet e përzgjedhura, qëndrueshmëria e rezultateve dhe kuptimi i matjeve të krahasimit.",
)


@st.cache_data(show_spinner="Po ngarkohen rezultatet e krahasimit…")
def load_benchmark_bundle(release_sha256: str) -> tuple[pd.DataFrame, dict]:
    # One release digest binds the leaderboard and selected configurations.
    del release_sha256
    return readers.load_benchmark_bundle()


if paths.BENCHMARK_RELEASE.exists():
    benchmark_release_sha256 = validate_canonical_release(
        "benchmark", require_current_provenance=True
    ).manifest_sha256
    lb, champions = load_benchmark_bundle(benchmark_release_sha256)
else:
    lb, champions = pd.DataFrame(), {}

if lb.empty:
    st.info("Rezultatet e krahasimit të modeleve nuk janë të disponueshme.")
    with st.expander("Udhëzime për mirëmbajtjen"):
        st.code("thesis pipeline benchmark", language="bash")
        st.caption(
            "Ekzekutimi i plotë mund të zgjasë. Prova --quick nuk zëvendëson rezultatet e plota."
        )
    st.stop()

# Display-only spelling fix for a released label (Albanian sentence case).
lb["family_label_sq"] = lb["family_label_sq"].replace(
    {"Regresion Logjistik": "Regresion logjistik"}
)
unsup = lb[lb["kind"] == "unsupervised"].copy()
sup = lb[lb["kind"] == "supervised"].copy()
selected_families = champions.get("ensemble_families") or []
protocol = champions.get("benchmark_protocol") or {}
election_settings = protocol.get("election_settings") or {}
thresholds = protocol.get("thresholds") or {}
train_end = election_settings.get("benchmark_oot_train_max_year", 2023)
test_start = int(train_end) + 1
precision_k = thresholds.get("benchmark_precision_at", 500)

st.info(
    "Krahasimi mat qëndrueshmërinë dhe përputhjen me etiketa të nxjerra nga rregullat. "
    "Nuk ka shkelje të konfirmuara si bazë testimi, prandaj rezultatet nuk tregojnë "
    "cili model zbulon më saktë mashtrimin."
)
c1, c2, c3 = st.columns(3)
c1.metric("Konfigurime të krahasuara", fmt_number(len(lb)))
c2.metric("Familje modelesh", str(lb["family"].nunique()))
c3.metric("Modele të përzgjedhura", str(len(selected_families)))
if selected_families:
    st.markdown(
        "**Modelet që përdoren së bashku:** "
        + ", ".join(FAMILY_LABELS_SQ.get(family, family) for family in selected_families)
    )

tab_selection, tab_supervised, tab_details = st.tabs(
    ["Përzgjedhja e modeleve", "Riprodhimi i rregullave", "Metoda dhe hollësitë"]
)

with tab_selection:
    st.subheader("Cili konfigurim u rendit i pari në secilën familje modelesh?")
    st.caption(
        "Shfaqet konfigurimi me pikët më të larta në secilën familje modelesh. Pikët përmbledhin "
        "tri matje të brendshme; shiriti më i gjatë nuk do të thotë më shumë "
        "shkelje të zbuluara."
    )
    if unsup.empty:
        st.info(
            "Nuk ka rezultate për modelet e mësimit të pambikëqyrur, që identifikojnë raste të pazakonta."
        )
    else:
        # Keep an actual configuration row; groupby.first() could mix metrics
        # across rows when the best configuration has a missing measurement.
        best_per_family = (
            unsup.sort_values("composite", ascending=False).drop_duplicates("family").copy()
        )
        best_per_family["Përzgjedhja"] = best_per_family["family"].map(
            lambda family: (
                "Përdoret në kombinim" if family in selected_families else "Vetëm për krahasim"
            )
        )
        fig = px.bar(
            best_per_family.sort_values("composite"),
            x="composite",
            y="family_label_sq",
            orientation="h",
            color="Përzgjedhja",
            color_discrete_map={
                "Përdoret në kombinim": PALETTE["primary"],
                "Vetëm për krahasim": PALETTE["neutral"],
            },
            text_auto=".3f",
            labels={"composite": "Pikët e krahasimit (0–1)", "family_label_sq": "Modeli"},
            hover_data={"params": False, "family_label_sq": True, "composite": ":.3f"},
        )
        fig.update_layout(
            height=max(360, 45 * len(best_per_family)),
            xaxis_range=[0, 1],
            yaxis_title=None,
            legend={"orientation": "h", "y": 1.13, "title": None},
            margin={"l": 10, "r": 20, "t": 45, "b": 20},
        )
        fig.update_traces(hovertemplate="%{y}<br>Pikët e krahasimit: %{x:.3f}<extra></extra>")
        fig.update_layout(separators=", ")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Pikët = 45% përputhje me etiketat sipas rregullave (AUC) + "
            "35% ngjashmëri e përzgjedhjeve pas ritrajnimit (Jaccard) + "
            "20% qëndrueshmëri kur ndryshon rastësia gjatë trajnimit. "
            "Peshat janë përcaktuar nga autori."
        )
        st.subheader("Si krahasohen tri matjet kryesore?")
        compact = best_per_family.sort_values("composite", ascending=False)[
            [
                "family_label_sq",
                "Përzgjedhja",
                "composite",
                "proxy_auc_07",
                "stability_jaccard",
                "seed_consistency",
            ]
        ]
        st.dataframe(
            fmt_columns(
                compact,
                {"composite": 3, "proxy_auc_07": 3, "stability_jaccard": 3, "seed_consistency": 3},
            ),
            hide_index=True,
            use_container_width=True,
            column_config={
                "family_label_sq": st.column_config.TextColumn("Modeli"),
                "composite": "Pikët e krahasimit",
                "proxy_auc_07": "Përputhja me rregullat (AUC)",
                "stability_jaccard": "Qëndrueshmëria (Jaccard)",
                "seed_consistency": "Qëndrueshmëria ndaj rastësisë",
            },
        )
        st.caption(
            "Jaccard: 1 = përzgjidhen të njëjtët tenderë, 0 = asnjë tender i përbashkët. "
            "Përputhja e lartë me rregullat tregon ngjashmëri me rregullat ekzistuese, "
            "jo saktësi kundrejt rasteve reale."
        )
        with st.expander("Të gjitha konfigurimet dhe parametrat"):
            columns = [
                "family_label_sq",
                "params",
                "composite",
                "proxy_auc_07",
                "proxy_auc_04",
                "precision_at_k",
                "stability_jaccard",
                "seed_consistency",
                "spearman_rule",
                "fit_seconds",
                "n_fits",
            ]
            st.dataframe(
                fmt_columns(
                    unsup.sort_values("composite", ascending=False).reindex(columns=columns),
                    {
                        "composite": 3,
                        "proxy_auc_07": 3,
                        "proxy_auc_04": 3,
                        "precision_at_k": 3,
                        "stability_jaccard": 3,
                        "seed_consistency": 3,
                        "spearman_rule": 3,
                        "fit_seconds": 1,
                        "n_fits": 0,
                    },
                ),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "family_label_sq": "Modeli",
                    "params": "Parametrat",
                    "composite": "Pikët e krahasimit",
                    "proxy_auc_07": "AUC ndaj rregullave ≥0,7",
                    "proxy_auc_04": "AUC ndaj rregullave ≥0,4",
                    "precision_at_k": f"Përputhja në {precision_k} vendet e para",
                    "stability_jaccard": "Jaccard",
                    "seed_consistency": "Qëndrueshmëria ndaj rastësisë",
                    "spearman_rule": "Spearman ndaj rregullave",
                    "fit_seconds": "Koha (sekonda)",
                    "n_fits": "Trajnime",
                },
            )
            st.download_button(
                "Shkarko tabelën e plotë (CSV)",
                data=unsup.to_csv(index=False).encode("utf-8-sig"),
                file_name="krahasimi_modeleve.csv",
                mime="text/csv",
            )
        with st.expander("Përputhja me rregullat kundrejt qëndrueshmërisë"):
            st.caption(
                "Çdo pikë është një konfigurim. Vendosni kursorin mbi të për të parë parametrat."
            )
            plot_frame = unsup.dropna(subset=["stability_jaccard", "proxy_auc_07"])
            if plot_frame.empty:
                st.info("Nuk ka matje të plota për këtë grafik.")
            else:
                fig = px.scatter(
                    plot_frame,
                    x="stability_jaccard",
                    y="proxy_auc_07",
                    color="family_label_sq",
                    hover_data=["params"],
                    labels={
                        "stability_jaccard": "Qëndrueshmëria (Jaccard)",
                        "proxy_auc_07": "Përputhja me rregullat ≥0,7 (AUC)",
                        "family_label_sq": "Modeli",
                        "params": "Parametrat",
                    },
                )
                fig.update_traces(marker={"size": 9})
                fig.update_layout(
                    height=420,
                    xaxis_range=[0, 1],
                    yaxis_range=[0, 1],
                    margin={"l": 10, "r": 20, "t": 20, "b": 20},
                )
                fig.update_layout(separators=", ")
                st.plotly_chart(fig, use_container_width=True)

with tab_supervised:
    st.subheader("Sa mirë i riprodhojnë klasifikuesit rregullat?")
    st.markdown(
        f"Modelet trajnohen me tenderët deri në vitin **{train_end}** dhe testohen "
        f"me tenderët nga **{test_start}** e tutje. Në të dyja bashkësitë, etiketat "
        "për krahasim përcaktohen nga vetë rregullat. Meqë modelet dhe rregullat përdorin "
        "informacion të ngjashëm, rezultate shumë të larta janë të pritshme."
    )
    st.caption(
        "Ky vlerësim me ndarje kohore nuk simulon përdorimin në kohë reale dhe nuk vërteton "
        "aftësinë për të zbuluar shkelje ose për të përgjithësuar rezultatet në të dhëna të reja."
    )
    if sup.empty:
        st.info("Nuk ka rezultate për klasifikuesit.")
    else:
        supervised_columns = ["family_label_sq", "oot_rocauc", "oot_prauc", "cv_rocauc_mean"]
        supervised_labels = {
            "family_label_sq": "Modeli",
            "params": "Parametrat",
            "oot_rocauc": f"ROC-AUC nga {test_start}",
            "oot_prauc": f"PR-AUC nga {test_start}",
            "oot_ece": f"Gabimi i kalibrimit (ECE) nga {test_start}",
            "cv_rocauc_mean": "ROC-AUC në vlerësimin e kryqëzuar",
            "cv_rocauc_std": "Devijimi standard i ROC-AUC (vlerësim i kryqëzuar)",
            "cv_prauc_mean": "PR-AUC në vlerësimin e kryqëzuar",
            "cv_brier_mean": "Treguesi Brier në vlerësimin e kryqëzuar",
            "fit_seconds": "Koha (sekonda)",
            "n_fits": "Trajnime",
        }
        supervised_decimals = {
            "oot_rocauc": 4,
            "oot_prauc": 4,
            "oot_ece": 4,
            "cv_rocauc_mean": 4,
            "cv_rocauc_std": 4,
            "cv_prauc_mean": 4,
            "cv_brier_mean": 4,
            "fit_seconds": 1,
            "n_fits": 0,
        }
        st.dataframe(
            fmt_columns(
                sup.sort_values("oot_rocauc", ascending=False, na_position="last").reindex(
                    columns=supervised_columns
                ),
                supervised_decimals,
            ),
            hide_index=True,
            use_container_width=True,
            column_config={column: supervised_labels[column] for column in supervised_columns},
        )
        st.caption(
            "Çdo rresht paraqet një konfigurim. Mungesa e vlerës tregon se matja nuk është kryer."
        )
        # Missing future-period evaluations must never be replaced by CV
        # and then relabelled as held-out evidence.
        temporal = sup.dropna(subset=["cv_rocauc_mean", "oot_rocauc"])
        if not temporal.empty:
            with st.expander("Krahaso ndarjen kohore me vlerësimin e kryqëzuar"):
                st.caption("Të dy boshtet matin përputhjen me etiketat sipas rregullave.")
                fig = px.scatter(
                    temporal,
                    x="cv_rocauc_mean",
                    y="oot_rocauc",
                    color="family_label_sq",
                    hover_data=["params"],
                    labels={
                        "cv_rocauc_mean": "ROC-AUC në vlerësimin e kryqëzuar",
                        "oot_rocauc": f"ROC-AUC në tenderët nga {test_start}",
                        "family_label_sq": "Modeli",
                        "params": "Parametrat",
                    },
                )
                fig.add_shape(
                    type="line",
                    x0=0,
                    y0=0,
                    x1=1,
                    y1=1,
                    line={"dash": "dash", "color": PALETTE["accent"]},
                )
                fig.update_layout(
                    height=400,
                    xaxis_range=[0, 1],
                    yaxis_range=[0, 1],
                    margin={"l": 10, "r": 20, "t": 20, "b": 20},
                )
                fig.update_layout(separators=", ")
                st.plotly_chart(fig, use_container_width=True)
        with st.expander("Parametrat dhe matjet e plota të klasifikuesve"):
            st.dataframe(
                fmt_columns(sup.reindex(columns=list(supervised_labels)), supervised_decimals),
                hide_index=True,
                use_container_width=True,
                column_config=supervised_labels,
            )

with tab_details:
    st.subheader("Si u bë përzgjedhja?")
    st.markdown(
        "Për secilën familje modelesh provohen disa konfigurime. Fillimisht përzgjidhet konfigurimi me "
        "pikët më të larta për çdo familje, pastaj familjet që do të përdoren në kombinim. "
        "Përzgjedhja bazohet në krahasime brenda bashkësisë së analizuar. "
        "Pikët dhe percentilet kanë kuptim vetëm në raport me këtë bashkësi të dhënash."
    )
    st.markdown(
        f"Kontrolli i qëndrueshmërisë përdor **{election_settings.get('benchmark_bootstrap_runs', '—')} "
        "ritrajnime me mostra të nxjerra sërish nga të dhënat**. Për modelet që varen nga rastësia "
        f"kryhen **{election_settings.get('benchmark_extra_seeds', '—')} përsëritje shtesë**, "
        "me vlera fillestare të ndryshme të gjeneratorit të numrave të rastësishëm. "
        "Ky numër i kufizuar përsëritjesh nuk jep intervale që matin pasigurinë."
    )
    with st.expander("Konfigurimet e përzgjedhura"):
        rows = [
            {
                "Modeli": FAMILY_LABELS_SQ.get(family, family),
                "Përdoret në kombinim": "Po" if family in selected_families else "Jo",
                "Parametrat": json.dumps(info.get("params", {})),
                "Pikët e krahasimit": info.get("composite"),
                "AUC ndaj rregullave": info.get("proxy_auc_07"),
                "Qëndrueshmëria": info.get("stability_jaccard"),
            }
            for family, info in (champions.get("unsupervised") or {}).items()
        ]
        if rows:
            st.dataframe(
                fmt_columns(
                    pd.DataFrame(rows).sort_values("Pikët e krahasimit", ascending=False),
                    {"Pikët e krahasimit": 3, "AUC ndaj rregullave": 3, "Qëndrueshmëria": 3},
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Konfigurimet e përzgjedhura nuk janë të disponueshme.")
        if champions.get("supervised_champion"):
            selected = champions["supervised_champion"]
            family = selected.get("family")
            family_labels = sup.drop_duplicates("family").set_index("family")["family_label_sq"]
            readable_family = family_labels.get(family, family) if family else "—"
            st.markdown(f"**Klasifikuesi i përzgjedhur:** {readable_family}")
            st.json(selected)
        if champions.get("explainer"):
            st.markdown(
                "**Modeli shpjegues SHAP** riprodhon etiketat sipas rregullave. "
                "Ai nuk shpjegon pikët e kombinuara dhe nuk është model i pavarur për zbulimin e anomalive."
            )
            st.json(champions["explainer"])

    with st.expander("A ndryshon përzgjedhja nëse ndryshojnë peshat?"):
        sensitivity = champions.get("model_election_sensitivity") or {}
        scenarios = sensitivity.get("alternate_weight_scenarios") or {}
        scenario_labels = {
            "balanced": "Pesha të balancuara",
            "stability_emphasis": "Më shumë peshë për qëndrueshmërinë",
            "proxy_emphasis": "Më shumë peshë për përputhjen me rregullat",
        }
        sensitivity_rows = [
            {
                "Skenari": scenario_labels.get(name, name),
                "Modelet e përzgjedhura": ", ".join(
                    FAMILY_LABELS_SQ.get(family, family)
                    for family in value.get("ensemble_families", [])
                ),
                "Jaccard ndaj përzgjedhjes bazë": value.get("top_k_jaccard_vs_declared"),
                "Konfigurime të ndryshuara": value.get("changed_family_configuration_count"),
            }
            for name, value in scenarios.items()
        ]
        precision = sensitivity.get("precision_at_k_ranking") or {}
        if precision:
            sensitivity_rows.append(
                {
                    "Skenari": f"Vetëm përputhja në {precision_k} vendet e para",
                    "Modelet e përzgjedhura": ", ".join(
                        FAMILY_LABELS_SQ.get(family, family)
                        for family in precision.get("ensemble_families", [])
                    ),
                    "Jaccard ndaj përzgjedhjes bazë": precision.get("top_k_jaccard_vs_declared"),
                    "Konfigurime të ndryshuara": None,
                }
            )
        if sensitivity_rows:
            st.dataframe(
                fmt_columns(
                    pd.DataFrame(sensitivity_rows),
                    {"Jaccard ndaj përzgjedhjes bazë": 3, "Konfigurime të ndryshuara": 0},
                ),
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Vlera 1 e treguesit Jaccard do të thotë se u zgjodhën të njëjtat familje modelesh. "
                "Ky është kontroll i ndikimit të peshave; nuk mat saktësinë e modeleve."
            )
        else:
            st.info("Skenarët alternativë nuk janë të disponueshëm.")

    with st.expander("Gjurmueshmëria dhe riprodhimi i analizës"):
        st.caption(f"Rezultatet u gjeneruan më: {fmt_datetime(champions.get('created_at'))}")
        st.markdown(
            "Tabelat, konfigurimet e përzgjedhura dhe skedarët e modeleve lidhen "
            "me të njëjtin version të të dhënave dhe të kodit. Kontrolli i integritetit "
            "kryhet përpara ngarkimit, në mënyrë që rezultatet nga ekzekutime të ndryshme të mos "
            "përzihen. Ky kontroll teknik nuk zëvendëson verifikimin e përfundimeve."
        )
        st.code(champions.get("composite_formula", ""), language="text")
        st.json(
            {
                "data_fingerprint": champions.get("data_fingerprint"),
                "protocol_fingerprint": champions.get("protocol_fingerprint"),
                "implementation_fingerprint": champions.get("implementation_fingerprint"),
                "protocol": protocol,
            }
        )
        st.caption("Dokumentet: docs/methodology.md dhe data/models/benchmark/leaderboard.md")
