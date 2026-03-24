"""
ui/sections.py
Streamlit section renderers: traffic, user, 5G KPIs, 4G KPIs, contributor tables.
Single Responsibility: renders pre-computed data only, no business logic.

KEY CHANGES:
1. CSV download bug fix — st.download_button now uses a unique stable key AND
   the CSV bytes are pre-computed outside the column layout.  Streamlit re-runs
   the entire script on every interaction; if the download button's `data`
   argument changes between runs (e.g. because a column-layout widget changes
   state first), it triggers another rerun and the page jumps to the top.
   Fix: compute CSV once, store in a local variable, pass directly.

2. 5G contributor section shows Site ID + NRCELName columns (cell-level).
   The _style_5g_contributor helper is updated to colour both columns.
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


# ── Download button helper ────────────────────────────────────────────────────

def _csv_download_button(
    df: pd.DataFrame,
    file_name: str,
    key: str,
    label: str = "⬇ CSV",
) -> None:
    """
    Render a download button for a DataFrame as CSV.

    BUG FIX: Compute CSV bytes ONCE before calling st.download_button.
    Generating bytes inside the button call can cause Streamlit to re-evaluate
    the expression on every rerun and scroll the page back to the top.
    Using a stable `key` prevents duplicate-widget errors across tabs.
    """
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=file_name,
        mime="text/csv",
        key=key,
        use_container_width=True,
    )


# ── Overview ──────────────────────────────────────────────────────────────────

def render_traffic_section(
    df_5g_traffic: pd.DataFrame,
    df_4g_traffic: pd.DataFrame,
) -> None:
    fig = build_traffic_chart(df_5g_traffic, df_4g_traffic)
    st.plotly_chart(fig, use_container_width=True)


def render_user_section(
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
) -> None:
    fig = build_user_chart(df_5g_user, df_4g_user)
    st.plotly_chart(fig, use_container_width=True)


def render_overview_section(
    df_5g_traffic: pd.DataFrame,
    df_4g_traffic: pd.DataFrame,
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
) -> None:
    col_left, col_right = st.columns(2, gap="medium")
    with col_left:
        render_traffic_section(df_5g_traffic, df_4g_traffic)
    with col_right:
        render_user_section(df_5g_user, df_4g_user)


# ── 5G KPI Section ────────────────────────────────────────────────────────────

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
    Charts: full-range long line charts (2-column grid) with threshold line.
    """
    if df_pa13.empty and df_day.empty:
        st.warning("No 5G KPI data available for the selected range.")
        return

    kpi_day = [k for k in KPI_5G if k.source == "day"]
    kpi_pa13 = [k for k in KPI_5G if k.source == "pa13"]

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

        from config.kpi_config import KPI_5G as _KPI_5G

        thresh_map = {k.name: k.threshold for k in _KPI_5G}
        dir_map = {k.name: k.higher_is_better for k in _KPI_5G}
        summary["Threshold"] = summary["KPI"].map(thresh_map)

        def _enrich_status(row):
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

        cols_order = ["KPI", "Unit", "Threshold", "PRE", "POST", "DELTA (%)", "STATUS"]
        summary = summary[[c for c in cols_order if c in summary.columns]]

        summary_csv = summary.to_csv(index=False).encode("utf-8")

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
                # FIX: use pre-computed bytes + stable key
                st.download_button(
                    label="⬇ CSV",
                    data=summary_csv,
                    file_name="5g_kpi_baseline.csv",
                    mime="text/csv",
                    key="dl_5g_baseline",
                    use_container_width=True,
                )
            st.dataframe(
                _style_5g_baseline(summary),
                use_container_width=True,
                hide_index=True,
            )

    n_cols = 2
    kpi_chunks = [KPI_5G[i: i + n_cols] for i in range(0, len(KPI_5G), n_cols)]

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
                st.plotly_chart(fig, use_container_width=True)


# ── 4G KPI Section ────────────────────────────────────────────────────────────

def render_4g_kpi_section(
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
) -> None:
    if df_4g.empty:
        st.warning("No 4G data available for the selected range.")
        return

    summary = build_cluster_summary_table(
        df_4g, KPI_4G, pre_window, post_window, date_col
    )
    if not summary.empty:
        # Pre-compute CSV
        summary_4g_csv = summary.to_csv(index=False).encode("utf-8")
        with st.expander("📊 4G KPI Summary (PRE vs POST)", expanded=True):
            hdr_col, btn_col = st.columns([6, 1])
            with hdr_col:
                st.caption(
                    f"PRE: {pre_window[0]} → {pre_window[1]}  |  "
                    f"POST: {post_window[0]} → {post_window[1]}"
                )
            with btn_col:
                st.download_button(
                    label="⬇ CSV",
                    data=summary_4g_csv,
                    file_name="4g_kpi_baseline.csv",
                    mime="text/csv",
                    key="dl_4g_baseline",
                    use_container_width=True,
                )
            st.dataframe(
                style_summary_table(summary),
                use_container_width=True,
                hide_index=True,
            )

    n_cols = 2
    kpi_chunks = [KPI_4G[i: i + n_cols] for i in range(0, len(KPI_4G), n_cols)]

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
                st.plotly_chart(fig, use_container_width=True)


