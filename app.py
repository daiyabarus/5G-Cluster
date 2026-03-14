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
    page_title="5G/4G KPI Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Modern White Background CSS ─────────────────────────────────────────────
# st.markdown(
#     """
#     <style>
#     /* ── Fonts ── */
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
#     html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#     /* ── Base app background — clean white ── */
#     .stApp                 { background-color: #FFFFFF; }
#     .block-container       { padding-top: 1.5rem; max-width: 100% !important; 
#                              background-color: #FFFFFF; }

#     /* ── Sidebar (if ever used) ── */
#     section[data-testid="stSidebar"] { background-color: #F8FAFC; }

#     /* ── Text colors ── */
#     .stMarkdown p, .stMarkdown li,
#     .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
#     .stText                { color: #1E293B; }

#     h1, h2, h3              { color: #0F172A !important; font-weight: 600; }

#     /* ── Section headers (### markdown) ── */
#     h3                     { color: #1E293B !important;
#                              font-weight: 600; letter-spacing: 0.3px;
#                              border-left: 4px solid #3B82F6;
#                              padding-left: 1rem;
#                              margin-top: 1.5rem; }

#     /* ── Selectbox labels ── */
#     .stSelectbox label,
#     .stDateInput  label,
#     .stMultiSelect label   { color: #64748B !important;
#                              font-size: 0.8rem !important;
#                              font-weight: 500 !important;
#                              text-transform: uppercase;
#                              letter-spacing: 0.5px; }

#     /* ── Selectbox/input styling ── */
#     .stSelectbox [data-baseweb="select"] > div,
#     .stSelectbox [data-baseweb="select"] input,
#     .stSelectbox [data-baseweb="select"] span,
#     .stDateInput  input    { background-color: #FFFFFF !important;
#                              color: #1E293B !important;
#                              border: 1px solid #E2E8F0 !important;
#                              border-radius: 12px !important;
#                              box-shadow: 0 1px 2px rgba(0,0,0,0.02); }

#     /* ── Dropdown popup menu ── */
#     [data-baseweb="popover"],
#     [data-baseweb="popover"] ul,
#     [data-baseweb="menu"]   { background-color: #FFFFFF !important;
#                              border: 1px solid #E2E8F0 !important;
#                              border-radius: 12px !important;
#                              box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); }
#     [data-baseweb="menu"] li,
#     [data-baseweb="option"] { color: #1E293B !important;
#                              background-color: #FFFFFF !important; }
#     [data-baseweb="option"]:hover,
#     [data-baseweb="option"][aria-selected="true"]
#                            { background-color: #F1F5F9 !important;
#                              color: #3B82F6 !important; }

#     /* ── Date input calendar popup ── */
#     [data-baseweb="calendar"],
#     [data-baseweb="datepicker-calendar"]
#                            { background-color: #FFFFFF !important;
#                              color: #1E293B !important;
#                              border: 1px solid #E2E8F0 !important;
#                              border-radius: 12px !important;
#                              box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }

#     /* ── Expander ── */
#     details > summary,
#     .streamlit-expanderHeader
#                            { background-color: #F8FAFC !important;
#                              color: #1E293B !important;
#                              border: 1px solid #E2E8F0 !important;
#                              border-radius: 12px !important;
#                              padding: 0.75rem 1.25rem !important;
#                              font-weight: 500; }
#     .streamlit-expanderHeader:hover
#                            { background-color: #F1F5F9 !important; }
#     .streamlit-expanderContent
#                            { background-color: #FFFFFF !important;
#                              border: 1px solid #E2E8F0 !important;
#                              border-top: none !important;
#                              border-radius: 0 0 12px 12px !important;
#                              padding: 1rem !important; }

#     /* ── Tabs ── */
#     div[data-baseweb="tab-list"]
#                            { background-color: #F8FAFC !important;
#                              border-bottom: 1px solid #E2E8F0 !important;
#                              border-radius: 12px 12px 0 0;
#                              padding: 0.5rem 0.5rem 0; }
#     button[data-baseweb="tab"]
#                            { color: #64748B !important;
#                              font-weight: 500;
#                              background: transparent !important;
#                              border-radius: 8px 8px 0 0 !important;
#                              padding: 0.5rem 1rem; }
#     button[data-baseweb="tab"]:hover
#                            { color: #3B82F6 !important;
#                              background-color: #FFFFFF !important; }
#     button[data-baseweb="tab"][aria-selected="true"]
#                            { color: #3B82F6 !important;
#                              border-bottom: 2px solid #3B82F6 !important;
#                              background: transparent !important; }

