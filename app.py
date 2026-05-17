from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lbo.adapters import (  # noqa: E402
    ChineseCompactLBOAdapter,
    DragonDetailedLBOAdapter,
    GenericLBOAdapter,
    StarbucksProjectSundayAdapter,
    detect_best_adapter,
)
from lbo.charts.standard_model import (  # noqa: E402
    debt_paydown_waterfall,
    operating_trend_chart,
    sensitivity_heatmap,
    value_creation_bridge_chart,
)
from lbo.engine import (  # noqa: E402
    AdjustmentInputs,
    build_default_adjustments,
    generate_sop_analysis,
    run_adjusted_return_model,
    run_standardized_sensitivity,
)
from lbo.io.workbook_loader import WorkbookLoadError, load_workbook  # noqa: E402


def adapters():
    return [
        DragonDetailedLBOAdapter(),
        ChineseCompactLBOAdapter(),
        StarbucksProjectSundayAdapter(),
        GenericLBOAdapter(),
    ]


def format_value(value: object, unit: str | None = None) -> str:
    if value is None:
        return "Missing"
    if isinstance(value, (int, float)):
        if unit == "%":
            return f"{float(value):.1%}"
        if unit == "x":
            return f"{float(value):.2f}x"
        return f"{float(value):,.1f}"
    return str(value)


def metric_value(model, metric_id: str):
    metric = model.metrics.get(metric_id)
    return None if metric is None else metric.value


def metric_unit(model, metric_id: str):
    metric = model.metrics.get(metric_id)
    return None if metric is None else metric.unit


def slider_number(label: str, value: float | None, min_value: float, max_value: float, step: float, help_text: str):
    if value is None:
        st.caption(f"{label}: missing from StandardModel")
        return None
    return st.slider(label, min_value=min_value, max_value=max_value, value=float(value), step=step, help=help_text)


st.set_page_config(page_title="LBO / Investment Model Analyzer", layout="wide")
st.title("LBO / Investment Model Analyzer")

with st.sidebar:
    st.subheader("Workbook")
    uploaded = st.file_uploader("Upload Excel workbook", type=["xlsx", "xlsm"])
    password = st.text_input("Workbook password, if encrypted", type="password")

if uploaded is not None:
    st.session_state["workbook_bytes"] = uploaded.getvalue()
    st.session_state["workbook_name"] = uploaded.name
    if password:
        st.session_state["workbook_password"] = password

workbook_bytes = st.session_state.get("workbook_bytes")
workbook_name = st.session_state.get("workbook_name")
if workbook_bytes is None:
    st.info("Upload an Excel workbook to analyze. The app converts it into StandardModel before dashboard, SOP, reconciliation, or sensitivity outputs.")
    st.stop()

try:
    password_map = {workbook_name or "uploaded": st.session_state.get("workbook_password")} if st.session_state.get("workbook_password") else {}
    loaded = load_workbook(workbook_bytes, password_map=password_map, source_file=workbook_name)
except WorkbookLoadError as exc:
    st.error(exc.message)
    st.stop()

adapter_list = adapters()
match = detect_best_adapter(loaded.workbook, adapter_list)
adapter = next((candidate for candidate in adapter_list if candidate.adapter_name == match.adapter_name), GenericLBOAdapter())
model = adapter.extract(loaded.workbook, source_file=loaded.source_file)
sop = generate_sop_analysis(model)
sensitivity = run_standardized_sensitivity(model)
st.session_state["standard_model"] = model
st.session_state["sop_result"] = sop

default_adjustments = build_default_adjustments(model)
with st.sidebar:
    st.subheader("Scenario Adjustments")
    entry_multiple = slider_number("Entry EV / EBITDA", default_adjustments.entry_multiple, 0.0, 25.0, 0.1, "Uses extracted entry EBITDA and implied entry net debt.")
    exit_multiple = slider_number("Exit EV / EBITDA", default_adjustments.exit_multiple, 0.0, 30.0, 0.1, "Uses extracted exit EBITDA as the base.")
    ebitda_growth_delta = st.slider("Exit EBITDA adjustment", -0.50, 0.50, 0.0, 0.01, help="Applied to extracted exit EBITDA.")
    exit_net_debt = slider_number("Exit net debt", default_adjustments.exit_net_debt, -5000.0, 10000.0, 10.0, "Positive means net debt; negative means net cash.")
    sponsor_ownership = slider_number("Sponsor ownership", default_adjustments.sponsor_ownership, 0.0, 1.0, 0.01, "Inferred from sponsor proceeds / exit equity or sponsor invested / entry equity.")
    cash_distribution = st.number_input("Dividends / cash distribution", value=0.0, step=10.0)

adjusted = run_adjusted_return_model(
    model,
    AdjustmentInputs(
        entry_multiple=entry_multiple,
        exit_multiple=exit_multiple,
        ebitda_growth_delta=ebitda_growth_delta,
        exit_net_debt=exit_net_debt,
        cash_distribution=cash_distribution,
        sponsor_ownership=sponsor_ownership,
    ),
)

st.caption(f"Workbook: {loaded.source_file}")
status_cols = st.columns(5)
status_cols[0].metric("Template", model.metadata.detected_template_id)
status_cols[1].metric("Adapter Confidence", f"{model.metadata.confidence_score:.0%}")
status_cols[2].metric("Coverage", f"{model.extraction_coverage:.0%}")
status_cols[3].metric("Missing", len(model.missing_fields))
status_cols[4].metric("Excel Errors", len(model.metadata.excel_errors))

