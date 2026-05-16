from __future__ import annotations

from datetime import date

import pyxirr

from lbo.schemas.models import (
    DebtModel,
    DebtPeriod,
    EngineAssumptions,
    FinancialStatementTable,
    MetricValue,
    PythonEngineOutputs,
    SensitivityTable,
    ValueCreationBridge,
)


def run_python_engine(
    metrics: dict[str, MetricValue],
    tables: dict[str, FinancialStatementTable],
    assumptions: EngineAssumptions,
) -> PythonEngineOutputs:
    entry_year = _first_year(tables.get("ebitda"), fallback=2025)
    exit_year = assumptions.exit_year
    holding_period = max(exit_year - entry_year, 1)

    entry_ebitda = _first_numeric(tables.get("ebitda"), fallback=_numeric(metrics["ebitda"].value))
    entry_revenue = _first_numeric(tables.get("revenue"), fallback=_numeric(metrics["revenue"].value))
    excel_net_debt = max(_numeric(metrics["net_debt"].value), 0.0)
    excel_cash_flow = _numeric(metrics["cash_flow"].value)

    entry_ev = entry_ebitda * assumptions.entry_multiple
    initial_debt = min(max(excel_net_debt, 0.0), entry_ev * 0.8)
    sponsor_equity = max(entry_ev - initial_debt, 1.0)

    debt_model = _build_debt_model(
        initial_debt=initial_debt,
        entry_revenue=entry_revenue,
        entry_ebitda=entry_ebitda,
        entry_year=entry_year,
        exit_year=exit_year,
        assumptions=assumptions,
        fallback_cash_flow=excel_cash_flow,
    )
    ending_net_debt = debt_model.periods[-1].ending_debt if debt_model.periods else initial_debt

    exit_ebitda = entry_ebitda * ((1 + assumptions.ebitda_growth) ** holding_period)
    exit_ev = exit_ebitda * assumptions.exit_multiple
    exit_equity_value = max(exit_ev - ending_net_debt, 0.0)
    tax_leakage = max(exit_equity_value - sponsor_equity, 0.0) * assumptions.tax_rate
    after_tax_exit_equity = max(exit_equity_value - tax_leakage, 0.0)
    moic = after_tax_exit_equity / sponsor_equity if sponsor_equity else None
    irr = _annual_irr(entry_year, exit_year, sponsor_equity, after_tax_exit_equity)

    bridge = ValueCreationBridge(
        entry_equity_value=sponsor_equity,
        ebitda_growth=(exit_ebitda - entry_ebitda) * assumptions.entry_multiple,
        multiple_expansion=exit_ebitda * (assumptions.exit_multiple - assumptions.entry_multiple),
        deleveraging=initial_debt - ending_net_debt,
        dividends=0.0,
        tax_leakage=-tax_leakage,
        exit_equity_value=after_tax_exit_equity,
    )

    sensitivity = _build_sensitivity(
        assumptions=assumptions,
        entry_ebitda=entry_ebitda,
        exit_ebitda=exit_ebitda,
        initial_debt=initial_debt,
        ending_net_debt=ending_net_debt,
        entry_year=entry_year,
        sponsor_equity_floor=1.0,
    )

    return PythonEngineOutputs(
        entry_year=entry_year,
        entry_ebitda=entry_ebitda,
        exit_ebitda=exit_ebitda,
        entry_ev=entry_ev,
        exit_ev=exit_ev,
        sponsor_equity=sponsor_equity,
        exit_equity_value=exit_equity_value,
        after_tax_exit_equity=after_tax_exit_equity,
        irr=irr,
        moic=moic,
        ending_net_debt=ending_net_debt,
        net_debt_to_ebitda=ending_net_debt / exit_ebitda if exit_ebitda else None,
        debt_model=debt_model,
        value_creation_bridge=bridge,
        sensitivity=sensitivity,
    )


def _build_debt_model(
    initial_debt: float,
    entry_revenue: float,
    entry_ebitda: float,
    entry_year: int,
    exit_year: int,
    assumptions: EngineAssumptions,
    fallback_cash_flow: float,
) -> DebtModel:
    periods: list[DebtPeriod] = []
    opening_debt = initial_debt
    for year in range(entry_year + 1, exit_year + 1):
        elapsed = year - entry_year
        revenue = entry_revenue * ((1 + assumptions.ebitda_growth) ** elapsed)
        ebitda = entry_ebitda * ((1 + assumptions.ebitda_growth) ** elapsed)
        capex = revenue * assumptions.capex_intensity
        interest = opening_debt * assumptions.debt_interest_rate
        cash_available = max(ebitda * (1 - assumptions.tax_rate) - capex - interest, fallback_cash_flow, 0.0)
        repayment = min(opening_debt, cash_available * assumptions.debt_repayment_speed)
        ending_debt = max(opening_debt - repayment, 0.0)
        periods.append(
            DebtPeriod(
                year=year,
                opening_debt=opening_debt,
                interest=interest,
                cash_available_for_repayment=cash_available,
                repayment=repayment,
                ending_debt=ending_debt,
            )
        )
        opening_debt = ending_debt
    return DebtModel(periods=periods)


def _build_sensitivity(
    assumptions: EngineAssumptions,
    entry_ebitda: float,
    exit_ebitda: float,
    initial_debt: float,
    ending_net_debt: float,
    entry_year: int,
    sponsor_equity_floor: float,
) -> SensitivityTable:
    entry_multiples = [round(assumptions.entry_multiple + offset, 1) for offset in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    exit_multiples = [round(assumptions.exit_multiple + offset, 1) for offset in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    values: list[list[float | None]] = []
    for entry_multiple in entry_multiples:
        row: list[float | None] = []
        entry_ev = entry_ebitda * entry_multiple
        sponsor_equity = max(entry_ev - min(initial_debt, entry_ev * 0.8), sponsor_equity_floor)
        for exit_multiple in exit_multiples:
            exit_equity = max(exit_ebitda * exit_multiple - ending_net_debt, 0.0)
            tax_leakage = max(exit_equity - sponsor_equity, 0.0) * assumptions.tax_rate
            row.append(_annual_irr(entry_year, assumptions.exit_year, sponsor_equity, exit_equity - tax_leakage))
        values.append(row)
    return SensitivityTable(entry_multiples=entry_multiples, exit_multiples=exit_multiples, values=values)


def _annual_irr(entry_year: int, exit_year: int, sponsor_equity: float, exit_equity: float) -> float | None:
    if sponsor_equity <= 0 or exit_equity <= 0:
        return None
    try:
        return float(
            pyxirr.xirr(
                [date(entry_year, 12, 31), date(exit_year, 12, 31)],
                [-sponsor_equity, exit_equity],
            )
        )
    except Exception:
        return None


def _first_year(table: FinancialStatementTable | None, fallback: int) -> int:
    if not table or not table.periods:
        return fallback
    try:
        return int(table.periods[0])
    except ValueError:
        return fallback


def _first_numeric(table: FinancialStatementTable | None, fallback: float) -> float:
    if not table or not table.rows:
        return fallback
    values = next(iter(table.rows.values()))
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return fallback


def _numeric(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0