#     /* ── Buttons ── */
#     .stButton > button     { background: #3B82F6;
#                              color: #FFFFFF !important;
#                              border: none; border-radius: 12px;
#                              font-weight: 600; font-size: 0.9rem;
#                              padding: 0.5rem 1.5rem;
#                              transition: all 0.2s ease;
#                              box-shadow: 0 4px 6px -1px rgba(59,130,246,0.2); }
#     .stButton > button:hover
#                            { background: #2563EB; 
#                              transform: translateY(-1px);
#                              box-shadow: 0 10px 15px -3px rgba(59,130,246,0.3); }

#     /* ── Metric cards ── */
#     div[data-testid="stMetric"]
#                            { background-color: #FFFFFF;
#                              border: 1px solid #E2E8F0;
#                              border-radius: 16px;
#                              padding: 1rem 1.25rem;
#                              box-shadow: 0 1px 3px rgba(0,0,0,0.02);
#                              transition: all 0.2s ease; }
#     div[data-testid="stMetric"]:hover
#                            { box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
#                              border-color: #CBD5E1; }
#     div[data-testid="stMetricLabel"]  
#                            { color: #64748B !important; 
#                              font-size: 0.85rem !important;
#                              font-weight: 500; }
#     div[data-testid="stMetricValue"]  
#                            { color: #0F172A !important; 
#                              font-size: 2rem !important; 
#                              font-weight: 700 !important; }
#     div[data-testid="stMetricDelta"]  
#                            { font-size: 0.85rem !important;
#                              padding-top: 0.25rem; }

#     /* ── DataFrames ── */
#     [data-testid="stDataFrame"]
#                            { border: 1px solid #E2E8F0;
#                              border-radius: 16px;
#                              overflow: hidden;
#                              box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
#     .stDataFrame           { font-size: 0.9rem; }
    
#     /* ── Caption ── */
#     .stCaption, small      { color: #94A3B8 !important; 
#                              font-size: 0.8rem !important; }

#     /* ── Alerts ── */
#     .stAlert               { border-radius: 12px !important;
#                              border: 1px solid #E2E8F0 !important; }
#     div[data-testid="stAlert"] p
#                            { color: #1E293B !important; }
#     div[data-testid="stAlert"] svg
#                            { color: #3B82F6 !important; }

#     /* ── Spinner ── */
#     .stSpinner p           { color: #64748B !important; }

#     /* ── Dividers ── */
#     hr                     { border: none;
#                              border-top: 1px solid #E2E8F0;
#                              margin: 2rem 0; }
#     .section-divider       { border: none;
#                              border-top: 2px solid #F1F5F9;
#                              margin: 2rem 0; }

#     /* ── Info/Warning/Error boxes ── */
#     .stAlert               { background-color: #F8FAFC !important; }
#     .stAlert.info          { border-left: 4px solid #3B82F6; }
#     .stAlert.warning       { border-left: 4px solid #F59E0B; }
#     .stAlert.error         { border-left: 4px solid #EF4444; }

#     /* ── Header styling ── */
#     .dashboard-header      { background: linear-gradient(135deg, #F8FAFC, #FFFFFF);
#                              padding: 1.5rem 2rem;
#                              border-radius: 24px;
#                              border: 1px solid #E2E8F0;
#                              margin-bottom: 1.5rem;
#                              box-shadow: 0 1px 2px rgba(0,0,0,0.02); }

#     /* ── Footer styling ── */
#     .dashboard-footer      { text-align: center;
#                              color: #94A3B8;
#                              font-size: 0.8rem;
#                              padding: 2rem 0 1rem;
#                              border-top: 1px solid #E2E8F0;
#                              margin-top: 2rem; }

#     /* ── Progress bars ── */
#     .stProgress > div > div > div
#                            { background-color: #3B82F6 !important; }

#     /* ── Code blocks ── */
#     code                   { background-color: #F1F5F9 !important;
#                              color: #0F172A !important;
#                              border-radius: 6px;
#                              padding: 0.2rem 0.4rem; }

#     /* ── Checkboxes ── */
#     .stCheckbox label      { color: #1E293B !important; }
#     .stCheckbox label span { border-color: #CBD5E1 !important; }
#     .stCheckbox label input:checked + span
#                            { background-color: #3B82F6 !important;
#                              border-color: #3B82F6 !important; }

#     /* ── Radio buttons ── */
#     .stRadio label         { color: #1E293B !important; }
#     .stRadio label input:checked + div
#                            { color: #3B82F6 !important; }

