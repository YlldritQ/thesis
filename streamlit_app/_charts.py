"""Presentation-only charts and Albanian labels; published model inputs stay unchanged."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from thesis.domain.procedures import classify_procedure_series
from thesis.viz import PALETTE, ensemble_contribution_bar, shap_waterfall  # noqa: F401

CATEGORY_LABELS = {"goods": "Furnizime", "services": "Shërbime", "works": "Punë"}
METHOD_LABELS = {
    "open": "E hapur (klasifikimi i burimit)",
    "limited": "E kufizuar (klasifikimi i burimit)",
    "selective": "Përzgjedhëse (klasifikimi i burimit)",
    "minimum": "Vlerë minimale",
    "direct": "E drejtpërdrejtë",
}
PROCEDURE_LABELS = {
    "standard_open": "Procedurë e hapur",
    "restricted": "Procedurë e kufizuar",
    "price_quotation": "Kuotim i çmimeve",
    "minimum_value": "Vlerë minimale",
    "design_contest": "Konkurs projektimi",
    "negotiated_without_notice": "E negociuar pa publikim",
    "negotiated_with_notice": "E negociuar me publikim",
    "framework_mini_tender": "Mini-tender në marrëveshje kornizë",
    "selective": "Procedurë përzgjedhëse",
    "unknown": "E papërcaktuar",
}


def _label(value: object, labels: dict[str, str]) -> str:
    if pd.isna(value) or not str(value).strip():
        return "E papërcaktuar"
    return labels.get(str(value), str(value))


def category_label(value: object) -> str:
    return _label(value, CATEGORY_LABELS)


def method_label(value: object) -> str:
    return _label(value, METHOD_LABELS)


def procedure_label(value: object) -> str:
    return _label(value, PROCEDURE_LABELS)


def fmt_number(value: float | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}".translate(str.maketrans({",": " ", ".": ","}))


def fmt_eur(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    for threshold, suffix in ((1e9, "miliardë €"), (1e6, "milionë €"), (1e3, "mijë €")):
        if abs(value) >= threshold:
            return f"{fmt_number(value / threshold, 2 if threshold >= 1e6 else 1)} {suffix}"
    return f"{fmt_number(value)} €"


def fmt_datetime(value: object) -> str:
    """Show an ISO timestamp as «19.07.2026 12:28 UTC»; keep unparseable text as given."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "—"
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(stamp):
        return "—"
    if stamp.tzinfo is None:
        return stamp.strftime("%d.%m.%Y %H:%M")
    return stamp.tz_convert("UTC").strftime("%d.%m.%Y %H:%M UTC")


def fmt_columns(frame: pd.DataFrame, decimals: dict[str, int]) -> pd.DataFrame:
    """Display copy with Albanian number text (e.g. «0,375») in the named columns."""
    view = frame.copy()
    for column, digits in decimals.items():
        if column in view:
            view[column] = view[column].map(lambda value, d=digits: fmt_number(value, d))
    return view


SIGNAL_TYPE_LABELS = {
    "review": "Shqyrtim i tenderit",
    "data_quality": "Cilësia e të dhënave",
    "operational": "Ndjekja e procedurës",
}
RULE_TABLE_COLUMNS = {
    "code": "Kodi",
    "description": "Përshkrimi",
    "weight": "Pesha",
    "reference": "Referenca",
    "score_enabled": "Ndikon në pikë",
    "signal_type": "Lloji",
    "threshold_rationale": "Arsyetimi i pragut",
    "limitations": "Kufizimet",
}
RULE_TABLE_CAPTION = "Përshkrimet e rregullave janë në anglisht, si në kodin burimor."


def rule_table_sq(rules: pd.DataFrame) -> pd.DataFrame:
    """Albanian headers and labels for the published rule registry; values stay as published."""
    view = fmt_columns(rules, {"weight": 2})
    if "score_enabled" in view:
        view["score_enabled"] = view["score_enabled"].map({True: "Po", False: "Jo"})
    if "signal_type" in view:
        view["signal_type"] = view["signal_type"].map(
            lambda value: SIGNAL_TYPE_LABELS.get(value, value)
        )
    return view.rename(columns=RULE_TABLE_COLUMNS)


