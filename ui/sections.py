"""
ui/sections.py
Streamlit section renderers: traffic, user, 5G KPIs, 4G KPIs, contributor tables.
Single Responsibility: renders pre-computed data only, no business logic.
"""

from __future__ import annotations

from datetime import date
import io

import pandas as pd
import streamlit as st

from config.kpi_config import KPI_5G, KPI_4G, KPIDefinition
from data.processor import (
    compute_daily_kpi,
    build_cluster_summary_table,
    build_site_contributor_table,
    build_5g_failed_contributor_table,
)
from utils.charts import (
    build_traffic_chart,
    build_user_chart,
    build_kpi_line_chart,
    style_summary_table,
    COLOR_5G,
    COLOR_4G,
)


def render_traffic_section(
    df_5g_traffic: pd.DataFrame,
    df_4g_traffic: pd.DataFrame,
) -> None:
    """Left column of the 2-col overview — called by render_overview_section."""
    fig = build_traffic_chart(df_5g_traffic, df_4g_traffic)
    st.plotly_chart(fig, width='stretch')


def render_user_section(
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
) -> None:
    """Right column of the 2-col overview — called by render_overview_section."""
    fig = build_user_chart(df_5g_user, df_4g_user)
    st.plotly_chart(fig, width='stretch')


def render_overview_section(
    df_5g_traffic: pd.DataFrame,
    df_4g_traffic: pd.DataFrame,
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
) -> None:
    """
    2-column overview row:
      Left  → Daily Traffic GB (4G + 5G area chart)
      Right → Active Users (4G + 5G area chart)
    """
    col_left, col_right = st.columns(2, gap="medium")
    with col_left:
        render_traffic_section(df_5g_traffic, df_4g_traffic)
    with col_right:
        render_user_section(df_5g_user, df_4g_user)


def render_5g_kpi_section(
    df_pa13: pd.DataFrame,
    df_day: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
) -> None:
    """
    5G KPI — Cluster Level.

    Summary table: PRE vs POST baseline comparison for every KPI.
      - PRE  = first half of date range
      - POST = second half of date range
      - DELTA % and STATUS computed per KPI
      - For KPIs WITH a threshold: STATUS also reflects pass/fail vs target
      - Download button exports summary as CSV

    Charts: full-range long line charts (2-column grid) with threshold line.
    """
    # st.markdown("### 📡 5G KPI — Cluster Level")

    if df_pa13.empty and df_day.empty:
        st.warning("No 5G KPI data available for the selected range.")
        return

    kpi_day = [k for k in KPI_5G if k.source == "day"]
    kpi_pa13 = [k for k in KPI_5G if k.source == "pa13"]

    # ── Build baseline summary (PRE vs POST) ─────────────────────────────────
    import pandas as _pd

    summaries = []
    if kpi_day and not df_day.empty:
        summaries.append(
            build_cluster_summary_table(
                df_day, kpi_day, pre_window, post_window, date_col
            )
        )
    if kpi_pa13 and not df_pa13.empty:
        summaries.append(
            build_cluster_summary_table(
                df_pa13, kpi_pa13, pre_window, post_window, date_col
            )
        )

    if summaries:
        summary = _pd.concat(summaries, ignore_index=True)

        # Enrich: add Threshold column and override STATUS for threshold KPIs
        from config.kpi_config import KPI_5G as _KPI_5G

        thresh_map = {k.name: k.threshold for k in _KPI_5G}
        dir_map = {k.name: k.higher_is_better for k in _KPI_5G}
        summary["Threshold"] = summary["KPI"].map(thresh_map)

        def _enrich_status(row):
            """If threshold defined, flag fail even if baseline delta is OK."""
            thr = row.get("Threshold")
            post_val = row.get("POST")
            status = row.get("STATUS", "N/A")
            if thr is not None and post_val is not None:
                hib = dir_map.get(row["KPI"], True)
                failed = (post_val < thr) if hib else (post_val > thr)
                if failed and "Degrade" not in str(status):
                    return "🔴 Below Target"
            return status

        summary["STATUS"] = summary.apply(_enrich_status, axis=1)

        # Reorder columns
        cols_order = ["KPI", "Unit", "Threshold", "PRE", "POST", "DELTA (%)", "STATUS"]
        summary = summary[[c for c in cols_order if c in summary.columns]]

        with st.expander(
            "📊 5G KPI — Baseline Comparison (PRE vs POST)", expanded=True
        ):
            hdr_col, btn_col = st.columns([6, 1])
            with hdr_col:
                st.caption(
                    f"PRE: {pre_window[0]} → {pre_window[1]}  |  "
                    f"POST: {post_window[0]} → {post_window[1]}"
                )
            with btn_col:
                csv_bytes = summary.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇ CSV",
                    data=csv_bytes,
                    file_name="5g_kpi_baseline.csv",
                    mime="text/csv",
                    width='stretch',
                )
            st.dataframe(
                _style_5g_baseline(summary),
                width='stretch',
                hide_index=True,
            )

    # ── Charts grid — 2 columns, full date range ──────────────────────────────
    n_cols = 2
    kpi_chunks = [KPI_5G[i : i + n_cols] for i in range(0, len(KPI_5G), n_cols)]

    for chunk in kpi_chunks:
        cols = st.columns(n_cols)
        for idx, kpi in enumerate(chunk):
            with cols[idx]:
                source_df = df_day if kpi.source == "day" else df_pa13
                df_daily = compute_daily_kpi(source_df, kpi, date_col)
                fig = build_kpi_line_chart(
                    df_daily=df_daily,
                    kpi_name=kpi.name,
                    unit=kpi.unit,
                    threshold=kpi.threshold,
                    date_col=date_col,
                    color=COLOR_5G,
                )
                st.plotly_chart(fig, width='stretch')


