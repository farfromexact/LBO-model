from __future__ import annotations

from pydantic import BaseModel, Field

from lbo.engine.adjustment_engine import ValueCreationBridgeResult
from lbo.schemas.standard_model import SensitivityMatrix, StandardModel


class MemoMetrics(BaseModel):
    revenue_cagr: float | None = None
    ebitda_cagr: float | None = None
    ending_ebitda_margin: float | None = None
    fcf_conversion: float | None = None
    entry_multiple: float | None = None
    exit_multiple: float | None = None
    moic: float | None = None
    irr: float | None = None
    value_creation_bridge: ValueCreationBridgeResult = Field(default_factory=ValueCreationBridgeResult)
    warnings: list[str] = Field(default_factory=list)


def calculate_memo_metrics(model: StandardModel) -> MemoMetrics:
    revenue_cagr = _cagr(_first(model.financials.revenue), _last(model.financials.revenue), _period_count(model.financials.revenue))
    ebitda_cagr = _cagr(_first(model.financials.ebitda), _last(model.financials.ebitda), _period_count(model.financials.ebitda))
    ending_margin = _safe_div(_last(model.financials.ebitda), _last(model.financials.revenue))
    fcf_conversion = _safe_div(_last(model.financials.fcf), _last(model.financials.ebitda))
    bridge = _value_creation_bridge(model)
    return MemoMetrics(
        revenue_cagr=revenue_cagr,
        ebitda_cagr=ebitda_cagr,
        ending_ebitda_margin=ending_margin,
        fcf_conversion=fcf_conversion,
        entry_multiple=_metric_float(model.valuation.entry_multiple),
        exit_multiple=_metric_float(model.valuation.exit_multiple),
        moic=_metric_float(model.returns.moic),
        irr=_metric_float(model.returns.irr),
        value_creation_bridge=bridge,
        warnings=list(model.metadata.warnings),
    )


def generate_template_sensitivities(model: StandardModel) -> list[SensitivityMatrix]:
    exit_multiple = _metric_float(model.valuation.exit_multiple) or 10.0
    ebitda = _metric_float(model.valuation.exit_ebitda) or _last(model.financials.ebitda)
    sponsor_equity = abs(_metric_float(model.returns.sponsor_equity_invested) or 0.0)
    ownership = _safe_div(_metric_float(model.returns.sponsor_exit_proceeds), _metric_float(model.valuation.exit_equity_value)) or 1.0
    exit_net_debt = _safe_sub(_metric_float(model.valuation.exit_ev), _metric_float(model.valuation.exit_equity_value)) or 0.0
    if ebitda is None or sponsor_equity == 0:
        return []

    return [
        _matrix(
            "exit_multiple_ebitda_cagr",
            "Exit Multiple x EBITDA CAGR",
            "EBITDA CAGR",
            "Exit Multiple",
            [-0.05, 0.0, 0.05],
            [exit_multiple - 1.0, exit_multiple, exit_multiple + 1.0],
            lambda cagr, multiple: _moic_from_exit(ebitda * (1 + cagr), multiple, exit_net_debt, ownership, sponsor_equity),
        ),
        _matrix(
            "exit_multiple_exit_net_debt",
            "Exit Multiple x Exit Net Debt",
            "Exit Net Debt",
            "Exit Multiple",
            [exit_net_debt - 100.0, exit_net_debt, exit_net_debt + 100.0],
            [exit_multiple - 1.0, exit_multiple, exit_multiple + 1.0],
            lambda debt, multiple: _moic_from_exit(ebitda, multiple, debt, ownership, sponsor_equity),
        ),
        _matrix(
            "revenue_cagr_ebitda_margin",
            "Revenue CAGR x EBITDA Margin",
            "Revenue CAGR",
            "EBITDA Margin",
            [-0.05, 0.0, 0.05],
            [0.15, 0.20, 0.25],
            lambda revenue_growth, margin: _moic_from_exit((_last(model.financials.revenue) or 0.0) * (1 + revenue_growth) * margin, exit_multiple, exit_net_debt, ownership, sponsor_equity),
        ),
        _matrix(
            "sponsor_ownership_exit_multiple",
            "Sponsor Ownership x Exit Multiple",
            "Sponsor Ownership",
            "Exit Multiple",
            [max(ownership - 0.10, 0.0), ownership, min(ownership + 0.10, 1.0)],
            [exit_multiple - 1.0, exit_multiple, exit_multiple + 1.0],
            lambda own, multiple: _moic_from_exit(ebitda, multiple, exit_net_debt, own, sponsor_equity),
        ),
    ]


def _matrix(matrix_id, title, row_name, col_name, row_values, col_values, calc) -> SensitivityMatrix:
    values = [[calc(row, col) for col in col_values] for row in row_values]
    return SensitivityMatrix(
        matrix_id=matrix_id,
        title=title,
        row_axis_name=row_name,
        col_axis_name=col_name,
        row_values=row_values,
        col_values=col_values,
        values=values,
        metric="MOIC",
        source_sheet="Python Engine",
        source_range="generated",
        confidence="medium",
        extraction_method="python_calculated",
    )


def _value_creation_bridge(model: StandardModel) -> ValueCreationBridgeResult:
    entry_equity = _metric_float(model.valuation.entry_equity_value)
    exit_equity = _metric_float(model.valuation.exit_equity_value)
    entry_ebitda = _metric_float(model.valuation.entry_ebitda)
    exit_ebitda = _metric_float(model.valuation.exit_ebitda)
    entry_multiple = _metric_float(model.valuation.entry_multiple)
    exit_multiple = _metric_float(model.valuation.exit_multiple)
    entry_net_debt = _safe_sub(_metric_float(model.valuation.entry_ev), entry_equity)
    exit_net_debt = _safe_sub(_metric_float(model.valuation.exit_ev), exit_equity)
    dividends = 0.0
    ebitda_growth = None if None in (entry_ebitda, exit_ebitda, entry_multiple) else (exit_ebitda - entry_ebitda) * entry_multiple
    multiple_expansion = None if None in (exit_ebitda, entry_multiple, exit_multiple) else exit_ebitda * (exit_multiple - entry_multiple)
    deleveraging = None if None in (entry_net_debt, exit_net_debt) else entry_net_debt - exit_net_debt
    return ValueCreationBridgeResult(
        entry_equity_value=entry_equity,
        ebitda_growth=ebitda_growth,
        multiple_expansion=multiple_expansion,
        deleveraging=deleveraging,
        dividends=dividends,
        exit_equity_value=exit_equity,
    )


def _moic_from_exit(ebitda: float, multiple: float, net_debt: float, ownership: float, sponsor_equity: float) -> float | None:
    if sponsor_equity == 0:
        return None
    return ((ebitda * multiple - net_debt) * ownership) / sponsor_equity


def _metric_float(metric) -> float | None:
    value = getattr(metric, "value", None)
    return float(value) if isinstance(value, (int, float)) else None


def _first(series) -> float | None:
    return _metric_float(sorted(series.items())[0][1]) if series else None


def _last(series) -> float | None:
    return _metric_float(sorted(series.items())[-1][1]) if series else None


def _period_count(series) -> int:
    return max(len(series) - 1, 0)


def _cagr(start: float | None, end: float | None, periods: int) -> float | None:
    if start in (None, 0) or end is None or periods <= 0:
        return None
    return (end / start) ** (1 / periods) - 1


def _safe_div(a, b):
    return None if a is None or b in (None, 0) else a / b


def _safe_sub(a, b):
    return None if a is None or b is None else a - b
