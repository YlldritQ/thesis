"""Plotly chart helpers — used by both Streamlit pages and notebooks.

Consistent palette, formatting, locale-aware EUR labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = {
    "primary": "#1f4e79",
    "secondary": "#bf6900",
    "accent": "#76787a",
    "good": "#2ca25f",
    "bad": "#c0392b",
    "neutral": "#7f8c8d",
}

CATEGORY_COLORS = {
    "goods": PALETTE["primary"],
    "services": PALETTE["secondary"],
    "works": PALETTE["good"],
}

METHOD_COLORS = {
    "open": PALETTE["primary"],
    "minimum": PALETTE["bad"],
    "limited": PALETTE["secondary"],
    "selective": PALETTE["accent"],
}


def fmt_eur(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "—"
    if abs(x) >= 1e9:
        return f"€{x / 1e9:,.2f} B"
    if abs(x) >= 1e6:
        return f"€{x / 1e6:,.2f} M"
    if abs(x) >= 1e3:
        return f"€{x / 1e3:,.1f} K"
    return f"€{x:,.0f}"


def kpi_chip(label: str, value: str, delta: str | None = None) -> dict:
    """Returns the dict needed for st.metric style usage from caller."""
    return {"label": label, "value": value, "delta": delta}


def time_series_volume(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly["release_date"],
            y=monthly["tenders"],
            name="tenderë",
            marker_color=PALETTE["primary"],
            opacity=0.85,
        )
    )
    if "roll12_median" in monthly.columns:
        fig.add_trace(
            go.Scatter(
                x=monthly["release_date"],
                y=monthly["roll12_median"],
                name="mesatarja rrëshqitëse 12-mujore",
                mode="lines",
                line={"color": PALETTE["bad"], "width": 2},
            )
        )
    fig.update_layout(
        title="Volumi i tenderëve ndër vite",
        height=380,
        xaxis_title=None,
        yaxis_title="tenderë / muaj",
        hovermode="x unified",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def time_series_value(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly["release_date"],
            y=monthly["value_mn"],
            name="EUR (mn)",
            marker_color=PALETTE["good"],
            opacity=0.85,
        )
    )
    fig.update_layout(
        title="Vlera e parashikuar e tenderëve ndër vite (EUR milionë)",
        height=380,
        xaxis_title=None,
        yaxis_title="EUR (mn)",
        hovermode="x unified",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def category_bar(df: pd.DataFrame, value_col: str, title: str) -> go.Figure:
    g = df.groupby("category")[value_col].sum().sort_values()
    fig = px.bar(
        g.reset_index(),
        x=value_col,
        y="category",
        orientation="h",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        text_auto=".2s",
    )
    fig.update_layout(
        title=title, height=320, showlegend=False, margin={"l": 20, "r": 20, "t": 50, "b": 20}
    )
    return fig


def method_bar(df: pd.DataFrame, value_col: str, title: str) -> go.Figure:
    g = df.groupby("method", dropna=False)[value_col].sum().sort_values()
    fig = px.bar(
        g.reset_index(),
        x=value_col,
        y="method",
        orientation="h",
        color="method",
        color_discrete_map=METHOD_COLORS,
        text_auto=".2s",
    )
    fig.update_layout(
        title=title, height=320, showlegend=False, margin={"l": 20, "r": 20, "t": 50, "b": 20}
    )
    return fig


def value_histogram(values: pd.Series, log: bool = True) -> go.Figure:
    v = values.dropna()
    v = v[v > 0]
    if log:
        v = np.log10(v)
        x_label = "log10(EUR)"
    else:
        x_label = "EUR"
    fig = px.histogram(v, nbins=60, color_discrete_sequence=[PALETTE["primary"]])
    fig.update_layout(
        title="Shpërndarja e vlerës së parashikuar" + (" (log)" if log else ""),
        height=300,
        showlegend=False,
        xaxis_title=x_label,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def lorenz_curve(values: pd.Series, label: str) -> go.Figure:
    v = values.dropna().sort_values().values
    if len(v) == 0:
        return go.Figure()
    cum_x = np.arange(1, len(v) + 1) / len(v)
    cum_y = np.cumsum(v) / v.sum()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=cum_x,
            y=cum_y,
            mode="lines",
            line={"color": PALETTE["primary"], "width": 2},
            name="Lorenz",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line={"color": PALETTE["accent"], "width": 1, "dash": "dash"},
            name="barazi e plotë",
        )
    )
    fig.update_layout(
        title=f"Kurba Lorenz — {label}",
        xaxis_title="pjesa kumulative e subjekteve",
        yaxis_title="pjesa kumulative e vlerës",
        height=380,
        hovermode="closest",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def top_n_bar(
    df: pd.DataFrame, name_col: str, value_col: str, n: int = 15, title: str = ""
) -> go.Figure:
    g = df.groupby(name_col)[value_col].sum().nlargest(n).sort_values()
    fig = px.bar(
        g.reset_index(),
        x=value_col,
        y=name_col,
        orientation="h",
        color_discrete_sequence=[PALETTE["primary"]],
        text_auto=".2s",
    )
    fig.update_layout(
        title=title,
        height=max(300, 25 * n + 100),
        showlegend=False,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def anomaly_score_hist(scores: pd.Series, threshold: float | None = None) -> go.Figure:
    fig = px.histogram(scores.dropna(), nbins=50, color_discrete_sequence=[PALETTE["primary"]])
    if threshold is not None:
        fig.add_vline(
            x=threshold,
            line_dash="dash",
            line_color=PALETTE["bad"],
            annotation_text=f"pragu={threshold:.2f}",
            annotation_position="top right",
        )
    fig.update_layout(
        title="Shpërndarja e pikëve të anomalive",
        height=320,
        showlegend=False,
        xaxis_title="pikë",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def shap_waterfall(
    feature_names: list[str], values: np.ndarray, base_value: float, x_value: float, title: str = ""
) -> go.Figure:
    """Custom waterfall — independent of shap.plots.waterfall (matplotlib)."""
    order = np.argsort(np.abs(values))[::-1]
    feature_names = [feature_names[i] for i in order]
    values = values[order]
    colors = [PALETTE["bad"] if v > 0 else PALETTE["good"] for v in values]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=feature_names,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.3f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=title
        or f"SHAP i proxy-t të rregullave (dalja log-odds={x_value:.3f}, baza={base_value:.3f})",
        height=max(280, 28 * len(feature_names) + 100),
        xaxis_title="kontributi në daljen log-odds të modelit proxy të rregullave",
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


def ensemble_contribution_bar(explanation: pd.DataFrame, title: str = "") -> go.Figure:
    """Plot exact additive components prepared by ``HybridEnsembleComposition``."""
    required = {
        "component_label",
        "component_type",
        "value_in_formula",
        "weight",
        "direct_contribution",
    }
    missing = sorted(required.difference(explanation.columns))
    if missing:
        raise ValueError(f"ensemble explanation columns are missing: {missing}")
    colors = {
        "detector_rank": PALETTE["primary"],
        "rule": PALETTE["secondary"],
        "context": PALETTE["good"],
    }
    view = explanation.copy()
    view["color"] = view["component_type"].map(colors).fillna(PALETTE["neutral"])
    fig = go.Figure(
        go.Bar(
            x=view["direct_contribution"],
            y=view["component_label"],
            orientation="h",
            marker_color=view["color"],
            customdata=np.column_stack([view["value_in_formula"], view["weight"]]),
            hovertemplate=(
                "%{y}<br>vlera në formulë=%{customdata[0]:.4f}"
                "<br>pesha=%{customdata[1]:.4f}"
                "<br>kontributi=%{x:.4f}<extra></extra>"
            ),
            text=[f"{value:.4f}" for value in view["direct_contribution"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=title or "Zbërthimi ekzakt i pikës së ansamblit",
        height=max(300, 48 * len(view) + 100),
        xaxis_title="kontributi ekzakt në ensemble_score",
        yaxis_title=None,
        showlegend=False,
        margin={"l": 20, "r": 30, "t": 50, "b": 20},
    )
    return fig
