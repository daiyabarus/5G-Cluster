"""
utils/charts.py
Reusable Plotly chart factory functions for white background theme.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Modern color palette for white background ─────────────────────────────────
COLOR_5G = "#3B82F6"  # Blue
COLOR_4G = "#F97316"  # Orange
COLOR_THRESHOLD = "#EF4444"  # Bright Red - explicit
COLOR_PRE = "#8B5CF6"  # Purple
COLOR_POST = "#3B82F6"  # Blue

# Clean white theme colors
_BG_PAPER = "#FFFFFF"  # Pure white background
_BG_PLOT = "#F8FAFC"  # Slightly off-white for plot area
_TEXT = "#0F172A"  # Dark slate for text
_TEXT_MUTED = "#64748B"  # Muted text for labels
_GRID = "rgba(226, 232, 240, 0.6)"  # Light gray grid lines
_BORDER = "#E2E8F0"  # Border color

LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    paper_bgcolor=_BG_PAPER,
    plot_bgcolor=_BG_PLOT,
    font=dict(family="Inter, sans-serif", size=12, color=_TEXT),
    title_font=dict(color=_TEXT, size=14, family="Inter, sans-serif", weight=600),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color=_TEXT, size=11),
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor=_BORDER,
        borderwidth=1,
        itemsizing="constant",
    ),
    margin=dict(l=48, r=24, t=64, b=48),
    hoverlabel=dict(
        bgcolor="white",
        font_size=12,
        font_family="Inter, sans-serif",
        bordercolor=_BORDER,
    ),
)


def _apply_layout(fig: go.Figure, title: str, **kwargs) -> go.Figure:
    layout = {
        **LAYOUT_DEFAULTS,
        "title": dict(
            text=f"<b>{title}</b>",
            font=dict(size=16, color=_TEXT),
            x=0,
            xanchor="left",
        ),
        "xaxis": dict(
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
            color=_TEXT_MUTED,
            tickfont=dict(color=_TEXT_MUTED, size=11),
            title_font=dict(color=_TEXT_MUTED, size=11, weight=500),
            linecolor=_BORDER,
            linewidth=1,
        ),
        "yaxis": dict(
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
            color=_TEXT_MUTED,
            tickfont=dict(color=_TEXT_MUTED, size=11),
            title_font=dict(color=_TEXT_MUTED, size=11, weight=500),
            linecolor=_BORDER,
            linewidth=1,
        ),
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
                line=dict(color=COLOR_4G, width=2.5),
                fillcolor=f"rgba(249, 115, 22, 0.15)",  # Orange with opacity
                hovertemplate="<b>%{x}</b><br>4G Traffic: %{y:,.2f} GB<extra></extra>",
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
                line=dict(color=COLOR_5G, width=2.5),
                fillcolor=f"rgba(59, 130, 246, 0.15)",  # Blue with opacity
                hovertemplate="<b>%{x}</b><br>5G Traffic: %{y:,.2f} GB<extra></extra>",
            )
        )

    return _apply_layout(
        fig, 
        "📊 Daily Traffic (GB) — 4G vs 5G", 
        yaxis_title="Traffic (GB)",
        hovermode="x unified",
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
                line=dict(color=COLOR_4G, width=2.5),
                fillcolor=f"rgba(249, 115, 22, 0.15)",  # Orange with opacity
                hovertemplate="<b>%{x}</b><br>4G Users: %{y:,.0f}<extra></extra>",
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
                line=dict(color=COLOR_5G, width=2.5),
                fillcolor=f"rgba(59, 130, 246, 0.15)",  # Blue with opacity
                hovertemplate="<b>%{x}</b><br>5G Users: %{y:,.0f}<extra></extra>",
            )
        )

    return _apply_layout(
        fig, 
        "👥 Daily Active Users — 4G vs 5G", 
        yaxis_title="Avg Users",
        hovermode="x unified",
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
                line=dict(color=color, width=4),
                marker=dict(size=6, color=color, line=dict(color="white", width=1)),
                hovertemplate="<b>%{x}</b><br>%{y:.4f}<extra></extra>",
            )
        )

    if threshold is not None:
        # Force red color with explicit RGBA
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#EF4444",  # Explicit red hex
            line_width=2.5,
            opacity=1.0,
            # annotation_text=f"<b>Target: {threshold}</b>",
            # annotation_position="top right",
            # annotation_font=dict(
            #     color="#EF4444",  # Explicit red
            #     size=11,
            #     family="Inter, sans-serif",
            #     weight="bold"
            # ),
            # annotation_bgcolor="rgba(255, 255, 255, 0.95)",
            # annotation_bordercolor="#EF4444",  # Red border
            # annotation_borderwidth=1,
        )

    y_title = f"{kpi_name} ({unit})" if unit else kpi_name
    
    # Apply layout
    fig = _apply_layout(fig, kpi_name, yaxis_title=y_title, height=320)
    
    # Post-processing: ensure threshold line is red
    if threshold is not None:
        # Update any shapes that might be threshold lines
        for shape in fig.layout.shapes:
            if hasattr(shape, 'line') and shape.line.dash == "dash":
                shape.line.color = "#EF4444"
        
        # Update annotations
        for annotation in fig.layout.annotations:
            if "Target:" in annotation.text:
                annotation.font.color = "#EF4444"
                annotation.bordercolor = "#EF4444"
    
    return fig


# ── Multi-KPI grid (for 5G/4G KPI sections) ──────────────────────────────────


def build_kpi_grid(
    kpi_daily_map: dict[str, pd.DataFrame],
    kpi_meta_map: dict,
    n_cols: int = 2,
    color: str = COLOR_5G,
) -> list[tuple[str, go.Figure]]:
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
    """
    if pre_window:
        fig.add_vrect(
            x0=str(pre_window[0]),
            x1=str(pre_window[1]),
            fillcolor="rgba(139, 92, 246, 0.08)",
            layer="below",
            line_width=0,
            annotation_text="<b>PRE</b>",
            annotation_position="top left",
            annotation_font=dict(color="#8B5CF6", size=11),
        )
    if post_window:
        fig.add_vrect(
            x0=str(post_window[0]),
            x1=str(post_window[1]),
            fillcolor="rgba(59, 130, 246, 0.08)",
            layer="below",
            line_width=0,
            annotation_text="<b>POST</b>",
            annotation_position="top right",
            annotation_font=dict(color=COLOR_5G, size=11),
        )


