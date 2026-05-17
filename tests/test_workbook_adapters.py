from __future__ import annotations

from pathlib import Path

import pytest

from lbo.adapters import (
    ChineseCompactLBOAdapter,
    DragonDetailedLBOAdapter,
    GenericLBOAdapter,
    StarbucksProjectSundayAdapter,
    detect_best_adapter,
)
from lbo.io.workbook_loader import WorkbookLoadError, load_workbook


DRAGON_PATH = Path("examples/CPE 龙岛竹项目_财务模型_20260317.xlsx")
SPARK_PATH = Path(
    r"C:\Users\macon\work\【投资组】股权基金项目\2025年\施尔丰 KKR 蒋鹏飞\施尔丰项目材料\施尔丰项目材料-中文版\2.2 Project Spark - Financial Model_vS_vCN.xlsx"
)
SUNDAY_PATH = Path(r"C:\Users\macon\code\starbucks\Project Sunday_Financial Model_Full Version_vS.xlsx")


def _adapters():
    return [DragonDetailedLBOAdapter(), ChineseCompactLBOAdapter(), StarbucksProjectSundayAdapter(), GenericLBOAdapter()]


def test_dragon_detailed_adapter_detection_and_sample_values() -> None:
    if not DRAGON_PATH.exists():
        pytest.skip("Dragon fixture workbook not available")
    loaded = load_workbook(DRAGON_PATH)
    match = detect_best_adapter(loaded.workbook, _adapters())
    assert match.template_id == "dragon_detailed_lbo"

    model = DragonDetailedLBOAdapter().extract(loaded.workbook, str(DRAGON_PATH))
    assert model.valuation.entry_ev.value == pytest.approx(1130)
    assert model.valuation.entry_ebitda.value == pytest.approx(131.2685)
    assert model.valuation.entry_multiple.value == pytest.approx(8.6083)
    assert model.valuation.exit_multiple.value == pytest.approx(10.0)
    assert str(model.valuation.exit_date.value) == "2030-12-31"
    assert model.valuation.exit_ev.value == pytest.approx(3025.0123)
    assert model.returns.moic.value == pytest.approx(3.4694, abs=0.0001)
    assert model.returns.irr.value == pytest.approx(0.282309, abs=0.000001)
    assert model.metadata.excel_errors


def test_chinese_compact_adapter_detection_and_sample_values() -> None:
    if not SPARK_PATH.exists():
        pytest.skip("Spark fixture workbook not available")
    loaded = load_workbook(SPARK_PATH)
    match = detect_best_adapter(loaded.workbook, _adapters())
    assert match.template_id == "chinese_compact_lbo"

    model = ChineseCompactLBOAdapter().extract(loaded.workbook, str(SPARK_PATH))
    assert model.metadata.project_name == "Spark项目"
    assert model.valuation.entry_ebitda.value == pytest.approx(22.4323, abs=0.0001)
    assert model.valuation.entry_multiple.value == pytest.approx(12.9)
    assert model.valuation.entry_ev.value == pytest.approx(289.3772)
    assert model.valuation.entry_equity_value.value == pytest.approx(282.8050)
    assert model.financials.revenue[2028].value == pytest.approx(179.9, abs=0.1)
    assert model.financials.ebitda[2028].value == pytest.approx(50.24, abs=0.1)
    assert model.financials.fcf[2028].value == pytest.approx(27.86, abs=0.1)
    assert len(model.sensitivities) >= 3
    assert model.returns.irr is None
    assert "No single base case found; extracted scenario matrix only." in model.metadata.warnings


def test_starbucks_adapter_encrypted_loading_and_sample_values() -> None:
    if not SUNDAY_PATH.exists():
        pytest.skip("Project Sunday fixture workbook not available")
    with pytest.raises(WorkbookLoadError) as exc:
        load_workbook(SUNDAY_PATH)
    assert exc.value.code == "encrypted_password_required"

    loaded = load_workbook(SUNDAY_PATH, password_map={"Project Sunday": "Sunday2025!"})
    assert loaded.encrypted
    match = detect_best_adapter(loaded.workbook, _adapters())
    assert match.template_id == "starbucks_project_sunday"

    model = StarbucksProjectSundayAdapter().extract(loaded.workbook, str(SUNDAY_PATH))
    assert "Project Sunday" in model.metadata.project_name
    assert model.returns.irr.value == pytest.approx(0.22684, abs=0.000001)
    assert model.returns.moic.value == pytest.approx(3.3917, abs=0.0001)
    assert model.returns.net_gain.value == pytest.approx(4522.981, abs=0.01)
    assert str(model.valuation.entry_date.value) == "2026-03-31"
    assert str(model.valuation.exit_date.value) == "2032-03-31"
    assert model.valuation.entry_equity_value.value == pytest.approx(4224.4087)
    assert model.returns.sponsor_equity_invested.value == pytest.approx(1891.0928)
    assert model.valuation.entry_ev.value == pytest.approx(3924.4087)
    assert model.valuation.exit_ev.value == pytest.approx(9745.858, abs=0.01)
    assert model.valuation.exit_equity_value.value == pytest.approx(10045.858, abs=0.01)
    assert model.returns.sponsor_cash_flows
    assert model.debt.net_debt