# ── Contributor Section ───────────────────────────────────────────────────────

def render_contributor_section(
    df_pa13: pd.DataFrame,
    df_day: pd.DataFrame,
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
) -> None:
    """
    Cell/Site Contributor Analysis.

    5G tab → threshold-based, CELL level (Site ID + NRCELName).
    4G tab → PRE/POST delta-based, site level.
    Payload tab → Traffic & Users degraded sites.
    """
    tab_5g, tab_4g, tab_payload = st.tabs(
        [
            "📡 5G — Threshold Failures",
            "📻 4G — PRE vs POST Delta",
            "📦 Payload (Traffic & Users)",
        ]
    )

    # ── 5G Tab: threshold-based failures, CELL-level ──────────────────────
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
                sort_cols = (
                    ["Site ID", "NRCELName", "Gap"]
                    if "NRCELName" in contrib_5g.columns
                    else ["Site ID", "Gap"]
                )
                contrib_5g_sorted = contrib_5g.sort_values(sort_cols, ascending=True)
                total_rows = len(contrib_5g_sorted)

                # Show which date was used (max xDate from the data)
                max_date_label = (
                    contrib_5g_sorted["Date"].iloc[0]
                    if "Date" in contrib_5g_sorted.columns
                    else "latest date"
                )

                csv_5g = contrib_5g_sorted.to_csv(index=False).encode("utf-8")

                hdr_c, btn_c = st.columns([6, 1])
                with hdr_c:
                    has_cell = "NRCELName" in contrib_5g_sorted.columns
                    st.caption(
                        f"📅 Snapshot date: **{max_date_label}** — "
                        f"{total_rows} cell–KPI combinations failing threshold. "
                        + ("Grouped by Site ID + NRCELName. " if has_cell else "")
                        + "Sorted by gap (most negative = worst)."
                    )
                with btn_c:
                    st.download_button(
                        label="⬇ CSV",
                        data=csv_5g,
                        file_name="5g_contributor.csv",
                        mime="text/csv",
                        key="dl_5g_contrib",
                        use_container_width=True,
                    )
                st.dataframe(
                    _style_5g_contributor(contrib_5g_sorted),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("✅ All 5G cells are meeting their KPI thresholds.")
        else:
            st.info("No 5G cell data available or no KPIs have defined thresholds.")

    # ── 4G Tab: PRE/POST delta-based ──────────────────────────────────────
    with tab_4g:
        if df_4g.empty or "site_id" not in df_4g.columns:
            st.info("No 4G site data available.")
        else:
            contrib_4g = build_site_contributor_table(
                df_4g, KPI_4G, pre_window, post_window, date_col
            )
            if not contrib_4g.empty:
                total_4g = len(contrib_4g)

                # Pre-compute CSV
                csv_4g = contrib_4g.to_csv(index=False).encode("utf-8")

                hdr_c2, btn_c2 = st.columns([6, 1])
                with hdr_c2:
                    st.caption(
                        f"{total_4g} degraded site–KPI combinations (incl. Traffic) — "
                        f"PRE: {pre_window[0]} → {pre_window[1]} | "
                        f"POST: {post_window[0]} → {post_window[1]}"
                    )
                with btn_c2:
                    st.download_button(
                        label="⬇ CSV",
                        data=csv_4g,
                        file_name="4g_contributor.csv",
                        mime="text/csv",
                        key="dl_4g_contrib",
                        use_container_width=True,
                    )
                st.dataframe(
                    style_summary_table(contrib_4g),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("✅ No degraded 4G sites found in this period.")

    # ── Payload Tab ───────────────────────────────────────────────────────
    with tab_payload:
        st.markdown("#### 📦 Payload Contributor — Traffic & Active Users")
        st.caption(
            "Sites where Daily Traffic (GB) or Active Users degraded "
            "between PRE and POST windows."
        )
        _render_payload_contributor(df_4g, pre_window, post_window)


# ── Payload contributor ───────────────────────────────────────────────────────

def _render_payload_contributor(
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
    site_col: str = "site_id",
) -> None:
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
            pre_v = grp.loc[pre_mask, col_num].sum() if col_num in grp.columns else np.nan
            post_v = grp.loc[post_mask, col_num].sum() if col_num in grp.columns else np.nan
        return pre_v, post_v

    col_left, col_right = st.columns(2, gap="medium")

    # ── Left: Traffic ──────────────────────────────────────────────────────
    with col_left:
        st.markdown(
            "<p style='color:#64748B;font-size:0.8rem;font-weight:500;"
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

            # Pre-compute CSV
            csv_traffic = df_t.to_csv(index=False).encode("utf-8")

            hc_t, bc_t = st.columns([5, 1])
            with hc_t:
                st.caption(f"{len(df_t)} sites degraded")
            with bc_t:
                st.download_button(
                    label="⬇ CSV",
                    data=csv_traffic,
                    file_name="payload_traffic.csv",
                    mime="text/csv",
                    key="dl_payload_traffic",
                    use_container_width=True,
                )

            styled_traffic = df_t.style.map(
                lambda v: (
                    "color:#DC2626;font-weight:600"
                    if isinstance(v, str) and "Degrade" in v
                    else ""
                ),
                subset=["STATUS"],
            ).map(
                lambda v: (
                    "color:#DC2626"
                    if isinstance(v, (int, float)) and v < -5
                    else "color:#1E293B"
                ),
                subset=["DELTA (%)"],
            )
            st.dataframe(styled_traffic, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No traffic-degraded sites found.")

    # ── Right: Active Users ────────────────────────────────────────────────
    with col_right:
        st.markdown(
            "<p style='color:#64748B;font-size:0.8rem;font-weight:500;"
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
                if np.isnan(pre_v) or pre_v == 0:
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

            # Pre-compute CSV
            csv_users = df_u.to_csv(index=False).encode("utf-8")

            hc_u, bc_u = st.columns([5, 1])
            with hc_u:
                st.caption(f"{len(df_u)} sites degraded")
            with bc_u:
                st.download_button(
                    label="⬇ CSV",
                    data=csv_users,
                    file_name="payload_users.csv",
                    mime="text/csv",
                    key="dl_payload_users",
                    use_container_width=True,
                )

            styled_users = df_u.style.map(
                lambda v: (
                    "color:#DC2626;font-weight:600"
                    if isinstance(v, str) and "Degrade" in v
                    else ""
                ),
                subset=["STATUS"],
            ).map(
                lambda v: (
                    "color:#DC2626"
                    if isinstance(v, (int, float)) and v < -5
                    else "color:#1E293B"
                ),
                subset=["DELTA (%)"],
            )
            st.dataframe(styled_users, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No user-degraded sites found.")


# ── Styling helpers ───────────────────────────────────────────────────────────

def _style_5g_baseline(df: pd.DataFrame):
    """Color coding for 5G KPI baseline comparison table."""

    def color_status(val: str) -> str:
        s = str(val)
        if "Degrade" in s or "Below Target" in s:
            return "background-color:rgba(220,38,38,0.1);color:#DC2626;font-weight:600"
        if "Improve" in s:
            return "background-color:rgba(22,163,74,0.1);color:#16A34A;font-weight:600"
        if "Maintain" in s:
            return "background-color:rgba(245,158,11,0.1);color:#F59E0B"
        return "color:#64748B"

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

    def color_threshold(val) -> str:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return "color:#94A3B8"
        return "color:#3B82F6"

    styler = df.style
    if "STATUS" in df.columns:
        styler = styler.map(color_status, subset=["STATUS"])
    if "DELTA (%)" in df.columns:
        styler = styler.map(color_delta, subset=["DELTA (%)"])
    if "Threshold" in df.columns:
        styler = styler.map(color_threshold, subset=["Threshold"])

    styler = styler.set_table_styles([
        {
            "selector": "thead th",
            "props": [
                ("background-color", "#F8FAFC"),
                ("color", "#0F172A"),
                ("font-weight", "600"),
                ("font-size", "0.85rem"),
                ("padding", "0.75rem"),
                ("border-bottom", "2px solid #E2E8F0"),
            ],
        },
        {
            "selector": "tbody td",
            "props": [
                ("padding", "0.75rem"),
                ("border-bottom", "1px solid #F1F5F9"),
            ],
        },
    ])
    return styler


def _style_5g_contributor(df: pd.DataFrame):
    """
    Color coding for 5G threshold-failure contributor table.
    Handles both site-level (no NRCELName) and cell-level (with NRCELName).
    """

    def color_gap(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color: #DC2626; font-weight: 600"
            if v < 0:
                return "color: #F97316"
        except (TypeError, ValueError):
            pass
        return "color: #1E293B"

    def color_status(val: str) -> str:
        if "Failed" in str(val):
            return "background-color: rgba(220,38,38,0.1); color: #DC2626"
        return ""

    def highlight_cell_name(val) -> str:
        """Light blue tint for the NRCELName column for visual distinction."""
        return "color: #2563EB; font-weight: 500"

    styler = df.style
    if "Gap" in df.columns:
        styler = styler.map(color_gap, subset=["Gap"])
    if "STATUS" in df.columns:
        styler = styler.map(color_status, subset=["STATUS"])
    if "NRCELName" in df.columns:
        styler = styler.map(highlight_cell_name, subset=["NRCELName"])

    styler = styler.set_table_styles([
        {
            "selector": "thead th",
            "props": [
                ("background-color", "#F8FAFC"),
                ("color", "#0F172A"),
                ("font-weight", "600"),
                ("font-size", "0.85rem"),
                ("padding", "0.75rem"),
                ("border-bottom", "2px solid #E2E8F0"),
            ],
        },
        {
            "selector": "tbody td",
            "props": [
                ("padding", "0.75rem"),
                ("border-bottom", "1px solid #F1F5F9"),
            ],
        },
    ])
    return styler