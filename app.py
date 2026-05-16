from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lbo.charts import debt_paydown_waterfall, operating_trend_chart, sensitivity_heatmap, value_creation_bridge_chart
from lbo.engine import build_snapshot, load_scenario_defaults
from lbo.io.excel_loader import WorkbookLoadError
from lbo.schemas import EngineAssumptions


def default_workbook_path() -> Path | None:
    return next((ROOT / "examples").glob("CPE*20260317.xlsx"), None)


def format_metric(value: object, unit: str | None = None) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        if unit == "%":
            return f"{value:.1%}"
        if unit == "x":
            return f"{value:.2f}x"
        return f"{value:,.1f}"
    return str(value)


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

workbook_path = default_workbook_path()
if workbook_path is None or not workbook_path.exists():
    st.error("Default CPE workbook was not found.")
    st.caption(f"Expected path pattern: {ROOT / 'examples' / 'CPE*20260317.xlsx'}")
    st.stop()

try:
    snapshot = build_snapshot(workbook_path, scenario=scenario, engine_assumptions=engine_assumptions)
except WorkbookLoadError as exc:
    st.error(str(exc))
    st.stop()

st.session_state["model_snapshot"] = snapshot
st.caption(f"Workbook: {snapshot.workbook_name} | Scenario: {snapshot.scenario}")

engine = snapshot.python_engine
if engine is None:
    st.error("Python engine did not return outputs.")
    st.stop()

st.subheader("Deal Snapshot")
cols = st.columns(5)
cols[0].metric("IRR", format_metric(engine.irr, "%"))
cols[1].metric("MOIC", format_metric(engine.moic, "x"))
cols[2].metric("Exit Equity Value", format_metric(engine.exit_equity_value))
cols[3].metric("Exit EV", format_metric(engine.exit_ev))
cols[4].metric("Net Debt / EBITDA", format_metric(engine.net_debt_to_ebitda, "x"))

st.divider()
st.subheader("1. Value Creation Bridge")
st.plotly_chart(value_creation_bridge_chart(engine.value_creation_bridge), use_container_width=True)
st.caption("Core LBO view: entry equity value to exit equity value by EBITDA growth, multiple movement, deleveraging, and distributions.")

st.divider()
st.subheader("2. Debt Paydown Waterfall")
st.plotly_chart(debt_paydown_waterfall(engine.debt_model), use_container_width=True)
st.caption("Shows whether returns are driven by deleveraging or by exit multiple support.")

st.divider()
st.subheader("3. Revenue / EBITDA / FCF Trend")
st.plotly_chart(operating_trend_chart(snapshot.tables), use_container_width=True)
st.caption("Validates the operating story behind the return model.")

st.divider()
st.subheader("4. Sensitivity Heatmap")
st.plotly_chart(sensitivity_heatmap(engine.sensitivity), use_container_width=True)
st.caption("IRR sensitivity across entry and exit multiples.")

with st.expander("Audit: source sheets and extracted Excel values"):
    st.dataframe(snapshot.core_sheets.as_rows(), use_container_width=True, hide_index=True)
    if snapshot.core_sheets.missing_roles:
        st.warning("Missing sheet roles: " + ", ".join(snapshot.core_sheets.missing_roles))

    metric_rows = [
        {
            "Metric": metric.display_name,
            "Excel Value": metric.value,
            "Unit": metric.unit,
            "Source": metric.source.display,
            "Label": metric.source.label,
        }
        for metric in snapshot.metrics.values()
    ]
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)