def render_4g_kpi_section(
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
) -> None:
    """
    4G KPI section.
    Charts: full date range line charts (no PRE/POST bands).
    Summary table: PRE vs POST delta shown above charts.
    """
    # st.markdown("### 📻 4G KPI — Cluster Level")

    if df_4g.empty:
        st.warning("No 4G data available for the selected range.")
        return

    # Summary table (PRE/POST only in table, not in charts)
    summary = build_cluster_summary_table(
        df_4g, KPI_4G, pre_window, post_window, date_col
    )
    if not summary.empty:
        with st.expander("📊 4G KPI Summary (PRE vs POST)", expanded=True):
            st.dataframe(
                style_summary_table(summary),
                width='stretch',
                hide_index=True,
            )

    # Long charts grid — 2 columns, full date range
    n_cols = 2
    kpi_chunks = [KPI_4G[i : i + n_cols] for i in range(0, len(KPI_4G), n_cols)]

    for chunk in kpi_chunks:
        cols = st.columns(n_cols)
        for idx, kpi in enumerate(chunk):
            with cols[idx]:
                df_daily = compute_daily_kpi(df_4g, kpi, date_col)
                fig = build_kpi_line_chart(
                    df_daily=df_daily,
                    kpi_name=kpi.name,
                    unit=kpi.unit,
                    threshold=kpi.threshold,
                    date_col=date_col,
                    color=COLOR_4G,
                )
                st.plotly_chart(fig, width='stretch')


