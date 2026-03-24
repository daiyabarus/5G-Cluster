"""
config/kpi_config.py
Centralised KPI definitions, thresholds, and direction flags.

KEY CHANGE: formula_num and formula_denum now support LISTS of column names.
When a list is provided, the processor sums all listed columns before computing
the ratio. This handles KPIs like UL Interference that require adding counters
from multiple sources (PUCCH + PUSCH) before dividing.

Example:
    UL Interference  = (PUCCH_NUM + PUSCH_NUM) / (PUCCH_DENUM + PUSCH_DENUM)
    DL Spectrum Eff  = (SE_NUM + SE_DENUM_X) / (SE_DENUM + SE_DENUMX_DIV)

Processor logic handles both str and list[str] transparently.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union


@dataclass(frozen=True)
class KPIDefinition:
    name: str
    # Accept either a single column name OR a list of columns to be summed
    formula_num: Union[str, list[str]]
    formula_denum: Union[str, list[str]]
    unit: str = "%"
    threshold: Optional[float] = None
    higher_is_better: bool = True
    multiply: float = 100.0
    source: str = "pa13"  # "pa13" | "day" | "4g"


# ── 5G KPI Definitions ────────────────────────────────────────────────────────
KPI_5G: list[KPIDefinition] = [
    # ── FROM PA13 TABLE ──────────────────────────────────────────────────────
    KPIDefinition(
        name="Availability",
        formula_num="5G_CELL_AVAILABILITY_SYSTEM_NUM",
        formula_denum="5G_CELL_AVAILABILITY_SYSTEM_DENUM",
        threshold=98.0,
        higher_is_better=True,
        source="pa13",
    ),
    KPIDefinition(
        name="Accessibility",
        formula_num=[
            "NR_5020D_5G_NSA_NON_STAND_ALONE_CALL_ACCESSIBILITY_5G_SIDE_NUM1",
            "NR_5020D_5G_NSA_NON_STAND_ALONE_CALL_ACCESSIBILIT_5G_SIDE_NUM2",
        ],
        formula_denum=[
            "NR_5020D_5G_NSA_NON_STAND_ALONE_CALL_ACCESSIBILITY_5G_SIDE_DENUM1",
            "NR_5020D_5G_NSA_NON_STAND_ALONE_CALL_ACCESSIBILITY_5G_SIDE_DENUM2",
        ],
        threshold=99.0,
        higher_is_better=True,
        source="day",
    ),
    KPIDefinition(
        name="SCG Abnormal Release Rate",
        formula_num="5G_CALL_DROP_RATE_NUM",
        formula_denum="5G_CALL_DROP_RATE_DENUM",
        threshold=0.5,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="Intra-PSCell Change SR",
        formula_num="5G_INTRA_ESGNB_PSCELL_CHANGE_NUM",
        formula_denum="5G_INTRA_ESGNB_PSCELL_CHANGE_DENUM",
        threshold=98.0,
        higher_is_better=True,
        source="pa13",
    ),
    KPIDefinition(
        name="Inter-PSCell Change SR",
        formula_num="5G_INTER_ESGNB_PSCELL_CHANGE_NUM",
        formula_denum="5G_INTER_ESGNB_PSCELL_CHANGE_DENUM",
        threshold=97.0,
        higher_is_better=True,
        source="pa13",
    ),
    KPIDefinition(
        name="DL BLER",
        formula_num="5G_DL_INITIAL_BLER_NUM",
        formula_denum="5G_DL_INITIAL_BLER_DENUM",
        threshold=0.2,
        higher_is_better=False,
        source="pa13",
        multiply=1.0,
    ),
    KPIDefinition(
        name="UL BLER",
        formula_num="5G_UL_INITIAL_BLER_NUM",
        formula_denum="5G_UL_INITIAL_BLER_DENUM",
        threshold=0.4,
        higher_is_better=False,
        source="pa13",
        multiply=1.0,
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
        name="Rank 4 Share",
        formula_num="MIMO_RANK_4_SHARE_NUM",
        formula_denum="MIMO_RANK_4_SHARE_DENUM",
        threshold=None,
        higher_is_better=True,
        source="pa13",
    ),
    # ── MULTI-COUNTER KPI: UL Interference ────────────────────────────────
    # Formula: (PUCCH_NUM + PUSCH_NUM) / (PUCCH_DENUM + PUSCH_DENUM)
    # Both numerator columns are summed BEFORE the division.
    # This is the correct way to combine counters from two sources.
    KPIDefinition(
        name="UL Interference",
        formula_num=["5G_UL_INTERFERENCE_PUCCH_NUM", "5G_UL_INTERFERENCE_PUSCH_NUM"],
        formula_denum=[
            "5G_UL_INTERFERENCE_PUCCH_DENUM",
            "5G_UL_INTERFERENCE_PUSCH_DENUM",
        ],
        threshold=-110.0,
        higher_is_better=False,
        unit="dBm",
        multiply=1.0,
        source="pa13",
    ),
    KPIDefinition(
        name="QPSK Ratio",
        formula_num="5G_QPSK_RATIO_NUM",
        formula_denum="5G_QPSK_RATIO_DENUM",
        threshold=None,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="DL Latency",
        formula_num="5G_DL_LATENCY_IN_GNB_NUM",
        formula_denum="5G_DL_LATENCY_IN_GNB_DENUM",
        threshold=None,
        higher_is_better=False,
        unit="ms",
        multiply=0.01,
        source="pa13",
    ),
    KPIDefinition(
        name="DL Spectrum Efficiency",
        formula_num="5G_DL_SPECTRUM_EFFICIENCY_NUM",
        formula_denum=[
            "5G_DL_SPECTRUM_EFFICIENCY_DENUM",
            "5G_DL_SPECTRUM_EFFICIENCY_DENUM_X",
            "5G_DL_SPECTRUM_EFFICIENCY_DENUMX_DIV",
        ],
        threshold=None,
        higher_is_better=True,
        unit="bps/Hz",
        source="pa13",
        multiply=10.0,
    ),
    KPIDefinition(
        name="DL User Throughput",
        formula_num="5G_DL_USER_THPUT_NUM",
        formula_denum="5G_DL_USER_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.001,
        source="pa13",
    ),
    KPIDefinition(
        name="UL User Throughput",
        formula_num="5G_UL_USER_THPUT_NUM",
        formula_denum="5G_UL_USER_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.001,
        source="pa13",
    ),
    KPIDefinition(
        name="DL Cell Throughput",
        formula_num="5G_DL_CELL_THPUT_NUM",
        formula_denum="5G_DL_CELL_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=1.0,
        source="pa13",
    ),
    KPIDefinition(
        name="UL Cell Throughput",
        formula_num="5G_UL_CELL_THPUT_NUM",
        formula_denum="5G_UL_CELL_THPUT_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=1.0,
        source="pa13",
    ),
    KPIDefinition(
        name="DL PRB Utilization",
        formula_num="5G_DL_PRB_UTILIZATION_NUM",
        formula_denum="5G_DL_PRB_UTILIZATION_DENUM",
        threshold=None,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="UL PRB Utilization",
        formula_num="5G_UL_PRB_UTILIZATION_NUM",
        formula_denum="5G_UL_PRB_UTILIZATION_DENUM",
        threshold=None,
        higher_is_better=False,
        source="pa13",
    ),
    KPIDefinition(
        name="Avg EN-DC User",
        formula_num="5G_AVG_EN_DC_USER_NUM",
        formula_denum="5G_AVG_EN_DC_USER_DENUM",
        threshold=None,
        higher_is_better=True,
        unit="",
        source="pa13",
        multiply=1.0,
    ),
    # ── FROM DAY TABLE ────────────────────────────────────────────────────
    KPIDefinition(
        name="Average CQI",
        formula_num="AVG_WB_CQI_256QAM_NUM",
        formula_denum="AVG_WB_CQI_256QAM_DENUM",
        threshold=8.5,
        higher_is_better=True,
        unit="",
        multiply=1.0,
        source="day",
    ),
    KPIDefinition(
        name="SgNB Addition Success Rate",
        formula_num="NR_5005A_5G_SGNB_RECONFIGURATION_SUCCESS_RATIO_NUM",
        formula_denum="NR_5005A_5G_SGNB_RECONFIGURATION_SUCCESS_RATIO_DENUM",
        threshold=97.5,
        higher_is_better=True,
        source="day",
    ),
    # KPIDefinition(
    #     name="5G Cell Accessibility",
    #     formula_num="NR_5004B_5G_SGNB_ADDITION_PREPARATION_SUCCESS_RATIO_NUM",
    #     formula_denum="NR_5004B_5G_SGNB_ADDITION_PREPARATION_SUCCESS_RATIO_DENUM",
    #     threshold=99.0,
    #     higher_is_better=True,
    #     source="day",
    # ),
]

# ── 5G Traffic KPI ────────────────────────────────────────────────────────────
KPI_5G_TRAFFIC = {
    "dl_col": "5G_DL_TRAFFIC_VOLUME_GB",
    "ul_col": "5G_UL_TRAFFIC_VOLUME_GB",
    "source": "pa13",
}

KPI_5G_USER = {
    "num_col": "5G_AVG_EN_DC_USER_NUM",
    "denum_col": "5G_AVG_EN_DC_USER_DENUM",
    "source": "pa13",
}
# ── 4G KPI Definitions ────────────────────────────────────────────────────────
KPI_4G: list[KPIDefinition] = [
    KPIDefinition(
        name="Availability",
        formula_num="CELL_AVAILIBILITY_NUM",
        formula_denum="CELL_AVAILIBILITY_DENUM",
        threshold=98.5,
        higher_is_better=True,
        source="4g",
    ),
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
        name="EUT",
        formula_num="EUT_NUM",
        formula_denum="EUT_DENUM",
        threshold=3,
        higher_is_better=True,
        unit="Mbps",
        multiply=1.0,
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
        name="UL Interference",
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
        formula_num="DL_CELL_THROUGHPUT",
        formula_denum="",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    KPIDefinition(
        name="UL Cell Throughput",
        formula_num="UL_CELL_THROUGHPUT",
        formula_denum="",
        threshold=None,
        higher_is_better=True,
        unit="Mbps",
        multiply=0.000001,
        source="4g",
    ),
    KPIDefinition(
        name="Traffic (GB)",
        formula_num="DATA_TRAFFIC_GB",
        formula_denum="",
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