def style_chart(fig: go.Figure, *, height: int = 350) -> go.Figure:
    fig.update_layout(
        height=height,
        separators=", ",
        font={"family": "sans-serif", "size": 12},
        margin={"l": 12, "r": 24, "t": 48 if fig.layout.title.text else 20, "b": 20},
        legend={"orientation": "h", "y": -0.22, "x": 0, "title_text": ""},
    )
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def monthly_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Recompute every time-series numerator and denominator from the selected rows.

    Unrepresented months stay missing, never evidence of zero national activity.
    Missing bidder lists do not count as zero bidders.
    """
    columns = [
        "release_date",
        "tenders",
        "value_mn",
        "single_bidder_pct",
        "zero_bidder_pct",
        "bidder_data_coverage_pct",
        "observed_bidders",
    ]
    dated = frame.dropna(subset=["release_date"]).copy()
    if dated.empty:
        return pd.DataFrame(columns=columns)
    dated = dated.set_index("release_date").sort_index()
    observed = (
        dated["bidder_data_observed"].fillna(False).astype(bool) & dated["num_bidders"].notna()
    )
    dated["observed"] = observed.astype(int)
    dated["single"] = dated["num_bidders"].eq(1).where(observed)
    dated["zero"] = dated["num_bidders"].eq(0).where(observed)
    grouped = dated.resample("MS")
    counts = grouped.size()
    result = pd.DataFrame(
        {
            "tenders": counts.where(counts.gt(0)),
            "value_mn": grouped["estimated_value_eur"].sum(min_count=1) / 1e6,
            "single_bidder_pct": grouped["single"].mean() * 100,
            "zero_bidder_pct": grouped["zero"].mean() * 100,
            "bidder_data_coverage_pct": grouped["observed"].mean() * 100,
            "observed_bidders": grouped["observed"].sum().where(counts.gt(0)),
        }
    )
    return result.reset_index()[columns]


def time_series_volume(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=monthly["release_date"],
            y=monthly["tenders"],
            name="Tenderë",
            marker_color=PALETTE["primary"],
            hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} tenderë<extra></extra>",
        )
    )
    fig.update_layout(
        title="Sa tenderë janë publikuar çdo muaj?",
        yaxis_title="Numri i tenderëve",
        xaxis_title=None,
    )
    fig.update_yaxes(tickformat=",~f")
    return style_chart(fig)


def time_series_value(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=monthly["release_date"],
            y=monthly["value_mn"],
            name="Vlera e parashikuar",
            marker_color="#13877b",
            hovertemplate="%{x|%m/%Y}<br>%{y:,.2f} milionë €<extra></extra>",
        )
    )
    fig.update_layout(
        title="Sa është vlera e parashikuar çdo muaj?", yaxis_title="Milionë euro", xaxis_title=None
    )
    return style_chart(fig)


def category_bar(df: pd.DataFrame, value_col: str, title: str) -> go.Figure:
    view = df.assign(category=df["category"].map(category_label))
    return top_n_bar(view, "category", value_col, n=5, title=title)


def method_bar(df: pd.DataFrame, value_col: str, title: str) -> go.Figure:
    view = df.assign(procedure=classify_procedure_series(df).map(procedure_label))
    return top_n_bar(view, "procedure", value_col, n=12, title=title)


def top_n_bar(
    df: pd.DataFrame, name_col: str, value_col: str, n: int = 15, title: str = ""
) -> go.Figure:
    view = df.assign(
        **{name_col: df[name_col].fillna("E papërcaktuar").replace("", "E papërcaktuar")}
    )
    grouped = view.groupby(name_col)[value_col].sum(min_count=1).dropna().nlargest(n).sort_values()
    currency = "eur" in value_col
    scale = 1e6 if currency and not grouped.empty and grouped.max() >= 1e6 else 1
    unit = "Milionë euro" if scale == 1e6 else ("Euro" if currency else "Numri i tenderëve")
    names = [str(name) for name in grouped.index]
    display_names = [name if len(name) <= 42 else name[:39] + "…" for name in names]
    # Numeric positions keep distinct long names separate even when their prefixes match.
    fig = go.Figure(
        go.Bar(
            x=grouped.values / scale,
            y=list(range(len(grouped))),
            orientation="h",
            marker_color=PALETTE["primary"],
            text=[fmt_eur(v) if currency else fmt_number(v) for v in grouped.values],
            customdata=names,
            textposition="auto",
            hovertemplate="%{customdata}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(title=title, xaxis_title=unit, yaxis_title=None)
    fig.update_xaxes(tickformat=",.0f")
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(grouped))), ticktext=display_names)
    return style_chart(fig, height=max(280, 32 * len(grouped) + 90))


def value_histogram(values: pd.Series, log: bool = True) -> go.Figure:
    """Familiar euro bands avoid asking readers to interpret logarithms."""
    del log
    valid = values.dropna()
    valid = valid[valid >= 0]
    labels = [
        "Nën 1 mijë €",
        "1–10 mijë €",
        "10–100 mijë €",
        "100 mijë–1 milion €",
        "1–10 milionë €",
        "10 milionë € e lart",
    ]
    bands = pd.cut(valid, bins=[0, 1e3, 1e4, 1e5, 1e6, 1e7, np.inf], labels=labels, right=False)
    counts = bands.value_counts(sort=False)
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=counts.values,
            marker_color=PALETTE["primary"],
            hovertemplate="%{x}<br>%{y:,.0f} tenderë<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title="Vlera e parashikuar", yaxis_title="Numri i tenderëve")
    fig.update_yaxes(tickformat=",~f")
    return style_chart(fig)


def lorenz_curve(values: pd.Series, label: str) -> go.Figure:
    valid = values.dropna().clip(lower=0).sort_values().to_numpy()
    fig = go.Figure()
    if len(valid) and valid.sum() > 0:
        fig.add_trace(
            go.Scatter(
                x=np.r_[0, np.arange(1, len(valid) + 1) / len(valid)],
                y=np.r_[0, np.cumsum(valid) / valid.sum()],
                mode="lines",
                name="Shpërndarja e vlerës",
                line={"color": PALETTE["primary"], "width": 3},
                hovertemplate="%{x:.0%} e subjekteve<br>%{y:.1%} e vlerës<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode="lines",
                name="Ndarje e barabartë",
                line={"color": PALETTE["neutral"], "dash": "dash"},
            )
        )
    else:
        fig.add_annotation(text="Nuk ka vlera pozitive për këtë krahasim.", showarrow=False)
    fig.update_layout(
        title=f"Si shpërndahet vlera? · {label}",
        xaxis_title="Pjesa e subjekteve, nga vlera më e vogël",
        yaxis_title="Pjesa e vlerës së përgjithshme",
    )
    fig.update_xaxes(tickformat=".0%", range=[0, 1])
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    return style_chart(fig, height=380)


def anomaly_score_hist(scores: pd.Series, threshold: float | None = None) -> go.Figure:
    fig = px.histogram(x=scores.dropna(), nbins=40, color_discrete_sequence=[PALETTE["primary"]])
    if threshold is not None:
        fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color=PALETTE["bad"],
            annotation_text=f"Pragu: {fmt_number(threshold, 2)}",
        )
    fig.update_layout(
        title="Si shpërndahen pikët e shqyrtimit?",
        xaxis_title="Pikët (0–1)",
        yaxis_title="Numri i tenderëve",
        showlegend=False,
    )
    fig.update_yaxes(tickformat=",~f")
    return style_chart(fig)