if model.metadata.warnings:
    for warning in model.metadata.warnings:
        st.warning(warning)
if model.missing_fields:
    st.info("Missing fields: " + ", ".join(model.missing_fields))

overview_tab, adjustment_tab, chart_tab, sensitivity_tab, sop_tab, audit_tab = st.tabs(
    ["Overview", "Adjustments", "Charts", "Sensitivity", "SOP", "Audit"]
)

with overview_tab:
    st.subheader("Extracted Base Case")
    kpis = st.columns(6)
    for col, label, metric_id in [
        (kpis[0], "Revenue", "revenue"),
        (kpis[1], "EBITDA", "ebitda"),
        (kpis[2], "Net Debt", "net_debt"),
        (kpis[3], "Entry EV", "entry_ev"),
        (kpis[4], "MOIC", "moic"),
        (kpis[5], "IRR", "irr"),
    ]:
        col.metric(label, format_value(metric_value(model, metric_id), metric_unit(model, metric_id)))

    st.subheader("Adjusted Case")
    adjusted_cols = st.columns(5)
    adjusted_cols[0].metric("Adj. Entry EV", format_value(adjusted.entry_ev, model.metadata.unit))
    adjusted_cols[1].metric("Adj. Exit EV", format_value(adjusted.exit_ev, model.metadata.unit))
    adjusted_cols[2].metric("Adj. Exit Equity", format_value(adjusted.exit_equity_value, model.metadata.unit))
    adjusted_cols[3].metric("Adj. MOIC", format_value(adjusted.moic, "x"))
    adjusted_cols[4].metric("Adj. IRR", format_value(adjusted.irr, "%"))

with adjustment_tab:
    st.subheader("Adjustment Trace")
    if adjusted.warnings:
        for warning in adjusted.warnings:
            st.warning(warning)
    st.dataframe(
        pd.DataFrame(
            [
                {"Item": "Entry EV", "Value": adjusted.entry_ev},
                {"Item": "Entry Equity Value", "Value": adjusted.entry_equity_value},
                {"Item": "Sponsor Equity Invested", "Value": adjusted.sponsor_equity_invested},
                {"Item": "Exit EBITDA", "Value": adjusted.exit_ebitda},
                {"Item": "Exit EV", "Value": adjusted.exit_ev},
                {"Item": "Exit Equity Value", "Value": adjusted.exit_equity_value},
                {"Item": "Sponsor Exit Proceeds", "Value": adjusted.sponsor_exit_proceeds},
                {"Item": "MOIC", "Value": adjusted.moic},
                {"Item": "IRR", "Value": adjusted.irr},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.plotly_chart(value_creation_bridge_chart(adjusted.bridge), use_container_width=True, key="adjustment_bridge_chart")
    st.caption("Cash flow used for adjusted return: " + ", ".join(format_value(value) for value in adjusted.cash_flows) if adjusted.cash_flows else "Adjusted cash flow is unavailable.")

with chart_tab:
    st.plotly_chart(operating_trend_chart(model), use_container_width=True, key="charts_operating_trend")
    st.plotly_chart(debt_paydown_waterfall(model), use_container_width=True, key="charts_debt_waterfall")
    st.plotly_chart(value_creation_bridge_chart(adjusted.bridge), use_container_width=True, key="charts_bridge_chart")

with sensitivity_tab:
    if sensitivity.matrices:
        selected_title = st.selectbox("Sensitivity matrix", [matrix.title for matrix in sensitivity.matrices], key="sensitivity_matrix_select")
        matrix = next(item for item in sensitivity.matrices if item.title == selected_title)
        st.plotly_chart(sensitivity_heatmap(matrix), use_container_width=True, key=f"sensitivity_heatmap_{matrix.matrix_id}")
        st.dataframe(
            pd.DataFrame(matrix.values, index=matrix.row_values, columns=matrix.col_values),
            use_container_width=True,
        )
    elif sensitivity.warnings:
        for warning in sensitivity.warnings:
            st.warning(warning)

with sop_tab:
    section_tabs = st.tabs(
        [
            "Deal Summary",
            "Data Quality",
            "Key Assumptions",
            "Operating",
            "Returns",
            "Value Creation",
            "Debt",
            "Risk Flags",
        ]
    )
    sections = [
        sop.deal_summary,
        sop.data_quality,
        sop.key_assumptions,
        sop.operating_performance,
        sop.return_analysis,
        sop.value_creation_bridge,
        sop.debt_and_deleveraging,
        sop.risk_flags,
    ]
    for tab, lines in zip(section_tabs, sections):
        with tab:
            for line in lines or ["No findings."]:
                st.write(f"- {line}")

with audit_tab:
    st.subheader("Metric Lineage")
    rows = [
        {
            "Metric": metric.label,
            "Metric ID": metric.metric_id,
            "Value": metric.value,
            "Period": metric.period,
            "Unit": metric.unit,
            "Confidence": metric.confidence,
            "Method": metric.extraction_method,
            "Warning": metric.warning,
            "Source Sheet": metric.source_sheet,
            "Source Cell/Range": metric.source_cell or metric.source_range,
        }
        for metric in model.metrics.values()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if model.metadata.excel_errors:
        st.subheader("Excel Errors")
        st.dataframe(pd.DataFrame({"Error": model.metadata.excel_errors[:200]}), use_container_width=True, hide_index=True)
