from __future__ import annotations

from pathlib import Path

from lbo.engine.assumptions import load_scenario_defaults
from lbo.engine.python_engine import run_python_engine
from lbo.analytics.reconciliation import reconcile_all
from lbo.io.config import load_metrics_config, load_sheet_aliases
from lbo.io.excel_loader import ExcelLoader, WorkbookInput
from lbo.io.metric_extractor import extract_metrics, extract_tables
from lbo.io.sheet_detector import detect_core_sheets
from lbo.registry import load_metric_registry
from lbo.schemas.models import EngineAssumptions, ModelSnapshot, ReturnModel, ScenarioName


def build_snapshot(
    workbook_file: WorkbookInput,
    scenario: ScenarioName = "Base",
    engine_assumptions: EngineAssumptions | None = None,
    sheet_aliases_path: str | Path | None = None,
    metrics_config_path: str | Path | None = None,
) -> ModelSnapshot:
    aliases_config = load_sheet_aliases(sheet_aliases_path)
    metrics_config = load_metrics_config(metrics_config_path)
    metric_registry = load_metric_registry()

    with ExcelLoader(workbook_file, data_only=True) as loader:
        sheets = loader.list_sheets()
        core_sheets = detect_core_sheets(sheets, aliases_config)
        metrics = extract_metrics(loader, core_sheets, metrics_config)
        tables = extract_tables(loader, core_sheets, metrics_config)
        assumptions = engine_assumptions or load_scenario_defaults(scenario)
        python_engine = run_python_engine(metrics, tables, assumptions)

        return_model = ReturnModel(
            irr=metrics.get("irr"),
            moic=metrics.get("moic"),
            entry_ev=metrics.get("entry_ev"),
            exit_ev=metrics.get("exit_ev"),
            python_outputs=python_engine,
        )

        reconciliation = reconcile_all(metrics, python_engine, metric_registry)

        return ModelSnapshot(
            workbook_name=loader.workbook_name,
            scenario=scenario,
            sheets=sheets,
            core_sheets=core_sheets,
            metrics=metrics,
            tables=tables,
            engine_assumptions=assumptions,
            python_engine=python_engine,
            return_model=return_model,
            reconciliation=reconciliation,
        )
