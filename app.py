"""
app.py  ─  5G/4G Network KPI Dashboard
Entry point for: streamlit run app.py

Architecture:
  config/    → DB config, KPI definitions/thresholds
  data/      → ClickHouse queries (repository) + transformations (processor)
  ui/        → Streamlit widgets (filters, sections)
  utils/     → Plotly chart factories
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

# ── Ensure project root on sys.path ──────────────────────────────────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.database import ClickHouseConnection
from data.repository import (
    fetch_5g_list,
    fetch_4g_list,
    fetch_5g_kpi_day,
    fetch_5g_kpi_pa13,
    fetch_4g_kpi,
)
from data.processor import (
    enrich_5g_with_site,
    enrich_4g_with_site,
    compute_baseline_windows,
    compute_5g_daily_traffic,
    compute_4g_daily_traffic,
    compute_5g_daily_user,
    compute_4g_daily_user,
)
from ui.filters import render_filter_panel
from ui.sections import (
    render_overview_section,
    render_5g_kpi_section,
    render_4g_kpi_section,
    render_contributor_section,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Streamlit page config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="5G/4G Network KPI Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS — modern slate dark theme, fully legible dropdowns ─────────────
st.markdown(
    """
    <style>
    /* ── Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Base app background ── */
    .stApp                 { background-color: #0F1523; }
    .block-container       { padding-top: 1.2rem; max-width: 100% !important; }

    /* ── Sidebar (if ever used) ── */
    section[data-testid="stSidebar"] { background-color: #151C2C; }

    /* ── All core text — dark-on-light handled by Streamlit theme,
          we only override what breaks on dark background ── */
    .stMarkdown p, .stMarkdown li,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stText                { color: #E2E8F0; }

    /* ── Section headers (### markdown) ── */
    h3                     { color: #F0F4FF !important;
                             font-weight: 600; letter-spacing: 0.3px; }

    /* ── Selectbox: label above box ── */
    .stSelectbox label,
    .stDateInput  label,
    .stMultiSelect label   { color: #94A3B8 !important;
                             font-size: 0.8rem !important;
                             font-weight: 500 !important;
                             text-transform: uppercase;
                             letter-spacing: 0.5px; }

    /* ── Selectbox/input: the visible box (dark bg, light text) ── */
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] input,
    .stSelectbox [data-baseweb="select"] span,
    .stDateInput  input    { background-color: #1E2740 !important;
                             color: #E2E8F0 !important;
                             border: 1px solid #2D3A55 !important;
                             border-radius: 8px !important; }

    /* ── Dropdown popup menu (the list items) ── */
    [data-baseweb="popover"],
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"]   { background-color: #1E2740 !important;
                             border: 1px solid #2D3A55 !important;
                             border-radius: 8px !important; }
    [data-baseweb="menu"] li,
    [data-baseweb="option"] { color: #E2E8F0 !important;
                             background-color: #1E2740 !important; }
    [data-baseweb="option"]:hover,
    [data-baseweb="option"][aria-selected="true"]
                           { background-color: #263254 !important;
                             color: #60C8E8 !important; }

    /* ── Date input calendar popup ── */
    [data-baseweb="calendar"],
    [data-baseweb="datepicker-calendar"]
                           { background-color: #1E2740 !important;
                             color: #E2E8F0 !important; }

    /* ── Expander ── */
    details > summary,
    .streamlit-expanderHeader
                           { background-color: #1A2235 !important;
                             color: #CBD5E0 !important;
                             border: 1px solid #2D3A55 !important;
                             border-radius: 8px !important;
                             padding: 0.5rem 1rem !important; }
    .streamlit-expanderContent
                           { background-color: #161D2F !important;
                             border: 1px solid #2D3A55 !important;
                             border-top: none !important;
                             border-radius: 0 0 8px 8px !important; }

    /* ── Tabs ── */
    div[data-baseweb="tab-list"]
                           { background-color: #161D2F !important;
                             border-bottom: 1px solid #2D3A55 !important;
                             border-radius: 8px 8px 0 0;
                             padding: 0 0.5rem; }
    button[data-baseweb="tab"]
                           { color: #94A3B8 !important;
                             font-weight: 500;
                             background: transparent !important;
                             border-radius: 6px 6px 0 0 !important; }
    button[data-baseweb="tab"]:hover
                           { color: #CBD5E0 !important;
                             background-color: #1E2740 !important; }
    button[data-baseweb="tab"][aria-selected="true"]
                           { color: #60C8E8 !important;
                             border-bottom: 2px solid #60C8E8 !important;
                             background: transparent !important; }

    /* ── Buttons ── */
    .stButton > button     { background: linear-gradient(135deg, #3B82F6, #1D4ED8);
                             color: #FFFFFF !important;
                             border: none; border-radius: 8px;
                             font-weight: 600; font-size: 0.9rem;
                             padding: 0.4rem 1.2rem;
                             transition: all 0.18s ease;
                             box-shadow: 0 2px 8px rgba(59,130,246,0.3); }
    .stButton > button:hover
                           { opacity: 0.88; transform: translateY(-1px);
                             box-shadow: 0 4px 12px rgba(59,130,246,0.45); }

    /* ── Metric cards ── */
    div[data-testid="stMetric"]
                           { background-color: #1A2235;
                             border: 1px solid #2D3A55;
                             border-radius: 10px;
                             padding: 0.8rem 1rem; }
    div[data-testid="stMetricLabel"]  { color: #94A3B8 !important; font-size: 0.78rem !important; }
    div[data-testid="stMetricValue"]  { color: #F0F4FF !important; font-size: 1.5rem !important; font-weight: 600 !important; }
    div[data-testid="stMetricDelta"]  { font-size: 0.78rem !important; }

    /* ── Caption ── */
    .stCaption, small      { color: #64748B !important; font-size: 0.78rem !important; }

    /* ── Alerts ── */
    .stAlert               { border-radius: 8px !important; }
    div[data-testid="stAlert"] p
                           { color: #E2E8F0 !important; }

    /* ── Spinner ── */
    .stSpinner p           { color: #94A3B8 !important; }

    /* ── Divider ── */
    .section-divider       { border: none;
                             border-top: 1px solid #1E2740;
                             margin: 1.5rem 0; }

    /* ── Dataframe border ── */
    [data-testid="stDataFrame"]
                           { border: 1px solid #2D3A55;
                             border-radius: 8px;
                             overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Singleton DB connection (cached across reruns) ────────────────────────────
@st.cache_resource(show_spinner=False)
def get_db_connection() -> ClickHouseConnection:
    return ClickHouseConnection()


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    # Header
    st.markdown(
        """
        <div style='display:flex; align-items:center; gap:12px; margin-bottom:0.5rem'>
          <span style='font-size:2rem'>📡</span>
          <div>
            <h1 style='margin:0; font-size:1.6rem; color:#FAFAFA'>
              5G / 4G Network KPI Dashboard
            </h1>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ── DB connection ─────────────────────────────────────────────────────────
    try:
        conn = get_db_connection()
    except Exception as exc:
        st.error(f"❌ Cannot connect to ClickHouse: {exc}")
        st.stop()

    # ── Filter panel ──────────────────────────────────────────────────────────
    filters = render_filter_panel(conn)

    st.divider()

    # ── Guard: require selections before running ──────────────────────────────
    if not filters["run_query"]:
        st.info(
            "⬆️  Select a Region, NC 5G and Date Range, then press **▶ Run** to load KPIs.",
            icon="ℹ️",
        )
        return

    if not filters["site_ids"]:
        st.warning(
            "No Site IDs found for the selected NC 5G. Please check the selection."
        )
        return

    site_ids = filters["site_ids"]
    start_date = filters["start_date"]
    end_date = filters["end_date"]

    # ── Compute baseline windows (half-split, silent) ────────────────────────
    pre_window, post_window = compute_baseline_windows(start_date, end_date)

    # ── Fetch reference lists ─────────────────────────────────────────────────
    with st.spinner("Loading 5G / 4G site lists…"):
        client = conn.get_client()
        df_5glist = fetch_5g_list(client, site_ids)
        df_4glist = fetch_4g_list(client, site_ids)

    if df_5glist.empty:
        st.error("No 5G sites found. Please verify site IDs in `ioh_adm.t_list_5g`.")
        return

    # ── Derive ID lists for KPI queries ──────────────────────────────────────
    nrbts_ids = df_5glist["nrbts"].dropna().astype(str).unique().tolist()
    mrbts_ids = (
        df_4glist["mrbts"].dropna().astype(str).unique().tolist()
        if not df_4glist.empty
        else []
    )

    # ── Fetch KPI data ────────────────────────────────────────────────────────
    with st.spinner("Querying 5G / 4G KPI data… (this may take a moment)"):
        df_5g_raw_day = fetch_5g_kpi_day(client, nrbts_ids, start_date, end_date)
        df_5g_raw_pa13 = fetch_5g_kpi_pa13(client, nrbts_ids, start_date, end_date)
        df_4g_raw = (
            fetch_4g_kpi(client, mrbts_ids, start_date, end_date)
            if mrbts_ids
            else _empty_df()
        )

    # ── Enrich with site_id ───────────────────────────────────────────────────
    df_5gday = enrich_5g_with_site(df_5g_raw_day, df_5glist)
    df_5gpa13 = enrich_5g_with_site(df_5g_raw_pa13, df_5glist)
    df_4g = enrich_4g_with_site(df_4g_raw, df_4glist)

    # Convert xDate to string for consistent plotting
    for df in [df_5gday, df_5gpa13, df_4g]:
        if not df.empty and "xDate" in df.columns:
            df["xDate"] = df["xDate"].astype(str)

    # ── Site list overview ────────────────────────────────────────────────────
    with st.expander(f"📋 Site List ({len(site_ids)} sites)", expanded=False):
        col_a, col_b = st.columns(2)
        col_a.markdown("**5G Sites**")
        col_a.dataframe(df_5glist, width='stretch', hide_index=True)
        col_b.markdown("**4G Sites**")
        col_b.dataframe(df_4glist, width='stretch', hide_index=True)

    # ── Aggregate for traffic / user charts ──────────────────────────────────
    df_5g_traffic = compute_5g_daily_traffic(df_5gpa13)
    df_4g_traffic = compute_4g_daily_traffic(df_4g)
    df_5g_user = compute_5g_daily_user(df_5gday)
    df_4g_user = compute_4g_daily_user(df_4g)

    # ─────────────────────────────────────────────────────────────────────────
    # CHART SECTIONS
    # ─────────────────────────────────────────────────────────────────────────

    render_overview_section(df_5g_traffic, df_4g_traffic, df_5g_user, df_4g_user)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    render_5g_kpi_section(df_5gpa13, df_5gday, pre_window, post_window)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    render_4g_kpi_section(df_4g, pre_window, post_window)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    render_contributor_section(df_5gpa13, df_5gday, df_4g, pre_window, post_window)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='text-align:center; color:#4A5568; font-size:0.75rem; padding:2rem 0 1rem'>
          5G/4G Network KPI Dashboard · Built with Streamlit & ClickHouse
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empty_df():
    import pandas as pd

    return pd.DataFrame()


if __name__ == "__main__":
    main()
