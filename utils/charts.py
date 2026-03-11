"""
utils/charts.py
Reusable Plotly chart factory functions.
Open/Closed: add new chart types without modifying existing ones.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Color palette ─────────────────────────────────────────────────────────────
COLOR_5G = "#00B4D8"
COLOR_4G = "#FF6B35"
COLOR_THRESHOLD = "#FF2D2D"
COLOR_PRE = "#7B2D8B"
COLOR_POST = "#00B4D8"
COLOR_GRID = "rgba(255,255,255,0.08)"

# Slate-dark palette — matches CSS theme
_BG_PAPER = "#0F1523"  # app base
_BG_PLOT = "#161D2F"  # chart canvas (slightly lighter)
_TEXT = "#E2E8F0"  # primary text
_TEXT_MUTED = "#94A3B8"  # axis labels / legend
_GRID = "rgba(255,255,255,0.055)"
_BORDER = "#2D3A55"

LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor=_BG_PAPER,
    plot_bgcolor=_BG_PLOT,
    font=dict(family="Inter, sans-serif", size=12, color=_TEXT),
    title_font=dict(color=_TEXT, size=14, family="Inter, sans-serif"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color=_TEXT, size=11),
        bgcolor="rgba(22,29,47,0.85)",
        bordercolor=_BORDER,
        borderwidth=1,
    ),
    margin=dict(l=48, r=24, t=52, b=36),
    xaxis=dict(
        gridcolor=_GRID,
        showgrid=True,
        zeroline=False,
        color=_TEXT_MUTED,
        tickfont=dict(color=_TEXT_MUTED, size=11),
        title_font=dict(color=_TEXT_MUTED, size=11),
        linecolor=_BORDER,
        linewidth=1,
    ),
    yaxis=dict(
        gridcolor=_GRID,
        showgrid=True,
        zeroline=False,
        color=_TEXT_MUTED,
        tickfont=dict(color=_TEXT_MUTED, size=11),
        title_font=dict(color=_TEXT_MUTED, size=11),
        linecolor=_BORDER,
        linewidth=1,
    ),
)


def _apply_layout(fig: go.Figure, title: str, **kwargs) -> go.Figure:
    layout = {
        **LAYOUT_DEFAULTS,
        "title": dict(text=title, font=dict(size=16)),
        **kwargs,
    }
    fig.update_layout(**layout)
    return fig


# ── Traffic area chart ────────────────────────────────────────────────────────


def build_traffic_chart(
    df_5g: pd.DataFrame,
    df_4g: pd.DataFrame,
    date_col: str = "xDate",
) -> go.Figure:
    """Long area chart across full date range — no PRE/POST bands."""
    fig = go.Figure()

    if not df_4g.empty and "DATA_TRAFFIC_GB" in df_4g.columns:
        fig.add_trace(
            go.Scatter(
                x=df_4g[date_col],
                y=df_4g["DATA_TRAFFIC_GB"],
                name="4G Traffic (GB)",
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLOR_4G, width=2),
                fillcolor="rgba(255,107,53,0.25)",
            )
        )

    if not df_5g.empty and "5G_TRAFFIC_GB" in df_5g.columns:
        fig.add_trace(
            go.Scatter(
                x=df_5g[date_col],
                y=df_5g["5G_TRAFFIC_GB"],
                name="5G Traffic (GB)",
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLOR_5G, width=2),
                fillcolor="rgba(0,180,216,0.25)",
            )
        )

    return _apply_layout(
        fig, "📶 Daily Traffic (GB) — 4G vs 5G", yaxis_title="Traffic (GB)"
    )


# ── User area chart ───────────────────────────────────────────────────────────


def build_user_chart(
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
    date_col: str = "xDate",
) -> go.Figure:
    """Long area chart across full date range — no PRE/POST bands."""
    fig = go.Figure()

    if not df_4g_user.empty and "4G_USER" in df_4g_user.columns:
        fig.add_trace(
            go.Scatter(
                x=df_4g_user[date_col],
                y=df_4g_user["4G_USER"],
                name="LTE Avg Users",
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLOR_4G, width=2),
                fillcolor="rgba(255,107,53,0.25)",
            )
        )

    if not df_5g_user.empty and "5G_USER" in df_5g_user.columns:
        fig.add_trace(
            go.Scatter(
                x=df_5g_user[date_col],
                y=df_5g_user["5G_USER"],
                name="5G Avg Users",
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLOR_5G, width=2),
                fillcolor="rgba(0,180,216,0.25)",
            )
        )

    return _apply_layout(
        fig, "👥 Daily Active Users — 4G vs 5G", yaxis_title="Avg Users"
    )


# ── KPI line chart with threshold ─────────────────────────────────────────────


def build_kpi_line_chart(
    df_daily: pd.DataFrame,
    kpi_name: str,
    unit: str,
    threshold: Optional[float],
    date_col: str = "xDate",
    color: str = COLOR_5G,
) -> go.Figure:
    """
    Long line chart across full date range.
    Shows threshold line if defined — no PRE/POST shaded bands.
    """
    fig = go.Figure()

    if not df_daily.empty and "kpi_value" in df_daily.columns:
        fig.add_trace(
            go.Scatter(
                x=df_daily[date_col],
                y=df_daily["kpi_value"],
                name=kpi_name,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=5),
                hovertemplate="%{x}<br><b>%{y:.4f}</b><extra></extra>",
            )
        )

    if threshold is not None:
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color=COLOR_THRESHOLD,
            annotation_text=f"Target: {threshold}",
            annotation_position="top right",
            annotation_font_color=COLOR_THRESHOLD,
        )

    y_title = f"{kpi_name} ({unit})" if unit else kpi_name
    return _apply_layout(fig, kpi_name, yaxis_title=y_title, height=320)


# ── Multi-KPI grid (for 5G/4G KPI sections) ──────────────────────────────────


def build_kpi_grid(
    kpi_daily_map: dict[str, pd.DataFrame],
    kpi_meta_map: dict,
    n_cols: int = 2,
    color: str = COLOR_5G,
) -> list[go.Figure]:
    """
    Returns list of (kpi_name, figure) tuples — long charts, no PRE/POST bands.
    Caller renders them in a Streamlit column grid.
    """
    figs = []
    for kpi_name, df_daily in kpi_daily_map.items():
        meta = kpi_meta_map.get(kpi_name, {})
        fig = build_kpi_line_chart(
            df_daily=df_daily,
            kpi_name=kpi_name,
            unit=meta.get("unit", "%"),
            threshold=meta.get("threshold"),
            color=color,
        )
        figs.append((kpi_name, fig))
    return figs


# ── Helpers ───────────────────────────────────────────────────────────────────


def add_baseline_bands(fig: go.Figure, pre_window: tuple, post_window: tuple) -> None:
    """
    Optionally overlay PRE/POST shaded bands on a figure.
    Called explicitly by summary-table context — NOT used by standard KPI charts.
    Charts are long/full-range with no PRE/POST bands.
    """
    if pre_window:
        fig.add_vrect(
            x0=str(pre_window[0]),
            x1=str(pre_window[1]),
            fillcolor="rgba(123,45,139,0.12)",
            layer="below",
            line_width=0,
            annotation_text="PRE",
            annotation_position="top left",
            annotation_font_color="#C678DD",
        )
    if post_window:
        fig.add_vrect(
            x0=str(post_window[0]),
            x1=str(post_window[1]),
            fillcolor="rgba(0,180,216,0.12)",
            layer="below",
            line_width=0,
            annotation_text="POST",
            annotation_position="top right",
            annotation_font_color=COLOR_5G,
        )


# ── Contributor table styling ─────────────────────────────────────────────────


def style_summary_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply color coding to the summary/contributor table."""

    def color_status(val: str) -> str:
        if "Degrade" in str(val):
            return "background-color: rgba(255,45,45,0.25); color: #FF6B6B"
        if "Improve" in str(val):
            return "background-color: rgba(0,200,100,0.2); color: #00C878"
        return "background-color: rgba(255,200,0,0.15); color: #FFD700"

    def color_delta(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color: #FF6B6B"
            if v > 5:
                return "color: #00C878"
        except (TypeError, ValueError):
            pass
        return "color: #FAFAFA"

    styler = df.style
    if "STATUS" in df.columns:
        styler = styler.applymap(color_status, subset=["STATUS"])
    if "DELTA (%)" in df.columns:
        styler = styler.applymap(color_delta, subset=["DELTA (%)"])
    return styler
