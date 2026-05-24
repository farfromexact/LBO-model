from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pyxirr

from lbo.adapters.base_adapter import AdapterMatch, BaseWorkbookAdapter, build_metric, get_openpyxl_workbook
from lbo.io.template_generator import TEMPLATE_SHEETS
from lbo.schemas.standard_model import (
    DebtSummary,
    FinancialSeries,
    ModelMetadata,
    ReturnSummary,
    StandardModel,
    ValuationSummary,
)
from lbo.schemas.template_input import (
    DealInput,
    DebtScheduleInput,
    OperatingForecast,
    QualitativeInputs,
    ReturnInputs,
    TemplateInputModel,
    metric_float,
)


class TemplateInputAdapter(BaseWorkbookAdapter):
    template_id = "standard_input_template"
    adapter_name = "Standard Input Template Adapter"

    def can_handle(self, workbook) -> AdapterMatch:
        wb = get_openpyxl_workbook(workbook)
        matched = [sheet for sheet in TEMPLATE_SHEETS if sheet in wb.sheetnames]
        missing = [sheet for sheet in TEMPLATE_SHEETS if sheet not in wb.sheetnames]
        confidence = len(matched) / len(TEMPLATE_SHEETS)
        return AdapterMatch(
            template_id=self.template_id,
            adapter_name=self.adapter_name,
            confidence_score=confidence,
            matched_features=matched,
            missing_features=missing,
            warnings=[] if not missing else [f"Missing required template sheets: {', '.join(missing)}"],
        )

    def extract_input(self, workbook, source_file: str = "standard_template.xlsx") -> TemplateInputModel:
        wb = get_openpyxl_workbook(workbook)
        missing_sheets = [sheet for sheet in TEMPLATE_SHEETS if sheet not in wb.sheetnames]
        if missing_sheets:
            raise ValueError(f"Missing required template sheets: {', '.join(missing_sheets)}")

        missing_fields: list[str] = []
        warnings: list[str] = []
        deal_values = _field_sheet(wb["Deal Setup"], source_file)
        return_values = _field_sheet(wb["Return Assumptions"], source_file)
        qualitative_values = _field_sheet(wb["Qualitative Inputs"], source_file)
        operating = _operating_forecast(wb["Operating Forecast"], source_file, missing_fields, warnings)
        debt = _debt_schedule(wb["Debt & Cash"], source_file, missing_fields, warnings)

        deal = DealInput(**{field: _required_field(deal_values, field, "Deal Setup", missing_fields) for field in DealInput.model_fields})
        returns = ReturnInputs(**{field: _required_field(return_values, field, "Return Assumptions", missing_fields) for field in ReturnInputs.model_fields})
        qualitative = QualitativeInputs(
            **{field: _required_field(qualitative_values, field, "Qualitative Inputs", missing_fields) for field in QualitativeInputs.model_fields}
        )
        _validate_period_count(operating.periods, missing_fields, warnings)
        return TemplateInputModel(
            source_file=source_file,
            deal=deal,
            operating=operating,
            debt=debt,
            returns=returns,
            qualitative=qualitative,
            missing_fields=list(dict.fromkeys(missing_fields)),
            warnings=warnings,
        )

    def extract(self, workbook, source_file: str = "standard_template.xlsx") -> StandardModel:
        template = self.extract_input(workbook, source_file)
        return standard_model_from_template(template)