#     /* ── Slider ── */
#     .stSlider label        { color: #64748B !important; }
#     div[data-baseweb="slider"] div
#                            { background-color: #3B82F6 !important; }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

st.markdown(
    """
    <style>
    /* ── Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Base app background — clean white ── */
    .stApp                 { background-color: #FFFFFF; }
    .block-container       { padding-top: 1.5rem; max-width: 100% !important; 
                             background-color: #FFFFFF; }

    /* ── Sidebar (if ever used) ── */
    section[data-testid="stSidebar"] { background-color: #F8FAFC; }

    /* ── Text colors ── */
    .stMarkdown p, .stMarkdown li,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stText                { color: #1E293B; }

    h1, h2, h3              { color: #0F172A !important; font-weight: 600; }

    /* ── Section headers (### markdown) ── */
    h3                     { color: #1E293B !important;
                             font-weight: 600; letter-spacing: 0.3px;
                             border-left: 4px solid #3B82F6;
                             padding-left: 1rem;
                             margin-top: 1.5rem; }

    /* ── Selectbox labels ── */
    .stSelectbox label,
    .stDateInput  label,
    .stMultiSelect label   { color: #64748B !important;
                             font-size: 0.8rem !important;
                             font-weight: 500 !important;
                             text-transform: uppercase;
                             letter-spacing: 0.5px; }

    /* ── Selectbox/input styling ── */
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] input,
    .stSelectbox [data-baseweb="select"] span,
    .stDateInput  input    { background-color: #FFFFFF !important;
                             color: #1E293B !important;
                             border: 1px solid #E2E8F0 !important;
                             border-radius: 12px !important;
                             box-shadow: 0 1px 2px rgba(0,0,0,0.02); }

    /* ── Dropdown popup menu ── */
    [data-baseweb="popover"],
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"]   { background-color: #FFFFFF !important;
                             border: 1px solid #E2E8F0 !important;
                             border-radius: 12px !important;
                             box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    [data-baseweb="menu"] li,
    [data-baseweb="option"] { color: #1E293B !important;
                             background-color: #FFFFFF !important; }
    [data-baseweb="option"]:hover,
    [data-baseweb="option"][aria-selected="true"]
                           { background-color: #F1F5F9 !important;
                             color: #3B82F6 !important; }

    /* ── Date input calendar popup ── */
    [data-baseweb="calendar"],
    [data-baseweb="datepicker-calendar"]
                           { background-color: #FFFFFF !important;
                             color: #1E293B !important;
                             border: 1px solid #E2E8F0 !important;
                             border-radius: 12px !important;
                             box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }

    /* ── Expander ── */
    details > summary,
    .streamlit-expanderHeader
                           { background-color: #F8FAFC !important;
                             color: #1E293B !important;
                             border: 1px solid #E2E8F0 !important;
                             border-radius: 12px !important;
                             padding: 0.75rem 1.25rem !important;
                             font-weight: 500; }
    .streamlit-expanderHeader:hover
                           { background-color: #F1F5F9 !important; }
    .streamlit-expanderContent
                           { background-color: #FFFFFF !important;
                             border: 1px solid #E2E8F0 !important;
                             border-top: none !important;
                             border-radius: 0 0 12px 12px !important;
                             padding: 1rem !important; }

    /* ── Tabs ── */
    div[data-baseweb="tab-list"]
                           { background-color: #F8FAFC !important;
                             border-bottom: 1px solid #E2E8F0 !important;
                             border-radius: 12px 12px 0 0;
                             padding: 0.5rem 0.5rem 0; }
    button[data-baseweb="tab"]
                           { color: #64748B !important;
                             font-weight: 500;
                             background: transparent !important;
                             border-radius: 8px 8px 0 0 !important;
                             padding: 0.5rem 1rem; }
    button[data-baseweb="tab"]:hover
                           { color: #3B82F6 !important;
                             background-color: #FFFFFF !important; }
    button[data-baseweb="tab"][aria-selected="true"]
                           { color: #3B82F6 !important;
                             border-bottom: 2px solid #3B82F6 !important;
                             background: transparent !important; }

    /* ── Buttons ── */
    .stButton > button     { background: #3B82F6;
                             color: #FFFFFF !important;
                             border: none; border-radius: 12px;
                             font-weight: 600; font-size: 0.9rem;
                             padding: 0.5rem 1.5rem;
                             transition: all 0.2s ease;
                             box-shadow: 0 4px 6px -1px rgba(59,130,246,0.2); }
    .stButton > button:hover
                           { background: #2563EB; 
                             transform: translateY(-1px);
                             box-shadow: 0 10px 15px -3px rgba(59,130,246,0.3); }

    /* ── Metric cards ── */
    div[data-testid="stMetric"]
                           { background-color: #FFFFFF;
                             border: 1px solid #E2E8F0;
                             border-radius: 16px;
                             padding: 1rem 1.25rem;
                             box-shadow: 0 1px 3px rgba(0,0,0,0.02);
                             transition: all 0.2s ease; }
    div[data-testid="stMetric"]:hover
                           { box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
                             border-color: #CBD5E1; }
    div[data-testid="stMetricLabel"]  
                           { color: #64748B !important; 
                             font-size: 0.85rem !important;
                             font-weight: 500; }
    div[data-testid="stMetricValue"]  
                           { color: #0F172A !important; 
                             font-size: 2rem !important; 
                             font-weight: 700 !important; }
    div[data-testid="stMetricDelta"]  
                           { font-size: 0.85rem !important;
                             padding-top: 0.25rem; }

    /* ── DataFrames ── */
    [data-testid="stDataFrame"]
                           { border: 1px solid #E2E8F0;
                             border-radius: 16px;
                             overflow: hidden;
                             box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
    
    /* ── Caption ── */
    .stCaption, small      { color: #94A3B8 !important; 
                             font-size: 0.8rem !important; }

    /* ── Alerts ── */
    .stAlert               { border-radius: 12px !important;
                             border: 1px solid #E2E8F0 !important; }

    /* ── Spinner ── */
    .stSpinner p           { color: #64748B !important; }

    /* ── Dividers ── */
    hr                     { border: none;
                             border-top: 1px solid #E2E8F0;
                             margin: 2rem 0; }
    .section-divider       { border: none;
                             border-top: 2px solid #F1F5F9;
                             margin: 2rem 0; }

    /* ── Header styling ── */
    .dashboard-header      { background: linear-gradient(135deg, #F8FAFC, #FFFFFF);
                             padding: 1.5rem 2rem;
                             border-radius: 24px;
                             border: 1px solid #E2E8F0;
                             margin-bottom: 1.5rem;
                             box-shadow: 0 1px 2px rgba(0,0,0,0.02); }

    /* ── Footer styling ── */
    .dashboard-footer      { text-align: center;
                             color: #94A3B8;
                             font-size: 0.8rem;
                             padding: 2rem 0 1rem;
                             border-top: 1px solid #E2E8F0;
                             margin-top: 2rem; }
    
    /* IMPORTANT: Jangan override Plotly chart colors */
    .js-plotly-plot, .plotly, .plot-container
                           { background-color: transparent !important; }
    .main-svg              { background: transparent !important; }
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
    # Modern Header
    # st.markdown(
    #     """
    #     <div class="dashboard-header">
    #         <div style='display:flex; align-items:center; gap:16px;'>
    #             <span style='font-size:2.5rem; background: #3B82F6; 
    #                        width: 60px; height: 60px; display: flex; 
    #                        align-items: center; justify-content: center;
    #                        border-radius: 20px; color: white;'>📡</span>
    #             <div>
    #                 <h1 style='margin:0; font-size:1.8rem; color:#0F172A; 
    #                            font-weight:700; letter-spacing:-0.02em;'>
    #                     5G / 4G Network KPI Dashboard
    #                 </h1>
    #                 <p style='margin:0.25rem 0 0 0; color:#64748B; 
    #                          font-size:0.9rem;'>
    #                     Real-time network performance monitoring · 
    #                     <span style='color:#3B82F6;'>ClickHouse</span> backend
    #                 </p>
    #             </div>
    #         </div>
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )

    # ── DB connection ─────────────────────────────────────────────────────────
    try:
        conn = get_db_connection()
    except Exception as exc:
        st.error(f"❌ Cannot connect to ClickHouse: {exc}")
        st.stop()

    # ── Filter panel ──────────────────────────────────────────────────────────
    filters = render_filter_panel(conn)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

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

    # ── Modern Footer ─────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="dashboard-footer">
            <div style="display: flex; justify-content: center; gap: 2rem; 
                        margin-bottom: 1rem;">
                <span style="color: #94A3B8;">⚡ Real-time updates</span>
                <span style="color: #94A3B8;">📊 5G/4G Analytics</span>
                <span style="color: #94A3B8;">🔍 ClickHouse backend</span>
            </div>
            <div style="color: #CBD5E1; font-size: 0.75rem;">
                5G/4G Network KPI Dashboard · Built with Streamlit & ClickHouse · 
                v1.0.0
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