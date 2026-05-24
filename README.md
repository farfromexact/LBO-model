# LBO Investment Memo

Streamlit app for generating a standardized LBO / investment memo from a user-completed Excel input template.

## V1 Scope

V1 uses a standard Excel template as the source of truth. It does not try to reliably parse arbitrary third-party LBO workbooks.

The app can:

- generate and download a standard input template;
- upload and validate the completed template;
- convert validated inputs into `StandardModel`;
- calculate return summary, value creation bridge, debt paydown, and sensitivity tables;
- show qualitative investment thesis, risks, diligence questions, and exit rationale supplied by the user;
- display missing fields and audit warnings clearly.

Legacy Dragon / Spark / Project Sunday adapters are retained as experimental import paths only.

## Standard Template Sheets

- `Deal Setup`
- `Operating Forecast`
- `Debt & Cash`
- `Return Assumptions`
- `Qualitative Inputs`

Forecast periods support 3-7 years. Missing numeric fields are treated as missing, not zero.

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Test

```powershell
python -m pytest
```
