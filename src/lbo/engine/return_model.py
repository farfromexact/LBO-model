from __future__ import annotations

from datetime import datetime
from typing import Any

import pyxirr

from lbo.io.excel_loader import ExcelLoader
from lbo.schemas.models import ReturnBridge, SponsorCashFlow


def build_excel_return_bridge(loader: ExcelLoader, return_sheet: str) -> ReturnBridge:
    cash_flows = _sponsor_cash_flows(loader, return_sheet)
    sponsor_equity_invested = abs(_number(loader.read_cell(return_sheet, "L101")))
    sponsor_proceeds = sum(cash_flow.amount for cash_flow in cash_flows if cash_flow.amount > 0)
    dividends = sum(_number(loader.read_cell(return_sheet, cell)) for cell in ["M99", "N99", "O99", "P99", "Q99", "R99"])
    moic = sponsor_proceeds / sponsor_equity_invested if sponsor_equity_invested else None

    return ReturnBridge(
        entry_ev=_number(loader.read_cell(return_sheet, "G19")),
        entry_net_debt=_number(loader.read_cell(return_sheet, "G22")),
        transaction_fees=0.0,
        rollover_or_management_equity=0.0,
        entry_equity_value=_number(loader.read_cell(return_sheet, "G24")),
        sponsor_equity_invested=sponsor_equity_invested,
        exit_ev=_number(loader.read_cell(return_sheet, "R89")),
        exit_net_debt=_number(loader.read_cell(return_sheet, "R90")),
        exit_equity_value=_number(loader.read_cell(return_sheet, "R93")),
        dividends=dividends,
        sponsor_proceeds=sponsor_proceeds,
        moic=moic,
        irr=_xirr(cash_flows),
        sponsor_cash_flows=cash_flows,
        missing_items=[],
    )


def _sponsor_cash_flows(loader: ExcelLoader, sheet: str) -> list[SponsorCashFlow]:
    amounts = loader.read_flat_range(sheet, "L101:R101")
    dates = loader.read_flat_range(sheet, "L86:R86")
    return [
        SponsorCashFlow(date=_date(value_date), amount=_number(amount))
        for value_date, amount in zip(dates, amounts)
    ]


def _xirr(cash_flows: list[SponsorCashFlow]) -> float | None:
    try:
        return float(pyxirr.xirr([cash_flow.date for cash_flow in cash_flows], [cash_flow.amount for cash_flow in cash_flows]))
    except Exception:
        return None


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _date(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date()
    return value

