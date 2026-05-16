from __future__ import annotations

import pytest

from lbo.io.config import load_sheet_aliases
from lbo.io.excel_loader import ExcelLoader, WorkbookLoadError
from lbo.io.sheet_detector import detect_core_sheets


def test_loader_lists_sheets(example_workbook) -> None:
    with ExcelLoader(example_workbook) as loader:
        sheets = loader.list_sheets()

    assert "Output_财务" in sheets
    assert "资产负债表" in sheets
    assert "回报测算-EVEBITDA（核心假设）" in sheets


def test_detect_core_sheets(example_workbook) -> None:
    with ExcelLoader(example_workbook) as loader:
        core_sheets = detect_core_sheets(loader.list_sheets(), load_sheet_aliases())

    assert core_sheets.financial_output == "Output_财务"
    assert core_sheets.balance_sheet == "资产负债表"
    assert core_sheets.cash_flow == "现金流量表"
    assert core_sheets.capex == "Output_产能"
    assert core_sheets.return_model == "回报测算-EVEBITDA（核心假设）"
    assert core_sheets.missing_roles == []


def test_read_scalar_cell(example_workbook) -> None:
    with ExcelLoader(example_workbook) as loader:
        irr = loader.read_cell("回报测算-EVEBITDA（核心假设）", "G104")
        moic = loader.read_cell("回报测算-EVEBITDA（核心假设）", "G103")

    assert irr == pytest.approx(0.2823092043)
    assert moic == pytest.approx(3.4694423228)


def test_unreadable_workbook_has_clear_error(invalid_workbook) -> None:
    with pytest.raises(WorkbookLoadError, match="Unable to load workbook"):
        with ExcelLoader(invalid_workbook) as loader:
            loader.list_sheets()
