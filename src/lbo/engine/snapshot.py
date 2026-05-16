from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from lbo.io.config import load_metrics_config, load_sheet_aliases
from lbo.io.excel_loader import ExcelLoader, WorkbookInput
from lbo.io.metric_extractor import extract_metrics, extract_tables
from lbo.io.sheet_detector import detect_core_sheets
from lbo.schemas.models import ModelSnapshot, ReconciliationItem, ReturnModel, ScenarioName


def build_snapshot(
    workbook_file: WorkbookInput,
    scenario: ScenarioName = "Base",
    sheet_aliases_path: str | Path | None = None,
    metrics_config_path: str | Path | None = None,
) -> ModelSnapshot:
    aliases_config = load_sheet_aliases(sheet_aliases_path)
    metrics_config = load_metrics_config(metrics_config_path)

    with ExcelLoader(workbook_file, data_only=True) as loader:
        sheets = loader.list_sheets()
        core_sheets = detect_core_sheets(sheets, aliases_config)
        metrics = extract_metrics(loader, core_sheets, metrics_config)
        tables = extract_tables(loader, core_sheets, metrics_config)

        return_model = ReturnModel(
            irr=metrics.get("irr"),
            moic=metrics.get("moic"),
            entry_ev=metrics.get("entry_ev"),
            exit_ev=metrics.get("exit_ev"),
        )

        reconciliation = [
            ReconciliationItem(
                metric_key=metric.key,
                metric_name=metric.display_name,
                excel_value=metric.value,
                python_value=None,
                variance=None,
                status="Pending Python engine",
                source=metric.source,
            )
            for metric in metrics.values()
        ]

        return ModelSnapshot(
            workbook_name=loader.workbook_name,
            scenario=scenario,
            sheets=sheets,
            core_sheets=core_sheets,
            metrics=metrics,
            tables=tables,
            return_model=return_model,
            reconciliation=reconciliation,
        )

