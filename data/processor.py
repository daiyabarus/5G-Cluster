"""
data/processor.py
All data transformation, enrichment, and KPI calculation logic.
Single Responsibility: transforms raw DataFrames, no DB/UI concerns.

KEY NOTES:
1. _resolve_columns() handles formula_num/formula_denum as str OR list[str].
   When a list is given, all listed columns are summed before the ratio:
     UL Interference  = (PUCCH_NUM + PUSCH_NUM) / (PUCCH_DENUM + PUSCH_DENUM)
     DL Spectrum Eff  = (SE_NUM + SE_DENUM_X) / (SE_DENUM + SE_DENUMX_DIV)

2. NRCELName is a NATIVE column in both KPI source tables — no join needed.
   enrich_5g_with_site() only joins site_id via NRBTS_ID → nrbts.
   build_5g_failed_contributor_table() groups directly by NRCELName (+ site_id).
   Output: Site ID | NRCELName | KPI | Threshold | Actual | Gap | Unit | STATUS
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional, Union

import numpy as np
import pandas as pd

from config.kpi_config import (
    KPIDefinition,
    DEGRADE_THRESHOLD,
    IMPROVE_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _resolve_columns(
    formula: Union[str, list[str]],
    df: pd.DataFrame,
) -> Optional[pd.Series]:
    """
    Given a formula that is either:
      - a single column name  → return that column as a Series
      - a list of column names → return the element-wise SUM of all listed columns

    Returns None if ALL required columns are missing (logs a warning per missing col).
    Partial presence is handled gracefully: missing columns contribute 0 to the sum.
    """
    if isinstance(formula, str):
        if not formula:
            return None
        if formula not in df.columns:
            logger.warning("Column '%s' not found in dataframe", formula)
            return None
        return df[formula]

    # List case — sum all available columns
    available = []
    for col in formula:
        if col in df.columns:
            available.append(df[col])
        else:
            logger.warning("Multi-counter column '%s' not found — treated as 0", col)

    if not available:
        return None
    if len(available) == 1:
        return available[0]
    return sum(available)  # element-wise sum of Series objects


def _resolve_columns_agg(
    formula: Union[str, list[str]],
    df: pd.DataFrame,
    group_keys: list[str],
) -> Optional[pd.Series]:
    """
    Aggregate (sum by group_keys) then sum across list columns.
    Returns a Series aligned to the grouped result index.
    Used by compute_daily_kpi to aggregate before ratio.
    """
    if isinstance(formula, str):
        cols = [formula] if formula else []
    else:
        cols = formula

    available = [c for c in cols if c in df.columns]
    if not available:
        return None

    agg = df[group_keys + available].groupby(group_keys).sum(numeric_only=True)
    result = agg[available[0]].copy()
    for c in available[1:]:
        result = result + agg[c]
    return result


# ── Enrichment ────────────────────────────────────────────────────────────────


def enrich_5g_with_site(
    df_kpi: pd.DataFrame,
    df_5glist: pd.DataFrame,
    kpi_nrbts_col: str = "NRBTS_ID",
) -> pd.DataFrame:
    """
    Join site_id from df_5glist into a 5G KPI dataframe via NRBTS_ID → nrbts.

    NRCELName is already a native column in both KPI tables
    (5G_KPI_CELL_NUM_DENUM_DAY and 5G_KPI_CELL_NUM_DENUM_DAY_PA13),
    so no join is needed for the cell name — only site_id is added here.
    """
    if df_kpi.empty or df_5glist.empty:
        return df_kpi

    mapping = (
        df_5glist[["nrbts", "site_id"]]
        .drop_duplicates()
        .rename(columns={"nrbts": kpi_nrbts_col})
    )
    return df_kpi.merge(mapping, on=kpi_nrbts_col, how="left")


def enrich_4g_with_site(
    df_kpi: pd.DataFrame,
    df_4glist: pd.DataFrame,
    kpi_mrbts_col: str = "MRBTS_ID",
) -> pd.DataFrame:
    """Join Site_ID from df_4glist into a 4G KPI dataframe."""
    if df_kpi.empty or df_4glist.empty:
        return df_kpi
    mapping = df_4glist[["mrbts", "Site_ID"]].drop_duplicates()
    mapping = mapping.rename(columns={"mrbts": kpi_mrbts_col, "Site_ID": "site_id"})
    merged = df_kpi.merge(mapping, on=kpi_mrbts_col, how="left")
    return merged


# ── Date helpers ──────────────────────────────────────────────────────────────


def compute_baseline_windows(
    start_date: date,
    end_date: date,
) -> tuple[tuple[date, date], tuple[date, date]]:
    """
    Split selected range in half: PRE = first half, POST = second half.
    POST gets the extra day on odd ranges. Minimum 1 day per window.
    """
    total_days = (end_date - start_date).days + 1
    pre_days = max(1, total_days // 2)
    pre_start = start_date
    pre_end = start_date + timedelta(days=pre_days - 1)
    post_start = pre_end + timedelta(days=1)
    if post_start > end_date:
        post_start = end_date
    return (pre_start, pre_end), (post_start, end_date)


# ── KPI Ratio Computation ─────────────────────────────────────────────────────


def _safe_ratio(num: pd.Series, denum: pd.Series, multiply: float) -> pd.Series:
    """Compute num/denum * multiply, handling zeros safely."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(denum != 0, (num / denum) * multiply, np.nan)
    return pd.Series(result, index=num.index)


