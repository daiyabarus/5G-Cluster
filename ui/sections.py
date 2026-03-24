"""
ui/sections.py
Streamlit section renderers: traffic, user, 5G KPIs, 4G KPIs, contributor tables.
Single Responsibility: renders pre-computed data only, no business logic.

CHANGES v2:
1. ALL summary/contributor tables moved to BOTTOM of each section (after charts).
2. Download logic replaced: st.dataframe column_config.LinkColumn removed;
   instead each table gets a native st.download_button via pre-computed CSV bytes
   (kept stable-key pattern) — no dependency on st.experimental_data_editor.
3. NC 5G multiselect → chart lines are color-coded per NC 5G cluster when
   group_col="nc5g_label" is available (passed via nc5g_color_map).
4. KPI charts use 3-column grid inside st.container(border=True).
5. Modern card containers with st.container(border=True) per chart group.
"""

from __future__ import annotations

from datetime import date, datetime

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
    add_baseline_bands,
    COLOR_5G,
    COLOR_4G,
    COLOR_NC5G_PALETTE,
    _hex_to_rgba,
)

# ── NC 5G color map helper ────────────────────────────────────────────────────


def _make_nc5g_color_map(nc5g_list: list[str]) -> dict[str, str]:
    """Map each NC 5G label → a color from the shared palette."""
    return {
        nc: COLOR_NC5G_PALETTE[i % len(COLOR_NC5G_PALETTE)]
        for i, nc in enumerate(nc5g_list)
    }


# ── Download button helper ────────────────────────────────────────────────────