def render_contributor_section(
    df_pa13: pd.DataFrame,
    df_day: pd.DataFrame,
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
) -> None:
    """
    Site Contributor Analysis — Top 10.

    5G logic  → threshold-based:
      Shows sites that FAIL their KPI threshold over the full date range.
      Columns: Site ID | KPI | Threshold | Actual | Gap | Unit | STATUS
      Only KPIs with a defined threshold are included.

    4G logic  → PRE/POST delta-based:
      Shows top-10 most degraded sites by PRE→POST delta%.
      Columns: Site ID | KPI | PRE | POST | DELTA (%) | STATUS
    """
    # st.markdown("### 🔍 Site Contributor Analysis (Top 10 Degraded)")

    tab_5g, tab_4g, tab_payload = st.tabs(
        [
            "📡 5G — Threshold Failures",
            "📻 4G — PRE vs POST Delta",
            "📦 Payload (Traffic & Users)",
        ]
    )

    # ── 5G Tab: threshold-based failures ─────────────────────────────────────
    with tab_5g:
        import pandas as _pd

        kpi_day_list = [k for k in KPI_5G if k.source == "day"]
        kpi_pa13_list = [k for k in KPI_5G if k.source == "pa13"]

        contribs_5g = []
        if kpi_day_list and not df_day.empty and "site_id" in df_day.columns:
            contribs_5g.append(
                build_5g_failed_contributor_table(df_day, kpi_day_list, date_col)
            )
        if kpi_pa13_list and not df_pa13.empty and "site_id" in df_pa13.columns:
            contribs_5g.append(
                build_5g_failed_contributor_table(df_pa13, kpi_pa13_list, date_col)
            )

        if contribs_5g:
            contrib_5g = _pd.concat(contribs_5g, ignore_index=True)
            if not contrib_5g.empty:
                contrib_5g_sorted = contrib_5g.sort_values("Gap", ascending=True)
                total_rows = len(contrib_5g_sorted)
                hdr_c, btn_c = st.columns([6, 1])
                with hdr_c:
                    st.caption(
                        f"All {total_rows} site–KPI combinations failing threshold. "
                        "Sorted by gap (most negative = worst)."
                    )
                with btn_c:
                    st.download_button(
                        "⬇ CSV",
                        data=contrib_5g_sorted.to_csv(index=False).encode(),
                        file_name="5g_contributor.csv",
                        mime="text/csv",
                        width='stretch',
                        key="dl_5g_contrib",
                    )
                st.dataframe(
                    _style_5g_contributor(contrib_5g_sorted),
                    width='stretch',
                    hide_index=True,
                )
            else:
                st.success("✅ All 5G sites are meeting their KPI thresholds.")
        else:
            st.info("No 5G site data available or no KPIs have defined thresholds.")

    # ── 4G Tab: PRE/POST delta-based ─────────────────────────────────────────
    with tab_4g:
        if df_4g.empty or "site_id" not in df_4g.columns:
            st.info("No 4G site data available.")
        else:
            contrib_4g = build_site_contributor_table(
                df_4g, KPI_4G, pre_window, post_window, date_col
            )
            if not contrib_4g.empty:
                total_4g = len(contrib_4g)
                hdr_c2, btn_c2 = st.columns([6, 1])
                with hdr_c2:
                    st.caption(
                        f"All {total_4g} degraded site–KPI combinations (incl. Traffic) — "
                        f"PRE: {pre_window[0]} → {pre_window[1]} | "
                        f"POST: {post_window[0]} → {post_window[1]}"
                    )
                with btn_c2:
                    st.download_button(
                        "⬇ CSV",
                        data=contrib_4g.to_csv(index=False).encode(),
                        file_name="4g_contributor.csv",
                        mime="text/csv",
                        width='stretch',
                        key="dl_4g_contrib",
                    )
                st.dataframe(
                    style_summary_table(contrib_4g),
                    width='stretch',
                    hide_index=True,
                )
            else:
                st.success("✅ No degraded 4G sites found in this period.")

    # ── Payload Tab: Traffic + Users degraded ────────────────────────────────
    with tab_payload:
        st.markdown("#### 📦 Payload Contributor — Traffic & Active Users")
        st.caption(
            "Sites where Daily Traffic (GB) or Active Users degraded "
            "between PRE and POST windows."
        )
        _render_payload_contributor(df_4g, pre_window, post_window)


