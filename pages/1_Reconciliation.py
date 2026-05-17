from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


st.set_page_config(page_title="StandardModel Audit", layout="wide")
st.title("StandardModel Audit")

standard_model = st.session_state.get("standard_model")
sop_result = st.session_state.get("sop_result")
if standard_model is None:
    st.info("Upload and analyze a workbook on the main page first.")
    st.stop()

st.subheader("Extraction Summary")
cols = st.columns(4)
cols[0].metric("Coverage", f"{standard_model.metadata.extraction_coverage:.0%}")
cols[1].metric("Extracted", f"{standard_model.extracted_metric_count}/{standard_model.required_metric_count}")
cols[2].metric("Missing", len(standard_model.missing_fields))
cols[3].metric("Warnings", len(standard_model.warnings))

st.subheader("Standard Metrics")
rows = [
    {
        "Metric": metric.display_name,
        "Metric ID": metric.metric_id,
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
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.subheader("SOP Model Audit")
if sop_result is None:
    st.info("SOP result was not found in session state.")
else:
    for line in sop_result.model_audit:
        st.write(f"- {line}")
