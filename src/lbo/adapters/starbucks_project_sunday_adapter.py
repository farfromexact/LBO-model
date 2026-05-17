from __future__ import annotations

from lbo.adapters.base_adapter import (
    BaseWorkbookAdapter,
    build_metric,
    collect_excel_errors,
    get_openpyxl_workbook,
    row_value,
    sheet_match,
)
from lbo.schemas.standard_model import DebtSummary, FinancialSeries, ModelMetadata, ReturnSummary, StandardModel, ValuationSummary


RETURN_SHEET = "Return"
CONSOLIDATED_SHEET = "Consolidated Statements"
DEBT_SHEET = "Debt Schedule"


class StarbucksProjectSundayAdapter(BaseWorkbookAdapter):
    template_id = "starbucks_project_sunday"
    adapter_name = "Starbucks Project Sunday Adapter"
    fingerprint_sheets = [
        RETURN_SHEET,
        CONSOLIDATED_SHEET,
        DEBT_SHEET,
        "Capex and D&A",
        "Overall P&L (USD)",
        "Store P&L (USD)",
        "Store P&L (RMB)",
        "Tier 1 City",
        "Tier 2 City",
        "Tier 3 City and Below",
        "Special Locations",
    ]

    def can_handle(self, workbook):
        return sheet_match(workbook, self.fingerprint_sheets, self.adapter_name, self.template_id)

    def extract(self, workbook, source_file: str = "uploaded_workbook.xlsx") -> StandardModel:
        wb = get_openpyxl_workbook(workbook)
        ret = wb[RETURN_SHEET]
        statements = wb[CONSOLIDATED_SHEET]
        debt_sheet = wb[DEBT_SHEET]
        excel_errors = collect_excel_errors(wb)
        warnings = ["Workbook contains Excel errors; valid values were still extracted."] if excel_errors else []
        financials = FinancialSeries(
            revenue=_statement_series(statements, 12, "revenue", "Total Revenue"),
            ebitda=_statement_series(statements, 18, "ebitda", "Adj. EBITDA"),
            ebit=_statement_series(statements, 27, "ebit", "Adj. EBIT"),
            capex=_statement_series(statements, 110, "capex", "Capex"),
            fcf=_statement_series(statements, 113, "fcf", "Free Cash Flow"),
            net_debt=_debt_series(debt_sheet, 124, "net_debt", "Net Debt"),
        )
        debt = DebtSummary(
            net_debt=_debt_series(debt_sheet, 124, "net_debt", "Net Debt"),
            net_debt_to_ebitda=_debt_series(debt_sheet, 128, "net_debt_to_ebitda", "Net Debt / Adj. EBITDA", unit="x"),
            gross_debt=_debt_series(debt_sheet, 129, "gross_debt_to_ebitda", "Gross Debt / Adj. EBITDA", unit="x"),
        )
        valuation = ValuationSummary(
            entry_date=row_value(ret, 7, 6, "entry_date", "Entry Date"),
            exit_date=row_value(ret, 8, 6, "exit_date", "Exit Date"),
            entry_equity_value=row_value(ret, 11, 6, "entry_equity_value", "Entry Equity Value", unit="USD mm"),
            entry_ev=row_value(ret, 16, 6, "entry_ev", "Enterprise Value", unit="USD mm"),
            entry_multiple=row_value(ret, 22, 6, "entry_multiple", "Entry EV/Adj. EBITDA", unit="x"),
            exit_ev=row_value(ret, 34, 16, "exit_ev", "Enterprise Value at Exit", unit="USD mm"),
            exit_equity_value=row_value(ret, 37, 16, "exit_equity_value", "Equity Value at Exit", unit="USD mm"),
            exit_multiple=row_value(ret, 33, 16, "exit_multiple", "Exit EV/Adj. EBITDA", unit="x"),
            exit_ebitda=row_value(ret, 32, 16, "exit_ebitda", "Exit Adj. EBITDA", unit="USD mm"),
        )
        returns = ReturnSummary(
            irr=row_value(ret, 42, 16, "irr", "Boyu IRR", unit="%"),
            moic=row_value(ret, 43, 16, "moic", "Boyu MoC", unit="x"),
            net_gain=row_value(ret, 44, 16, "net_gain", "Boyu Net Gain", unit="USD mm"),
            sponsor_equity_invested=row_value(ret, 19, 6, "sponsor_equity_invested", "Boyu Consortium Equity Cost", unit="USD mm"),
            sponsor_exit_proceeds=row_value(ret, 41, 16, "sponsor_exit_proceeds", "Boyu Exit Cash Flow", unit="USD mm"),
            sponsor_cash_flows=_cash_flows(ret),
        )
        metadata = ModelMetadata(
            source_file=source_file,
            detected_template_id=self.template_id,
            adapter_name=self.adapter_name,
            confidence_score=self.can_handle(wb).confidence_score,
            project_name=str(ret["C3"].value) if ret["C3"].value else None,
            currency="USD",
            unit="mm",
            warnings=warnings,
            missing_fields=[],
            excel_errors=excel_errors,
        )
        return StandardModel(metadata=metadata, financials=financials, valuation=valuation, returns=returns, debt=debt)


def _statement_series(sheet, row: int, metric_id: str, label: str) -> dict[int, object]:
    result = {}
    for col in range(1, sheet.max_column + 1):
        year = sheet.cell(6, col).value or sheet.cell(7, col).value
        value = sheet.cell(row, col).value
        if isinstance(year, (int, float)) and isinstance(value, (int, float)):
            result[int(year)] = build_metric(
                metric_id=metric_id,
                label=label,
                value=float(value),
                period=int(year),
                unit="USD mm",
                source_sheet=sheet.title,
                source_cell=sheet.cell(row, col).coordinate,
                extraction_method="fixed_cell",
                confidence="high",
            )
    return result


def _debt_series(sheet, row: int, metric_id: str, label: str, unit: str = "USD mm") -> dict[int, object]:
    result = {}
    for col in range(1, sheet.max_column + 1):
        year = sheet.cell(44, col).value or sheet.cell(6, col).value
        value = sheet.cell(row, col).value
        if isinstance(year, (int, float)) and isinstance(value, (int, float)):
            result[int(year)] = build_metric(
                metric_id=metric_id,
                label=label,
                value=float(value),
                period=int(year),
                unit=unit,
                source_sheet=sheet.title,
                source_cell=sheet.cell(row, col).coordinate,
                extraction_method="fixed_cell",
                confidence="high",
            )
    return result


def _cash_flows(sheet) -> list[object]:
    flows = []
    for col in range(8, 17):
        value = sheet.cell(41, col).value
        period = sheet.cell(31, col).value or sheet.cell(8, col).value
        if isinstance(value, (int, float)):
            flows.append(
                build_metric(
                    metric_id="sponsor_cash_flow",
                    label="Boyu Cash Flow",
                    value=float(value),
                    period=period,
                    unit="USD mm",
                    source_sheet=sheet.title,
                    source_cell=sheet.cell(41, col).coordinate,
                    extraction_method="fixed_cell",
                    confidence="high",
                )
            )
    return flows
