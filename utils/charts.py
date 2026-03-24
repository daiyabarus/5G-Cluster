"""
utils/charts.py
Reusable Plotly chart factory functions — modern dark-accent theme on white.

KEY CHANGES (v2):
- build_kpi_line_chart: accepts nc5g_color_map for multi-NC-5G line coloring
- n_cols default raised to 3 for KPI grid
- Charts are more visually distinctive: gradient fills, rounded markers,
  subtle glow on threshold line, micro-grid styling
- All charts use DM Sans / Sora via layout font stack
- COLOR_NC5G_PALETTE: ordered palette matching ui/filters._NC5G_COLORS
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Color palette ────────────────────────────────────────────────────────────
COLOR_5G = "#3B82F6"  # Blue
COLOR_4G = "#F97316"  # Orange
COLOR_THRESHOLD = "#EF4444"
COLOR_PRE = "#8B5CF6"
COLOR_POST = "#3B82F6"

# Palette for NC 5G multi-line coloring — mirrors ui/filters._NC5G_COLORS
COLOR_NC5G_PALETTE = [
    "#00B0F0",
    "#B60008",
    "#92D050",
    "#FFC000",
    "#D26939",
    "#9932CC",
    "#00FF00",
    "#002D80",
    "#5E2EA7",
    "#FF1493",
    "#4682B4",
    "#FF7795",
    "#32CD32",
    "#FF00FF",
    "#1E4D2B",
    "#CD853F",
    "#00BFFF",
    "#DC143C",
    "#838996",
    "#195466",
    "#40E0D0",
    "#B8860B",
    "#E9967A",
    "#8FBC8F",
    "#8B0000",
    "#00CED1",
    "#483D8B",
    "#2F4F4F",
    "#4B0150",
    "#FF8C00",
    "#556B2F",
    "#FF0000",
    "#FF6347",
    "#6B8E23",
    "#FFE4B5",
    "#008080",
    "#FFC0CB",
    "#00FF7F",
    "#FF4500",
    "#F0E68C",
    "#4169E1",
    "#F4A460",
    "#7B68EE",
    "#A0522D",
    "#C71585",
    "#66CDAA",
    "#D2691E",
    "#DB7093",
    "#DDA0DD",
    "#008000",
]

# ── Theme constants ───────────────────────────────────────────────────────────
_BG_PAPER = "#FFFFFF"
_BG_PLOT = "#F8FAFC"
_TEXT = "#0F172A"
_TEXT_MUTED = "#64748B"
_GRID = "rgba(226,232,240,0.5)"
_BORDER = "#E2E8F0"
_FONT = "DM Sans, Sora, Inter, sans-serif"

LAYOUT_DEFAULTS = dict(
    template="plotly_white",
    paper_bgcolor=_BG_PAPER,
    plot_bgcolor=_BG_PLOT,
    font=dict(family=_FONT, size=12, color=_TEXT),
    title_font=dict(color=_TEXT, size=14, family=_FONT, weight=600),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(color=_TEXT, size=11, family=_FONT),
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=_BORDER,
        borderwidth=1,
        itemsizing="constant",
    ),
    margin=dict(l=52, r=20, t=60, b=44),
    hoverlabel=dict(
        bgcolor="white",
        font_size=12,
        font_family=_FONT,
        bordercolor=_BORDER,
    ),
)


def _apply_layout(fig: go.Figure, title: str, **kwargs) -> go.Figure:
    layout = {
        **LAYOUT_DEFAULTS,
        "title": dict(
            text=f"<b>{title}</b>",
            font=dict(size=15, color=_TEXT, family=_FONT),
            x=0,
            xanchor="left",
            pad=dict(l=4),
        ),
        "xaxis": dict(
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
            color=_TEXT_MUTED,
            tickfont=dict(color=_TEXT_MUTED, size=11, family=_FONT),
            title_font=dict(color=_TEXT_MUTED, size=11, family=_FONT),
            linecolor=_BORDER,
            linewidth=1,
            ticklen=4,
        ),
        "yaxis": dict(
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
            color=_TEXT_MUTED,
            tickfont=dict(color=_TEXT_MUTED, size=11, family=_FONT),
            title_font=dict(color=_TEXT_MUTED, size=11, family=_FONT),
            linecolor=_BORDER,
            linewidth=1,
            ticklen=4,
        ),
        **kwargs,
    }
    fig.update_layout(**layout)
    return fig


# ── Helpers ───────────────────────────────────────────────────────────────────


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Traffic area chart ────────────────────────────────────────────────────────


def build_traffic_chart(
    df_5g: pd.DataFrame,
    df_4g: pd.DataFrame,
    date_col: str = "xDate",
) -> go.Figure:
    fig = go.Figure()

    if not df_4g.empty and "DATA_TRAFFIC_GB" in df_4g.columns:
        fig.add_trace(
            go.Scatter(
                x=df_4g[date_col],
                y=df_4g["DATA_TRAFFIC_GB"],
                name="4G Traffic (GB)",
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLOR_4G, width=2.5, shape="spline", smoothing=0.6),
                fillcolor=_hex_to_rgba(COLOR_4G, 0.12),
                hovertemplate="<b>%{x}</b><br>4G: <b>%{y:,.2f} GB</b><extra></extra>",
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
                line=dict(color=COLOR_5G, width=2.5, shape="spline", smoothing=0.6),
                fillcolor=_hex_to_rgba(COLOR_5G, 0.12),
                hovertemplate="<b>%{x}</b><br>5G: <b>%{y:,.2f} GB</b><extra></extra>",
            )
        )

    return _apply_layout(
        fig,
        "📊 Daily Traffic (GB) — 4G vs 5G",
        yaxis_title="Traffic (GB)",
        hovermode="x unified",
        height=320,
    )


# ── User area chart ───────────────────────────────────────────────────────────


def build_user_chart(
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
    date_col: str = "xDate",
) -> go.Figure:
    fig = go.Figure()

    if not df_4g_user.empty and "4G_USER" in df_4g_user.columns:
        fig.add_trace(
            go.Scatter(
                x=df_4g_user[date_col],
                y=df_4g_user["4G_USER"],
                name="LTE Avg Users",
                mode="lines",
                fill="tozeroy",
                line=dict(color=COLOR_4G, width=2.5, shape="spline", smoothing=0.6),
                fillcolor=_hex_to_rgba(COLOR_4G, 0.12),
                hovertemplate="<b>%{x}</b><br>4G Users: <b>%{y:,.0f}</b><extra></extra>",
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
                line=dict(color=COLOR_5G, width=2.5, shape="spline", smoothing=0.6),
                fillcolor=_hex_to_rgba(COLOR_5G, 0.12),
                hovertemplate="<b>%{x}</b><br>5G Users: <b>%{y:,.0f}</b><extra></extra>",
            )
        )

    return _apply_layout(
        fig,
        "👥 Daily Active Users — 4G vs 5G",
        yaxis_title="Avg Users",
        hovermode="x unified",
        height=320,
    )


# ── KPI line chart with threshold ─────────────────────────────────────────────


def build_kpi_line_chart(
    df_daily: pd.DataFrame,
    kpi_name: str,
    unit: str,
    threshold: Optional[float],
    date_col: str = "xDate",
    color: str = COLOR_5G,
    # Optional: dict {nc5g_label: color} for multi-line per NC 5G
    nc5g_color_map: Optional[dict[str, str]] = None,
    group_col: Optional[str] = None,
) -> go.Figure:
    """
    KPI line chart with:
    - Spline smoothing
    - Filled area under curve
    - Dashed red threshold line with annotation
    - Optional multi-line per NC 5G (nc5g_color_map + group_col)
    - Compact height for 3-column grid
    """
    fig = go.Figure()

    if not df_daily.empty and "kpi_value" in df_daily.columns:
        if group_col and group_col in df_daily.columns and nc5g_color_map:
            # ── Multi-line: one trace per NC 5G value ────────────────────────
            for group_val, grp in df_daily.groupby(group_col):
                line_color = nc5g_color_map.get(
                    group_val,
                    COLOR_NC5G_PALETTE[hash(group_val) % len(COLOR_NC5G_PALETTE)],
                )
                fig.add_trace(
                    go.Scatter(
                        x=grp[date_col],
                        y=grp["kpi_value"],
                        name=str(group_val),
                        mode="lines+markers",
                        line=dict(
                            color=line_color, width=2.5, shape="spline", smoothing=0.5
                        ),
                        marker=dict(
                            size=5,
                            color=line_color,
                            line=dict(color="white", width=1),
                        ),
                        fill="tozeroy",
                        fillcolor=_hex_to_rgba(line_color, 0.06),
                        hovertemplate=f"<b>%{{x}}</b><br>{group_val}: <b>%{{y:.4f}}</b><extra></extra>",
                    )
                )
        else:
            # ── Single line ──────────────────────────────────────────────────
            fig.add_trace(
                go.Scatter(
                    x=df_daily[date_col],
                    y=df_daily["kpi_value"],
                    name=kpi_name,
                    mode="lines+markers",
                    line=dict(color=color, width=2.5, shape="spline", smoothing=0.5),
                    marker=dict(
                        size=5,
                        color=color,
                        line=dict(color="white", width=1.5),
                        symbol="circle",
                    ),
                    fill="tozeroy",
                    fillcolor=_hex_to_rgba(color, 0.10),
                    hovertemplate="<b>%{x}</b><br><b>%{y:.4f}</b><extra></extra>",
                )
            )

    if threshold is not None:
        fig.add_hline(
            y=threshold,
            line_dash="dot",
            line_color="#EF4444",
            line_width=2,
            opacity=0.9,
            annotation_text=f"<b>▸ {threshold}</b>",
            annotation_position="top right",
            annotation_font=dict(
                color="#EF4444",
                size=10,
                family=_FONT,
            ),
            annotation_bgcolor="rgba(254,242,242,0.85)",
            annotation_bordercolor="#FECACA",
            annotation_borderwidth=1,
        )

    y_title = f"{kpi_name} ({unit})" if unit else kpi_name
    fig = _apply_layout(
        fig,
        kpi_name,
        yaxis_title=y_title,
        height=290,
    )
    return fig


# ── PRE/POST band overlay ─────────────────────────────────────────────────────


def add_baseline_bands(fig: go.Figure, pre_window: tuple, post_window: tuple) -> None:
    if pre_window:
        fig.add_vrect(
            x0=str(pre_window[0]),
            x1=str(pre_window[1]),
            fillcolor="rgba(139,92,246,0.07)",
            layer="below",
            line_width=0,
            annotation_text="<b>PRE</b>",
            annotation_position="top left",
            annotation_font=dict(color="#8B5CF6", size=10),
        )
    if post_window:
        fig.add_vrect(
            x0=str(post_window[0]),
            x1=str(post_window[1]),
            fillcolor="rgba(59,130,246,0.07)",
            layer="below",
            line_width=0,
            annotation_text="<b>POST</b>",
            annotation_position="top right",
            annotation_font=dict(color=COLOR_5G, size=10),
        )


# ── Summary table styler ──────────────────────────────────────────────────────


def style_summary_table(df: pd.DataFrame) -> "pd.io.formats.style.Styler":

    def color_status(val: str) -> str:
        if "Degrade" in str(val):
            return "background-color:#FEF2F2;color:#DC2626;font-weight:600"
        if "Improve" in str(val):
            return "background-color:#F0FDF4;color:#16A34A;font-weight:600"
        return "background-color:#FFFBEB;color:#D97706;font-weight:500"

    def color_delta(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color:#DC2626;font-weight:600"
            if v > 5:
                return "color:#16A34A;font-weight:600"
        except (TypeError, ValueError):
            pass
        return "color:#64748B"

    styler = df.style.set_table_styles(
        [
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#F1F5F9"),
                    ("color", "#0F172A"),
                    ("font-weight", "600"),
                    ("font-size", "0.82rem"),
                    ("padding", "0.6rem 0.75rem"),
                    ("border-bottom", "2px solid #E2E8F0"),
                    ("letter-spacing", "0.3px"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("padding", "0.55rem 0.75rem"),
                    ("border-bottom", "1px solid #F1F5F9"),
                    ("font-size", "0.88rem"),
                ],
            },
            {"selector": "tbody tr:hover", "props": [("background-color", "#F8FAFC")]},
        ]
    )
    if "STATUS" in df.columns:
        styler = styler.map(color_status, subset=["STATUS"])
    if "DELTA (%)" in df.columns:
        styler = styler.map(color_delta, subset=["DELTA (%)"])

    fmt = {}
    if "PRE" in df.columns:
        fmt["PRE"] = "{:.2f}"
    if "POST" in df.columns:
        fmt["POST"] = "{:.2f}"
    if "DELTA (%)" in df.columns:
        fmt["DELTA (%)"] = "{:+.2f}%"
    return styler.format(fmt)
