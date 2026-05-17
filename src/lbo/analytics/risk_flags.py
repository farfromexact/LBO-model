from __future__ import annotations

from lbo.schemas.standard_model import StandardModel


def generate_risk_flags(model: StandardModel) -> list[str]:
    flags = list(model.metadata.warnings)
    if model.metadata.excel_errors:
        flags.append("Excel contains #REF!, #NAME?, #VALUE!, #DIV/0!, or #N/A errors.")
    if not model.returns.sponsor_cash_flows:
        flags.append("Missing sponsor cash flow.")
    if model.returns.irr is None or not model.returns.irr.is_available:
        flags.append("No single base IRR found.")
    if model.returns.moic is None or not model.returns.moic.is_available:
        flags.append("No single base MOIC found.")
    if "net_debt" in model.metrics and model.metrics["net_debt"].sign_convention is None:
        flags.append("Net debt sign convention unclear.")
    if model.valuation.exit_multiple and model.valuation.entry_multiple:
        try:
            entry = float(model.valuation.entry_multiple.value)
            exit_ = float(model.valuation.exit_multiple.value)
            if exit_ - entry > 1.0:
                flags.append("IRR may be materially driven by multiple expansion.")
        except (TypeError, ValueError):
            pass
    if model.financials.capex and model.financials.revenue:
        capex = sorted(model.financials.capex.items())[-1][1].value
        revenue = sorted(model.financials.revenue.items())[-1][1].value
        if isinstance(capex, (int, float)) and isinstance(revenue, (int, float)) and revenue and abs(capex / revenue) > 0.5:
            flags.append("Capex intensity abnormal.")
    return list(dict.fromkeys(flags))
