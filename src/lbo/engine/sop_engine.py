from __future__ import annotations

from pydantic import BaseModel, Field

from lbo.analytics.risk_flags import generate_risk_flags
from lbo.engine.sensitivity_engine import SensitivityResult, run_standardized_sensitivity
from lbo.schemas.standard_model import MetricValue, StandardModel


class SOPAnalysisResult(BaseModel):
    deal_summary: list[str] = Field(default_factory=list)
    data_quality: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    operating_performance: list[str] = Field(default_factory=list)
    return_analysis: list[str] = Field(default_factory=list)
    value_creation_bridge: list[str] = Field(default_factory=list)
    debt_and_deleveraging: list[str] = Field(default_factory=list)
    sensitivity_results: SensitivityResult
    risk_flags: list[str] = Field(default_factory=list)
    model_audit: list[str] = Field(default_factory=list)


def generate_sop_analysis(model: StandardModel) -> SOPAnalysisResult:
    sensitivity = run_standardized_sensitivity(model)
    risk_flags = generate_risk_flags(model)
    return SOPAnalysisResult(
        deal_summary=[
            _line("Project", model.metadata.project_name, None),
            _line("Entry EV", model.valuation.entry_ev, model.metadata.unit),
            _line("Exit EV", model.valuation.exit_ev, model.metadata.unit),
            _line("Entry Equity Value", model.valuation.entry_equity_value, model.metadata.unit),
            _line("Exit Equity Value", model.valuation.exit_equity_value, model.metadata.unit),
        ],
        data_quality=[
            f"Adapter: {model.metadata.adapter_name}",
            f"Template: {model.metadata.detected_template_id}",
            f"Detection confidence: {model.metadata.confidence_score:.0%}",
            f"Extraction coverage: {model.extraction_coverage:.0%}",
            f"Missing fields: {len(model.missing_fields)}",
            f"Excel errors: {len(model.metadata.excel_errors)}",
        ],
        key_assumptions=[
            _metric_source("Entry Multiple", model.valuation.entry_multiple),
            _metric_source("Exit Multiple", model.valuation.exit_multiple),
            _metric_source("Entry EBITDA", model.valuation.entry_ebitda),
            _metric_source("Exit EBITDA", model.valuation.exit_ebitda),
        ],
        operating_performance=[
            _series_latest("Revenue", model.financials.revenue),
            _series_latest("EBITDA", model.financials.ebitda),
            _series_latest("Capex", model.financials.capex),
            _series_latest("FCF", model.financials.fcf),
        ],
        return_analysis=[
            _line("IRR", model.returns.irr, "%"),
            _line("MOIC", model.returns.moic, "x"),
            _line("Net Gain", model.returns.net_gain, model.metadata.unit),
            _line("Sponsor Equity Invested", model.returns.sponsor_equity_invested, model.metadata.unit),
            _line("Sponsor Exit Proceeds", model.returns.sponsor_exit_proceeds, model.metadata.unit),
            f"Sponsor cash flow points: {len(model.returns.sponsor_cash_flows)}",
        ],
        value_creation_bridge=[
            _line("Entry Equity Value", model.valuation.entry_equity_value, model.metadata.unit),
            _line("Exit Equity Value", model.valuation.exit_equity_value, model.metadata.unit),
            "Detailed attribution is available only when the adapter extracts value creation rows.",
        ],
        debt_and_deleveraging=[
            _series_latest("Net Debt", model.debt.net_debt if model.debt else {}),
            _series_latest("Net Debt / EBITDA", model.debt.net_debt_to_ebitda if model.debt else {}),
        ],
        sensitivity_results=sensitivity,
        risk_flags=risk_flags,
        model_audit=_audit_rows(model),
    )


def _line(label: str, metric_or_value, unit: str | None) -> str:
    value = metric_or_value.value if isinstance(metric_or_value, MetricValue) else metric_or_value
    if value is None:
        return f"{label}: Missing"
    if unit == "%":
        return f"{label}: {float(value):.1%}" if isinstance(value, (int, float)) else f"{label}: {value}"
    if unit == "x":
        return f"{label}: {float(value):.2f}x" if isinstance(value, (int, float)) else f"{label}: {value}"
    suffix = f" {unit}" if unit else ""
    return f"{label}: {value:,.1f}{suffix}" if isinstance(value, (int, float)) else f"{label}: {value}{suffix}"


def _metric_source(label: str, metric: MetricValue | None) -> str:
    if metric is None or not metric.is_available:
        return f"{label}: Missing"
    return f"{label}: {_format(metric)} ({metric.source_sheet}!{metric.source_cell or metric.source_range})"


def _series_latest(label: str, series: dict[int, MetricValue] | None) -> str:
    if not series:
        return f"{label}: Missing"
    period, metric = sorted(series.items())[-1]
    return f"{label} {period}: {_format(metric)} ({metric.source_sheet}!{metric.source_cell})"


def _format(metric: MetricValue) -> str:
    if metric.value is None:
        return "Missing"
    if metric.unit == "%":
        return f"{float(metric.value):.1%}"
    if metric.unit == "x":
        return f"{float(metric.value):.2f}x"
    return f"{metric.value:,.1f}" if isinstance(metric.value, (int, float)) else str(metric.value)


def _audit_rows(model: StandardModel) -> list[str]:
    rows = []
    for metric in model.metrics.values():
        source = metric.source_cell or metric.source_range or "no source"
        rows.append(f"{metric.label}: {metric.confidence} confidence, {metric.extraction_method}, {metric.source_sheet or 'no sheet'}!{source}")
    rows.extend(f"Missing: {field}" for field in model.missing_fields)
    rows.extend(f"Excel error: {err}" for err in model.metadata.excel_errors[:20])
    return rows
