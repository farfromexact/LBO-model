from __future__ import annotations

from lbo.analytics import reconcile_metric


def test_reconcile_metric_classifies_pending() -> None:
    result = reconcile_metric("revenue", 100.0, None, 0.01)

    assert result["status"] == "Pending"
    assert result["variance"] is None


def test_reconcile_metric_classifies_ok_warning_critical() -> None:
    assert reconcile_metric("metric", 100.0, 100.5, 0.01)["status"] == "OK"
    assert reconcile_metric("metric", 100.0, 102.0, 0.01)["status"] == "Warning"
    assert reconcile_metric("metric", 100.0, 110.0, 0.01)["status"] == "Critical"

