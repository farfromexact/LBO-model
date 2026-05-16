from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lbo.charts import metric_line_chart, sensitivity_heatmap, value_creation_bridge_chart
from lbo.engine import build_snapshot, load_scenario_defaults
from lbo.io.excel_loader import WorkbookLoadError
from lbo.schemas import EngineAssumptions


DEFAULT_WORKBOOK = ROOT / "examples" / "CPE 龙岛竹项目_财务模型_20260317.xlsx"

st.set_page_config(page_title="LBO Dashboard", layout="wide")
st.title("LBO Dashboard")

scenario = st.selectbox("Scenario", ["Base", "Optimistic", "Pessimistic"], index=0)

defaults = load_scenario_defaults(scenario)
with st.sidebar:
    st.header("Python Engine")
    st.caption("MVP 0.2 assumptions")
    entry_multiple = st.number_input("Entry multiple", min_value=0.1, max_value=50.0, value=defaults.entry_multiple, step=0.1)
    exit_multiple = st.number_input("Exit multiple", min_value=0.1, max_value=50.0, value=defaults.exit_multiple, step=0.1)
    exit_year = st.number_input("Exit year", min_value=2025, max_value=2050, value=defaults.exit_year, step=1)
    debt_interest_rate = st.slider(
        "Debt interest rate",
        min_value=0.0,
        max_value=0.30,
        value=defaults.debt_interest_rate,
        step=0.005,
        format="%.3f",
    )
    debt_repayment_speed = st.slider(
        "Debt repayment speed",
        min_value=0.0,
        max_value=1.0,
        value=defaults.debt_repayment_speed,
        step=0.05,
    )
    ebitda_growth = st.slider(
        "EBITDA growth",
        min_value=-0.20,
        max_value=0.50,
        value=defaults.ebitda_growth,
        step=0.01,
    )
    capex_intensity = st.slider(
        "Capex intensity",
        min_value=0.0,
        max_value=0.50,
        value=defaults.capex_intensity,
        step=0.005,
        format="%.3f",
    )
    tax_rate = st.slider("Tax rate", min_value=0.0, max_value=0.50, value=defaults.tax_rate, step=0.01)

engine_assumptions = EngineAssumptions(
    scenario=scenario,
    entry_multiple=entry_multiple,
    exit_multiple=exit_multiple,
    exit_year=int(exit_year),
    debt_interest_rate=debt_interest_rate,
    debt_repayment_speed=debt_repayment_speed,
    ebitda_growth=ebitda_growth,
    capex_intensity=capex_intensity,
    tax_rate=tax_rate,
)

if not DEFAULT_WORKBOOK.exists():
    st.error("Default CPE workbook was not found.")
    st.caption(f"Expected path: {DEFAULT_WORKBOOK}")
    st.caption("For deployment, add the workbook at this path or re-enable workbook upload later.")
    st.stop()

try:
    snapshot = build_snapshot(DEFAULT_WORKBOOK, scenario=scenario, engine_assumptions=engine_assumptions)
except WorkbookLoadError as exc:
    st.error(str(exc))
    st.stop()

st.session_state["model_snapshot"] = snapshot

st.caption(f"Workbook: {snapshot.workbook_name} | Scenario: {snapshot.scenario}")

st.subheader("Detected Core Sheets")
st.dataframe(snapshot.core_sheets.as_rows(), use_container_width=True, hide_index=True)
if snapshot.core_sheets.missing_roles:
    st.warning("Missing sheet roles: " + ", ".join(snapshot.core_sheets.missing_roles))

st.subheader("Key Outputs")
metric_order = [
    "revenue",
    "ebitda",
    "net_debt",
    "capex",
    "cash_flow",
    "entry_ev",
    "exit_ev",
    "irr",
    "moic",
]

cols = st.columns(3)
for idx, key in enumerate(metric_order):
    metric = snapshot.metrics[key]
    value = "Missing" if metric.is_missing else metric.value
    if isinstance(value, float):
        if metric.unit == "%":
            value = f"{value:.1%}"
        elif metric.unit == "x":
            value = f"{value:.2f}x"
        else:
            value = f"{value:,.1f}"
    with cols[idx % 3]:
        st.metric(metric.display_name, value, help=metric.source.display)
        st.caption(f"Source: {metric.source.display}")
        if metric.missing_reason:
            st.caption(metric.missing_reason)

st.subheader("Financial Trends")
for key in ["revenue", "ebitda", "net_debt", "capex", "cash_flow"]:
    if key in snapshot.tables:
        st.plotly_chart(metric_line_chart(snapshot.tables[key]), use_container_width=True)

st.subheader("Python Engine Outputs")
engine = snapshot.python_engine
if engine is not None:
    output_cols = st.columns(4)
    output_cols[0].metric("Python IRR", "N/A" if engine.irr is None else f"{engine.irr:.1%}")
    output_cols[1].metric("Python MOIC", "N/A" if engine.moic is None else f"{engine.moic:.2f}x")
    output_cols[2].metric("Exit Equity Value", f"{engine.exit_equity_value:,.1f}")
    output_cols[3].metric(
        "Net Debt / EBITDA",
        "N/A" if engine.net_debt_to_ebitda is None else f"{engine.net_debt_to_ebitda:.2f}x",
    )

    debt_rows = [period.model_dump() for period in engine.debt_model.periods]
    st.dataframe(pd.DataFrame(debt_rows), use_container_width=True, hide_index=True)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.plotly_chart(value_creation_bridge_chart(engine.value_creation_bridge), use_container_width=True)
    with chart_cols[1]:
        st.plotly_chart(sensitivity_heatmap(engine.sensitivity), use_container_width=True)
