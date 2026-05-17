from __future__ import annotations

from datetime import date

import pyxirr
from pydantic import BaseModel, Field

from lbo.schemas.standard_model import StandardModel


class AdjustmentInputs(BaseModel):
    entry_multiple: float | None = None
    exit_multiple: float | None = None
    ebitda_growth_delta: float = 0.0
    exit_net_debt: float | None = None
    cash_distribution: float = 0.0
    sponsor_ownership: float | None = None


class ValueCreationBridgeResult(BaseModel):
    entry_equity_value: float | None = None
    ebitda_growth: float | None = None
    multiple_expansion: float | None = None
    deleveraging: float | None = None
    dividends: float | None = None
    exit_equity_value: float | None = None


class AdjustedReturnResult(BaseModel):
    entry_ev: float | None = None
    entry_equity_value: float | None = None
    sponsor_equity_invested: float | None = None
    exit_ebitda: float | None = None
    exit_ev: float | None = None
    exit_equity_value: float | None = None
    sponsor_exit_proceeds: float | None = None
    moic: float | None = None
    irr: float | None = None
    cash_flows: list[float] = Field(default_factory=list)
    bridge: ValueCreationBridgeResult = Field(default_factory=ValueCreationBridgeResult)
    warnings: list[str] = Field(default_factory=list)


def build_default_adjustments(model: StandardModel) -> AdjustmentInputs:
    return AdjustmentInputs(
        entry_multiple=_metric_float(model.valuation.entry_multiple),
        exit_multiple=_metric_float(model.valuation.exit_multiple),
        exit_net_debt=_infer_exit_net_debt(model),
        sponsor_ownership=_infer_sponsor_ownership(model),
    )


def run_adjusted_return_model(model: StandardModel, inputs: AdjustmentInputs) -> AdjustedReturnResult:
    warnings: list[str] = []
    entry_ebitda = _metric_float(model.valuation.entry_ebitda) or _earliest_float(model.financials.ebitda)
    exit_ebitda_base = _metric_float(model.valuation.exit_ebitda) or _latest_float(model.financials.ebitda)
    entry_ev_base = _metric_float(model.valuation.entry_ev)
    entry_equity_base = _metric_float(model.valuation.entry_equity_value)
    sponsor_invested_base = _metric_float(model.returns.sponsor_equity_invested)
    entry_net_debt = entry_ev_base - entry_equity_base if entry_ev_base is not None and entry_equity_base is not None else None

    if entry_ebitda is None:
        warnings.append("Missing entry EBITDA; adjusted entry EV cannot be calculated.")
    if exit_ebitda_base is None:
        warnings.append("Missing exit EBITDA; adjusted exit EV cannot be calculated.")
    if inputs.entry_multiple is None:
        warnings.append("Missing entry multiple; using extracted entry EV if available.")
    if inputs.exit_multiple is None:
        warnings.append("Missing exit multiple; adjusted exit EV cannot be calculated.")

    entry_ev = entry_ebitda * inputs.entry_multiple if entry_ebitda is not None and inputs.entry_multiple is not None else entry_ev_base
    entry_equity = entry_ev - entry_net_debt if entry_ev is not None and entry_net_debt is not None else entry_equity_base
    ownership = inputs.sponsor_ownership if inputs.sponsor_ownership is not None else _infer_sponsor_ownership(model)
    if ownership is None:
        warnings.append("Missing sponsor ownership; using extracted sponsor equity invested if available.")
    sponsor_invested = sponsor_invested_base
    if sponsor_invested is None and entry_equity is not None and ownership is not None:
        sponsor_invested = entry_equity * ownership

    exit_ebitda = exit_ebitda_base * (1 + inputs.ebitda_growth_delta) if exit_ebitda_base is not None else None
    exit_ev = exit_ebitda * inputs.exit_multiple if exit_ebitda is not None and inputs.exit_multiple is not None else None
    exit_net_debt = inputs.exit_net_debt
    if exit_net_debt is None:
        warnings.append("Missing exit net debt; adjusted exit equity value cannot be calculated.")
    exit_equity = exit_ev - exit_net_debt if exit_ev is not None and exit_net_debt is not None else None
    sponsor_proceeds = exit_equity * ownership + inputs.cash_distribution if exit_equity is not None and ownership is not None else None

    cash_flows: list[float] = []
    moic = None
    irr = None
    if sponsor_invested is not None and sponsor_invested != 0 and sponsor_proceeds is not None:
        cash_flows = [-abs(sponsor_invested), sponsor_proceeds]
        moic = sponsor_proceeds / abs(sponsor_invested)
        irr = _calculate_irr(model, cash_flows, moic, warnings)
    else:
        warnings.append("Missing sponsor invested/proceeds; adjusted MOIC and IRR not calculated.")

    bridge = _bridge(
        entry_equity_base=entry_equity,
        exit_equity=exit_equity,
        entry_ebitda=entry_ebitda,
        exit_ebitda_base=exit_ebitda_base,
        exit_ebitda=exit_ebitda,
        entry_multiple=inputs.entry_multiple,
        exit_multiple=inputs.exit_multiple,
        entry_net_debt=entry_net_debt,
        exit_net_debt=exit_net_debt,
        dividends=inputs.cash_distribution,
    )
    return AdjustedReturnResult(
        entry_ev=entry_ev,
        entry_equity_value=entry_equity,
        sponsor_equity_invested=sponsor_invested,
        exit_ebitda=exit_ebitda,
        exit_ev=exit_ev,
        exit_equity_value=exit_equity,
        sponsor_exit_proceeds=sponsor_proceeds,
        moic=moic,
        irr=irr,
        cash_flows=cash_flows,
        bridge=bridge,
        warnings=warnings,
    )