def _render_payload_contributor(
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
    site_col: str = "site_id",
) -> None:
    """
    Show per-site PRE/POST/DELTA for:
      - DATA_TRAFFIC_GB  (higher is better → degrade if POST < PRE by >5%)
      - Active Users     (ACTIVE_USER_NUM / ACTIVE_USER_DENUM, higher is better)
    Displayed in 2 columns side by side.
    """
    import numpy as np

    DEGRADE_THR = -5.0

    def _prepost(grp, col_num, col_den=None):
        pre_mask = (grp[date_col] >= str(pre_window[0])) & (
            grp[date_col] <= str(pre_window[1])
        )
        post_mask = (grp[date_col] >= str(post_window[0])) & (
            grp[date_col] <= str(post_window[1])
        )
        if col_den and col_den in grp.columns:
            pre_n = grp.loc[pre_mask, col_num].sum()
            pre_d = grp.loc[pre_mask, col_den].sum()
            post_n = grp.loc[post_mask, col_num].sum()
            post_d = grp.loc[post_mask, col_den].sum()
            pre_v = (pre_n / pre_d) if pre_d > 0 else np.nan
            post_v = (post_n / post_d) if post_d > 0 else np.nan
        else:
            pre_v = (
                grp.loc[pre_mask, col_num].sum() if col_num in grp.columns else np.nan
            )
            post_v = (
                grp.loc[post_mask, col_num].sum() if col_num in grp.columns else np.nan
            )
        return pre_v, post_v

    col_left, col_right = st.columns(2, gap="medium")

    # ── Left: Traffic ─────────────────────────────────────────────────────────
    with col_left:
        st.markdown(
            "<p style='color:#94A3B8;font-size:0.8rem;font-weight:500;"
            "text-transform:uppercase;letter-spacing:0.5px'>"
            "📶 Traffic (GB) — Degraded Sites</p>",
            unsafe_allow_html=True,
        )
        rows_traffic = []
        if (
            not df_4g.empty
            and site_col in df_4g.columns
            and "DATA_TRAFFIC_GB" in df_4g.columns
        ):
            for site, grp in df_4g.groupby(site_col):
                pre_v, post_v = _prepost(grp, "DATA_TRAFFIC_GB")
                if np.isnan(pre_v) or pre_v == 0:
                    continue
                delta = ((post_v - pre_v) / abs(pre_v)) * 100
                if delta <= DEGRADE_THR:
                    rows_traffic.append(
                        {
                            "Site ID": site,
                            "PRE (GB)": round(pre_v, 3),
                            "POST (GB)": round(post_v, 3),
                            "DELTA (%)": round(delta, 2),
                            "STATUS": "🔴 Degrade",
                        }
                    )

        if rows_traffic:
            import pandas as _pd

            df_t = _pd.DataFrame(rows_traffic).sort_values("DELTA (%)", ascending=True)
            hc_t, bc_t = st.columns([5, 1])
            with hc_t:
                st.caption(f"{len(df_t)} sites degraded")
            with bc_t:
                st.download_button(
                    "⬇ CSV",
                    data=df_t.to_csv(index=False).encode(),
                    file_name="payload_traffic.csv",
                    mime="text/csv",
                    width='stretch',
                    key="dl_payload_traffic",
                )
            st.dataframe(
                df_t.style.applymap(
                    lambda v: (
                        "color:#FCA5A5;font-weight:600"
                        if isinstance(v, str) and "Degrade" in v
                        else ""
                    ),
                    subset=["STATUS"],
                ).applymap(
                    lambda v: (
                        "color:#FCA5A5"
                        if isinstance(v, (int, float)) and v < -5
                        else "color:#E2E8F0"
                    ),
                    subset=["DELTA (%)"],
                ),
                width='stretch',
                hide_index=True,
            )
        else:
            st.success("✅ No traffic-degraded sites found.")

    # ── Right: Active Users ───────────────────────────────────────────────────
    with col_right:
        st.markdown(
            "<p style='color:#94A3B8;font-size:0.8rem;font-weight:500;"
            "text-transform:uppercase;letter-spacing:0.5px'>"
            "👥 Active Users — Degraded Sites</p>",
            unsafe_allow_html=True,
        )
        rows_users = []
        num_col, den_col = "ACTIVE_USER_NUM", "ACTIVE_USER_DENUM"
        fb_col = "RRC_CONNECTED_USER"
        has_ratio = (
            not df_4g.empty and num_col in df_4g.columns and den_col in df_4g.columns
        )
        has_fb = not df_4g.empty and fb_col in df_4g.columns

        if (has_ratio or has_fb) and site_col in df_4g.columns:
            for site, grp in df_4g.groupby(site_col):
                if has_ratio:
                    pre_v, post_v = _prepost(grp, num_col, den_col)
                else:
                    pre_v, post_v = _prepost(grp, fb_col)
                import numpy as _np

                if _np.isnan(pre_v) or pre_v == 0:
                    continue
                delta = ((post_v - pre_v) / abs(pre_v)) * 100
                if delta <= DEGRADE_THR:
                    rows_users.append(
                        {
                            "Site ID": site,
                            "PRE (Users)": round(pre_v, 2),
                            "POST (Users)": round(post_v, 2),
                            "DELTA (%)": round(delta, 2),
                            "STATUS": "🔴 Degrade",
                        }
                    )

        if rows_users:
            import pandas as _pd2

            df_u = _pd2.DataFrame(rows_users).sort_values("DELTA (%)", ascending=True)
            hc_u, bc_u = st.columns([5, 1])
            with hc_u:
                st.caption(f"{len(df_u)} sites degraded")
            with bc_u:
                st.download_button(
                    "⬇ CSV",
                    data=df_u.to_csv(index=False).encode(),
                    file_name="payload_users.csv",
                    mime="text/csv",
                    width='stretch',
                    key="dl_payload_users",
                )
            st.dataframe(
                df_u.style.applymap(
                    lambda v: (
                        "color:#FCA5A5;font-weight:600"
                        if isinstance(v, str) and "Degrade" in v
                        else ""
                    ),
                    subset=["STATUS"],
                ).applymap(
                    lambda v: (
                        "color:#FCA5A5"
                        if isinstance(v, (int, float)) and v < -5
                        else "color:#E2E8F0"
                    ),
                    subset=["DELTA (%)"],
                ),
                width='stretch',
                hide_index=True,
            )
        else:
            st.success("✅ No user-degraded sites found.")


