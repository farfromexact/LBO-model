from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lbo.charts import metric_line_chart
from lbo.engine import build_snapshot
from lbo.io.excel_loader import WorkbookLoadError


st.set_page_config(page_title="LBO Dashboard", layout="wide")
st.title("LBO Dashboard")

uploaded = st.file_uploader("Upload Excel workbook", type=["xlsx", "xlsm"])
scenario = st.selectbox("Scenario", ["Base", "Optimistic", "Pessimistic"], index=0)

if uploaded is None:
    st.info("Upload an Excel workbook to generate the dashboard.")
    st.stop()

try:
    snapshot = build_snapshot(uploaded, scenario=scenario)
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

