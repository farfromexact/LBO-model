from __future__ import annotations

from lbo.schemas.standard_model import ReturnSummary, StandardModel


def can_calculate_returns(model: StandardModel) -> bool:
    return bool(model.returns.sponsor_cash_flows and model.returns.sponsor_equity_invested and model.returns.sponsor_exit_proceeds)


def get_return_summary(model: StandardModel) -> ReturnSummary:
    return model.returns
