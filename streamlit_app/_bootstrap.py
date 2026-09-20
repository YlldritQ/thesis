"""Shared bootstrap for every Streamlit page.

* Adds ``src/`` to ``sys.path`` so the ``thesis`` package imports resolve.
* Exposes Streamlit-cached data loaders.
* Provides shared helpers: filter sidebar, KPI rows, page header, the
  always-on "Anomalia ≠ mashtrim" disclaimer.

NB: code identifiers stay in English (industry convention); user-facing
strings are in Albanian.
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from _charts import (  # noqa: E402,F401
    category_label,
    fmt_eur,
    fmt_number,
    method_label,
    procedure_label,
)
from streamlit.errors import StreamlitPageNotFoundError  # noqa: E402

from thesis import paths  # noqa: E402,F401
from thesis.io import readers  # noqa: E402
from thesis.release import canonical_release_contract, validate_canonical_release  # noqa: E402

# ---------------------------------------------------------------- cached loads


def _release_token(manifest: Path) -> str:
    """Validate the release chain, then return its exact manifest cache key.

    Validation happens before Streamlit can return a cached frame. A changed
    artifact with an unchanged manifest therefore fails closed instead of
    remaining hidden behind a prior cache entry.
    """
    for stage in ("bronze", "silver", "gold", "benchmark", "ml"):
        if canonical_release_contract(stage).manifest.resolve() == manifest.resolve():
            return validate_canonical_release(
                stage,
                require_current_provenance=True,
            ).manifest_sha256
    raise ValueError(f"not a canonical release manifest: {manifest}")


@st.cache_data(show_spinner="Po ngarkohen tenderët…")
def _cached_tenders(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_silver_tenders()


def cached_tenders() -> pd.DataFrame:
    return _cached_tenders(_release_token(paths.SILVER_RELEASE))


@st.cache_data(show_spinner="Po ngarkohen vendimet e dhënies…")
def _cached_awards(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_silver_awards()


def cached_awards() -> pd.DataFrame:
    return _cached_awards(_release_token(paths.SILVER_RELEASE))


@st.cache_data(show_spinner="Po ngarkohet përmbledhja e tenderëve…")
def _cached_gold(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_gold_tenders()


def cached_gold() -> pd.DataFrame:
    return _cached_gold(_release_token(paths.ML_RELEASE))


@st.cache_data(show_spinner="Po ngarkohet përmbledhja e furnizuesve…")
def _cached_suppliers(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_gold_suppliers()


def cached_suppliers() -> pd.DataFrame:
    return _cached_suppliers(_release_token(paths.GOLD_RELEASE))


@st.cache_data(show_spinner="Po ngarkohen autoritetet kontraktuese…")
def _cached_entities(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_gold_entities()


def cached_entities() -> pd.DataFrame:
    return _cached_entities(_release_token(paths.GOLD_RELEASE))


@st.cache_data(show_spinner="po ngarkohen metrikat mujore ...")
def _cached_monthly(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_monthly()


def cached_monthly() -> pd.DataFrame:
    return _cached_monthly(_release_token(paths.GOLD_RELEASE))


@st.cache_data(show_spinner="po ngarkohen vlerat SHAP ...")
def _cached_shap(release_token: str) -> pd.DataFrame:
    del release_token
    return readers.load_shap_values()


def cached_shap() -> pd.DataFrame:
    return _cached_shap(_release_token(paths.ML_RELEASE))


@st.cache_data(show_spinner="po ngarkohen të dhënat e lidhura të panelit ...")
def _cached_dashboard_bundle(
    silver_release_token: str,
    gold_release_token: str,
    ml_release_token: str,
    include_shap: bool,
    include_model_metadata: bool,
) -> dict[str, Any]:
    del silver_release_token, gold_release_token, ml_release_token
    return readers.load_dashboard_bundle(
        include_shap=include_shap,
        include_model_metadata=include_model_metadata,
    )


def cached_dashboard_bundle(
    *,
    include_shap: bool = False,
    include_model_metadata: bool = False,
) -> dict[str, Any]:
    """Return cross-stage page inputs from one guarded release-chain read."""
    return _cached_dashboard_bundle(
        _release_token(paths.SILVER_RELEASE),
        _release_token(paths.GOLD_RELEASE),
        _release_token(paths.ML_RELEASE),
        include_shap,
        include_model_metadata,
    )


@st.cache_data(show_spinner="po ngarkohet raporti i validimit ...")
def _cached_validation_report(release_token: str) -> dict:
    del release_token
    return readers.load_validation_report()


def cached_validation_report() -> dict:
    return _cached_validation_report(_release_token(paths.ML_RELEASE))


# -------------------------------------------------------------------- filters

UNKNOWN_FILTER_OPTION = "E papërcaktuar"


def _is_missing_dimension(series: pd.Series) -> pd.Series:
    """Treat nulls and blank strings as the explicit missing-value bucket."""
    blank = series.astype("string").str.strip().eq("").fillna(False)
    return series.isna() | blank


def _selected_filter_mask(
    series: pd.Series, selected: list[object] | tuple[object, ...]
) -> pd.Series:
    """Return a dimension mask that preserves an explicit missing bucket.

    An empty selection retains the historical UI meaning of "all values".
    """
    if not selected:
        return pd.Series(True, index=series.index)
    include_missing = UNKNOWN_FILTER_OPTION in selected
    known = [value for value in selected if value != UNKNOWN_FILTER_OPTION]
    mask = series.isin(known)
    if include_missing:
        mask |= _is_missing_dimension(series)
    return mask.fillna(False)


def _dimension_options(series: pd.Series) -> list[object]:
    """Return sorted nonblank values plus the always-visible missing bucket."""
    values = [value for value in series.dropna().unique().tolist() if str(value).strip()]
    return [*sorted(values, key=lambda value: str(value)), UNKNOWN_FILTER_OPTION]


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Sidebar standarde me filtra: vit / kategori / metodë / autoritet.

    Filtrat ruhen ndërmjet faqeve përmes ``st.session_state``.
    """
    with st.sidebar:
        st.divider()
        st.markdown("### Kufizo të dhënat")
        st.caption("Pa përzgjedhje = të gjitha. Grafikët ndjekin filtrat e kësaj faqeje.")
        if st.button("Pastro filtrat", use_container_width=True):
            for key in (
                "filter_years",
                "filter_cats",
                "filter_methods",
                "filter_ent",
                "filter_value_min",
                "filter_value_max",
            ):
                st.session_state.pop(key, None)
        years = sorted([int(y) for y in df["year"].dropna().unique()])
        year_options = [*years, UNKNOWN_FILTER_OPTION]
        sel_years = st.multiselect(
            "Viti",
            year_options,
            key="filter_years",
            placeholder="Të gjitha vitet",
            help="Viti i publikimit. 'E papërcaktuar' përfshin tenderët pa datë publikimi.",
        )
        cats = _dimension_options(df["category"])
        sel_cats = st.multiselect(
            "Kategoria",
            cats,
            key="filter_cats",
            format_func=category_label,
            placeholder="Të gjitha kategoritë",
        )
        methods = _dimension_options(df["method"])
        sel_methods = st.multiselect(
            "Metoda sipas burimit",
            methods,
            key="filter_methods",
            format_func=method_label,
            placeholder="Të gjitha metodat",
            help="Klasifikimi i përgjithshëm në burim. Grafikët e procedurave përdorin edhe llojin e hollësishëm të procedurës.",
        )

        ent_names = sorted([str(x) for x in df["procuring_entity_name"].dropna().unique()])
        sel_ent = st.multiselect(
            "Autoriteti kontraktues",
            ent_names,
            key="filter_ent",
            placeholder="Të gjitha autoritetet",
            help="Lëre bosh për të gjitha.",
        )

        with st.expander("Vlera e parashikuar (€)"):
            min_value = st.number_input(
                "Nga (€)",
                min_value=0.0,
                value=None,
                step=1000.0,
                key="filter_value_min",
                placeholder="Pa kufi të poshtëm",
            )
            max_value = st.number_input(
                "Deri në (€)",
                min_value=0.0,
                value=None,
                step=1000.0,
                key="filter_value_max",
                placeholder="Pa kufi të sipërm",
            )
            st.caption("Kur vendos kufij, tenderët pa vlerë të publikuar përjashtohen.")
        if min_value is not None and max_value is not None and min_value > max_value:
            st.warning("Kufiri i poshtëm duhet të jetë më i vogël se kufiri i sipërm.")
            return df.iloc[:0].copy()

    out = df.copy()
    if sel_years:
        out = out[_selected_filter_mask(out["year"], sel_years)]
    if sel_cats:
        out = out[_selected_filter_mask(out["category"], sel_cats)]
    if sel_methods:
        out = out[_selected_filter_mask(out["method"], sel_methods)]
    if sel_ent:
        out = out[out["procuring_entity_name"].isin(sel_ent)]
    if "estimated_value_eur" in out.columns:
        if min_value is not None:
            out = out[out["estimated_value_eur"].ge(min_value)]
        if max_value is not None:
            out = out[out["estimated_value_eur"].le(max_value)]
    return out


