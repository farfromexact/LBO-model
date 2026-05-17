from __future__ import annotations

from pydantic import BaseModel, Field

from lbo.schemas.standard_model import SensitivityMatrix, StandardModel


class SensitivityCase(BaseModel):
    case_name: str
    exit_multiple: float | None = None
    ebitda_cagr: float | None = None
    implied_exit_ev: float | None = None
    implied_moic: float | None = None
    warning: str | None = None


class SensitivityResult(BaseModel):
    cases: list[SensitivityCase] = Field(default_factory=list)
    matrices: list[SensitivityMatrix] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def run_standardized_sensitivity(model: StandardModel) -> SensitivityResult:
    if model.sensitivities:
        return SensitivityResult(matrices=model.sensitivities)

    entry_multiple = _float(model.valuation.entry_multiple.value if model.valuation.entry_multiple else None)
    ebitda = _latest_float(model.financials.ebitda)
    if entry_multiple is None and ebitda:
        entry_ev = _float(model.valuation.entry_ev.value if model.valuation.entry_ev else None)
        entry_multiple = entry_ev / ebitda if entry_ev else None
    sponsor_equity = _float(model.returns.sponsor_equity_invested.value if model.returns.sponsor_equity_invested else None)
    if entry_multiple is None or ebitda is None or sponsor_equity in (None, 0):
        return SensitivityResult(warnings=["Missing base inputs; generated sensitivity not calculated."])

    row_values = [-0.05, 0.0, 0.05]
    col_values = [max(entry_multiple - 1.0, 0.0), entry_multiple, entry_multiple + 1.0]
    values: list[list[float | None]] = []
    cases: list[SensitivityCase] = []
    for cagr in row_values:
        row = []
        for exit_multiple in col_values:
            exit_ev = ebitda * ((1 + cagr) ** 5) * exit_multiple
            moic = exit_ev / abs(sponsor_equity)
            row.append(moic)
            cases.append(
                SensitivityCase(
                    case_name=f"{exit_multiple:.1f}x / {cagr:.0%} EBITDA CAGR",
                    exit_multiple=exit_multiple,
                    ebitda_cagr=cagr,
                    implied_exit_ev=exit_ev,
                    implied_moic=moic,
                )
            )
        values.append(row)
    matrix = SensitivityMatrix(
        matrix_id="generated_exit_multiple_ebitda_cagr",
        title="Exit Multiple x EBITDA CAGR",
        row_axis_name="EBITDA CAGR",
        col_axis_name="Exit EV/EBITDA Multiple",
        row_values=row_values,
        col_values=col_values,
        values=values,
        metric="MOIC",
        source_sheet="Python Engine",
        source_range="generated",
        confidence="low",
        extraction_method="python_calculated",
    )
    return SensitivityResult(cases=cases, matrices=[matrix])


def _latest_float(series) -> float | None:
    if not series:
        return None
    metric = sorted(series.items())[-1][1]
    return _float(metric.value)


def _float(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None