# ── Contributor table styling ─────────────────────────────────────────────────


def style_summary_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply color coding to the summary/contributor table with modern styling."""

    def color_status(val: str) -> str:
        if "Degrade" in str(val):
            return "background-color: #FEF2F2; color: #DC2626; font-weight: 500;"
        if "Improve" in str(val):
            return "background-color: #F0FDF4; color: #16A34A; font-weight: 500;"
        return "background-color: #FFFBEB; color: #D97706; font-weight: 500;"

    def color_delta(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color: #DC2626; font-weight: 600;"
            if v > 5:
                return "color: #16A34A; font-weight: 600;"
        except (TypeError, ValueError):
            pass
        return "color: #64748B;"

    styler = df.style.set_table_styles([
        {'selector': 'thead th', 
         'props': [('background-color', '#F8FAFC'), 
                   ('color', '#0F172A'),
                   ('font-weight', '600'),
                   ('font-size', '0.85rem'),
                   ('padding', '0.75rem'),
                   ('border-bottom', '2px solid #E2E8F0')]},
        {'selector': 'tbody td', 
         'props': [('padding', '0.75rem'),
                   ('border-bottom', '1px solid #F1F5F9')]},
        {'selector': 'tbody tr:hover', 
         'props': [('background-color', '#F8FAFC')]},
    ])
    
    if "STATUS" in df.columns:
        styler = styler.map(color_status, subset=["STATUS"])
    if "DELTA (%)" in df.columns:
        styler = styler.map(color_delta, subset=["DELTA (%)"])
    
    return styler.format({
        "PRE": "{:.2f}",
        "POST": "{:.2f}",
        "DELTA (%)": "{:+.2f}%",
    })