def compute_daily_kpi(
    df: pd.DataFrame,
    kpi: KPIDefinition,
    date_col: str = "xDate",
    group_col: Optional[str] = None,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    group_keys = [date_col]
    if group_col and group_col in df.columns:
        group_keys.append(group_col)

    # Collect all required columns
    num_cols = (
        [kpi.formula_num] if isinstance(kpi.formula_num, str) else kpi.formula_num
    )
    den_cols = []
    if kpi.formula_denum:
        den_cols = (
            [kpi.formula_denum]
            if isinstance(kpi.formula_denum, str)
            else kpi.formula_denum
        )

    num_cols = [c for c in num_cols if c]
    den_cols = [c for c in den_cols if c]

    # Validate at least one num column exists
    available_num = [c for c in num_cols if c in df.columns]
    if not available_num:
        logger.warning("No numerator columns found for KPI '%s'", kpi.name)
        return pd.DataFrame()

    all_agg_cols = list(
        dict.fromkeys(available_num + [c for c in den_cols if c in df.columns])
    )

    agg_base = (
        df[group_keys + all_agg_cols]
        .groupby(group_keys)
        .sum(numeric_only=True)
        .reset_index()
    )

    # Build summed numerator and denominator
    num_series = agg_base[[c for c in available_num if c in agg_base.columns]].sum(
        axis=1
    )

    available_den = [c for c in den_cols if c in agg_base.columns]
    if available_den:
        den_series = agg_base[available_den].sum(axis=1)
        agg_base["kpi_value"] = _safe_ratio(num_series, den_series, kpi.multiply)
    else:
        agg_base["kpi_value"] = num_series * kpi.multiply

    agg_base["kpi_name"] = kpi.name
    agg_base["unit"] = kpi.unit
    return agg_base


def compute_cluster_kpi(
    df: pd.DataFrame,
    kpi: KPIDefinition,
    window: Optional[tuple[date, date]] = None,
    date_col: str = "xDate",
) -> float:
    """
    Return a single cluster-level KPI value for a date window.
    Handles formula_num / formula_denum as str OR list[str].
    """
    if df.empty:
        return np.nan

    if window:
        mask = (df[date_col] >= str(window[0])) & (df[date_col] <= str(window[1]))
        df = df[mask]

    if df.empty:
        return np.nan

    num_series = _resolve_columns(kpi.formula_num, df)
    if num_series is None:
        return np.nan
    num_sum = num_series.sum()

    if kpi.formula_denum:
        den_series = _resolve_columns(kpi.formula_denum, df)
        if den_series is not None:
            den_sum = den_series.sum()
            if den_sum == 0:
                return np.nan
            return (num_sum / den_sum) * kpi.multiply

    return num_sum * kpi.multiply


# ── Traffic aggregation ───────────────────────────────────────────────────────


def compute_5g_daily_traffic(
    df_pa13: pd.DataFrame, date_col: str = "xDate"
) -> pd.DataFrame:
    """Sum DL+UL traffic per day from PA13 table."""
    if df_pa13.empty:
        return pd.DataFrame()
    needed = [date_col, "5G_DL_TRAFFIC_VOLUME_GB", "5G_UL_TRAFFIC_VOLUME_GB"]
    missing = [c for c in needed if c not in df_pa13.columns]
    if missing:
        logger.warning("5G traffic columns missing: %s", missing)
        return pd.DataFrame()
    agg = df_pa13[needed].groupby(date_col).sum(numeric_only=True).reset_index()
    agg["5G_TRAFFIC_GB"] = (
        agg["5G_DL_TRAFFIC_VOLUME_GB"] + agg["5G_UL_TRAFFIC_VOLUME_GB"]
    )
    return agg[[date_col, "5G_TRAFFIC_GB"]]


def compute_4g_daily_traffic(
    df_4g: pd.DataFrame, date_col: str = "xDate"
) -> pd.DataFrame:
    """Sum 4G total/DL/UL traffic per day."""
    if df_4g.empty:
        return pd.DataFrame()
    total_col = "DATA_TRAFFIC_GB"
    if total_col not in df_4g.columns:
        dl_col, ul_col = "DATA_DL_TRAFFIC_GB", "DATA_UL_TRAFFIC_GB"
        if dl_col in df_4g.columns and ul_col in df_4g.columns:
            df_4g = df_4g.copy()
            df_4g[total_col] = df_4g[dl_col] + df_4g[ul_col]
        else:
            logger.warning("DATA_TRAFFIC_GB column missing from 4G dataframe")
            return pd.DataFrame()
    cols = [date_col, total_col]
    for extra in ("DATA_DL_TRAFFIC_GB", "DATA_UL_TRAFFIC_GB"):
        if extra in df_4g.columns:
            cols.append(extra)
    agg = df_4g[cols].groupby(date_col).sum(numeric_only=True).reset_index()
    return agg


def compute_5g_daily_user(
    df_day: pd.DataFrame, date_col: str = "xDate"
) -> pd.DataFrame:
    """Avg NSA user per day from the DAY table."""
    if df_day.empty:
        return pd.DataFrame()
    num_col = "NR_5124A_5G_AVERAGE_NUMBER_OF_NSA_USERS_NUM"
    den_col = "NR_5124A_5G_AVERAGE_NUMBER_OF_NSA_USERS_DENUM"
    direct_col = "NR_5124A_5G_AVERAGE_NUMBER_OF_NSA_USERS"

    if num_col in df_day.columns and den_col in df_day.columns:
        agg = (
            df_day[[date_col, num_col, den_col]]
            .groupby(date_col)
            .sum(numeric_only=True)
            .reset_index()
        )
        agg["5G_USER"] = _safe_ratio(agg[num_col], agg[den_col], 1.0)
        return agg[[date_col, "5G_USER"]]

    if direct_col in df_day.columns:
        agg = (
            df_day[[date_col, direct_col]]
            .groupby(date_col)
            .mean(numeric_only=True)
            .reset_index()
        )
        agg["5G_USER"] = agg[direct_col]
        return agg[[date_col, "5G_USER"]]

    logger.warning("5G user columns missing in DAY dataframe")
    return pd.DataFrame()


def compute_4g_daily_user(df_4g: pd.DataFrame, date_col: str = "xDate") -> pd.DataFrame:
    """Avg active LTE user per day."""
    if df_4g.empty:
        return pd.DataFrame()
    num_col = "ACTIVE_USER_NUM"
    den_col = "ACTIVE_USER_DENUM"
    fallback_col = "RRC_CONNECTED_USER"
    if num_col in df_4g.columns and den_col in df_4g.columns:
        agg = (
            df_4g[[date_col, num_col, den_col]]
            .groupby(date_col)
            .sum(numeric_only=True)
            .reset_index()
        )
        agg["4G_USER"] = _safe_ratio(agg[num_col], agg[den_col], 1.0)
        return agg[[date_col, "4G_USER"]]
    if fallback_col in df_4g.columns:
        agg = (
            df_4g[[date_col, fallback_col]]
            .groupby(date_col)
            .sum(numeric_only=True)
            .reset_index()
        )
        agg["4G_USER"] = agg[fallback_col]
        return agg[[date_col, "4G_USER"]]
    logger.warning(
        "4G user columns missing: %s / %s / %s", num_col, den_col, fallback_col
    )
    return pd.DataFrame()


# ── Baseline / Contributor Table ──────────────────────────────────────────────


def determine_status(
    delta: float,
    higher_is_better: bool,
    degrade_threshold: float = DEGRADE_THRESHOLD,
    improve_threshold: float = IMPROVE_THRESHOLD,
) -> str:
    """Determine status string based on delta% and direction."""
    if pd.isna(delta):
        return "N/A"
    effective_delta = delta if higher_is_better else -delta
    if effective_delta <= degrade_threshold:
        return "🔴 Degrade"
    if effective_delta >= improve_threshold:
        return "🟢 Improve"
    return "🟡 Maintain"


def build_cluster_summary_table(
    df: pd.DataFrame,
    kpi_list: list[KPIDefinition],
    pre_window: tuple[date, date],
    post_window: tuple[date, date],
    date_col: str = "xDate",
) -> pd.DataFrame:
    """Build PRE/POST/DELTA summary table for a list of KPIs."""
    rows = []
    for kpi in kpi_list:
        pre_val = compute_cluster_kpi(df, kpi, pre_window, date_col)
        post_val = compute_cluster_kpi(df, kpi, post_window, date_col)

        if pd.notna(pre_val) and pd.notna(post_val) and pre_val != 0:
            delta = post_val - pre_val
            delta_pct = (delta / abs(pre_val)) * 100
        else:
            delta_pct = np.nan

        status = (
            determine_status(delta_pct, kpi.higher_is_better)
            if pd.notna(delta_pct)
            else "N/A"
        )

        rows.append(
            {
                "KPI": kpi.name,
                "PRE": round(pre_val, 4) if pd.notna(pre_val) else None,
                "POST": round(post_val, 4) if pd.notna(post_val) else None,
                "DELTA (%)": round(delta_pct, 2) if pd.notna(delta_pct) else None,
                "STATUS": status,
                "Unit": kpi.unit,
            }
        )
    return pd.DataFrame(rows)


def build_site_contributor_table(
    df: pd.DataFrame,
    kpi_list: list[KPIDefinition],
    pre_window: tuple[date, date],
    post_window: tuple[date, date],
    date_col: str = "xDate",
    site_col: str = "site_id",
) -> pd.DataFrame:
    """
    Compute per-site PRE/POST/DELTA for each KPI.
    Returns ALL degraded sites (no top-N cap).
    Also includes DATA_TRAFFIC_GB degrade logic automatically.
    """
    if df.empty or site_col not in df.columns:
        return pd.DataFrame()

    rows = []
    for kpi in kpi_list:
        # Validate columns exist
        num_cols = (
            [kpi.formula_num] if isinstance(kpi.formula_num, str) else kpi.formula_num
        )
        if not any(c in df.columns for c in num_cols if c):
            continue

        for site, grp in df.groupby(site_col):
            pre = compute_cluster_kpi(grp, kpi, pre_window, date_col)
            post = compute_cluster_kpi(grp, kpi, post_window, date_col)

            if pd.notna(pre) and pd.notna(post) and pre != 0:
                delta_pct = ((post - pre) / abs(pre)) * 100
            else:
                delta_pct = np.nan

            status = (
                determine_status(delta_pct, kpi.higher_is_better)
                if pd.notna(delta_pct)
                else "N/A"
            )

            if status != "🔴 Degrade":
                continue

            rows.append(
                {
                    "Site ID": site,
                    "KPI": kpi.name,
                    "PRE": round(pre, 4) if pd.notna(pre) else None,
                    "POST": round(post, 4) if pd.notna(post) else None,
                    "DELTA (%)": round(delta_pct, 2) if pd.notna(delta_pct) else None,
                    "STATUS": status,
                }
            )

    # ── Extra: DATA_TRAFFIC_GB degrade check ──────────────────────────────
    traffic_col = "DATA_TRAFFIC_GB"
    if traffic_col in df.columns:
        for site, grp in df.groupby(site_col):
            pre_mask = (grp[date_col] >= str(pre_window[0])) & (
                grp[date_col] <= str(pre_window[1])
            )
            post_mask = (grp[date_col] >= str(post_window[0])) & (
                grp[date_col] <= str(post_window[1])
            )
            pre_val = grp.loc[pre_mask, traffic_col].sum()
            post_val = grp.loc[post_mask, traffic_col].sum()
            if pre_val > 0:
                delta_pct = ((post_val - pre_val) / abs(pre_val)) * 100
                if delta_pct <= DEGRADE_THRESHOLD:
                    rows.append(
                        {
                            "Site ID": site,
                            "KPI": "Traffic (GB)",
                            "PRE": round(pre_val, 4),
                            "POST": round(post_val, 4),
                            "DELTA (%)": round(delta_pct, 2),
                            "STATUS": "🔴 Degrade",
                        }
                    )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["Site ID", "DELTA (%)"], ascending=[True, True]
    ).reset_index(drop=True)


