import os
import streamlit as st
import pandas as pd
from clickhouse_driver import Client
from io import BytesIO
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# LOAD ENV
# ─────────────────────────────────────────────
load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="NR Relation Analyzer", page_icon="📡", layout="wide")
st.title("📡 NR Relation Analyzer")
st.caption("Deteksi korelasi SgNB Refuse & identifikasi relasi MeNB→SgNB yang missing")

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    st.subheader("🔌 Koneksi ClickHouse")
    ch_host     = st.text_input("Host",     value=os.getenv("CH_HOST", "localhost"))
    ch_port     = st.number_input("Port",   value=int(os.getenv("CH_PORT", 9000)), step=1)
    ch_user     = st.text_input("User",     value=os.getenv("CH_USERNAME", "default"))
    ch_password = st.text_input("Password", value=os.getenv("CH_PASSWORD", ""), type="password")
    ch_database = st.text_input("Database", value=os.getenv("CH_DATABASE", "default"))
    st.divider()
    st.subheader("🎯 Target Sel 5G (SgNB)")
    s_mrbts  = st.number_input("S_MRBTS",  value=0, step=1)
    s_nrbts  = st.number_input("S_NRBTS",  value=0, step=1)
    s_nrcell = st.number_input("S_NRCELL", value=0, step=1)
    st.divider()
    st.subheader("📅 Offset Hari")
    p_dump_days       = st.number_input("Dump Days Offset (CM)",      value=0, step=1)
    p_kpi_days_hourly = st.number_input("KPI Days Offset (Hourly)",   value=1, step=1)
    st.divider()
    st.subheader("🔍 Filter Korelasi")
    corr_threshold = st.slider("Min Threshold Korelasi", 0.0, 1.0, 0.7, 0.05)
    min_samples    = st.number_input("Min Jumlah Sample", value=10, step=1)
    run_btn = st.button("▶️ Jalankan Analisis", use_container_width=True, type="primary")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_client():
    return Client(host=ch_host, port=int(ch_port), user=ch_user,
                  password=ch_password, database=ch_database,
                  settings={"use_numpy": False})

def run_query(client, query):
    rows, cols_meta = client.execute(query, with_column_types=True)
    return pd.DataFrame(rows, columns=[c[0] for c in cols_meta])

def to_excel_multi(sheets: dict) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buf.getvalue()

def get_corr_label(val):
    if val >= 0.9: return "🔴 Sangat Tinggi"
    if val >= 0.7: return "🟠 Tinggi"
    if val >= 0.5: return "🟡 Sedang"
    return "🟢 Rendah"

def get_missing_status(row):
    adj = str(row.get('Lnadjgnb_To_Nbr', '')).strip() == 'CREATED'
    rel = str(row.get('Lnrelgnbcell_To_Nbr', '')).strip() == 'CREATED'
    if adj and rel:       return 'COMPLETE'
    elif adj and not rel: return 'MISSING Lnrelgnbcell'
    elif not adj and rel: return 'MISSING Lnadjgnb'
    else:                 return 'MISSING BOTH'