def standard_model_from_template(template: TemplateInputModel) -> StandardModel:
    currency = _metric_str(template.deal.currency)
    unit = _metric_str(template.deal.unit)
    warnings = list(template.warnings)
    missing_fields = list(template.missing_fields)

    entry_ev = template.deal.entry_ev
    entry_equity = template.deal.entry_equity_value
    sponsor_invested = template.deal.sponsor_equity_invested
    entry_multiple = _calculated_or_input(
        template.deal.entry_multiple,
        "entry_multiple",
        "Entry EV / EBITDA",
        _safe_div(metric_float(entry_ev), _first_float(template.operating.ebitda)),
    )

    exit_ebitda = _calculated_or_input(template.returns.exit_ebitda, "exit_ebitda", "Exit EBITDA", _last_float(template.operating.ebitda), unit=unit)
    exit_multiple = template.deal.exit_multiple
    exit_ev = _calculated_or_input(
        template.returns.exit_ev,
        "exit_ev",
        "Exit EV",
        _safe_mul(metric_float(exit_ebitda), metric_float(exit_multiple)),
        unit=unit,
    )
    exit_net_debt = template.returns.exit_net_debt
    exit_equity = _calculated_or_input(
        template.returns.exit_equity_value,
        "exit_equity_value",
        "Exit Equity Value",
        _safe_sub(metric_float(exit_ev), metric_float(exit_net_debt)),
        unit=unit,
    )

    dividends = metric_float(template.returns.dividends_cash_distributions) or 0.0
    sponsor_ownership = metric_float(template.deal.sponsor_ownership)
    sponsor_proceeds = _calculated_or_input(
        template.returns.sponsor_proceeds,
        "sponsor_exit_proceeds",
        "Sponsor Exit Proceeds",
        _safe_add(_safe_mul(metric_float(exit_equity), sponsor_ownership), dividends),
        unit=unit,
    )
    sponsor_cash_flows = _sponsor_cash_flows(template, sponsor_invested, sponsor_proceeds, dividends, unit)
    calculated_moic = _calculate_moic(sponsor_cash_flows)
    calculated_irr = _calculate_irr(sponsor_cash_flows)
    moic = _return_metric(template.returns.moic, "moic", "MOIC", calculated_moic, "x", missing_fields)
    irr = _return_metric(template.returns.irr, "irr", "IRR", calculated_irr, "%", missing_fields)
    net_gain = _calculated_metric(
        "net_gain",
        "Net Gain",
        _safe_sub(metric_float(sponsor_proceeds), abs(metric_float(sponsor_invested) or 0.0)) if metric_float(sponsor_proceeds) is not None else None,
        unit=unit,
    )

    financials = FinancialSeries(
        revenue=template.operating.revenue,
        ebitda=template.operating.ebitda,
        capex=template.operating.capex,
        fcf=template.operating.fcf,
        net_debt=template.debt.net_debt,
    )
    debt_summary = DebtSummary(
        gross_debt=template.debt.ending_debt,
        cash=template.debt.cash,
        net_debt=template.debt.net_debt,
        net_debt_to_ebitda=_net_debt_to_ebitda(template.debt.net_debt, template.operating.ebitda),
    )
    valuation = ValuationSummary(
        entry_date=template.deal.entry_date,
        exit_date=template.deal.exit_date,
        entry_ev=entry_ev,
        entry_equity_value=entry_equity,
        entry_multiple=entry_multiple,
        entry_ebitda=_calculated_metric("entry_ebitda", "Entry EBITDA", _first_float(template.operating.ebitda), unit=unit),
        exit_ev=exit_ev,
        exit_equity_value=exit_equity,
        exit_multiple=exit_multiple,
        exit_ebitda=exit_ebitda,
    )
    returns = ReturnSummary(
        irr=irr,
        moic=moic,
        net_gain=net_gain,
        sponsor_cash_flows=sponsor_cash_flows,
        sponsor_equity_invested=sponsor_invested,
        sponsor_exit_proceeds=sponsor_proceeds,
    )
    model = StandardModel(
        metadata=ModelMetadata(
            source_file=template.source_file,
            detected_template_id="standard_input_template",
            adapter_name="Standard Input Template Adapter",
            confidence_score=1.0,
            project_name=_metric_str(template.deal.project_name),
            currency=currency,
            unit=unit,
            warnings=warnings + _audit_warnings(template, valuation, returns, financials, debt_summary),
            missing_fields=list(dict.fromkeys(missing_fields)),
        ),
        financials=financials,
        valuation=valuation,
        returns=returns,
        debt=debt_summary,
        qualitative={key: getattr(template.qualitative, key).value for key in QualitativeInputs.model_fields},
    )
    model.sensitivities = _template_sensitivities(model)
    model.metadata.extraction_coverage = model.extraction_coverage
    return model


def _field_sheet(sheet, source_file: str) -> dict[str, Any]:
    headers = {str(cell.value).strip().lower(): idx + 1 for idx, cell in enumerate(sheet[1]) if cell.value}
    field_col = headers.get("field_id")
    display_col = headers.get("display_name")
    value_col = headers.get("value")
    if not field_col or not value_col:
        raise ValueError(f"{sheet.title} must include field_id and value columns")
    result = {}
    for row in range(2, sheet.max_row + 1):
        field_id = sheet.cell(row, field_col).value
        if not field_id:
            continue
        label = sheet.cell(row, display_col).value if display_col else str(field_id)
        value_cell = sheet.cell(row, value_col)
        result[str(field_id)] = build_metric(
            metric_id=str(field_id),
            label=str(label or field_id),
            value=_coerce_value(value_cell.value),
            source_sheet=sheet.title,
            source_cell=value_cell.coordinate,
            extraction_method="fixed_cell" if value_cell.value is not None else "missing",
            confidence="high" if value_cell.value is not None else "missing",
            warning=None if value_cell.value is not None else "Missing template input",
        )
    return result


def _required_field(values: dict[str, Any], field_id: str, sheet_name: str, missing_fields: list[str]):
    metric = values.get(field_id)
    if metric is not None:
        if not metric.is_available:
            missing_fields.append(field_id)
        return metric
    missing_fields.append(field_id)
    return build_metric(
        metric_id=field_id,
        label=field_id.replace("_", " ").title(),
        value=None,
        source_sheet=sheet_name,
        extraction_method="missing",
        confidence="missing",
        warning="Missing required template field",
    )


