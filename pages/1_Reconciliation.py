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

model = st.session_state.get("standard_model")
sop = st.session_state.get("sop_result")
if model is None:
    st.info("Upload and analyze a workbook on the main page first.")
    st.stop()

cols = st.columns(5)
cols[0].metric("Template", model.metadata.detected_template_id)
cols[1].metric("Confidence", f"{model.metadata.confidence_score:.0%}")
cols[2].metric("Coverage", f"{model.extraction_coverage:.0%}")
cols[3].metric("Missing", len(model.missing_fields))
cols[4].metric("Excel Errors", len(model.metadata.excel_errors))

st.subheader("Metric Lineage")
rows = [
    {
        "Metric": metric.label,
        "Metric ID": metric.metric_id,
        "Period": metric.period,
        "Value": metric.value,
        "Unit": metric.unit,
        "Scale": metric.scale,
        "Sign Convention": metric.sign_convention,
        "Confidence": metric.confidence,
        "Method": metric.extraction_method,
        "Warning": metric.warning,
        "Source Sheet": metric.source_sheet,
        "Source Cell": metric.source_cell,
        "Source Range": metric.source_range,
    }
    for metric in model.metrics.values()
]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.subheader("Sensitivity Matrices")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Matrix": matrix.title,
                "Metric": matrix.metric,
                "Rows": len(matrix.row_values),
                "Columns": len(matrix.col_values),
                "Source": f"{matrix.source_sheet}!{matrix.source_range}",
                "Confidence": matrix.confidence,
                "Method": matrix.extraction_method,
            }
            for matrix in model.sensitivities
        ]
    ),
    use_container_width=True,
    hide_index=True,
)

st.subheader("SOP Model Audit")
if sop is None:
    st.info("SOP result was not found in session state.")
else:
    for line in sop.model_audit:
        st.write(f"- {line}")

if model.metadata.excel_errors:
    st.subheader("Excel Errors")
    for error in model.metadata.excel_errors[:100]:
        st.write(f"- {error}")