# ─────────────────────────────────────────────
# QUERY: MISSING RELATIONS
# ─────────────────────────────────────────────
def build_missing_query(s_mrbts, s_nrbts, s_nrcell, p_dump_days, p_kpi_days):
    return f"""
WITH
    {float(p_dump_days)} AS p_dump_days_offset,
    {p_kpi_days}         AS p_kpi_days_hourly_agg_offset,
    {s_mrbts}            AS s_mrbts,
    {s_nrbts}            AS s_nrbts,
    {s_nrcell}           AS s_nrcell,
    {s_mrbts}            AS n_mrbts,
    {s_nrbts}            AS n_nrbts,
    {s_nrcell}           AS n_nrcell,

q_nrcell AS (
    SELECT toInt64(t.nrcellidentity) AS nrCellId,
        argMax(t.mrbts, t.xdate) AS MRBTS,
        argMax(t.nrbts, t.xdate) AS NRBTS,
        argMax(t.nrcell, t.xdate) AS NRCELL
    FROM ioh_cm.nrcell t
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.nrcell) - p_dump_days_offset
    GROUP BY t.nrcellidentity
),

q_menb_list AS (
    SELECT
        t.oss,
        concat(toString(MIN(t.xdate)), ' - ', toString(MAX(t.xdate))) AS strDate,
        t.mrbts AS MeNB_MRBTS, t.lnbts AS MeNB_LNBTS, t.lncel AS MeNB_LNCEL,
        n.MRBTS AS S_MRBTS, n.NRBTS AS S_NRBTS, n.NRCELL AS S_NRCELL,
        n_mrbts AS N_MRBTS, n_nrbts AS N_NRBTS, n_nrcell AS N_NRCELL
    FROM ioh_cm.lnrelgnbcell t
        LEFT JOIN q_nrcell n ON toUInt64(assumeNotNull(t.nrcellid)) = toUInt64(assumeNotNull(n.nrCellId))
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.lnrelgnbcell) - p_dump_days_offset
        AND n.MRBTS=s_mrbts AND n.NRBTS=s_nrbts AND n.NRCELL=s_nrcell
    GROUP BY t.oss, t.mrbts, t.lnbts, t.lncel, n.MRBTS, n.NRBTS, n.NRCELL
),

q_kpi_refuse AS (
    SELECT
        concat(toString(MIN(t.xDate)), ' - ', toString(MAX(t.xDate))) AS MeNB_strDate,
        t.oss AS MeNB_oss,
        t.MRBTS_ID AS MeNB_MRBTS, t.LNBTS_ID AS MeNB_LNBTS, t.LNCEL_ID AS MeNB_LNCEL,
        SUM(t.SGNB_CHANGE_REFUSE) AS SGNB_CHANGE_REFUSE
    FROM isat_raw_4g.noklte_ps_lxpl_lncel_hour t
    WHERE t.xDate >= (SELECT MAX(xDate) FROM isat_raw_4g.noklte_ps_lxpl_lncel_hour) - p_kpi_days_hourly_agg_offset
    GROUP BY t.oss, t.MRBTS_ID, t.LNBTS_ID, t.LNCEL_ID
),

q_kpi_refuse_received AS (
    SELECT
        concat(toString(MIN(t.xDate)), ' - ', toString(MAX(t.xDate))) AS S_strDate,
        t.oss AS S_oss,
        t.MRBTS_ID AS S_MRBTS, t.RNBTS_ID AS S_NRBTS, t.RNCEL_ID AS S_NRCELL,
        SUM(t.X2_SGNB_CHG_REF_RECEIVED) AS X2_SGNB_CHG_REF_RECEIVED
    FROM isat_raw_5g.nokgnb_ps_nx2cc_nrcel_hour t
    WHERE t.xDate >= (SELECT MAX(xDate) FROM isat_raw_5g.nokgnb_ps_nx2cc_nrcel_hour) - p_kpi_days_hourly_agg_offset
    GROUP BY t.oss, t.MRBTS_ID, t.RNBTS_ID, t.RNCEL_ID
),

q_lncel_fdd AS (
    SELECT argMax(lf.oss, lf.xdate) AS oss,
        lf.MRBTS, lf.LNBTS, lf.LNCEL,
        argMax(lf.earfcnDL, lf.xdate) AS earfcnDL,
        CASE
            WHEN argMax(lf.earfcnDL, lf.xdate) BETWEEN 0    AND 599  THEN 'L2100'
            WHEN argMax(lf.earfcnDL, lf.xdate) BETWEEN 1200 AND 1949 THEN 'L1800'
            WHEN argMax(lf.earfcnDL, lf.xdate) BETWEEN 2750 AND 3449 THEN 'L2600'
            WHEN argMax(lf.earfcnDL, lf.xdate) BETWEEN 3450 AND 3799 THEN 'L900'
            WHEN argMax(lf.earfcnDL, lf.xdate) BETWEEN 9210 AND 9659 THEN 'L700'
            ELSE 'Unknown'
        END AS LTE_Band,
        CASE
            WHEN argMax(lf.earfcnDL, lf.xdate) BETWEEN 3450 AND 9659 THEN 'Low Band'
            ELSE 'High Band'
        END AS LTE_Band_Category
    FROM ioh_cm.lncel_fdd AS lf
    WHERE lf.xdate >= (SELECT MAX(xdate) FROM ioh_cm.lncel_fdd) - p_dump_days_offset
    GROUP BY lf.MRBTS, lf.LNBTS, lf.LNCEL
),

q_t_list_4g AS (
    SELECT t.mrbts AS MRBTS, t.lnbts AS LNBTS, t.lncel AS LNCEL,
        argMax(t.Site_ID, t.Last_update) AS SiteID,
        argMax(t.sector_id, t.Last_update) AS SectorID,
        argMax(t.`eNodeB Name`, t.Last_update) AS SiteName,
        argMax(t.azimuth, t.Last_update) AS Azimuth,
        argMax(t.Lat, t.Last_update) AS Lat,
        argMax(t.Long, t.Last_update) AS Lon
    FROM ioh_adm.t_list_4g t
    GROUP BY t.mrbts, t.lnbts, t.lncel
),

q_lte_cell_info AS (
    SELECT lf.MRBTS AS MeNB_MRBTS, lf.LNBTS AS MeNB_LNBTS, lf.LNCEL AS MeNB_LNCEL,
        tl.SiteID AS MeNB_SiteID, tl.SiteName AS MeNB_SiteName, tl.SectorID AS MeNB_SectorID,
        tl.Azimuth AS MeNB_Azimuth, tl.Lat AS MeNB_Lat, tl.Lon AS MeNB_Lon,
        lf.LTE_Band AS MeNB_LTE_Band, lf.LTE_Band_Category AS MeNB_LTE_Band_Category
    FROM q_lncel_fdd lf
        LEFT JOIN q_t_list_4g tl ON lf.MRBTS=tl.MRBTS AND lf.LNBTS=tl.LNBTS AND lf.LNCEL=tl.LNCEL
),

q_nrcell_fdd AS (
    SELECT t.mrbts AS MRBTS, t.nrbts AS NRBTS, t.nrcell AS NRCELL,
        argMax(t.nrarfcndl, t.xdate) AS nrarfcnDl,
        CASE
            WHEN argMax(t.nrarfcndl, t.xdate) BETWEEN 422000 AND 434000 THEN '2100 MHz - FDD (n1)'
            WHEN argMax(t.nrarfcndl, t.xdate) BETWEEN 361000 AND 376000 THEN '1800 MHz - FDD (n3)'
            WHEN argMax(t.nrarfcndl, t.xdate) BETWEEN 948000 AND 953333 THEN '700 MHz (n28)'
            WHEN argMax(t.nrarfcndl, t.xdate) BETWEEN 620000 AND 653333 THEN '3.5 GHz (n78)'
            ELSE 'Unknown'
        END AS NR_Band
    FROM ioh_cm.nrcell_fdd AS t
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.nrcell_fdd) - p_dump_days_offset
    GROUP BY t.mrbts, t.nrbts, t.nrcell
),

q_t_list_5g AS (
    SELECT t.mrbts AS MRBTS, t.nrbts AS NRBTS, t.nrcell AS NRCELL,
        t.site_id AS SiteID, t.site_name AS SiteName,
        t.azimuth AS Azimuth, t.Longitude AS Lon, t.Latitude AS Lat
    FROM ioh_adm.t_list_5g t
),

q_nr_cell_info AS (
    SELECT nf.MRBTS AS S_MRBTS, nf.NRBTS AS S_NRBTS, nf.NRCELL AS S_NRCELL,
        tl.SiteID AS S_SiteID, tl.SiteName AS S_SiteName,
        tl.Azimuth AS S_Azimuth, tl.Lat AS S_Lat, tl.Lon AS S_Lon,
        nf.NR_Band AS S_NR_Band
    FROM q_nrcell_fdd nf
        LEFT JOIN q_t_list_5g tl ON nf.MRBTS=tl.MRBTS AND nf.NRBTS=tl.NRBTS AND nf.NRCELL=tl.NRCELL
),

q_lnadjgnb_status AS (
    SELECT t.mrbts AS MeNB_MRBTS, t.lnbts AS MeNB_LNBTS, t.adjgnbid AS N_NRBTS,
        'CREATED' AS Lnadjgnb_To_Nbr,
        argMax(t.administrativestate, t.xdate) AS administrativeState,
        argMax(t.x2tognblinkstatus,   t.xdate) AS x2ToGnbLinkStatus
    FROM ioh_cm.lnadjgnb t
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.lnadjgnb) - p_dump_days_offset
    GROUP BY t.mrbts, t.lnbts, t.adjgnbid
),

q_lnrelgnbcell_status AS (
    SELECT DISTINCT
        t.mrbts AS MeNB_MRBTS, t.lnbts AS MeNB_LNBTS, t.lncel AS MeNB_LNCEL,
        n.MRBTS AS N_MRBTS, n.NRBTS AS N_NRBTS, n.NRCELL AS N_NRCELL,
        'CREATED' AS Lnrelgnbcell_To_Nbr
    FROM ioh_cm.lnrelgnbcell t
        LEFT JOIN q_nrcell n ON toUInt64(assumeNotNull(t.nrcellid)) = toUInt64(assumeNotNull(n.nrCellId))
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.lnrelgnbcell) - p_dump_days_offset
)

SELECT
    m.oss, m.strDate,
    m.MeNB_MRBTS, m.MeNB_LNBTS, m.MeNB_LNCEL,
    ci4.MeNB_SiteID, ci4.MeNB_SiteName, ci4.MeNB_SectorID,
    ci4.MeNB_LTE_Band, ci4.MeNB_LTE_Band_Category,
    ci4.MeNB_Azimuth, ci4.MeNB_Lat, ci4.MeNB_Lon,
    m.S_MRBTS, m.S_NRBTS, m.S_NRCELL,
    ci5.S_SiteID, ci5.S_SiteName, ci5.S_NR_Band,
    ci5.S_Azimuth, ci5.S_Lat, ci5.S_Lon,
    m.N_MRBTS, m.N_NRBTS, m.N_NRCELL,
    kr.SGNB_CHANGE_REFUSE,
    krr.X2_SGNB_CHG_REF_RECEIVED,
    kr.MeNB_strDate,
    krr.S_strDate,
    adj.Lnadjgnb_To_Nbr,
    adj.administrativeState,
    adj.x2ToGnbLinkStatus,
    rel.Lnrelgnbcell_To_Nbr
FROM q_menb_list m
    LEFT JOIN q_kpi_refuse kr
        ON m.MeNB_MRBTS=kr.MeNB_MRBTS AND m.MeNB_LNBTS=kr.MeNB_LNBTS AND m.MeNB_LNCEL=kr.MeNB_LNCEL
    LEFT JOIN q_kpi_refuse_received krr
        ON m.S_MRBTS=krr.S_MRBTS AND m.S_NRBTS=krr.S_NRBTS AND m.S_NRCELL=krr.S_NRCELL
    LEFT JOIN q_lte_cell_info ci4
        ON m.MeNB_MRBTS=ci4.MeNB_MRBTS AND m.MeNB_LNBTS=ci4.MeNB_LNBTS AND m.MeNB_LNCEL=ci4.MeNB_LNCEL
    LEFT JOIN q_nr_cell_info ci5
        ON m.S_MRBTS=ci5.S_MRBTS AND m.S_NRBTS=ci5.S_NRBTS AND m.S_NRCELL=ci5.S_NRCELL
    LEFT JOIN q_lnadjgnb_status adj
        ON m.MeNB_MRBTS=adj.MeNB_MRBTS AND m.MeNB_LNBTS=adj.MeNB_LNBTS AND m.N_NRBTS=adj.N_NRBTS
    LEFT JOIN q_lnrelgnbcell_status rel
        ON m.MeNB_MRBTS=rel.MeNB_MRBTS AND m.MeNB_LNBTS=rel.MeNB_LNBTS AND m.MeNB_LNCEL=rel.MeNB_LNCEL
        AND m.N_MRBTS=rel.N_MRBTS AND m.N_NRBTS=rel.N_NRBTS AND m.N_NRCELL=rel.N_NRCELL
"""

