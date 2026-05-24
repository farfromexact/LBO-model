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
    TemplateInputAdapter,
    detect_best_adapter,
)
from lbo.charts.standard_model import debt_paydown_waterfall, operating_trend_chart, sensitivity_heatmap, value_creation_bridge_chart  # noqa: E402
from lbo.engine import calculate_memo_metrics, generate_sop_analysis, run_standardized_sensitivity  # noqa: E402
from lbo.io.template_generator import create_standard_template_bytes  # noqa: E402
from lbo.io.workbook_loader import WorkbookLoadError, load_workbook  # noqa: E402


def legacy_adapters():
    return [DragonDetailedLBOAdapter(), ChineseCompactLBOAdapter(), StarbucksProjectSundayAdapter(), GenericLBOAdapter()]


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


def template_download_row(location: str) -> None:
    st.download_button(
        "Download standard Excel template",
        data=create_standard_template_bytes(5),
        file_name="standard_lbo_input_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"download_standard_template_{location}",
    )


st.set_page_config(page_title="LBO Investment Memo", layout="wide")
st.title("LBO Investment Memo")
st.caption("V1 uses a standardized Excel input template. Legacy workbook import is experimental.")

with st.sidebar:
    st.subheader("Standard Template")
    template_download_row("sidebar")
    uploaded = st.file_uploader("Upload completed standard template", type=["xlsx", "xlsm"])
    password = st.text_input("Workbook password, if encrypted", type="password")
    use_legacy = st.toggle("Experimental legacy Excel import", value=False)

if uploaded is None:
    st.subheader("Start Here")
    st.write("Download the standard Excel template, fill in the required deal inputs, then upload it from the sidebar.")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        template_download_row("empty_state")
    with col_b:
        st.info("The template includes Deal Setup, Operating Forecast, Debt & Cash, Return Assumptions, and Qualitative Inputs.")
    st.stop()

try:
    password_map = {uploaded.name: password} if password else {}
    loaded = load_workbook(uploaded.getvalue(), password_map=password_map, source_file=uploaded.name)
except WorkbookLoadError as exc:
    st.error(exc.message)
    st.stop()

if use_legacy:
    adapters = legacy_adapters()
    match = detect_best_adapter(loaded.workbook, adapters)
    adapter = next((candidate for candidate in adapters if candidate.adapter_name == match.adapter_name), GenericLBOAdapter())
    model = adapter.extract(loaded.workbook, source_file=loaded.source_file)
    st.warning("Legacy import is experimental. Use the standard template for production-quality memo output.")
else:
    adapter = TemplateInputAdapter()
    match = adapter.can_handle(loaded.workbook)
    if match.missing_features:
        st.error("Uploaded workbook is not the standard template.")
        st.write("Missing sheets: " + ", ".join(match.missing_features))
        st.stop()
    try:
        model = adapter.extract(loaded.workbook, source_file=loaded.source_file)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

memo = calculate_memo_metrics(model)
sop = generate_sop_analysis(model)
sensitivity = run_standardized_sensitivity(model)
st.session_state["standard_model"] = model
st.session_state["sop_result"] = sop

st.caption(f"Workbook: {loaded.source_file}")
status_cols = st.columns(5)
status_cols[0].metric("Template", model.metadata.detected_template_id)
status_cols[1].metric("Confidence", f"{model.metadata.confidence_score:.0%}")
status_cols[2].metric("Coverage", f"{model.extraction_coverage:.0%}")
status_cols[3].metric("Missing", len(model.missing_fields))
status_cols[4].metric("Warnings", len(model.metadata.warnings))

for warning in model.metadata.warnings:
    st.warning(warning)
if model.missing_fields:
    st.info("Missing fields: " + ", ".join(model.missing_fields))

upload_tab, memo_tab, bridge_tab, sensitivity_tab, risk_tab, audit_tab = st.tabs(
    ["Upload Standard Template", "Core Memo", "Return Bridge", "Sensitivity", "Risk Flags", "Model Audit"]
)

with upload_tab:
    st.subheader("Template Validation")
    template_download_row("upload_tab")
    st.write(f"Adapter: {model.metadata.adapter_name}")
    st.write(f"Project: {model.metadata.project_name or 'Missing'}")
    st.write(f"Currency / Unit: {model.metadata.currency or 'Missing'} / {model.metadata.unit or 'Missing'}")
    st.write(f"Forecast years: {sorted(model.financials.revenue.keys()) if model.financials.revenue else 'Missing'}")