# -------------------------------------------------------------------- helpers

CAVEAT_TEXT = (
    "**Anomalia ≠ mashtrim.** Sinjalet tregojnë raste për shqyrtim. "
    "Përfundimet kërkojnë verifikimin e dokumenteve të prokurimit."
)

STUDENT_DISCLAIMER = (
    "Projekt diplome bachelor · Të dhëna të një periudhe të caktuar, pa përditësim automatik. "
    "Paneli nuk është shërbim zyrtar i institucioneve."
)


def show_caveat(verbose: bool = False) -> None:
    """Mospranim i përhershëm: shenja anomalie nuk është gjetje mashtrimi."""
    if verbose:
        st.warning(CAVEAT_TEXT)
    else:
        st.caption(CAVEAT_TEXT)


def app_link(filename: str, label: str, *, sidebar: bool = False) -> None:
    """Use in-app navigation, with a link fallback for standalone page previews."""
    target = st.sidebar if sidebar else st
    path = ROOT / "streamlit_app" / filename
    try:
        target.page_link(str(path), label=label, use_container_width=True)
    except (StreamlitPageNotFoundError, KeyError):
        # Standalone page sessions and Streamlit AppTest can omit routing metadata.
        route = path.stem.split("_", 1)[-1] if filename != "Home.py" else ""
        target.markdown(
            f'<a class="nav-item" href="./{route}" target="_self">{escape(label)}</a>',
            unsafe_allow_html=True,
        )


