from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ScenarioName = Literal["Base", "Optimistic", "Pessimistic"]


class SourceRef(BaseModel):
    workbook: str
    sheet: str | None
    range: str
    label: str | None = None
    unit: str | None = None
    extraction_method: str

    @property
    def display(self) -> str:
        sheet = self.sheet or "Missing sheet"
        return f"{sheet}!{self.range}"


class MetricValue(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str
    display_name: str
    value: Any = None
    period: str | None = None
    unit: str | None = None
    source: SourceRef
    missing_reason: str | None = None

    @model_validator(mode="after")
    def require_source(self) -> "MetricValue":
        if self.source is None:
            raise ValueError("MetricValue requires source traceability")
        return self

    @classmethod
    def missing(
        cls,
        key: str,
        display_name: str,
        period: str | None,
        unit: str | None,
        source: SourceRef,
        missing_reason: str,
    ) -> "MetricValue":
        return cls(
            key=key,
            display_name=display_name,
            value=None,
            period=period,
            unit=unit,
            source=source,
            missing_reason=missing_reason,
        )

    @property
    def is_missing(self) -> bool:
        return self.missing_reason is not None


class CoreSheets(BaseModel):
    financial_output: str | None = None
    balance_sheet: str | None = None
    cash_flow: str | None = None
    capex: str | None = None
    return_model: str | None = None
    missing_roles: list[str] = Field(default_factory=list)

    def sheet_for_role(self, role: str) -> str | None:
        return getattr(self, role, None)

    def as_rows(self) -> list[dict[str, str | None]]:
        return [
            {"role": key, "sheet": value}
            for key, value in self.model_dump().items()
            if key != "missing_roles"
        ]


class FinancialStatementTable(BaseModel):
    name: str
    periods: list[str]
    rows: dict[str, list[Any]]
    unit: str | None = None
    source: SourceRef

    @model_validator(mode="after")
    def validate_row_widths(self) -> "FinancialStatementTable":
        expected = len(self.periods)
        for row_name, values in self.rows.items():
            if len(values) != expected:
                raise ValueError(f"Row '{row_name}' has {len(values)} values; expected {expected}")
        return self


class ReturnModel(BaseModel):
    irr: MetricValue | None = None
    moic: MetricValue | None = None
    entry_ev: MetricValue | None = None
    exit_ev: MetricValue | None = None
    status: str = "Excel sourced; Python engine pending"


class ReconciliationItem(BaseModel):
    metric_key: str
    metric_name: str
    excel_value: Any = None
    python_value: Any = None
    variance: float | None = None
    status: str = "Pending Python engine"
    source: SourceRef


class ModelSnapshot(BaseModel):
    workbook_name: str
    scenario: ScenarioName = "Base"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sheets: list[str]
    core_sheets: CoreSheets
    metrics: dict[str, MetricValue]
    tables: dict[str, FinancialStatementTable] = Field(default_factory=dict)
    return_model: ReturnModel
    reconciliation: list[ReconciliationItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_traceability(self) -> "ModelSnapshot":
        for metric in self.metrics.values():
            if metric.source is None:
                raise ValueError(f"Metric '{metric.key}' is missing source traceability")
        return self
