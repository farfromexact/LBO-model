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
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

status_counts = df["Status"].value_counts().to_dict() if not df.empty else {}
st.caption(
    " | ".join(
        f"{status}: {status_counts.get(status, 0)}"
        for status in ["OK", "Warning", "Critical", "Pending"]
    )
)