def page_header(title: str, subtitle: str = "", caveat: bool = True) -> None:
    """Standard page header. Emits the 'anomaly ≠ fraud' caveat on EVERY page
    (review M-24/AM-01) unless the caller will render the verbose banner
    itself (pass ``caveat=False`` then call ``show_caveat(verbose=True)``)."""
    st.markdown(
        """<style>
      [data-testid="stSidebarNav"] {display:none}
      .block-container {padding-top:2.4rem; max-width:1500px}
      h1 {font-size:2.25rem !important; letter-spacing:-.04em; line-height:1.16 !important}
      h2 {font-size:1.5rem !important; letter-spacing:-.025em}
      h3 {font-size:1.13rem !important}
      [data-testid="stMetric"] {border:1px solid rgba(128,128,128,.22);border-radius:12px;padding:16px 18px;min-height:115px}
      [data-testid="stMetricValue"] {font-size:1.65rem;letter-spacing:-.025em}
      [data-testid="stMetricLabel"] {white-space:normal}
      [data-testid="stMetricLabel"] p {white-space:normal;overflow:visible}
      .brand {font-size:1.1rem;font-weight:750;letter-spacing:-.025em;margin-bottom:2px}
      .brand-note {font-size:.75rem;opacity:.65;margin-bottom:24px}
      .nav-heading {font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;opacity:.6;margin:20px 0 8px}
      .nav-item {display:block;text-decoration:none !important;color:inherit !important;padding:9px 12px;border-radius:7px;font-size:.89rem}
      .nav-item:hover {background:rgba(19,135,123,.12)}
      .nav-item[aria-current="page"] {background:rgba(19,135,123,.16);font-weight:650}
      .page-kicker {font-size:.73rem;letter-spacing:.12em;text-transform:uppercase;font-weight:650;margin-bottom:12px;opacity:.7}
      @media(max-width:700px) {h1 {font-size:1.8rem !important}.block-container {padding-top:1.4rem}}
    </style>""",
        unsafe_allow_html=True,
    )
    groups = [
        (
            "Analiza",
            [
                ("Home.py", "", "Ballina"),
                ("1_Overview.py", "Overview", "Përmbledhja"),
                ("2_Explore.py", "Explore", "Kërko tenderë"),
                ("3_Anomalies.py", "Anomalies", "Sinjalet për shqyrtim"),
                ("4_Entities.py", "Entities", "Autoritetet dhe furnizuesit"),
            ],
        ),
        (
            "Rreth analizës",
            [
                ("5_Methodology.py", "Methodology", "Si funksionon analiza"),
                ("6_Validation.py", "Validation", "Kontrollet e modeleve"),
                ("7_Krahasimi_i_Modeleve.py", "Krahasimi_i_Modeleve", "Krahasimi i modeleve"),
                ("8_Fjalori.py", "Fjalori", "Fjalori i termave"),
            ],
        ),
    ]
    # Self-assignment preserves filter values when visiting a page without widgets.
    for key in (
        "filter_years",
        "filter_cats",
        "filter_methods",
        "filter_ent",
        "filter_value_min",
        "filter_value_max",
    ):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    st.sidebar.markdown(
        '<div class="brand">Prokurimi në Kosovë</div><div class="brand-note">Të dhëna publike · Projekt diplome</div>',
        unsafe_allow_html=True,
    )
    for heading, links in groups:
        st.sidebar.markdown(f'<div class="nav-heading">{heading}</div>', unsafe_allow_html=True)
        for filename, route, label in links:
            app_link(f"pages/{filename}" if route else filename, label, sidebar=True)
    st.markdown(
        '<div class="page-kicker">Të dhënat e prokurimit publik</div>', unsafe_allow_html=True
    )
    st.markdown(f"# {escape(title)}")
    if subtitle:
        st.markdown(subtitle)
    if caveat:
        show_caveat(verbose=False)


def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, val, delta) in zip(cols, items):
        with col:
            st.metric(label, val, delta, delta_color="off")