def _bridge(
    entry_equity_base: float | None,
    exit_equity: float | None,
    entry_ebitda: float | None,
    exit_ebitda_base: float | None,
    exit_ebitda: float | None,
    entry_multiple: float | None,
    exit_multiple: float | None,
    entry_net_debt: float | None,
    exit_net_debt: float | None,
    dividends: float,
) -> ValueCreationBridgeResult:
    ebitda_growth = None
    multiple_expansion = None
    deleveraging = None
    if entry_ebitda is not None and exit_ebitda is not None and entry_multiple is not None:
        ebitda_growth = (exit_ebitda - entry_ebitda) * entry_multiple
    if exit_ebitda is not None and entry_multiple is not None and exit_multiple is not None:
        multiple_expansion = exit_ebitda * (exit_multiple - entry_multiple)
    if entry_net_debt is not None and exit_net_debt is not None:
        deleveraging = entry_net_debt - exit_net_debt
    return ValueCreationBridgeResult(
        entry_equity_value=entry_equity_base,
        ebitda_growth=ebitda_growth,
        multiple_expansion=multiple_expansion,
        deleveraging=deleveraging,
        dividends=dividends,
        exit_equity_value=exit_equity,
    )


def _calculate_irr(model: StandardModel, cash_flows: list[float], moic: float | None, warnings: list[str]) -> float | None:
    entry_date = _metric_date(model.valuation.entry_date)
    exit_date = _metric_date(model.valuation.exit_date)
    if entry_date is not None and exit_date is not None:
        try:
            return pyxirr.xirr([entry_date, exit_date], cash_flows)
        except Exception as exc:
            warnings.append(f"XIRR failed: {exc}")
            return None
    if moic is not None:
        warnings.append("Entry/exit dates missing; IRR uses a 5-year annualized fallback.")
        return moic ** (1 / 5) - 1
    return None


def _infer_sponsor_ownership(model: StandardModel) -> float | None:
    exit_proceeds = _metric_float(model.returns.sponsor_exit_proceeds)
    exit_equity = _metric_float(model.valuation.exit_equity_value)
    if exit_proceeds is not None and exit_equity not in (None, 0):
        return exit_proceeds / exit_equity
    sponsor_invested = _metric_float(model.returns.sponsor_equity_invested)
    entry_equity = _metric_float(model.valuation.entry_equity_value)
    if sponsor_invested is not None and entry_equity not in (None, 0):
        return sponsor_invested / entry_equity
    return None


def _infer_exit_net_debt(model: StandardModel) -> float | None:
    exit_ev = _metric_float(model.valuation.exit_ev)
    exit_equity = _metric_float(model.valuation.exit_equity_value)
    if exit_ev is not None and exit_equity is not None:
        return exit_ev - exit_equity
    return _latest_float(model.financials.net_debt)


def _metric_float(metric) -> float | None:
    value = getattr(metric, "value", None)
    return float(value) if isinstance(value, (int, float)) else None


def _metric_date(metric) -> date | None:
    value = getattr(metric, "value", None)
    return value if isinstance(value, date) else None


def _latest_float(series) -> float | None:
    if not series:
        return None
    return _metric_float(sorted(series.items())[-1][1])


def _earliest_float(series) -> float | None:
    if not series:
        return None
    return _metric_float(sorted(series.items())[0][1])
