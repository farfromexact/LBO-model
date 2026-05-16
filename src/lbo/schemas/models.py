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


class EngineAssumptions(BaseModel):
    scenario: ScenarioName = "Base"
    entry_multiple: float = Field(gt=0)
    exit_multiple: float = Field(gt=0)
    exit_year: int = Field(ge=2025, le=2050)
    debt_interest_rate: float = Field(ge=0, le=1)
    debt_repayment_speed: float = Field(ge=0, le=1)
    ebitda_growth: float = Field(ge=-0.5, le=1)
    capex_intensity: float = Field(ge=0, le=1)
    tax_rate: float = Field(ge=0, le=1)


class DebtPeriod(BaseModel):
    year: int
    opening_debt: float
    interest: float
    cash_available_for_repayment: float
    repayment: float
    ending_debt: float


class DebtModel(BaseModel):
    periods: list[DebtPeriod] = Field(default_factory=list)


class ValueCreationBridge(BaseModel):
    ebitda_growth: float
    multiple_expansion: float
    debt_paydown: float
    tax_leakage: float

    @property
    def total(self) -> float:
        return self.ebitda_growth + self.multiple_expansion + self.debt_paydown + self.tax_leakage


class SensitivityTable(BaseModel):
    entry_multiples: list[float]
    exit_multiples: list[float]
    values: list[list[float | None]]

    @model_validator(mode="after")
    def validate_shape(self) -> "SensitivityTable":
        if len(self.values) != len(self.entry_multiples):
            raise ValueError("Sensitivity rows must match entry multiples")
        for row in self.values:
            if len(row) != len(self.exit_multiples):
                raise ValueError("Sensitivity columns must match exit multiples")
        return self


class PythonEngineOutputs(BaseModel):
    entry_year: int
    entry_ebitda: float
    exit_ebitda: float
    entry_ev: float
    exit_ev: float
    sponsor_equity: float
    exit_equity_value: float
    after_tax_exit_equity: float
    irr: float | None
    moic: float | None
    ending_net_debt: float
    net_debt_to_ebitda: float | None
    debt_model: DebtModel
    value_creation_bridge: ValueCreationBridge
    sensitivity: SensitivityTable


class ReturnModel(BaseModel):
    irr: MetricValue | None = None
    moic: MetricValue | None = None
    entry_ev: MetricValue | None = None
    exit_ev: MetricValue | None = None
    python_outputs: PythonEngineOutputs | None = None
    status: str = "Excel sourced; Python engine available for selected assumptions"


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
    engine_assumptions: EngineAssumptions | None = None
    python_engine: PythonEngineOutputs | None = None
    return_model: ReturnModel
    reconciliation: list[ReconciliationItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_traceability(self) -> "ModelSnapshot":
        for metric in self.metrics.values():
            if metric.source is None:
                raise ValueError(f"Metric '{metric.key}' is missing source traceability")
        return self

    @property
    def reconciliation_by_metric(self) -> dict[str, ReconciliationItem]:
        return {item.metric_key: item for item in self.reconciliation}
