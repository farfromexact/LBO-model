from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ConfidenceLevel = Literal["high", "medium", "low", "missing"]


class StandardMetric(BaseModel):
    metric_id: str
    display_name: str
    value: float | None = None
    period: str | None = None
    unit: str | None = None
    scale: float = 1.0
    sign_convention: str | None = None
    source_sheet: str | None = None
    source_cell: str | None = None
    confidence: ConfidenceLevel = "missing"
    missing_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    series: dict[str, float] = Field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.value is not None and self.confidence != "missing"


class FinancialStatement(BaseModel):
    statement_id: str
    display_name: str
    periods: list[str] = Field(default_factory=list)
    metrics: dict[str, StandardMetric] = Field(default_factory=dict)


class ValuationSummary(BaseModel):
    entry_ev: StandardMetric
    entry_equity_value: StandardMetric
    exit_ev: StandardMetric
    exit_equity_value: StandardMetric
    net_debt: StandardMetric


class ReturnSummary(BaseModel):
    moic: StandardMetric
    irr: StandardMetric
    sponsor_equity_invested: StandardMetric
    sponsor_proceeds: StandardMetric
    sponsor_cash_flows: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ModelMetadata(BaseModel):
    source_workbook: str
    adapter_name: str
    adapter_confidence: float
    detected_template: str
    extraction_coverage: float
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StandardModel(BaseModel):
    metadata: ModelMetadata
    metrics: dict[str, StandardMetric] = Field(default_factory=dict)
    financial_statements: dict[str, FinancialStatement] = Field(default_factory=dict)
    valuation: ValuationSummary
    returns: ReturnSummary
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def required_metric_count(self) -> int:
        return len(self.metrics)

    @property
    def extracted_metric_count(self) -> int:
        return sum(1 for metric in self.metrics.values() if metric.is_available)