def _operating_forecast(sheet, source_file: str, missing_fields: list[str], warnings: list[str]) -> OperatingForecast:
    rows = _table_rows(sheet, ["year", "revenue", "ebitda", "ebitda_margin", "capex", "cash_tax", "change_in_nwc", "fcf"])
    periods = [int(row["year"][0]) for row in rows if isinstance(row["year"][0], (int, float))]
    series = {name: {} for name in ["revenue", "ebitda", "ebitda_margin", "capex", "cash_tax", "change_in_nwc", "fcf"]}
    for row in rows:
        year_value, _ = row["year"]
        if not isinstance(year_value, (int, float)):
            continue
        year = int(year_value)
        for name in series:
            value, cell = row[name]
            series[name][year] = build_metric(
                metric_id=name,
                label=name.replace("_", " ").title(),
                value=value,
                period=year,
                unit="%" if name == "ebitda_margin" else None,
                source_sheet=sheet.title,
                source_cell=cell,
                extraction_method="fixed_cell" if value is not None else "missing",
                confidence="high" if value is not None else "missing",
                warning=None if value is not None else "Missing template input",
            )
            if value is None:
                missing_fields.append(f"operating.{name}.{year}")
    return OperatingForecast(periods=periods, **series)


def _debt_schedule(sheet, source_file: str, missing_fields: list[str], warnings: list[str]) -> DebtScheduleInput:
    names = ["opening_debt", "new_debt", "repayment", "cash_sweep", "ending_debt", "cash", "net_debt"]
    rows = _table_rows(sheet, ["year", *names])
    periods = [int(row["year"][0]) for row in rows if isinstance(row["year"][0], (int, float))]
    series = {name: {} for name in names}
    for row in rows:
        year_value, _ = row["year"]
        if not isinstance(year_value, (int, float)):
            continue
        year = int(year_value)
        for name in names:
            value, cell = row[name]
            series[name][year] = build_metric(
                metric_id=name,
                label=name.replace("_", " ").title(),
                value=value,
                period=year,
                source_sheet=sheet.title,
                source_cell=cell,
                extraction_method="fixed_cell" if value is not None else "missing",
                confidence="high" if value is not None else "missing",
                warning=None if value is not None else "Missing template input",
            )
            if value is None:
                missing_fields.append(f"debt.{name}.{year}")
    return DebtScheduleInput(periods=periods, **series)


def _table_rows(sheet, required_headers: list[str]) -> list[dict[str, tuple[Any, str]]]:
    headers = {str(cell.value).strip().lower(): idx + 1 for idx, cell in enumerate(sheet[1]) if cell.value}
    missing = [header for header in required_headers if header not in headers]
    if missing:
        raise ValueError(f"{sheet.title} missing required columns: {', '.join(missing)}")
    rows = []
    for row_idx in range(2, sheet.max_row + 1):
        if sheet.cell(row_idx, headers["year"]).value is None:
            continue
        rows.append({header: (_coerce_value(sheet.cell(row_idx, headers[header]).value), sheet.cell(row_idx, headers[header]).coordinate) for header in required_headers})
    return rows


def _validate_period_count(periods: list[int], missing_fields: list[str], warnings: list[str]) -> None:
    if not 3 <= len(periods) <= 7:
        warnings.append("Forecast period should contain 3-7 years.")
    if len(set(periods)) != len(periods):
        warnings.append("Forecast years contain duplicates.")


