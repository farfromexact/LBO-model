from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from lbo.io.config import CONFIG_DIR, load_yaml


class MetricRegistryEntry(BaseModel):
    metric_id: str
    display_name: str
    category: str
    period: str
    source_sheet: str
    source_cell: str
    unit: str
    scale: float = Field(gt=0)
    sign_convention: str
    tolerance: float = Field(ge=0)
    required_for_dashboard: bool = False

    @property
    def source_display(self) -> str:
        return f"{self.source_sheet}!{self.source_cell}"


MetricRegistry = dict[str, MetricRegistryEntry]


def load_metric_registry(path: str | Path | None = None) -> MetricRegistry:
    data = load_yaml(path or CONFIG_DIR / "metric_registry.yaml")
    entries = [MetricRegistryEntry(**item) for item in data.get("metrics", [])]
    registry = {entry.metric_id: entry for entry in entries}
    validate_registry(registry)
    return registry


def validate_registry(registry: MetricRegistry) -> None:
    if not registry:
        raise ValueError("Metric registry is empty")

    if len(registry) != len(set(registry)):
        raise ValueError("Metric registry contains duplicate metric IDs")

    for metric_id, entry in registry.items():
        if metric_id != entry.metric_id:
            raise ValueError(f"Registry key '{metric_id}' does not match entry metric_id '{entry.metric_id}'")
        if not entry.source_sheet or not entry.source_cell:
            raise ValueError(f"Metric '{metric_id}' is missing source sheet/cell")
        if entry.tolerance < 0:
            raise ValueError(f"Metric '{metric_id}' has negative tolerance")


def get_required_dashboard_metrics(registry: MetricRegistry | None = None) -> list[MetricRegistryEntry]:
    registry = registry or load_metric_registry()
    return [entry for entry in registry.values() if entry.required_for_dashboard]


def get_metric_source(metric_id: str, registry: MetricRegistry | None = None) -> dict[str, str]:
    registry = registry or load_metric_registry()
    if metric_id not in registry:
        raise KeyError(f"Metric '{metric_id}' is not in the registry")
    entry = registry[metric_id]
    return {"source_sheet": entry.source_sheet, "source_cell": entry.source_cell}

