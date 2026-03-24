"""
data/repository.py
All ClickHouse query logic.
Single Responsibility: data fetching only — no UI, no calculations.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import pandas as pd
from clickhouse_connect.driver import Client

logger = logging.getLogger(__name__)


def _query_to_df(client: Client, sql: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Returns empty DF on error."""
    try:
        result = client.query_df(sql)
        return result
    except Exception as exc:
        logger.error("Query failed:\n%s\nError: %s", sql, exc)
        return pd.DataFrame()


def fetch_regions(client: Client) -> list[str]:
    sql = """
        SELECT DISTINCT REGION
        FROM ioh_tmp.`5G_Site_Tracker`
        ORDER BY REGION
    """
    df = _query_to_df(client, sql)
    if df.empty:
        return []
    return df.iloc[:, 0].dropna().tolist()


def fetch_nc5g(client: Client, region: str) -> list[str]:
    sql = f"""
        SELECT DISTINCT `NC 5G`
        FROM ioh_tmp.`5G_Site_Tracker`
        WHERE REGION = '{region}'
        ORDER BY `NC 5G`
    """
    df = _query_to_df(client, sql)
    if df.empty:
        return []
    return df.iloc[:, 0].dropna().tolist()


def fetch_site_ids(client: Client, nc5g_list: list[str]) -> list[str]:
    """
    Fetch distinct SITE IDs for one or more NC 5G values.
    Supports multiselect — accepts a list of NC 5G strings.
    Uses `NC 5G` IN (...) clause for multi-value filtering.
    """
    if not nc5g_list:
        return []
    escaped = [f"'{v}'" for v in nc5g_list]
    in_clause = f"({', '.join(escaped)})"
    sql = f"""
        SELECT DISTINCT `SITE ID`
        FROM ioh_tmp.`5G_Site_Tracker`
        WHERE `NC 5G` IN {in_clause}
        ORDER BY `SITE ID`
    """
    df = _query_to_df(client, sql)
    if df.empty:
        return []
    return df.iloc[:, 0].dropna().tolist()


def _format_list(values: list[str]) -> str:
    """Format a list as ClickHouse IN clause string."""
    escaped = [f"'{v}'" for v in values]
    return f"({', '.join(escaped)})"


def fetch_5g_list(client: Client, site_ids: list[str]) -> pd.DataFrame:
    if not site_ids:
        return pd.DataFrame()
    ids_str = _format_list(site_ids)
    sql = f"""
        SELECT
            mrbts, nrbts, nrcell, site_id, name, branch, sales_area,
            micro_cluster_sa, site_name, band, nrafcndl, sector,
            `NC`, `REGION`, `CITY`, `Longitude`, `Latitude`,
            sector_flag, sector_name, azimuth, hos, logic_dir, status
        FROM ioh_adm.t_list_5g
        WHERE site_id IN {ids_str}
    """
    return _query_to_df(client, sql)


def fetch_4g_list(client: Client, site_ids: list[str]) -> pd.DataFrame:
    if not site_ids:
        return pd.DataFrame()
    ids_str = _format_list(site_ids)
    sql = f"""
        SELECT
            operator, vendor, `UniqueID`, `eNodeB Name`, `Cell Name`,
            `LocalCell Id`, mrbts, lnbts, lncel, `Site_ID`,
            system_key, bw, band, `earfcnDL`, sector_id, sector_type,
            azimuth, oss, last_date, `DlMimoMode`, `Antena`, `Last_update`,
            `Hos`, `Coverage`, `CellStat`, `Siteid_latest`,
            `Long`, `Lat`, `Region`, `Micro_cluster`, `Branch`,
            `Kabupaten`, `Nano_cluster`, sector_flag, sector_name, `Region2`
        FROM ioh_adm.t_list_4g
        WHERE `Siteid_latest` IN {ids_str}
    """
    return _query_to_df(client, sql)


def fetch_5g_kpi_day(
    client: Client,
    nrbts_ids: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if not nrbts_ids:
        return pd.DataFrame()
    ids_str = _format_list(nrbts_ids)
    sql = f"""
        SELECT *
        FROM isat_kpi.`5G_KPI_CELL_NUM_DENUM_DAY`
        WHERE xDate BETWEEN '{start_date}' AND '{end_date}'
          AND NRBTS_ID IN {ids_str}
    """
    return _query_to_df(client, sql)


def fetch_5g_kpi_pa13(
    client: Client,
    nrbts_ids: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if not nrbts_ids:
        return pd.DataFrame()
    ids_str = _format_list(nrbts_ids)
    sql = f"""
        SELECT *
        FROM isat_kpi.`5G_KPI_CELL_NUM_DENUM_DAY_PA13`
        WHERE xDate BETWEEN '{start_date}' AND '{end_date}'
          AND NRBTS_ID IN {ids_str}
    """
    return _query_to_df(client, sql)


def fetch_4g_kpi(
    client: Client,
    mrbts_ids: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if not mrbts_ids:
        return pd.DataFrame()
    ids_str = _format_list(mrbts_ids)
    sql = f"""
        SELECT *
        FROM isat_kpi.`4G_KPI_NUM_DENUM_DAY`
        WHERE xDate BETWEEN '{start_date}' AND '{end_date}'
          AND MRBTS_ID IN {ids_str}
    """
    return _query_to_df(client, sql)