def _coerce_value(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        text = value.strip()
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return text
    return value


def _calculated_or_input(input_metric, metric_id: str, label: str, calculated: float | None, unit: str | None = None):
    if input_metric.is_available:
        return input_metric.model_copy(update={"metric_id": metric_id, "label": label, "unit": unit or input_metric.unit})
    return _calculated_metric(metric_id, label, calculated, unit=unit)


def _return_metric(input_metric, metric_id: str, label: str, calculated: float | None, unit: str, missing_fields: list[str]):
    if calculated is None:
        missing_fields.append(metric_id)
        return build_metric(metric_id, label, None, unit=unit, extraction_method="missing", confidence="missing", warning="Missing sponsor cash flows or dates")
    return build_metric(metric_id, label, calculated, unit=unit, source_sheet="Python Engine", source_range="calculated", extraction_method="python_calculated", confidence="high")


def _calculated_metric(metric_id: str, label: str, value: float | None, unit: str | None = None):
    return build_metric(metric_id, label, value, unit=unit, source_sheet="Python Engine", source_range="calculated", extraction_method="python_calculated" if value is not None else "missing", confidence="high" if value is not None else "missing", warning=None if value is not None else "Missing inputs for calculation")


def _sponsor_cash_flows(template, sponsor_invested, sponsor_proceeds, dividends: float, unit: str | None):
    entry_date = template.deal.entry_date.value if isinstance(template.deal.entry_date.value, date) else None
    exit_date = template.deal.exit_date.value if isinstance(template.deal.exit_date.value, date) else None
    invested = metric_float(sponsor_invested)
    proceeds = metric_float(sponsor_proceeds)
    if entry_date is None or exit_date is None or invested is None or proceeds is None:
        return []
    return [
        build_metric("sponsor_cash_flow", "Sponsor Cash Flow", -abs(invested), period=entry_date.isoformat(), unit=unit, source_sheet=sponsor_invested.source_sheet, source_cell=sponsor_invested.source_cell, extraction_method="python_calculated", confidence="high"),
        build_metric("sponsor_cash_flow", "Sponsor Cash Flow", proceeds + dividends, period=exit_date.isoformat(), unit=unit, source_sheet=sponsor_proceeds.source_sheet, source_cell=sponsor_proceeds.source_cell, extraction_method="python_calculated", confidence="high"),
    ]


def _calculate_moic(cash_flows) -> float | None:
    if len(cash_flows) < 2:
        return None
    invested = abs(metric_float(cash_flows[0]) or 0.0)
    proceeds = metric_float(cash_flows[-1])
    if invested == 0 or proceeds is None:
        return None
    return proceeds / invested


def _calculate_irr(cash_flows) -> float | None:
    if len(cash_flows) < 2:
        return None
    dates = []
    values = []
    for flow in cash_flows:
        if not isinstance(flow.period, str):
            return None
        dates.append(datetime.fromisoformat(flow.period).date())
        values.append(metric_float(flow))
    if any(value is None for value in values):
        return None
    try:
        return pyxirr.xirr(dates, values)
    except Exception:
        return None


def _net_debt_to_ebitda(net_debt, ebitda):
    result = {}
    for year, debt_metric in net_debt.items():
        result[year] = _calculated_metric("net_debt_to_ebitda", "Net Debt / EBITDA", _safe_div(metric_float(debt_metric), metric_float(ebitda.get(year))), unit="x")
    return result


def _template_sensitivities(model: StandardModel):
    from lbo.engine.template_memo_engine import generate_template_sensitivities

    return generate_template_sensitivities(model)


def _audit_warnings(template, valuation, returns, financials, debt) -> list[str]:
    warnings = []
    for year, margin in template.operating.ebitda_margin.items():
        value = metric_float(margin)
        if value is not None and (value > 0.80 or value < 0):
            warnings.append(f"Suspicious: EBITDA margin in {year} is outside 0%-80%.")
    for year, fcf in template.operating.fcf.items():
        value = _safe_div(metric_float(fcf), metric_float(template.operating.ebitda.get(year)))
        if value is not None and (value > 1.50 or value < -0.50):
            warnings.append(f"Suspicious: FCF conversion in {year} is outside -50%-150%.")
    for year, capex in template.operating.capex.items():
        if metric_float(capex) is not None and metric_float(template.operating.revenue.get(year)) is not None and metric_float(capex) > metric_float(template.operating.revenue.get(year)):
            warnings.append(f"Suspicious: Capex exceeds revenue in {year}.")
    for year, leverage in debt.net_debt_to_ebitda.items():
        value = metric_float(leverage)
        if value is not None and value > 8.0:
            warnings.append(f"Suspicious: Net debt / EBITDA exceeds 8.0x in {year}.")
    irr = metric_float(returns.irr)
    if irr is not None and (irr > 1.0 or irr < -1.0):
        warnings.append("Suspicious: IRR is outside -100% to 100%.")
    moic = metric_float(returns.moic)
    if moic is not None and moic < 0:
        warnings.append("Suspicious: MOIC is below 0.")
    entry_multiple = metric_float(valuation.entry_multiple)
    exit_multiple = metric_float(valuation.exit_multiple)
    rationale = str(template.qualitative.exit_rationale.value or "").strip()
    if entry_multiple is not None and exit_multiple is not None and exit_multiple - entry_multiple > 2.0 and not rationale:
        warnings.append("Suspicious: Exit multiple materially exceeds entry multiple without exit rationale.")
    return warnings


def _metric_str(metric) -> str | None:
    return str(metric.value) if metric and metric.value is not None else None


def _first_float(series) -> float | None:
    return metric_float(sorted(series.items())[0][1]) if series else None


def _last_float(series) -> float | None:
    return metric_float(sorted(series.items())[-1][1]) if series else None


def _safe_div(a, b):
    return None if a is None or b in (None, 0) else a / b


def _safe_mul(a, b):
    return None if a is None or b is None else a * b


def _safe_sub(a, b):
    return None if a is None or b is None else a - b


def _safe_add(a, b):
    return None if a is None or b is None else a + b