def _style_5g_baseline(df: pd.DataFrame):
    """Color coding for 5G KPI baseline comparison table."""

    def color_status(val: str) -> str:
        s = str(val)
        if "Degrade" in s or "Below Target" in s:
            return "background-color:rgba(220,38,38,0.2);color:#FCA5A5;font-weight:600"
        if "Improve" in s:
            return "background-color:rgba(5,150,105,0.2);color:#6EE7B7;font-weight:600"
        if "Maintain" in s:
            return "background-color:rgba(251,191,36,0.1);color:#FDE68A"
        return "color:#94A3B8"

    def color_delta(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color:#FCA5A5;font-weight:600"
            if v > 5:
                return "color:#6EE7B7;font-weight:600"
        except (TypeError, ValueError):
            pass
        return "color:#E2E8F0"

    def color_threshold(val) -> str:
        if val is None or (isinstance(val, float) and __import__("math").isnan(val)):
            return "color:#4B5563"
        return "color:#93C5FD"

    styler = df.style
    if "STATUS" in df.columns:
        styler = styler.applymap(color_status, subset=["STATUS"])
    if "DELTA (%)" in df.columns:
        styler = styler.applymap(color_delta, subset=["DELTA (%)"])
    if "Threshold" in df.columns:
        styler = styler.applymap(color_threshold, subset=["Threshold"])
    return styler


def _style_5g_contributor(df: pd.DataFrame):
    """Color coding for 5G threshold-failure contributor table."""

    def color_gap(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color: #FF4444; font-weight: bold"
            if v < 0:
                return "color: #FF9944"
        except (TypeError, ValueError):
            pass
        return "color: #FAFAFA"

    def color_status(val: str) -> str:
        if "Failed" in str(val):
            return "background-color: rgba(255,45,45,0.25); color: #FF6B6B"
        return ""

    styler = df.style
    if "Gap" in df.columns:
        styler = styler.applymap(color_gap, subset=["Gap"])
    if "STATUS" in df.columns:
        styler = styler.applymap(color_status, subset=["STATUS"])
    return styler
