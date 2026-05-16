from __future__ import annotations

from typing import Any

from lbo.registry.metric_registry import MetricRegistry, MetricRegistryEntry
from lbo.schemas.models import MetricValue, PythonEngineOutputs, ReconciliationItem, ReturnBridge, SourceRef


def reconcile_metric(
    metric_id: str,
    excel_value: Any,
    python_value: Any,
    tolerance: float,
) -> dict[str, float | str | None]:
    if not isinstance(excel_value, (int, float)) or not isinstance(python_value, (int, float)):
        return {
            "variance": None,
            "variance_pct": None,
            "status": "Pending",
        }

    variance = float(python_value - excel_value)
    denominator = abs(float(excel_value))
    variance_pct = None if denominator == 0 else variance / denominator
    abs_variance_pct = abs(variance_pct) if variance_pct is not None else abs(variance)

    if abs_variance_pct <= tolerance:
        status = "OK"
    elif abs_variance_pct <= tolerance * 3:
        status = "Warning"
    else:
        status = "Critical"

    return {
        "variance": variance,
        "variance_pct": variance_pct,
        "status": status,
    }


def reconcile_all(
    excel_snapshot: dict[str, MetricValue],
    python_result: PythonEngineOutputs | None,
    registry: MetricRegistry,
    return_bridge: ReturnBridge | None = None,
) -> list[ReconciliationItem]:
    rows: list[ReconciliationItem] = []
    for metric_id, entry in registry.items():
        excel_metric = excel_snapshot.get(metric_id)
        excel_value = excel_metric.value if excel_metric is not None else None
        python_value = _python_value_for_metric(metric_id, python_result, return_bridge)
        result = reconcile_metric(metric_id, excel_value, python_value, entry.tolerance)
        source = _source_for(entry, excel_metric)

        rows.append(
            ReconciliationItem(
                metric_key=entry.metric_id,
                metric_name=entry.display_name,
                period=entry.period,
                excel_value=excel_value,
                python_value=python_value,
                variance=result["variance"],
                variance_pct=result["variance_pct"],
                tolerance=entry.tolerance,
                status=result["status"],
                unit=entry.unit,
                scale=entry.scale,
                sign_convention=entry.sign_convention,
                required_for_dashboard=entry.required_for_dashboard,
                source_sheet=entry.source_sheet,
                source_cell=entry.source_cell,
                source=source,
            )
        )
    return rows


def reconciliation_rows(snapshot) -> list[dict[str, object]]:
    return [
        {
            "Metric": item.metric_name,
            "Period": item.period,
            "Excel Value": item.excel_value,
            "Python Value": item.python_value,
            "Variance": item.variance,
            "Variance %": item.variance_pct,
            "Tolerance": item.tolerance,
            "Status": item.status,
            "Unit": item.unit,
            "Source Sheet": item.source_sheet,
            "Source Cell": item.source_cell,
        }
        for item in snapshot.reconciliation
    ]


def _python_value_for_metric(
    metric_id: str,
    python_result: PythonEngineOutputs | None,
    return_bridge: ReturnBridge | None,
) -> float | None:
    bridge_mapping = {}
    if return_bridge is not None:
        bridge_mapping = {
            "entry_ev": return_bridge.entry_ev,
            "entry_equity_value": return_bridge.entry_equity_value,
            "sponsor_equity_invested": -return_bridge.sponsor_equity_invested,
            "exit_ev": return_bridge.exit_ev,
            "exit_equity_value": return_bridge.exit_equity_value,
            "sponsor_proceeds": return_bridge.sponsor_proceeds,
            "irr": return_bridge.irr,
            "moic": return_bridge.moic,
        }
    if metric_id in bridge_mapping:
        return bridge_mapping[metric_id]

    engine_mapping = {}
    if python_result is not None:
        engine_mapping = {
            "net_debt": python_result.ending_net_debt,
        }
    return engine_mapping.get(metric_id)


def _source_for(entry: MetricRegistryEntry, excel_metric: MetricValue | None) -> SourceRef:
    if excel_metric is not None:
        return excel_metric.source
    return SourceRef(
        workbook="",
        sheet=entry.source_sheet,
        range=entry.source_cell,
        label=entry.display_name,
        unit=entry.unit,
        extraction_method="metric_registry",
    )
