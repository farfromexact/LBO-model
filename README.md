# LBO Model Dashboard

Excel-first Streamlit dashboard for extracting selected LBO / financial model outputs from the default CPE workbook.

## V1 Scope

- Load the default CPE workbook from `examples/CPE 龙岛竹项目_财务模型_20260317.xlsx`.
- Auto-detect likely core sheets.
- Extract key outputs with source traceability.
- Show a dashboard for Revenue, EBITDA, Net Debt, Capex, Cash Flow, Entry EV, Exit EV, IRR, and MOIC.
- Show an Excel vs Python reconciliation shell for the future Python calculation engine.

Excel is the source of truth for extracted values. The Python engine computes an MVP return model from selected user-editable assumptions.

The upload workflow is intentionally disabled for now and can be reintroduced later.

## Run

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```powershell
pytest
```
