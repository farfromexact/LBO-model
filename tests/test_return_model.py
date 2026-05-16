from __future__ import annotations

import pytest

from lbo.engine import build_snapshot


def test_return_model_reconciles_excel_sponsor_cash_flows(example_workbook) -> None:
    snapshot = build_snapshot(example_workbook)
    bridge = snapshot.return_model.bridge

    assert bridge is not None
    assert bridge.entry_ev == pytest.approx(1130)
    assert bridge.entry_equity_value == pytest.approx(695.7298970542984)
    assert bridge.sponsor_equity_invested == pytest.approx(552.4331520544102)
    assert bridge.exit_ev == pytest.approx(3025.012305344657)
    assert bridge.exit_equity_value == pytest.approx(3310.0814723715002)
    assert bridge.sponsor_proceeds == pytest.approx(1916.6349582337702)
    assert bridge.moic == pytest.approx(snapshot.metrics["moic"].value)
    assert bridge.irr == pytest.approx(snapshot.metrics["irr"].value)
    assert [cash_flow.amount for cash_flow in bridge.sponsor_cash_flows] == pytest.approx(
        [-552.4331520544102, 0, 0, 0, 0, 0, 1916.6349582337702]
    )

    for metric_id in [
        "entry_ev",
        "entry_equity_value",
        "sponsor_equity_invested",
        "exit_ev",
        "exit_equity_value",
        "sponsor_proceeds",
        "moic",
        "irr",
    ]:
        assert snapshot.reconciliation_by_metric[metric_id].status == "OK"

