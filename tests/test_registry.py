from __future__ import annotations

from lbo.registry import get_metric_source, get_required_dashboard_metrics, load_metric_registry, validate_registry


def test_load_metric_registry() -> None:
    registry = load_metric_registry()

    validate_registry(registry)
    assert "irr" in registry
    assert registry["irr"].tolerance > 0
    assert registry["exit_ev"].source_cell == "R89"


def test_required_dashboard_metrics() -> None:
    required = get_required_dashboard_metrics(load_metric_registry())

    assert {entry.metric_id for entry in required} >= {"irr", "moic", "net_debt"}


def test_get_metric_source() -> None:
    source = get_metric_source("moic", load_metric_registry())

    assert source["source_cell"] == "G103"

