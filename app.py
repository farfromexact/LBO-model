from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lbo.adapters import GenericExcelAdapter, detect_best_adapter
from lbo.engine import generate_sop_analysis, run_standardized_sensitivity


def format_value(value: object, unit: str | None = None) -> str:
    if value is None:
        return "Missing"
    if isinstance(value, float):
        if unit == "%":
            return f"{value:.1%}"
        if unit == "x":
            return f"{value:.2f}x"
        return f"{value:,.1f}"
    return str(value)


st.set_page_config(page_title="LBO / Investment Model Analyzer", layout="wide")
st.title("LBO / Investment Model Analyzer")

uploaded = st.file_uploader("Upload Excel workbook", type=["xlsx", "xlsm"])
if uploaded is not None:
    st.session_state["workbook_bytes"] = uploaded.getvalue()
    st.session_state["workbook_name"] = uploaded.name

workbook_bytes = st.session_state.get("workbook_bytes")
workbook_name = st.session_state.get("workbook_name")

if workbook_bytes is None:
    st.info("Upload an Excel workbook to analyze. The app will convert it into a StandardModel before any dashboard or SOP output is generated.")
    st.stop()

st.caption(f"Workbook: {workbook_name}")
adapters = [GenericExcelAdapter()]
match = detect_best_adapter(workbook_bytes, adapters)

st.subheader("Workbook Adapter")
adapter_cols = st.columns(3)
adapter_cols[0].metric("Detected Template", match.detected_template)
adapter_cols[1].metric("Adapter", match.adapter_name)
adapter_cols[2].metric("Confidence", f"{match.confidence:.0%}")
if not match.can_handle:
    st.error("No adapter can confidently handle this workbook.")
    st.write(match.warnings)
    st.stop()

adapter = next(adapter for adapter in adapters if adapter.adapter_name == match.adapter_name)
standard_model = adapter.extract(workbook_bytes)
sop_result = generate_sop_analysis(standard_model)
sensitivity = run_standardized_sensitivity(standard_model)

st.session_state["standard_model"] = standard_model
st.session_state["sop_result"] = sop_result

st.subheader("Extraction Coverage")
coverage_cols = st.columns(4)
coverage_cols[0].metric("Coverage", f"{standard_model.metadata.extraction_coverage:.0%}")
coverage_cols[1].metric("Extracted Metrics", f"{standard_model.extracted_metric_count}/{standard_model.required_metric_count}")
coverage_cols[2].metric("Missing Fields", len(standard_model.missing_fields))
coverage_cols[3].metric("Warnings", len(standard_model.warnings))

if standard_model.missing_fields:
    st.warning("Missing fields: " + ", ".join(standard_model.missing_fields))
if standard_model.warnings:
    for warning in standard_model.warnings:
        st.warning(warning)

st.subheader("SOP Output")
section_tabs = st.tabs(
    [
        "Deal Summary",
        "Data Quality",
        "Key Assumptions",
        "Operating Performance",
        "Return Analysis",
        "Value Creation",
        "Risk Flags",
        "Model Audit",
    ]
)

sections = [
    sop_result.deal_summary,
    sop_result.data_quality,
    sop_result.key_assumptions,
    sop_result.operating_performance,
    sop_result.return_analysis,
    sop_result.value_creation_bridge,
    sop_result.risk_flags,
    sop_result.model_audit,
]
for tab, lines in zip(section_tabs, sections):
    with tab:
        if lines:
            for line in lines:
                st.write(f"- {line}")
        else:
            st.write("No findings.")

st.subheader("Sensitivity Results")
if sensitivity.warnings:
    for warning in sensitivity.warnings:
        st.warning(warning)
else:
    st.dataframe(pd.DataFrame([case.model_dump() for case in sensitivity.cases]), use_container_width=True, hide_index=True)

st.subheader("Missing Fields and Warnings")
audit_rows = [
    {
        "Metric": metric.display_name,
        "Value": metric.value,
        "Period": metric.period,
        "Unit": metric.unit,
        "Confidence": metric.confidence,
        "Missing Reason": metric.missing_reason,
        "Source Sheet": metric.source_sheet,
        "Source Cell": metric.source_cell,
    }
    for metric in standard_model.metrics.values()
]
st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
