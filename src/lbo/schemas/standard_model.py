from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ExtractionMethod = Literal[
    "fixed_cell",
    "label_match",
    "row_series",
    "matrix",
    "python_calculated",
    "missing",
    "excel_error",
]
ConfidenceLevel = Literal["high", "medium", "low", "missing"]


class MetricValue(BaseModel):
    metric_id: str
    label: str
    value: float | str | date | None = None
    period: int | str | None = None
    unit: str | None = None
    scale: float | None = 1.0
    sign_convention: str | None = None
    source_sheet: str | None = None
    source_cell: str | None = None
    source_range: str | None = None
    extraction_method: ExtractionMethod = "missing"
    confidence: ConfidenceLevel = "missing"
    warning: str | None = None

    @property
    def display_name(self) -> str:
        return self.label

    @property
    def is_available(self) -> bool:
        return self.value is not None and self.confidence != "missing" and self.extraction_method != "missing"

    @property
    def missing_reason(self) -> str | None:
        return self.warning if not self.is_available else None

    @property
    def warnings(self) -> list[str]:
        return [self.warning] if self.warning else []


class FinancialSeries(BaseModel):
    revenue: dict[int, MetricValue] = Field(default_factory=dict)
    ebitda: dict[int, MetricValue] = Field(default_factory=dict)
    ebit: dict[int, MetricValue] | None = None
    net_income: dict[int, MetricValue] | None = None
    capex: dict[int, MetricValue] | None = None
    fcf: dict[int, MetricValue] | None = None
    net_debt: dict[int, MetricValue] | None = None


class ValuationSummary(BaseModel):
    entry_date: MetricValue | None = None
    exit_date: MetricValue | None = None
    entry_ev: MetricValue | None = None
    entry_equity_value: MetricValue | None = None
    entry_multiple: MetricValue | None = None
    entry_ebitda: MetricValue | None = None
    exit_ev: MetricValue | None = None
    exit_equity_value: MetricValue | None = None
    exit_multiple: MetricValue | None = None
    exit_ebitda: MetricValue | None = None


class ReturnSummary(BaseModel):
    irr: MetricValue | None = None
    moic: MetricValue | None = None
    net_gain: MetricValue | None = None
    sponsor_cash_flows: list[MetricValue] = Field(default_factory=list)
    sponsor_equity_invested: MetricValue | None = None
    sponsor_exit_proceeds: MetricValue | None = None

    @property
    def sponsor_proceeds(self) -> MetricValue | None:
        return self.sponsor_exit_proceeds


class DebtSummary(BaseModel):
    gross_debt: dict[int, MetricValue] = Field(default_factory=dict)
    cash: dict[int, MetricValue] = Field(default_factory=dict)
    net_debt: dict[int, MetricValue] = Field(default_factory=dict)
    net_debt_to_ebitda: dict[int, MetricValue] = Field(default_factory=dict)


class SensitivityMatrix(BaseModel):
    matrix_id: str
    title: str
    row_axis_name: str
    col_axis_name: str
    row_values: list[float | str]
    col_values: list[float | str]
    values: list[list[float | None]]
    metric: Literal["IRR", "MOIC", "Exit Equity Value", "EV"]
    source_sheet: str
    source_range: str
    confidence: Literal["high", "medium", "low"]
    extraction_method: Literal["matrix", "python_calculated"] = "matrix"


class ModelMetadata(BaseModel):
    source_file: str
    detected_template_id: str
    adapter_name: str
    confidence_score: float = Field(ge=0, le=1)
    project_name: str | None = None
    currency: str | None = None
    unit: str | None = None
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    excel_errors: list[str] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    extraction_coverage: float = 0.0

    @property
    def source_workbook(self) -> str:
        return self.source_file

    @property
    def detected_template(self) -> str:
        return self.detected_template_id

    @property
    def adapter_confidence(self) -> float:
        return self.confidence_score


