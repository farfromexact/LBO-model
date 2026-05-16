from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lbo.analytics import reconciliation_rows


st.set_page_config(page_title="Excel vs Python Reconciliation", layout="wide")
st.title("Excel vs Python Reconciliation")

snapshot = st.session_state.get("model_snapshot")
if snapshot is None:
    st.info("Upload a workbook on the dashboard page first.")
    st.stop()

rows = reconciliation_rows(snapshot)
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.caption("Python values are placeholders in v1. The calculation engine will populate them in later phases.")