def build_5g_failed_contributor_table(
    df: pd.DataFrame,
    kpi_list: list[KPIDefinition],
    date_col: str = "xDate",
    site_col: str = "site_id",
    cell_col: str = "NRCELName",
) -> pd.DataFrame:
    """
    5G contributor table — CELL-based, grouped by NRCELName.

    Uses ONLY the latest date (max xDate) in the dataframe, not the full range.
    This gives a snapshot of the worst-performing cells on the most recent day.

    NRCELName is a native column in both KPI source tables
    (5G_KPI_CELL_NUM_DENUM_DAY and 5G_KPI_CELL_NUM_DENUM_DAY_PA13).

    Grouping priority:
      1. site_id + NRCELName  (when both columns present — preferred)
      2. NRCELName only        (when site_id not yet joined)
      3. site_id only          (fallback if NRCELName absent)

    Output columns:
      Site ID | NRCELName | KPI | Threshold | Actual | Gap | Unit | STATUS

    A cell FAILS when:
      higher_is_better=True  → actual < threshold  (gap = actual - threshold, negative)
      higher_is_better=False → actual > threshold  (gap = threshold - actual, negative)
    """
    if df.empty:
        return pd.DataFrame()

    # ── Filter to max xDate only ──────────────────────────────────────────────
    max_date = df[date_col].max()
    df = df[df[date_col] == max_date].copy()
    if df.empty:
        return pd.DataFrame()
    logger.info("5G contributor: using max date = %s", max_date)

    has_site = site_col in df.columns
    has_cell = cell_col in df.columns

    if not has_site and not has_cell:
        logger.warning(
            "build_5g_failed_contributor_table: neither '%s' nor '%s' found in df",
            site_col,
            cell_col,
        )
        return pd.DataFrame()

    # Build group key list — always include NRCELName when available
    if has_site and has_cell:
        group_cols = [site_col, cell_col]
    elif has_cell:
        group_cols = [cell_col]
    else:
        group_cols = [site_col]

    rows = []
    kpis_with_threshold = [k for k in kpi_list if k.threshold is not None]

    for kpi in kpis_with_threshold:
        num_cols = (
            [kpi.formula_num] if isinstance(kpi.formula_num, str) else kpi.formula_num
        )
        if not any(c in df.columns for c in num_cols if c):
            continue

        for group_vals, grp in df.groupby(group_cols):
            # window=None → use all rows in grp (already filtered to max_date)
            val = compute_cluster_kpi(grp, kpi, window=None, date_col=date_col)
            if pd.isna(val):
                continue

            if kpi.higher_is_better:
                failed = val < kpi.threshold
                gap = val - kpi.threshold  # negative = below target
            else:
                failed = val > kpi.threshold
                gap = kpi.threshold - val  # negative = above target (bad)

            if not failed:
                continue

            # Unpack group key(s)
            if len(group_cols) == 2:
                site_val, cell_val = group_vals
            elif has_cell:
                site_val = None
                cell_val = group_vals
            else:
                site_val = group_vals
                cell_val = None

            rows.append(
                {
                    "Site ID": site_val if site_val is not None else "",
                    "NRCELName": cell_val if cell_val is not None else "",
                    "Date": str(max_date),
                    "KPI": kpi.name,
                    "Threshold": kpi.threshold,
                    "Actual": round(val, 4),
                    "Gap": round(gap, 4),
                    "Unit": kpi.unit,
                    "STATUS": "🔴 Failed",
                }
            )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)

    # Sort columns must match ascending length exactly
    if has_site and has_cell:
        sort_cols = ["Site ID", "NRCELName", "Gap"]
        ascending = [True, True, True]
    elif has_cell:
        sort_cols = ["NRCELName", "Gap"]
        ascending = [True, True]
    else:
        sort_cols = ["Site ID", "Gap"]
        ascending = [True, True]

    return result.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
