"""
ui/filters.py
Streamlit filter / selector panel.
Single Responsibility: renders and returns user selections only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from streamlit_extras.mandatory_date_range import date_range_picker

import streamlit as st

from config.database import ClickHouseConnection
from data.repository import fetch_regions, fetch_nc5g, fetch_site_ids


def render_filter_panel(conn: ClickHouseConnection) -> dict:
    """
    Render 4-column filter panel.
    Returns dict with keys: region, nc5g, site_ids, start_date, end_date, run_query
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

    # ── Column 2: NC 5G (depends on region) ──────────────────────────────────
    with col2:
        nc5g_options: list[str] = []
        if region and region != "— Select —":
            with st.spinner("Loading NC 5G…"):
                nc5g_options = fetch_nc5g(client, region)

        nc5g = st.selectbox(
            "📡 NC 5G",
            options=["— Select —"] + nc5g_options,
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
            # Fallback if streamlit-extras not installed
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
            width='stretch',
            type="primary",
            key="btn_run",
        )

    site_ids: list[str] = []
    if nc5g and nc5g != "— Select —":
        with st.spinner("Loading Site IDs…"):
            site_ids = fetch_site_ids(client, nc5g)

    return {
        "region": region if region != "— Select —" else None,
        "nc5g": nc5g if nc5g != "— Select —" else None,
        "site_ids": site_ids,
        "start_date": start_date,
        "end_date": end_date,
        "run_query": run_query,
    }