# ─────────────────────────────────────────────
# QUERY: CORRELATION
# ─────────────────────────────────────────────
def build_corr_query(s_mrbts, s_nrbts, s_nrcell, p_dump_days, p_kpi_days):
    return f"""
WITH
    {p_dump_days} AS p_dump_days_offset,
    {p_kpi_days}  AS p_kpi_days_hourly_agg_offset,
    {s_mrbts}     AS s_mrbts,
    {s_nrbts}     AS s_nrbts,
    {s_nrcell}    AS s_nrcell,

q_nrcell AS (
    SELECT toInt64(t.nrcellidentity) AS nrCellId,
        argMax(t.mrbts, t.xdate) AS MRBTS,
        argMax(t.nrbts, t.xdate) AS NRBTS,
        argMax(t.nrcell, t.xdate) AS NRCELL
    FROM ioh_cm.nrcell t
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.nrcell) - p_dump_days_offset
    GROUP BY t.nrcellidentity
),
q_menb_list_of_src AS (
    SELECT t.mrbts AS MeNB_MRBTS, t.lnbts AS MeNB_LNBTS, t.lncel AS MeNB_LNCEL,
        n.MRBTS AS S_MRBTS, n.NRBTS AS S_NRBTS, n.NRCELL AS S_NRCELL
    FROM ioh_cm.lnrelgnbcell t
        LEFT JOIN q_nrcell n ON toUInt64(assumeNotNull(t.nrcellid)) = toUInt64(assumeNotNull(n.nrCellId))
    WHERE t.xdate >= (SELECT MAX(xdate) FROM ioh_cm.lnrelgnbcell) - p_dump_days_offset
        AND n.MRBTS=s_mrbts AND n.NRBTS=s_nrbts AND n.NRCELL=s_nrcell
    GROUP BY t.mrbts, t.lnbts, t.lncel, n.MRBTS, n.NRBTS, n.NRCELL
),
q_kpi_refuse_received AS (
    SELECT t.xDate, t.xHour,
        t.MRBTS_ID AS S_MRBTS, t.RNBTS_ID AS S_NRBTS, t.RNCEL_ID AS S_NRCELL,
        t.X2_SGNB_CHG_REF_RECEIVED
    FROM isat_raw_5g.nokgnb_ps_nx2cc_nrcel_hour t
    WHERE t.xDate >= (SELECT MAX(xDate) FROM isat_raw_5g.nokgnb_ps_nx2cc_nrcel_hour) - p_kpi_days_hourly_agg_offset
),
q_kpi_refuse AS (
    SELECT t.xDate, t.xHour,
        t.MRBTS_ID AS MeNB_MRBTS, t.LNBTS_ID AS MeNB_LNBTS, t.LNCEL_ID AS MeNB_LNCEL,
        t.SGNB_CHANGE_REFUSE
    FROM isat_raw_4g.noklte_ps_lxpl_lncel_hour t
    WHERE t.xDate >= (SELECT MAX(xDate) FROM isat_raw_4g.noklte_ps_lxpl_lncel_hour) - p_kpi_days_hourly_agg_offset
),
q_comb AS (
    SELECT n.xDate, n.xHour,
        t.S_MRBTS, t.S_NRBTS, t.S_NRCELL,
        t.MeNB_MRBTS, t.MeNB_LNBTS, t.MeNB_LNCEL,
        n.X2_SGNB_CHG_REF_RECEIVED
    FROM q_menb_list_of_src t
        LEFT JOIN q_kpi_refuse_received n
            ON t.S_MRBTS=n.S_MRBTS AND t.S_NRBTS=n.S_NRBTS AND t.S_NRCELL=n.S_NRCELL
),
q_comb2 AS (
    SELECT t.xDate, t.xHour,
        t.S_MRBTS, t.S_NRBTS, t.S_NRCELL,
        t.MeNB_MRBTS, t.MeNB_LNBTS, t.MeNB_LNCEL,
        t.X2_SGNB_CHG_REF_RECEIVED, r.SGNB_CHANGE_REFUSE
    FROM q_comb t
        LEFT JOIN q_kpi_refuse r
            ON t.xDate=r.xDate AND t.xHour=r.xHour
            AND t.MeNB_MRBTS=r.MeNB_MRBTS AND t.MeNB_LNBTS=r.MeNB_LNBTS AND t.MeNB_LNCEL=r.MeNB_LNCEL
)
SELECT
    S_MRBTS, S_NRBTS, S_NRCELL,
    MeNB_MRBTS, MeNB_LNBTS, MeNB_LNCEL,
    CORR(X2_SGNB_CHG_REF_RECEIVED, SGNB_CHANGE_REFUSE) AS Ref_Rec_Corr,
    COUNT() AS NbrOfSample
FROM q_comb2
GROUP BY S_MRBTS, S_NRBTS, S_NRCELL, MeNB_MRBTS, MeNB_LNBTS, MeNB_LNCEL
"""

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔗 Missing Relations", "📈 Correlation Analysis"])

