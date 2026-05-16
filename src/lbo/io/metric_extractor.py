from __future__ import annotations

from typing import Any

from lbo.io.excel_loader import ExcelLoader
from lbo.schemas.models import CoreSheets, FinancialStatementTable, MetricValue, SourceRef


def extract_metrics(
    loader: ExcelLoader,
    core_sheets: CoreSheets,
    metrics_config: dict[str, Any],
) -> dict[str, MetricValue]:
    extracted: dict[str, MetricValue] = {}
    for key, config in metrics_config.get("metrics", {}).items():
        sheet_name = core_sheets.sheet_for_role(config["sheet_role"])
        source = SourceRef(
            workbook=loader.workbook_name,
            sheet=sheet_name,
            range=config["cell"],
            label=config.get("label"),
            unit=config.get("unit"),
            extraction_method=config.get("extraction_method", "configured_cell"),
        )

        if sheet_name is None:
            extracted[key] = MetricValue.missing(
                key=key,
                display_name=config["display_name"],
                period=config.get("period"),
                unit=config.get("unit"),
                source=source,
                missing_reason=f"Missing sheet role: {config['sheet_role']}",
            )
            continue

        value = loader.read_cell(sheet_name, config["cell"])
        extracted[key] = MetricValue(
            key=key,
            display_name=config["display_name"],
            value=value,
            period=config.get("period"),
            unit=config.get("unit"),
            source=source,
        )

    return extracted


def extract_tables(
    loader: ExcelLoader,
    core_sheets: CoreSheets,
    metrics_config: dict[str, Any],
) -> dict[str, FinancialStatementTable]:
    tables: dict[str, FinancialStatementTable] = {}
    for key, config in metrics_config.get("tables", {}).items():
        sheet_name = core_sheets.sheet_for_role(config["sheet_role"])
        source = SourceRef(
            workbook=loader.workbook_name,
            sheet=sheet_name,
            range=config["range"],
            label=config["display_name"],
            unit=config.get("unit"),
            extraction_method="configured_range",
        )
        periods = [str(period) for period in config["periods"]]

        if sheet_name is None:
            values = [None for _ in periods]
        else:
            values = loader.read_flat_range(sheet_name, config["range"])

        tables[key] = FinancialStatementTable(
            name=config["display_name"],
            periods=periods,
            rows={config["display_name"]: values},
            unit=config.get("unit"),
            source=source,
        )

    return tables

