"""
config/kpi_config.py
Centralised KPI definitions, thresholds, and direction flags.
Easy to extend: add a new KPI dict entry — no code changes elsewhere.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class KPIDefinition:
    name: str
    formula_num: str  # column name numerator
    formula_denum: str  # column name denominator
    unit: str = "%"
    threshold: Optional[float] = None
    # False = lower is better (drop rate, BLER, etc.)
    higher_is_better: bool = True
    # multiply ratio before display (1.0 for raw values)
    multiply: float = 100.0
    source: str = "pa13"  # 'pa13' | 'day' | '4g'


# ── 5G KPI Definitions ────────────────────────────────────────────────────────
# Source mapping (confirmed):
#   source="day"  → isat_kpi.5G_KPI_CELL_NUM_DENUM_DAY
#   source="pa13" → isat_kpi.5G_KPI_CELL_NUM_DENUM_DAY_PA13
# ─────────────────────────────────────────────────────────────────────────────
KPI_5G: list[KPIDefinition] = [
    # ── FROM DAY TABLE ────────────────────────────────────────────────────────
    KPIDefinition(
        name="Availability",
        formula_num="NR_5150A_5G_CELL_AVAILABILITY_RATIO_NUM",
        formula_denum="NR_5150A_5G_CELL_AVAILABILITY_RATIO_DENUM",
        threshold=None,
        higher_is_better=True,
        source="day",
    ),
    KPIDefinition(
        name="SgNB Addition Success Rate",
        formula_num="NR_5004B_5G_SGNB_ADDITION_PREPARATION_SUCCESS_RATIO_NUM",
        formula_denum="NR_5004B_5G_SGNB_ADDITION_PREPARATION_SUCCESS_RATIO_DENUM",
        threshold=97.5,
        higher_is_better=True,
        source="day",
    ),
    KPIDefinition(
        name="SCG Abnormal Release Rate",
        formula_num="NR_5026A_5G_NSA_RATIO_OF_UE_RELEASES_DUE_TO_ABNORMAL_REASONS_NUM",
        formula_denum="NR_5026A_5G_NSA_RATIO_OF_UE_RELEASES_DUE_TO_ABNORMAL_REASONS_DENUM",
        threshold=0.5,
        higher_is_better=False,
        source="day",
    ),
    KPIDefinition(
        name="Intra-PSCell Change SR",
        formula_num="NR_5049B_5G_INTRA_FREQUENCY_INTRA_DU_PSCELL_CHANGE_TOTAL_SUCCESS_RATIO_NUM",
        formula_denum="NR_5049B_5G_INTRA_FREQUENCY_INTRA_DU_PSCELL_CHANGE_TOTAL_SUCCESS_RATIO_DENUM",
        threshold=98.0,
        higher_is_better=True,
        source="day",
    ),
    KPIDefinition(
        name="Inter-PSCell Change SR",
        formula_num="NR_5187B_5G_INTER_FREQUENCY_INTRA_DU_HANDOVER_TOTAL_SUCCESS_RATIO_FOR_NSA_NUM",
        formula_denum="NR_5187B_5G_INTER_FREQUENCY_INTRA_DU_HANDOVER_TOTAL_SUCCESS_RATIO_FOR_NSA_DENUM",
        threshold=97.0,
        higher_is_better=True,
        source="day",
    ),
    # ── FROM PA13 TABLE ───────────────────────────────────────────────────────
    KPIDefinition(
        name="Average CQI",
        formula_num="5G_AVG_CQI_NUM",
        formula_denum="5G_AVG_CQI_DENUM",
        threshold=8.5,
        higher_is_better=True,
        unit="",
        multiply=1.0,
        source="pa13",
    ),
    KPIDefinition(
        name="DL BLER",
        formula_num="5G_DL_INITIAL_BLER_NUM",
        formula_denum="5G_DL_INITIAL_BLER_DENUM",
        threshold=0.2,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="UL BLER",
        formula_num="5G_UL_INITIAL_BLER_NUM",
        formula_denum="5G_UL_INITIAL_BLER_DENUM",
        threshold=0.4,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="Rank 2 Share",
        formula_num="MIMO_RANK_2_SHARE_NUM",
        formula_denum="MIMO_RANK_2_SHARE_DENUM",
        threshold=10.0,
        higher_is_better=True,
        source="pa13",
    ),
    KPIDefinition(
        name="UL Interference",
        formula_num="CELL_AVG_UL_RIP_SCHED_ALL_PRB_NUM",
        formula_denum="CELL_AVG_UL_RIP_SCHED_ALL_PRB_DENUM",
        threshold=-110.0,
        higher_is_better=False,
        unit="dBm",
        multiply=1.0,
        source="pa13",
    ),
    KPIDefinition(
        name="DL User Throughput",
        formula_num="5G_DL_USER_THPUT_NUM",
        formula_denum="5G_DL_USER_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="pa13",
    ),
    KPIDefinition(
        name="UL User Throughput",
        formula_num="5G_UL_USER_THPUT_NUM",
        formula_denum="5G_UL_USER_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="pa13",
    ),
    KPIDefinition(
        name="DL Cell Throughput",
        formula_num="5G_DL_CELL_THPUT_NUM",
        formula_denum="5G_DL_CELL_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="pa13",
    ),
    KPIDefinition(
        name="UL Cell Throughput",
        formula_num="5G_UL_CELL_THPUT_NUM",
        formula_denum="5G_UL_CELL_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="pa13",
    ),
    KPIDefinition(
        name="RB Utilization DL",
        formula_num="5G_DL_PRB_UTILIZATION_NUM",
        formula_denum="5G_DL_PRB_UTILIZATION_DENUM",
        threshold=None,
        higher_is_better=True,
        source="pa13",
    ),
    KPIDefinition(
        name="Ping-Pong Ratio",
        formula_num="PIMGPONG_RATIO_NUM",
        formula_denum="PIMGPONG_RATIO_DENUM",
        threshold=None,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="RRC Connected User",
        formula_num="SUM_AVE_RRC_USER",
        formula_denum="NUMBER_HOUR",
        threshold=None,
        higher_is_better=True,
        unit="",
        multiply=1.0,
        source="pa13",
    ),
]

# ── 5G Traffic KPI (from both pa13 tables) ───────────────────────────────────
KPI_5G_TRAFFIC = {
    "dl_col": "5G_DL_TRAFFIC_VOLUME_GB",
    "ul_col": "5G_UL_TRAFFIC_VOLUME_GB",
    "source": "pa13",
}

# ── 5G User KPI (from PA13 table — SUM_AVE_RRC_USER / NUMBER_HOUR) ───────────
# NOTE: PA13 does not have dedicated NSA user num/denum columns in most schemas.
# Using SUM_AVE_RRC_USER / NUMBER_HOUR as proxy for connected user average.
KPI_5G_USER = {
    "num": "SUM_AVE_RRC_USER",
    "denum": "NUMBER_HOUR",
    "source": "pa13",
}

# ── 4G KPI Definitions — exact columns from isat_kpi.4G_KPI_NUM_DENUM_DAY ───
# Column reference confirmed from provided schema header.
KPI_4G: list[KPIDefinition] = [
    # ── Availability ──────────────────────────────────────────────────────────
    KPIDefinition(
        name="Availability",
        formula_num="CELL_AVAILIBILITY_NUM",  # exact spelling in schema
        formula_denum="CELL_AVAILIBILITY_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    # ── Access KPIs ──────────────────────────────────────────────────────────
    KPIDefinition(
        name="RRC Connection Setup SR",
        formula_num="RRC_SR_NUM",
        formula_denum="RRC_SR_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="eRAB Setup SR",
        formula_num="ERAB_SR_NUM",
        formula_denum="ERAB_SR_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="CSFB Setup SR",
        formula_num="CSFB_PREP_SR_NUM",
        formula_denum="CSFB_PREP_SR_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="S1 Signalling SR",
        formula_num="CSSR_S1_CONN_NUM",
        formula_denum="CSSR_S1_CONN_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="VoLTE Call Setup SR",
        formula_num="CSSR_VOLTE_NUM",
        formula_denum="CSSR_VOLTE_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    # ── Retainability ─────────────────────────────────────────────────────────
    KPIDefinition(
        name="eRAB Drop Rate",
        formula_num="DROP_PS_NUM",
        formula_denum="DROP_PS_DENUM",
        threshold=None,
        higher_is_better=False,
        source="4g",
    ),
    KPIDefinition(
        name="VoLTE Drop Call Rate",
        formula_num="DROP_VOLTE_NUM",
        formula_denum="DROP_VOLTE_DENUM",
        threshold=None,
        higher_is_better=False,
        source="4g",
    ),
    # ── Mobility ──────────────────────────────────────────────────────────────
    KPIDefinition(
        name="Intra-Freq HO SR",
        formula_num="HOSR_INTRA_FREQ_NUM",
        formula_denum="HOSR_INTRA_FREQ_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="Inter-Freq HO SR",
        formula_num="HOSR_INTER_FREQ_NUM",
        formula_denum="HOSR_INTER_FREQ_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="VoLTE HO SR",
        formula_num="HOSR_VOLTE_NUM",
        formula_denum="HOSR_VOLTE_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    # ── Radio Quality ─────────────────────────────────────────────────────────
    KPIDefinition(
        name="Average CQI",
        formula_num="CQI_NUM",
        formula_denum="CQI_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="",
        multiply=1.0,
        source="4g",
    ),
    KPIDefinition(
        name="DL BLER",
        formula_num="RBLER_DL_NUM",
        formula_denum="RBLER_DL_DENUM",
        threshold=None,
        higher_is_better=False,
        source="4g",
    ),
    KPIDefinition(
        name="EUT (DL User Thput)",
        formula_num="EUT_NUM",
        formula_denum="EUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    KPIDefinition(
        name="Rank 2",
        formula_num="RANK2_NUM",
        formula_denum="RANK2_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
    KPIDefinition(
        name="UL Interference (PUCCH)",
        formula_num="RSSI_PUCCH_NUM",
        formula_denum="RSSI_PUCCH_DENUM",
        threshold=None,
        higher_is_better=False,
        unit="dBm",
        multiply=1.0,
        source="4g",
    ),
    KPIDefinition(
        name="QPSK Ratio",
        formula_num="QPSK_RATIO_NUM",
        formula_denum="QPSK_RATIO_DENUM",
        threshold=None,
        higher_is_better=False,
        source="4g",
    ),
    KPIDefinition(
        name="Last TTI",
        formula_num="LAST_TTI_NUM",
        formula_denum="LAST_TTI_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="",
        multiply=1.0,
        source="4g",
    ),
    # ── Throughput ────────────────────────────────────────────────────────────
    KPIDefinition(
        name="DL User Throughput",
        formula_num="DL_USER_THROUGHPUT_NUM",
        formula_denum="DL_USER_THROUGHPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    KPIDefinition(
        name="UL User Throughput",
        formula_num="UL_USER_THROUGHPUT_NUM",
        formula_denum="UL_USER_THROUGHPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    KPIDefinition(
        name="DL Cell Throughput",
        # direct value column (not num/denum)
        formula_num="DL_CELL_THROUGHPUT",
        formula_denum=None,
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    KPIDefinition(
        name="UL Cell Throughput",
        formula_num="UL_CELL_THROUGHPUT",  # direct value column
        formula_denum=None,
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    # ── Volume & Users ────────────────────────────────────────────────────────
    KPIDefinition(
        name="Traffic (GB)",
        formula_num="DATA_TRAFFIC_GB",
        formula_denum=None,
        threshold=None,
        higher_is_better=True,
        unit="GB",
        multiply=1.0,
        source="4g",
    ),
    KPIDefinition(
        name="RRC Connected User",
        formula_num="ACTIVE_USER_NUM",
        formula_denum="ACTIVE_USER_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="",
        multiply=1.0,
        source="4g",
    ),
    KPIDefinition(
        name="RB Utilization DL",
        formula_num="DL_PRB_UTILIZATION_NUM",
        formula_denum="DL_PRB_UTILIZATION_DENUM",
        threshold=None,
        higher_is_better=True,
        source="4g",
    ),
]

# Status thresholds for contributor table
DEGRADE_THRESHOLD: float = -5.0  # delta% below this = Degrade
IMPROVE_THRESHOLD: float = 5.0  # delta% above this = Improve
