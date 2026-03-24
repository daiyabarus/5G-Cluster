"""
ui/filters.py
Streamlit filter / selector panel.
Single Responsibility: renders and returns user selections only.

CHANGES:
- NC 5G now uses st.multiselect — user can pick one or more NC 5G values.
- fetch_site_ids receives a list[str] instead of a single str.
- Color coding for selected NC 5G tags uses a consistent palette.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from streamlit_extras.mandatory_date_range import date_range_picker

import streamlit as st

from config.database import ClickHouseConnection
from data.repository import fetch_regions, fetch_nc5g, fetch_site_ids

# Palette for NC 5G multiselect tag colors (cycles if > 8 selections)
_NC5G_COLORS = [
    "#3B82F6",  # blue
    "#F97316",  # orange
    "#10B981",  # emerald
    "#8B5CF6",  # violet
    "#EC4899",  # pink
    "#14B8A6",  # teal
    "#F59E0B",  # amber
    "#EF4444",  # red
]


def render_filter_panel(conn: ClickHouseConnection) -> dict:
    """
    Render 4-column filter panel.
    Returns dict with keys:
        region, nc5g_list, site_ids, start_date, end_date, run_query
    """
    client = conn.get_client()
    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])

    # ── Column 1: REGION ──────────────────────────────────────────────────────
    with col1:
        with st.spinner("Loading regions…"):
            regions = fetch_regions(client)
        region = st.selectbox(
            "🌏 Region",
            options=["— Select —"] + regions,
            key="sel_region",
        )

    # ── Column 2: NC 5G multiselect (depends on region) ──────────────────────
    with col2:
        nc5g_options: list[str] = []
        if region and region != "— Select —":
            with st.spinner("Loading NC 5G…"):
                nc5g_options = fetch_nc5g(client, region)

        nc5g_list: list[str] = st.multiselect(
            "📡 NC 5G",
            options=nc5g_options,
            placeholder="Select one or more…",
            key="sel_nc5g",
            disabled=not nc5g_options,
        )

    # ── Column 3: Date range ──────────────────────────────────────────────────
    with col3:
        yesterday = date.today() - timedelta(days=1)
        default_start = yesterday - timedelta(days=29)

        try:
            result = date_range_picker(
                title="📅 Date Range",
                default_start=default_start,
                default_end=yesterday,
                max_date=date.today(),
                error_message="Please select both start and end date",
            )
            start_date, end_date = result if result else (default_start, yesterday)
        except ImportError:
            dates = st.date_input(
                "📅 Date Range",
                value=(default_start, yesterday),
                max_value=date.today(),
                key="date_range",
            )
            if isinstance(dates, (list, tuple)) and len(dates) == 2:
                start_date, end_date = dates
            else:
                start_date, end_date = default_start, yesterday

    with col4:
        st.write("")
        st.write("")
        run_query = st.button(
            "▶ Run",
            width="stretch",
            type="primary",
            key="btn_run",
        )

    # ── Fetch site IDs for all selected NC 5G values ──────────────────────────
    site_ids: list[str] = []
    if nc5g_list:
        with st.spinner(f"Loading Site IDs for {len(nc5g_list)} NC 5G cluster(s)…"):
            site_ids = fetch_site_ids(client, nc5g_list)

    # ── Inline color legend for selected NC 5G values ─────────────────────────
    if nc5g_list:
        badges = []
        for i, nc in enumerate(nc5g_list):
            color = _NC5G_COLORS[i % len(_NC5G_COLORS)]
            badges.append(
                f"<span style='background:{color};color:#fff;padding:2px 10px;"
                f"border-radius:12px;font-size:0.75rem;font-weight:600;"
                f"margin-right:6px'>{nc}</span>"
            )
        st.markdown(
            "<div style='margin-top:4px;margin-bottom:2px'>"
            + "".join(badges)
            + f"<span style='color:#94A3B8;font-size:0.75rem;margin-left:6px'>"
            f"→ {len(site_ids)} site(s)</span></div>",
            unsafe_allow_html=True,
        )

    return {
        "region": region if region != "— Select —" else None,
        "nc5g_list": nc5g_list,
        # backward-compat: single value or None
        "nc5g": nc5g_list[0] if len(nc5g_list) == 1 else (nc5g_list or None),
        "site_ids": site_ids,
        "start_date": start_date,
        "end_date": end_date,
        "run_query": run_query,
    }
