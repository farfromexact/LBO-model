from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from lbo.schemas.standard_model import MetricValue


class DealInput(BaseModel):
    project_name: MetricValue
    company: MetricValue
    sector: MetricValue
    currency: MetricValue
    unit: MetricValue
    entry_date: MetricValue
    exit_date: MetricValue
    entry_ev: MetricValue
    entry_equity_value: MetricValue
    sponsor_equity_invested: MetricValue
    sponsor_ownership: MetricValue
    entry_multiple: MetricValue
    exit_multiple: MetricValue
    transaction_fees: MetricValue
    rollover_management_equity: MetricValue


class OperatingForecast(BaseModel):
    periods: list[int]
    revenue: dict[int, MetricValue] = Field(default_factory=dict)
    ebitda: dict[int, MetricValue] = Field(default_factory=dict)
    ebitda_margin: dict[int, MetricValue] = Field(default_factory=dict)
    capex: dict[int, MetricValue] = Field(default_factory=dict)
    cash_tax: dict[int, MetricValue] = Field(default_factory=dict)
    change_in_nwc: dict[int, MetricValue] = Field(default_factory=dict)
    fcf: dict[int, MetricValue] = Field(default_factory=dict)


class DebtScheduleInput(BaseModel):
    periods: list[int]
    opening_debt: dict[int, MetricValue] = Field(default_factory=dict)
    new_debt: dict[int, MetricValue] = Field(default_factory=dict)
    repayment: dict[int, MetricValue] = Field(default_factory=dict)
    cash_sweep: dict[int, MetricValue] = Field(default_factory=dict)
    ending_debt: dict[int, MetricValue] = Field(default_factory=dict)
    cash: dict[int, MetricValue] = Field(default_factory=dict)
    net_debt: dict[int, MetricValue] = Field(default_factory=dict)


class ReturnInputs(BaseModel):
    exit_ebitda: MetricValue
    exit_ev: MetricValue
    exit_net_debt: MetricValue
    exit_equity_value: MetricValue
    dividends_cash_distributions: MetricValue
    sponsor_proceeds: MetricValue
    moic: MetricValue
    irr: MetricValue


class QualitativeInputs(BaseModel):
    investment_thesis: MetricValue
    key_risks: MetricValue
    diligence_questions: MetricValue
    management_market_notes: MetricValue
    exit_rationale: MetricValue


class TemplateInputModel(BaseModel):
    source_file: str
    deal: DealInput
    operating: OperatingForecast
    debt: DebtScheduleInput
    returns: ReturnInputs
    qualitative: QualitativeInputs
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def forecast_year_count(self) -> int:
        return len(self.operating.periods)


def metric_date(metric: MetricValue) -> date | None:
    return metric.value if isinstance(metric.value, date) else None


def metric_float(metric: MetricValue | None) -> float | None:
    if metric is None:
        return None
    value = metric.value
    return float(value) if isinstance(value, (int, float)) else None

