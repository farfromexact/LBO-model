from __future__ import annotations

import pytest

from lbo.engine import build_snapshot


def test_build_snapshot_contains_v1_metrics(example_workbook) -> None:
    snapshot = build_snapshot(example_workbook)

    expected = {
        "revenue",
        "ebitda",
        "net_debt",
        "capex",
        "cash_flow",
        "entry_ev",
        "exit_ev",
        "irr",
        "moic",
    }
    assert set(snapshot.metrics) == expected
    assert all(metric.source is not None for metric in snapshot.metrics.values())
    assert snapshot.metrics["revenue"].value is not None
    assert snapshot.metrics["irr"].value is not None
    assert snapshot.engine_assumptions is not None
    assert snapshot.python_engine is not None
    assert snapshot.python_engine.moic is not None
    assert snapshot.python_engine.exit_ev == pytest.approx(snapshot.metrics["exit_ev"].value, rel=0.001)
    assert snapshot.python_engine.sensitivity.values
    assert len(snapshot.reconciliation) == len(expected)
    assert snapshot.reconciliation_by_metric["irr"].python_value is not None