with memo_tab:
    st.subheader("Deal Summary")
    deal_cols = st.columns(5)
    deal_cols[0].metric("Entry EV", format_value(metric_value(model, "entry_ev"), model.metadata.unit))
    deal_cols[1].metric("Exit EV", format_value(metric_value(model, "exit_ev"), model.metadata.unit))
    deal_cols[2].metric("MOIC", format_value(metric_value(model, "moic"), "x"))
    deal_cols[3].metric("IRR", format_value(metric_value(model, "irr"), "%"))
    deal_cols[4].metric("Net Gain", format_value(metric_value(model, "net_gain"), model.metadata.unit))

    st.subheader("Why This Deal")
    st.write(model.qualitative.get("investment_thesis") or "Missing investment thesis.")

    st.subheader("Operating Performance")
    perf_cols = st.columns(4)
    perf_cols[0].metric("Revenue CAGR", format_value(memo.revenue_cagr, "%"))
    perf_cols[1].metric("EBITDA CAGR", format_value(memo.ebitda_cagr, "%"))
    perf_cols[2].metric("Ending EBITDA Margin", format_value(memo.ending_ebitda_margin, "%"))
    perf_cols[3].metric("FCF Conversion", format_value(memo.fcf_conversion, "%"))
    st.plotly_chart(operating_trend_chart(model), use_container_width=True, key="memo_operating_trend")

    st.subheader("Sensitivity Snapshot")
    if sensitivity.matrices:
        st.plotly_chart(sensitivity_heatmap(sensitivity.matrices[0]), use_container_width=True, key="memo_sensitivity_snapshot")
    else:
        st.warning("Sensitivity not available because required inputs are missing.")

    st.subheader("Key Risks")
    st.write(model.qualitative.get("key_risks") or "Missing key risks.")

with bridge_tab:
    st.subheader("Value Creation Bridge")
    st.plotly_chart(value_creation_bridge_chart(memo.value_creation_bridge), use_container_width=True, key="memo_value_creation_bridge")
    st.subheader("Debt Paydown / Deleveraging")
    st.plotly_chart(debt_paydown_waterfall(model), use_container_width=True, key="memo_debt_paydown")

with sensitivity_tab:
    st.subheader("Sensitivity")
    if sensitivity.matrices:
        selected = st.selectbox("Matrix", [matrix.title for matrix in sensitivity.matrices], key="memo_sensitivity_select")
        matrix = next(item for item in sensitivity.matrices if item.title == selected)
        st.plotly_chart(sensitivity_heatmap(matrix), use_container_width=True, key=f"memo_heatmap_{matrix.matrix_id}")
        st.dataframe(pd.DataFrame(matrix.values, index=matrix.row_values, columns=matrix.col_values), use_container_width=True)
    else:
        for warning in sensitivity.warnings:
            st.warning(warning)

with risk_tab:
    st.subheader("Risk Flags")
    for flag in sop.risk_flags or ["No risk flags."]:
        st.write(f"- {flag}")
    st.subheader("Diligence Questions")
    st.write(model.qualitative.get("diligence_questions") or "Missing diligence questions.")
    st.subheader("Management / Market Notes")
    st.write(model.qualitative.get("management_market_notes") or "Missing management / market notes.")
    st.subheader("Exit Rationale")
    st.write(model.qualitative.get("exit_rationale") or "Missing exit rationale.")

with audit_tab:
    st.subheader("Metric Audit")
    rows = [
        {
            "Metric": metric.label,
            "Metric ID": metric.metric_id,
            "Value": metric.value,
            "Period": metric.period,
            "Status": "OK" if metric.is_available else "Missing",
            "Confidence": metric.confidence,
            "Method": metric.extraction_method,
            "Warning": metric.warning,
            "Source Sheet": metric.source_sheet,
            "Source Cell/Range": metric.source_cell or metric.source_range,
        }
        for metric in model.metrics.values()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if model.missing_fields:
        st.subheader("Missing Data")
        st.dataframe(pd.DataFrame({"Missing Field": model.missing_fields}), use_container_width=True, hide_index=True)
