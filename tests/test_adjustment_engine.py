from __future__ import annotations

import pytest

from lbo.adapters import DragonDetailedLBOAdapter
from lbo.engine.adjustment_engine import AdjustmentInputs, build_default_adjustments, run_adjusted_return_model
from lbo.io.workbook_loader import load_workbook


def test_adjusted_return_model_uses_standard_model_only() -> None:
    path = "examples/CPE 龙岛竹项目_财务模型_20260317.xlsx"
    model = DragonDetailedLBOAdapter().extract(load_workbook(path).workbook, path)
    defaults = build_default_adjustments(model)

    result = run_adjusted_return_model(model, defaults)

    assert result.exit_ev == pytest.approx(model.valuation.exit_ev.value)
    assert result.moic is not None
    assert result.irr is not None
    assert result.cash_flows


def test_adjusted_return_model_marks_missing_inputs() -> None:
    path = "examples/CPE 龙岛竹项目_财务模型_20260317.xlsx"
    model = DragonDetailedLBOAdapter().extract(load_workbook(path).workbook, path)

    result = run_adjusted_return_model(
        model,
        AdjustmentInputs(entry_multiple=None, exit_multiple=None, exit_net_debt=None, sponsor_ownership=None),
    )

    assert result.moic is None
    assert result.warnings
