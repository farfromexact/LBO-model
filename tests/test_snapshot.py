from __future__ import annotations

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
    assert len(snapshot.reconciliation) == len(expected)
