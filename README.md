# LBO Model Dashboard

Excel-first Streamlit dashboard for extracting selected LBO / financial model outputs from an existing workbook.

## V1 Scope

- Upload an Excel workbook.
- Auto-detect likely core sheets.
- Extract key outputs with source traceability.
- Show a dashboard for Revenue, EBITDA, Net Debt, Capex, Cash Flow, Entry EV, Exit EV, IRR, and MOIC.
- Show an Excel vs Python reconciliation shell for the future Python calculation engine.

Excel is the source of truth in v1. Python calculations are placeholders until the engine is built out.

## Run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```powershell
pytest
```

