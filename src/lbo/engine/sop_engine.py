from __future__ import annotations

from pydantic import BaseModel, Field

from lbo.engine.sensitivity_engine import SensitivityResult, run_standardized_sensitivity
from lbo.schemas.standard_model import StandardModel


class SOPAnalysisResult(BaseModel):
    deal_summary: list[str] = Field(default_factory=list)
    data_quality: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    operating_performance: list[str] = Field(default_factory=list)
    return_analysis: list[str] = Field(default_factory=list)
    value_creation_bridge: list[str] = Field(default_factory=list)
    sensitivity_results: SensitivityResult
    risk_flags: list[str] = Field(default_factory=list)
    model_audit: list[str] = Field(default_factory=list)


def generate_sop_analysis(model: StandardModel) -> SOPAnalysisResult:
    sensitivity = run_standardized_sensitivity(model)
    risk_flags = list(model.warnings)
    risk_flags.extend(f"Missing field: {field}" for field in model.missing_fields)

    return SOPAnalysisResult(
        deal_summary=[
            _line("Entry EV", model.valuation.entry_ev.value, model.valuation.entry_ev.unit),
            _line("Exit EV", model.valuation.exit_ev.value, model.valuation.exit_ev.unit),
            _line("MOIC", model.returns.moic.value, "x"),
            _line("IRR", model.returns.irr.value, "%"),
        ],
        data_quality=[
            f"Adapter: {model.metadata.adapter_name}",
            f"Template confidence: {model.metadata.adapter_confidence:.0%}",
            f"Extraction coverage: {model.metadata.extraction_coverage:.0%}",
            f"Missing fields: {len(model.missing_fields)}",
        ],
        key_assumptions=[
            _source_line("Revenue", model.metrics.get("revenue")),
            _source_line("EBITDA", model.metrics.get("ebitda")),
            _source_line("Net Debt", model.metrics.get("net_debt")),
            _source_line("Cash Flow", model.metrics.get("cash_flow")),
        ],
        operating_performance=[
            _line("Revenue", _value(model.metrics.get("revenue")), _unit(model.metrics.get("revenue"))),
            _line("EBITDA", _value(model.metrics.get("ebitda")), _unit(model.metrics.get("ebitda"))),
            _line("Cash Flow", _value(model.metrics.get("cash_flow")), _unit(model.metrics.get("cash_flow"))),
        ],
        return_analysis=[
            f"Sponsor cash flow count: {len(model.returns.sponsor_cash_flows)}",
            _line("Sponsor Equity Invested", model.returns.sponsor_equity_invested.value, model.returns.sponsor_equity_invested.unit),
            _line("Sponsor Proceeds", model.returns.sponsor_proceeds.value, model.returns.sponsor_proceeds.unit),
        ],
        value_creation_bridge=[
            _line("Entry Equity Value", model.valuation.entry_equity_value.value, model.valuation.entry_equity_value.unit),
            _line("Exit Equity Value", model.valuation.exit_equity_value.value, model.valuation.exit_equity_value.unit),
        ],
        sensitivity_results=sensitivity,
        risk_flags=risk_flags,
        model_audit=[
            f"{metric.display_name}: {metric.confidence} confidence ({metric.source_sheet or 'no sheet'}!{metric.source_cell or 'no cell'})"
            for metric in model.metrics.values()
        ],
    )


def _line(label: str, value, unit: str | None) -> str:
    if value is None:
        return f"{label}: Missing"
    suffix = f" {unit}" if unit else ""
    if unit == "%":
        return f"{label}: {value:.1%}"
    if unit == "x":
        return f"{label}: {value:.2f}x"
    return f"{label}: {value:,.1f}{suffix}"


def _source_line(label: str, metric) -> str:
    if metric is None or not metric.is_available:
        return f"{label}: Missing"
    return f"{label}: {metric.source_sheet}!{metric.source_cell}"


def _value(metric):
    return None if metric is None else metric.value


def _unit(metric):
    return None if metric is None else metric.unit

