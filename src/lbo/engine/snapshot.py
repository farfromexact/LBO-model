from __future__ import annotations

from pathlib import Path

from lbo.engine.assumptions import load_scenario_defaults
from lbo.engine.python_engine import run_python_engine
from lbo.io.config import load_metrics_config, load_sheet_aliases
from lbo.io.excel_loader import ExcelLoader, WorkbookInput
from lbo.io.metric_extractor import extract_metrics, extract_tables
from lbo.io.sheet_detector import detect_core_sheets
from lbo.schemas.models import EngineAssumptions, ModelSnapshot, ReconciliationItem, ReturnModel, ScenarioName


def build_snapshot(
    workbook_file: WorkbookInput,
    scenario: ScenarioName = "Base",
    engine_assumptions: EngineAssumptions | None = None,
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
        assumptions = engine_assumptions or load_scenario_defaults(scenario)
        python_engine = run_python_engine(metrics, tables, assumptions)

        return_model = ReturnModel(
            irr=metrics.get("irr"),
            moic=metrics.get("moic"),
            entry_ev=metrics.get("entry_ev"),
            exit_ev=metrics.get("exit_ev"),
            python_outputs=python_engine,
        )

        reconciliation = [
            ReconciliationItem(
                metric_key=metric.key,
                metric_name=metric.display_name,
                excel_value=metric.value,
                python_value=_python_value_for_metric(metric.key, python_engine),
                variance=_variance(metric.value, _python_value_for_metric(metric.key, python_engine)),
                status="Calculated by Python engine"
                if _python_value_for_metric(metric.key, python_engine) is not None
                else "Pending Python engine",
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
            engine_assumptions=assumptions,
            python_engine=python_engine,
            return_model=return_model,
            reconciliation=reconciliation,
        )


def _python_value_for_metric(key: str, python_engine):
    mapping = {
        "entry_ev": python_engine.entry_ev,
        "exit_ev": python_engine.exit_ev,
        "irr": python_engine.irr,
        "moic": python_engine.moic,
        "net_debt": python_engine.ending_net_debt,
    }
    return mapping.get(key)


def _variance(excel_value, python_value) -> float | None:
    if not isinstance(excel_value, (int, float)) or not isinstance(python_value, (int, float)):
        return None
    return float(python_value - excel_value)
