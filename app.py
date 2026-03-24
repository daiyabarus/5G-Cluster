"""
app.py  ─  5G/4G Network KPI Dashboard
Entry point for: streamlit run app.py

CHANGES v2:
- render_filter_panel returns nc5g_list (list[str]) instead of a single string
- nc5g_list threaded through to render_5g_kpi_section for per-cluster line coloring
- Modern CSS: DM Sans font, refined color palette, subtle chart card shadows
- Guard updated: requires nc5g_list to be non-empty (multiselect)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="5G/4G KPI Dashboard",
    page_icon="🐧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Modern CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Sora:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    /* ── Base ── */
    .stApp                 { background-color: #F8FAFC; }
    .block-container       { padding-top: 1.5rem; max-width: 100% !important;
                              background-color: #F8FAFC; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background-color: #F1F5F9; }

    /* ── Text ── */
    .stMarkdown p, .stMarkdown li,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1E293B; }
    h1, h2, h3 { color: #0F172A !important; font-weight: 700;
                 font-family: 'Sora', sans-serif; }
    h3 { color: #1E293B !important; font-weight: 600;
         border-left: 3px solid #3B82F6; padding-left: 0.85rem;
         margin-top: 1.25rem; }
    h4 { color: #334155 !important; font-weight: 600;
         font-family: 'Sora', sans-serif; margin-top: 0.5rem; }

    /* ── Filter labels ── */
    .stSelectbox label, .stDateInput label,
    .stMultiSelect label { color: #64748B !important;
                           font-size: 0.78rem !important;
                           font-weight: 600 !important;
                           text-transform: uppercase; letter-spacing: 0.6px; }

    /* ── Inputs ── */
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div,
    .stDateInput input    { background-color: #FFFFFF !important;
                             color: #1E293B !important;
                             border: 1.5px solid #E2E8F0 !important;
                             border-radius: 10px !important;
                             box-shadow: 0 1px 3px rgba(0,0,0,0.04); }

    /* ── Multiselect tags ── */
    [data-baseweb="tag"] { border-radius: 8px !important;
                           font-size: 0.78rem !important;
                           font-weight: 600 !important; }

    /* ── Dropdown menu ── */
    [data-baseweb="popover"], [data-baseweb="menu"]
                           { background-color: #FFFFFF !important;
                             border: 1.5px solid #E2E8F0 !important;
                             border-radius: 12px !important;
                             box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    [data-baseweb="option"] { color: #1E293B !important;
                               background-color: #FFFFFF !important; }
    [data-baseweb="option"]:hover,
    [data-baseweb="option"][aria-selected="true"]
                           { background-color: #EFF6FF !important;
                             color: #2563EB !important; }

    /* ── Expander ── */
    details > summary, .streamlit-expanderHeader
                           { background-color: #FFFFFF !important;
                             color: #1E293B !important;
                             border: 1.5px solid #E2E8F0 !important;
                             border-radius: 12px !important;
                             padding: 0.7rem 1.2rem !important;
                             font-weight: 600; }
    .streamlit-expanderContent
                           { background-color: #FFFFFF !important;
                             border: 1.5px solid #E2E8F0 !important;
                             border-top: none !important;
                             border-radius: 0 0 12px 12px !important;
                             padding: 1rem !important; }

    /* ── Tabs ── */
    div[data-baseweb="tab-list"]
                           { background-color: #F1F5F9 !important;
                             border-bottom: 1.5px solid #E2E8F0 !important;
                             border-radius: 12px 12px 0 0;
                             padding: 0.4rem 0.4rem 0; }
    button[data-baseweb="tab"]
                           { color: #64748B !important; font-weight: 500;
                             background: transparent !important;
                             border-radius: 8px 8px 0 0 !important;
                             padding: 0.45rem 1rem; }
    button[data-baseweb="tab"]:hover { color: #2563EB !important; }
    button[data-baseweb="tab"][aria-selected="true"]
                           { color: #2563EB !important;
                             border-bottom: 2.5px solid #2563EB !important;
                             background: rgba(37,99,235,0.05) !important; }

    /* ── Primary Button ── */
    .stButton > button     { background: linear-gradient(135deg, #3B82F6, #2563EB);
                             color: #FFFFFF !important;
                             border: none; border-radius: 10px;
                             font-weight: 700; font-size: 0.9rem;
                             padding: 0.5rem 1.5rem;
                             transition: all 0.2s ease;
                             box-shadow: 0 4px 12px rgba(59,130,246,0.25); }
    .stButton > button:hover { transform: translateY(-1px);
                               box-shadow: 0 8px 20px rgba(59,130,246,0.35); }

    /* ── Download button ── */
    [data-testid="stDownloadButton"] > button
                           { background: #F8FAFC !important;
                             color: #3B82F6 !important;
                             border: 1.5px solid #BFDBFE !important;
                             border-radius: 8px !important;
                             font-weight: 600 !important;
                             font-size: 0.8rem !important;
                             padding: 0.35rem 0.75rem !important;
                             transition: all 0.15s ease; }
    [data-testid="stDownloadButton"] > button:hover
                           { background: #EFF6FF !important;
                             border-color: #93C5FD !important; }

    /* ── st.container(border=True) cards ── */
    [data-testid="stVerticalBlockBorderWrapper"]
                           { border: 1.5px solid #E2E8F0 !important;
                             border-radius: 14px !important;
                             background-color: #FFFFFF !important;
                             box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
                             padding: 0.75rem !important; }

    /* ── Metric cards ── */
    div[data-testid="stMetric"]
                           { background-color: #FFFFFF;
                             border: 1.5px solid #E2E8F0;
                             border-radius: 14px;
                             padding: 1rem 1.25rem;
                             box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
    div[data-testid="stMetricLabel"]
                           { color: #64748B !important; font-size: 0.82rem !important;
                             font-weight: 600; text-transform: uppercase;
                             letter-spacing: 0.4px; }
    div[data-testid="stMetricValue"]
                           { color: #0F172A !important; font-size: 1.9rem !important;
                             font-weight: 700 !important;
                             font-family: 'Sora', sans-serif; }

    /* ── DataFrames ── */
    [data-testid="stDataFrame"]
                           { border: 1.5px solid #E2E8F0;
                             border-radius: 12px;
                             overflow: hidden;
                             box-shadow: 0 1px 3px rgba(0,0,0,0.03); }

    /* ── Caption ── */
    .stCaption, small      { color: #94A3B8 !important; font-size: 0.78rem !important; }

    /* ── Alerts ── */
    .stAlert               { border-radius: 10px !important;
                             border: 1px solid #E2E8F0 !important; }

    /* ── Spinner ── */
    .stSpinner p           { color: #64748B !important; }

    /* ── Dividers ── */
    hr                     { border: none; border-top: 1px solid #E2E8F0; margin: 1.5rem 0; }
    .section-divider       { border: none; border-top: 2px solid #F1F5F9; margin: 1.75rem 0; }

    /* ── Dashboard header ── */
    .dashboard-header      { background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%);
                             padding: 1.25rem 1.75rem;
                             border-radius: 18px;
                             border: 1.5px solid #DBEAFE;
                             margin-bottom: 1.25rem;
                             box-shadow: 0 2px 8px rgba(59,130,246,0.06); }

    /* ── Footer ── */
    .dashboard-footer      { text-align: center; color: #94A3B8;
                             font-size: 0.78rem;
                             padding: 1.5rem 0 0.75rem;
                             border-top: 1px solid #E2E8F0; margin-top: 1.5rem; }

    /* ── Plotly transparency ── */
    .js-plotly-plot, .plotly, .plot-container
                           { background-color: transparent !important; }
    .main-svg              { background: transparent !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_db_connection() -> ClickHouseConnection:
    return ClickHouseConnection()


def main() -> None:
    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="dashboard-header">
            <div style='display:flex;align-items:center;gap:14px'>
                <span style='font-size:2rem;background:linear-gradient(135deg,#3B82F6,#2563EB);
                             width:52px;height:52px;display:flex;align-items:center;
                             justify-content:center;border-radius:16px;color:white;
                             box-shadow:0 4px 12px rgba(59,130,246,0.3)'>📡</span>
                <div>
                    <h1 style='margin:0;font-size:1.6rem;color:#0F172A;
                               font-family:Sora,sans-serif;font-weight:700;
                               letter-spacing:-0.02em'>5G / 4G Network KPI Dashboard</h1>
                    <p style='margin:0.2rem 0 0;color:#64748B;font-size:0.88rem'>
                        Real-time network performance monitoring ·
                        <span style='color:#3B82F6;font-weight:600'>ClickHouse</span> backend
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── DB connection ──────────────────────────────────────────────────────────
    try:
        conn = get_db_connection()
    except Exception as exc:
        st.error(f"❌ Cannot connect to ClickHouse: {exc}")
        st.stop()

    # ── Filter panel ───────────────────────────────────────────────────────────
    filters = render_filter_panel(conn)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ── Guards ─────────────────────────────────────────────────────────────────
    if not filters["run_query"]:
        st.info(
            "⬆️  Select a Region, one or more NC 5G clusters and a Date Range, "
            "then press **▶ Run** to load KPIs.",
            icon="ℹ️",
        )
        return

    nc5g_list: list[str] = filters.get("nc5g_list", [])
    if not nc5g_list:
        st.warning("Please select at least one NC 5G cluster.")
        return

    if not filters["site_ids"]:
        st.warning(
            "No Site IDs found for the selected NC 5G cluster(s). Please check the selection."
        )
        return

    site_ids = filters["site_ids"]
    start_date = filters["start_date"]
    end_date = filters["end_date"]

    pre_window, post_window = compute_baseline_windows(start_date, end_date)

    # ── Fetch lists ────────────────────────────────────────────────────────────
    with st.spinner("Loading 5G / 4G site lists…"):
        client = conn.get_client()
        df_5glist = fetch_5g_list(client, site_ids)
        df_4glist = fetch_4g_list(client, site_ids)

    if df_5glist.empty:
        st.error("No 5G sites found. Please verify site IDs in `ioh_adm.t_list_5g`.")
        return

    nrbts_ids = df_5glist["nrbts"].dropna().astype(str).unique().tolist()
    mrbts_ids = (
        df_4glist["mrbts"].dropna().astype(str).unique().tolist()
        if not df_4glist.empty
        else []
    )

    # ── Fetch KPI data ─────────────────────────────────────────────────────────
    with st.spinner("Querying 5G / 4G KPI data… (this may take a moment)"):
        df_5g_raw_day = fetch_5g_kpi_day(client, nrbts_ids, start_date, end_date)
        df_5g_raw_pa13 = fetch_5g_kpi_pa13(client, nrbts_ids, start_date, end_date)
        df_4g_raw = (
            fetch_4g_kpi(client, mrbts_ids, start_date, end_date)
            if mrbts_ids
            else _empty_df()
        )

    # ── Enrich with site_id ────────────────────────────────────────────────────
    df_5gday = enrich_5g_with_site(df_5g_raw_day, df_5glist)
    df_5gpa13 = enrich_5g_with_site(df_5g_raw_pa13, df_5glist)
    df_4g = enrich_4g_with_site(df_4g_raw, df_4glist)

    for df in [df_5gday, df_5gpa13, df_4g]:
        if not df.empty and "xDate" in df.columns:
            df["xDate"] = df["xDate"].astype(str)

    # ── Site list overview ─────────────────────────────────────────────────────
    with st.expander(f"📋 Site List ({len(site_ids)} sites)", expanded=False):
        col_a, col_b = st.columns(2)
        col_a.markdown("**5G Sites**")
        col_a.dataframe(df_5glist, width="stretch", hide_index=True)
        col_b.markdown("**4G Sites**")
        col_b.dataframe(df_4glist, width="stretch", hide_index=True)

    # ── Aggregate traffic / user ───────────────────────────────────────────────
    df_5g_traffic = compute_5g_daily_traffic(df_5gpa13)
    df_4g_traffic = compute_4g_daily_traffic(df_4g)
    df_5g_user = compute_5g_daily_user(df_5gday)
    df_4g_user = compute_4g_daily_user(df_4g)

    # ─────────────────────────────────────────────────────────────────────────
    # CHART SECTIONS
    # ─────────────────────────────────────────────────────────────────────────

    render_overview_section(df_5g_traffic, df_4g_traffic, df_5g_user, df_4g_user)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    render_5g_kpi_section(
        df_5gpa13,
        df_5gday,
        pre_window,
        post_window,
        nc5g_list=nc5g_list,
    )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    render_4g_kpi_section(df_4g, pre_window, post_window)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    render_contributor_section(df_5gpa13, df_5gday, df_4g, pre_window, post_window)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="dashboard-footer">
            <div style="display:flex;justify-content:center;gap:2rem;margin-bottom:0.75rem">
                <span>⚡ Real-time updates</span>
                <span>📊 5G/4G Analytics</span>
                <span>🔍 ClickHouse backend</span>
            </div>
            <div style="color:#CBD5E1;font-size:0.73rem">
                5G/4G Cluster KPI Dashboard · Built with Streamlit & ClickHouse · v2.0.0
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empty_df():
    import pandas as pd

    return pd.DataFrame()


if __name__ == "__main__":
    main()