def _ts() -> str:
    """Return current datetime stamp: YYYYMMDD_HHMMSS."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _stamped(file_name: str) -> str:
    """
    Inject a datetime stamp before the .csv extension.
    E.g. "5g_contributor.csv" → "5g_contributor_20250324_143022.csv"
    """
    if file_name.lower().endswith(".csv"):
        base = file_name[:-4]
        return f"{base}_{_ts()}.csv"
    return f"{file_name}_{_ts()}"


def _csv_download_button(
    df: pd.DataFrame,
    file_name: str,
    key: str,
    label: str = "⬇ Download CSV",
) -> None:
    """
    Render a compact CSV download button.
    - CSV bytes pre-computed outside button call (prevents scroll-to-top reruns).
    - Filename automatically stamped with current datetime: {name}_{YYYYMMDD_HHMMSS}.csv
    """
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=_stamped(file_name),
        mime="text/csv",
        key=key,
        width="stretch",
    )


# ── Section label helper ──────────────────────────────────────────────────────


def _section_label(text: str) -> None:
    st.markdown(
        f"<p style='color:#64748B;font-size:0.78rem;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.7px;margin:0 0 6px 2px'>"
        f"{text}</p>",
        unsafe_allow_html=True,
    )


# ── Overview ──────────────────────────────────────────────────────────────────


def render_overview_section(
    df_5g_traffic: pd.DataFrame,
    df_4g_traffic: pd.DataFrame,
    df_5g_user: pd.DataFrame,
    df_4g_user: pd.DataFrame,
) -> None:
    col_left, col_right = st.columns(2, gap="medium")
    with col_left:
        with st.container(border=True):
            fig = build_traffic_chart(df_5g_traffic, df_4g_traffic)
            st.plotly_chart(fig, width="stretch")
    with col_right:
        with st.container(border=True):
            fig = build_user_chart(df_5g_user, df_4g_user)
            st.plotly_chart(fig, width="stretch")


# ── 5G KPI Section ────────────────────────────────────────────────────────────


def render_5g_kpi_section(
    df_pa13: pd.DataFrame,
    df_day: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
    nc5g_list: list[str] | None = None,
) -> None:
    """
    5G KPI — Cluster Level.
    Layout: charts first (3-column grid), summary table at the bottom.
    Lines are color-coded per NC 5G cluster when nc5g_list is provided.
    """
    if df_pa13.empty and df_day.empty:
        st.warning("No 5G KPI data available for the selected range.")
        return

    nc5g_list = nc5g_list or []
    nc5g_color_map = _make_nc5g_color_map(nc5g_list)

    kpi_day = [k for k in KPI_5G if k.source == "day"]
    kpi_pa13 = [k for k in KPI_5G if k.source == "pa13"]

    # ── 1. CHARTS (3-column grid) ─────────────────────────────────────────────
    st.markdown("#### 📡 5G KPI Trends")

    N_COLS = 3
    kpi_chunks = [KPI_5G[i : i + N_COLS] for i in range(0, len(KPI_5G), N_COLS)]

    for chunk in kpi_chunks:
        cols = st.columns(N_COLS, gap="small")
        for idx, kpi in enumerate(chunk):
            with cols[idx]:
                with st.container(border=True):
                    source_df = df_day if kpi.source == "day" else df_pa13

                    # Build daily KPI — group by nc5g_label if multi-NC-5G
                    group_col = None
                    if len(nc5g_list) > 1 and "nc5g_label" in source_df.columns:
                        group_col = "nc5g_label"

                    df_daily = compute_daily_kpi(
                        source_df, kpi, date_col, group_col=group_col
                    )

                    fig = build_kpi_line_chart(
                        df_daily=df_daily,
                        kpi_name=kpi.name,
                        unit=kpi.unit,
                        threshold=kpi.threshold,
                        date_col=date_col,
                        color=COLOR_5G,
                        nc5g_color_map=nc5g_color_map if group_col else None,
                        group_col=group_col,
                    )
                    st.plotly_chart(fig, width="stretch")

    # ── 2. SUMMARY TABLE (bottom) ─────────────────────────────────────────────
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

        thresh_map = {k.name: k.threshold for k in KPI_5G}
        dir_map = {k.name: k.higher_is_better for k in KPI_5G}
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

        with st.container(border=True):
            hdr_col, btn_col = st.columns([7, 1])
            with hdr_col:
                st.markdown("##### 📊 5G KPI — PRE vs POST Baseline")
                st.caption(
                    f"PRE: {pre_window[0]} → {pre_window[1]}  |  "
                    f"POST: {post_window[0]} → {post_window[1]}"
                )
            with btn_col:
                _csv_download_button(summary, "5g_kpi_baseline.csv", "dl_5g_baseline")

            st.dataframe(
                _style_5g_baseline(summary),
                width="stretch",
                hide_index=True,
            )


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

    # ── 1. CHARTS (3-column grid) ─────────────────────────────────────────────
    st.markdown("#### 📻 4G KPI Trends")

    N_COLS = 3
    kpi_chunks = [KPI_4G[i : i + N_COLS] for i in range(0, len(KPI_4G), N_COLS)]

    for chunk in kpi_chunks:
        cols = st.columns(N_COLS, gap="small")
        for idx, kpi in enumerate(chunk):
            with cols[idx]:
                with st.container(border=True):
                    df_daily = compute_daily_kpi(df_4g, kpi, date_col)
                    fig = build_kpi_line_chart(
                        df_daily=df_daily,
                        kpi_name=kpi.name,
                        unit=kpi.unit,
                        threshold=kpi.threshold,
                        date_col=date_col,
                        color=COLOR_4G,
                    )
                    st.plotly_chart(fig, width="stretch")

    # ── 2. SUMMARY TABLE (bottom) ─────────────────────────────────────────────
    summary = build_cluster_summary_table(
        df_4g, KPI_4G, pre_window, post_window, date_col
    )
    if not summary.empty:
        with st.container(border=True):
            hdr_col, btn_col = st.columns([7, 1])
            with hdr_col:
                st.markdown("##### 📊 4G KPI — PRE vs POST Baseline")
                st.caption(
                    f"PRE: {pre_window[0]} → {pre_window[1]}  |  "
                    f"POST: {post_window[0]} → {post_window[1]}"
                )
            with btn_col:
                _csv_download_button(summary, "4g_kpi_baseline.csv", "dl_4g_baseline")

            st.dataframe(
                style_summary_table(summary),
                width="stretch",
                hide_index=True,
            )


# ── Contributor Section ───────────────────────────────────────────────────────


def render_contributor_section(
    df_pa13: pd.DataFrame,
    df_day: pd.DataFrame,
    df_4g: pd.DataFrame,
    pre_window: tuple,
    post_window: tuple,
    date_col: str = "xDate",
) -> None:
    tab_5g, tab_4g, tab_payload = st.tabs(
        [
            "📡 5G — Threshold Failures",
            "📻 4G — PRE vs POST Delta",
            "📦 Payload (Traffic & Users)",
        ]
    )

    # ── 5G Tab ────────────────────────────────────────────────────────────────
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
                max_date_label = (
                    contrib_5g_sorted["Date"].iloc[0]
                    if "Date" in contrib_5g_sorted.columns
                    else "latest date"
                )

                hdr_c, btn_c = st.columns([7, 1])
                with hdr_c:
                    has_cell = "NRCELName" in contrib_5g_sorted.columns
                    st.caption(
                        f"📅 Snapshot: **{max_date_label}** — "
                        f"{total_rows} cell–KPI combinations failing threshold. "
                        + ("Grouped by Site ID + NRCELName." if has_cell else "")
                    )
                with btn_c:
                    _csv_download_button(
                        contrib_5g_sorted, "5g_contributor.csv", "dl_5g_contrib"
                    )

                st.dataframe(
                    _style_5g_contributor(contrib_5g_sorted),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.success("✅ All 5G cells are meeting their KPI thresholds.")
        else:
            st.info("No 5G cell data available or no KPIs have defined thresholds.")

    # ── 4G Tab ────────────────────────────────────────────────────────────────
    with tab_4g:
        if df_4g.empty or "site_id" not in df_4g.columns:
            st.info("No 4G site data available.")
        else:
            contrib_4g = build_site_contributor_table(
                df_4g, KPI_4G, pre_window, post_window, date_col
            )
            if not contrib_4g.empty:
                hdr_c2, btn_c2 = st.columns([7, 1])
                with hdr_c2:
                    st.caption(
                        f"{len(contrib_4g)} degraded site–KPI combinations — "
                        f"PRE: {pre_window[0]} → {pre_window[1]} | "
                        f"POST: {post_window[0]} → {post_window[1]}"
                    )
                with btn_c2:
                    _csv_download_button(
                        contrib_4g, "4g_contributor.csv", "dl_4g_contrib"
                    )

                st.dataframe(
                    style_summary_table(contrib_4g),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.success("✅ No degraded 4G sites found in this period.")

    # ── Payload Tab ───────────────────────────────────────────────────────────
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
            pre_n, pre_d = (
                grp.loc[pre_mask, col_num].sum(),
                grp.loc[pre_mask, col_den].sum(),
            )
            post_n, post_d = (
                grp.loc[post_mask, col_num].sum(),
                grp.loc[post_mask, col_den].sum(),
            )
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

    # ── Left: Traffic ──────────────────────────────────────────────────────
    with col_left:
        _section_label("📶 Traffic (GB) — Degraded Sites")
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
                _csv_download_button(df_t, "payload_traffic.csv", "dl_payload_traffic")

            st.dataframe(
                _style_delta_table(df_t, delta_col="DELTA (%)", status_col="STATUS"),
                width="stretch",
                hide_index=True,
            )
        else:
            st.success("✅ No traffic-degraded sites found.")

    # ── Right: Active Users ────────────────────────────────────────────────
    with col_right:
        _section_label("👥 Active Users — Degraded Sites")
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

            hc_u, bc_u = st.columns([5, 1])
            with hc_u:
                st.caption(f"{len(df_u)} sites degraded")
            with bc_u:
                _csv_download_button(df_u, "payload_users.csv", "dl_payload_users")

            st.dataframe(
                _style_delta_table(df_u, delta_col="DELTA (%)", status_col="STATUS"),
                width="stretch",
                hide_index=True,
            )
        else:
            st.success("✅ No user-degraded sites found.")


# ── Styling helpers ───────────────────────────────────────────────────────────

_TABLE_STYLES = [
    {
        "selector": "thead th",
        "props": [
            ("background-color", "#F1F5F9"),
            ("color", "#0F172A"),
            ("font-weight", "600"),
            ("font-size", "0.82rem"),
            ("padding", "0.6rem 0.75rem"),
            ("border-bottom", "2px solid #E2E8F0"),
            ("letter-spacing", "0.3px"),
        ],
    },
    {
        "selector": "tbody td",
        "props": [
            ("padding", "0.55rem 0.75rem"),
            ("border-bottom", "1px solid #F1F5F9"),
            ("font-size", "0.88rem"),
        ],
    },
    {
        "selector": "tbody tr:hover",
        "props": [("background-color", "#F8FAFC")],
    },
]


def _style_5g_baseline(df: pd.DataFrame):
    def color_status(val: str) -> str:
        s = str(val)
        if "Degrade" in s or "Below Target" in s:
            return "background-color:rgba(220,38,38,0.08);color:#DC2626;font-weight:600"
        if "Improve" in s:
            return "background-color:rgba(22,163,74,0.08);color:#16A34A;font-weight:600"
        if "Maintain" in s:
            return (
                "background-color:rgba(245,158,11,0.08);color:#D97706;font-weight:500"
            )
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
            return "color:#CBD5E1"
        return "color:#2563EB;font-weight:500"

    styler = df.style.set_table_styles(_TABLE_STYLES)
    if "STATUS" in df.columns:
        styler = styler.map(color_status, subset=["STATUS"])
    if "DELTA (%)" in df.columns:
        styler = styler.map(color_delta, subset=["DELTA (%)"])
    if "Threshold" in df.columns:
        styler = styler.map(color_threshold, subset=["Threshold"])
    return styler


def _style_5g_contributor(df: pd.DataFrame):
    def color_gap(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color:#DC2626;font-weight:600"
            if v < 0:
                return "color:#F97316"
        except (TypeError, ValueError):
            pass
        return "color:#1E293B"

    def color_status(val: str) -> str:
        if "Failed" in str(val):
            return "background-color:rgba(220,38,38,0.08);color:#DC2626;font-weight:600"
        return ""

    def highlight_cell(val) -> str:
        return "color:#2563EB;font-weight:500"

    styler = df.style.set_table_styles(_TABLE_STYLES)
    if "Gap" in df.columns:
        styler = styler.map(color_gap, subset=["Gap"])
    if "STATUS" in df.columns:
        styler = styler.map(color_status, subset=["STATUS"])
    if "NRCELName" in df.columns:
        styler = styler.map(highlight_cell, subset=["NRCELName"])
    return styler


def _style_delta_table(
    df: pd.DataFrame,
    delta_col: str = "DELTA (%)",
    status_col: str = "STATUS",
):
    def color_status(val: str) -> str:
        if "Degrade" in str(val):
            return "background-color:rgba(220,38,38,0.08);color:#DC2626;font-weight:600"
        return ""

    def color_delta(val) -> str:
        try:
            v = float(val)
            if v < -5:
                return "color:#DC2626;font-weight:600"
        except (TypeError, ValueError):
            pass
        return "color:#1E293B"

    styler = df.style.set_table_styles(_TABLE_STYLES)
    if status_col in df.columns:
        styler = styler.map(color_status, subset=[status_col])
    if delta_col in df.columns:
        styler = styler.map(color_delta, subset=[delta_col])
    return styler