# ══ TAB 1 — MISSING RELATIONS ══
with tab1:
    st.subheader("🔗 Deteksi Relasi MeNB → SgNB yang Missing")
    st.caption("Identifikasi sel 4G (MeNB) yang belum punya relasi Lnadjgnb / Lnrelgnbcell ke sel 5G target")

    if run_btn:
        try:
            client = get_client()
            with st.spinner("⏳ Menjalankan query missing relations..."):
                df_miss = run_query(client, build_missing_query(
                    s_mrbts, s_nrbts, s_nrcell, p_dump_days, p_kpi_days_hourly))

            if df_miss.empty:
                st.warning("⚠️ Tidak ada data. Periksa parameter S_MRBTS / S_NRBTS / S_NRCELL.")
            else:
                df_miss['Lnadjgnb_To_Nbr']          = df_miss['Lnadjgnb_To_Nbr'].fillna('')
                df_miss['Lnrelgnbcell_To_Nbr']       = df_miss['Lnrelgnbcell_To_Nbr'].fillna('')
                df_miss['SGNB_CHANGE_REFUSE']         = pd.to_numeric(df_miss['SGNB_CHANGE_REFUSE'], errors='coerce').fillna(0)
                df_miss['X2_SGNB_CHG_REF_RECEIVED']  = pd.to_numeric(df_miss['X2_SGNB_CHG_REF_RECEIVED'], errors='coerce').fillna(0)
                df_miss['Status'] = df_miss.apply(get_missing_status, axis=1)

                df_complete = df_miss[df_miss['Status'] == 'COMPLETE']
                df_missing  = df_miss[df_miss['Status'] != 'COMPLETE'].sort_values('SGNB_CHANGE_REFUSE', ascending=False)

                # Metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Pasangan Sel",          len(df_miss))
                c2.metric("✅ Complete",                  len(df_complete))
                c3.metric("❌ Missing (perlu dibuat)",    len(df_missing))
                c4.metric("Total SGNB Refuse (missing)", f"{int(df_missing['SGNB_CHANGE_REFUSE'].sum()):,}")

                st.divider()

                # Missing table
                st.subheader("❌ Relasi yang Harus Dibuat")
                disp = [c for c in [
                    'MeNB_SiteID','MeNB_SiteName','MeNB_MRBTS','MeNB_LNBTS','MeNB_LNCEL',
                    'MeNB_LTE_Band','MeNB_Azimuth',
                    'S_SiteID','S_SiteName','S_MRBTS','S_NRBTS','S_NRCELL','S_NR_Band',
                    'N_MRBTS','N_NRBTS','N_NRCELL',
                    'SGNB_CHANGE_REFUSE','X2_SGNB_CHG_REF_RECEIVED',
                    'Lnadjgnb_To_Nbr','Lnrelgnbcell_To_Nbr','Status'
                ] if c in df_missing.columns]

                st.dataframe(
                    df_missing[disp].reset_index(drop=True)
                    .style.format({'SGNB_CHANGE_REFUSE': '{:,.0f}', 'X2_SGNB_CHG_REF_RECEIVED': '{:,.0f}'}),
                    use_container_width=True, height=450
                )

                # Summary per site
                st.subheader("📊 Summary per MeNB Site")
                if 'MeNB_SiteID' in df_missing.columns:
                    df_sum = df_missing.groupby(['MeNB_SiteID','MeNB_SiteName']).agg(
                        Jumlah_Cell=('MeNB_LNCEL','count'),
                        Total_SGNB_Refuse=('SGNB_CHANGE_REFUSE','sum'),
                        Status=('Status', lambda x: ' | '.join(x.unique()))
                    ).reset_index().sort_values('Total_SGNB_Refuse', ascending=False)
                    st.dataframe(df_sum.style.format({'Total_SGNB_Refuse': '{:,.0f}'}),
                                 use_container_width=True)
                else:
                    df_sum = pd.DataFrame()

                # Export
                st.divider()
                col1, col2 = st.columns(2)
                sheets = {
                    'Missing Relations': df_missing[disp].reset_index(drop=True),
                    'Complete':          df_complete.reset_index(drop=True),
                    'All Data':          df_miss.reset_index(drop=True),
                }
                if not df_sum.empty:
                    sheets['Summary per Site'] = df_sum
                with col1:
                    st.download_button("⬇️ Download Excel",
                        data=to_excel_multi(sheets),
                        file_name=f"missing_relations_{s_mrbts}_{s_nrbts}_{s_nrcell}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True)
                with col2:
                    st.download_button("⬇️ Download CSV (Missing Only)",
                        data=df_missing[disp].to_csv(index=False).encode('utf-8'),
                        file_name=f"missing_relations_{s_mrbts}_{s_nrbts}_{s_nrcell}.csv",
                        mime="text/csv", use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.info("Pastikan koneksi ClickHouse benar dan parameter sudah diisi.")
    else:
        st.info("👈 Isi parameter di sidebar, lalu klik **Jalankan Analisis**.")
        with st.expander("ℹ️ Penjelasan Status"):
            st.markdown("""
| Status | Arti | Action |
|---|---|---|
| ✅ COMPLETE | Lnadjgnb + Lnrelgnbcell sudah ada | Tidak perlu action |
| 🟠 MISSING Lnrelgnbcell | X2 link sudah ada, tapi cell-level relation belum | Buat **Lnrelgnbcell** saja |
| 🔴 MISSING BOTH | Keduanya belum ada | Buat **Lnadjgnb** + **Lnrelgnbcell** |
            """)

# ══ TAB 2 — CORRELATION ══
with tab2:
    st.subheader("📈 Analisis Korelasi SgNB Refuse")
    st.caption("Hitung korelasi antara X2_SGNB_CHG_REF_RECEIVED (5G) dan SGNB_CHANGE_REFUSE (4G) per pasangan sel")

    if run_btn:
        try:
            client = get_client()
            with st.spinner("⏳ Menjalankan query korelasi..."):
                df_raw = run_query(client, build_corr_query(
                    s_mrbts, s_nrbts, s_nrcell, p_dump_days, p_kpi_days_hourly))

            if df_raw.empty:
                st.warning("⚠️ Tidak ada data korelasi.")
            else:
                df_raw["Ref_Rec_Corr"] = pd.to_numeric(df_raw["Ref_Rec_Corr"], errors="coerce")
                df_raw["NbrOfSample"]  = pd.to_numeric(df_raw["NbrOfSample"],  errors="coerce")
                df_raw["Corr_Abs"]     = df_raw["Ref_Rec_Corr"].abs()

                df = df_raw[
                    (df_raw["Corr_Abs"] >= corr_threshold) &
                    (df_raw["NbrOfSample"] >= min_samples)
                ].copy()
                df["Kategori"] = df["Ref_Rec_Corr"].apply(get_corr_label)
                df = df.sort_values("Corr_Abs", ascending=False).reset_index(drop=True)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Pasangan (raw)", len(df_raw))
                c2.metric("Lolos Filter",         len(df))
                c3.metric("Avg Korelasi",         f"{df['Ref_Rec_Corr'].mean():.3f}" if len(df) else "—")
                c4.metric("Max Korelasi",         f"{df['Ref_Rec_Corr'].max():.3f}"  if len(df) else "—")

                st.divider()

                if df.empty:
                    st.info("ℹ️ Tidak ada pasangan sel yang memenuhi threshold. Coba turunkan nilai threshold.")
                else:
                    disp = ["S_MRBTS","S_NRBTS","S_NRCELL","MeNB_MRBTS","MeNB_LNBTS","MeNB_LNCEL",
                            "Ref_Rec_Corr","NbrOfSample","Kategori"]
                    st.subheader("📋 Hasil Korelasi")
                    st.dataframe(
                        df[disp].style
                        .background_gradient(subset=["Ref_Rec_Corr"], cmap="RdYlGn", vmin=-1, vmax=1)
                        .format({"Ref_Rec_Corr": "{:.4f}"}),
                        use_container_width=True, height=420
                    )
                    st.subheader("🚨 Top 10 Paling Mencurigakan")
                    st.dataframe(df.head(10)[disp].style.format({"Ref_Rec_Corr": "{:.4f}"}),
                                 use_container_width=True)
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("⬇️ Download CSV",
                            data=df[disp].to_csv(index=False).encode("utf-8"),
                            file_name=f"correlation_{s_mrbts}_{s_nrbts}_{s_nrcell}.csv",
                            mime="text/csv", use_container_width=True)
                    with col2:
                        st.download_button("⬇️ Download Excel",
                            data=to_excel_multi({"Correlation Result": df[disp]}),
                            file_name=f"correlation_{s_mrbts}_{s_nrbts}_{s_nrcell}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.info("Pastikan koneksi ClickHouse benar dan parameter sudah diisi.")
    else:
        st.info("👈 Isi parameter di sidebar, lalu klik **Jalankan Analisis**.")
        with st.expander("ℹ️ Interpretasi Korelasi"):
            st.markdown("""
| Nilai | Kategori | Interpretasi |
|---|---|---|
| ≥ 0.9 | 🔴 Sangat Tinggi | Kemungkinan besar sel 4G ini penyebab masalah |    
| ≥ 0.7 | 🟠 Tinggi | Perlu investigasi lebih lanjut |
| ≥ 0.5 | 🟡 Sedang | Perlu dimonitor |
| < 0.5 | 🟢 Rendah | Tidak signifikan |
            """)