class StandardModel(BaseModel):
    metadata: ModelMetadata
    financials: FinancialSeries = Field(default_factory=FinancialSeries)
    valuation: ValuationSummary = Field(default_factory=ValuationSummary)
    returns: ReturnSummary = Field(default_factory=ReturnSummary)
    debt: DebtSummary | None = None
    sensitivities: list[SensitivityMatrix] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_metadata_lists(self) -> "StandardModel":
        for field in self.missing_fields:
            if field not in self.metadata.missing_fields:
                self.metadata.missing_fields.append(field)
        for warning in self.warnings:
            if warning not in self.metadata.warnings:
                self.metadata.warnings.append(warning)
        self.metadata.extraction_coverage = self.extraction_coverage
        return self

    @property
    def metrics(self) -> dict[str, MetricValue]:
        result: dict[str, MetricValue] = {}
        for name in [
            "entry_date",
            "exit_date",
            "entry_ev",
            "entry_equity_value",
            "entry_multiple",
            "entry_ebitda",
            "exit_ev",
            "exit_equity_value",
            "exit_multiple",
            "exit_ebitda",
        ]:
            metric = getattr(self.valuation, name)
            if metric is not None:
                result[metric.metric_id] = metric
        for name in ["irr", "moic", "net_gain", "sponsor_equity_invested", "sponsor_exit_proceeds"]:
            metric = getattr(self.returns, name)
            if metric is not None:
                result[metric.metric_id] = metric
        for series_name in ["revenue", "ebitda", "ebit", "net_income", "capex", "fcf", "net_debt"]:
            series = getattr(self.financials, series_name)
            if series:
                latest = _latest_metric(series)
                if latest is not None:
                    result[series_name] = latest
        return result

    @property
    def financial_statements(self) -> dict[str, object]:
        return {}

    @property
    def missing_fields(self) -> list[str]:
        missing = list(self.metadata.missing_fields)
        for metric_id in [
            "entry_ev",
            "entry_equity_value",
            "exit_ev",
            "exit_equity_value",
            "irr",
            "moic",
        ]:
            metric = self.metrics.get(metric_id)
            if (metric is None or not metric.is_available) and metric_id not in missing:
                missing.append(metric_id)
        return missing

    @property
    def warnings(self) -> list[str]:
        return self.metadata.warnings

    @property
    def required_metric_count(self) -> int:
        return 9

    @property
    def extracted_metric_count(self) -> int:
        required = ["revenue", "ebitda", "net_debt", "capex", "fcf", "entry_ev", "exit_ev", "irr", "moic"]
        return sum(1 for metric_id in required if self.metrics.get(metric_id) and self.metrics[metric_id].is_available)

    @property
    def extraction_coverage(self) -> float:
        return self.extracted_metric_count / self.required_metric_count if self.required_metric_count else 0.0


class FinancialStatement(BaseModel):
    statement_id: str
    display_name: str
    periods: list[str] = Field(default_factory=list)
    metrics: dict[str, MetricValue] = Field(default_factory=dict)


class StandardMetric(MetricValue):
    @classmethod
    def from_legacy(
        cls,
        metric_id: str,
        display_name: str,
        value: float | None = None,
        period: str | None = None,
        unit: str | None = None,
        scale: float = 1.0,
        sign_convention: str | None = None,
        source_sheet: str | None = None,
        source_cell: str | None = None,
        confidence: ConfidenceLevel = "missing",
        missing_reason: str | None = None,
        warnings: list[str] | None = None,
        series: dict[str, float] | None = None,
    ) -> "StandardMetric":
        warning = missing_reason or (warnings[0] if warnings else None)
        return cls(
            metric_id=metric_id,
            label=display_name,
            value=value,
            period=period,
            unit=unit,
            scale=scale,
            sign_convention=sign_convention,
            source_sheet=source_sheet,
            source_cell=source_cell,
            extraction_method="missing" if value is None else "label_match",
            confidence=confidence,
            warning=warning,
        )


def _latest_metric(series: dict[int, MetricValue]) -> MetricValue | None:
    available = [(period, metric) for period, metric in series.items() if metric.is_available]
    if not available:
        return None
    return sorted(available, key=lambda item: item[0])[-1][1]
