from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def example_workbook() -> bytes:
    workbook = Workbook()
    default = workbook.active
    workbook.remove(default)

    for sheet_name in [
        "Output_财务",
        "资产负债表",
        "现金流量表",
        "Output_产能",
        "回报测算-EVEBITDA（核心假设）",
    ]:
        workbook.create_sheet(sheet_name)

    workbook["Output_财务"]["P4"] = 1941.2009819748844
    workbook["Output_财务"]["K4"] = 1151.488690754277
    workbook["Output_财务"]["L4"] = 1290.0069
    workbook["Output_财务"]["M4"] = 1429.2017
    workbook["Output_财务"]["N4"] = 1573.4187
    workbook["Output_财务"]["O4"] = 1740.8288
    workbook["Output_财务"]["P96"] = 302.50123053446566
    workbook["Output_财务"]["K96"] = 131.26852833687414
    workbook["Output_财务"]["L96"] = 154.3358
    workbook["Output_财务"]["M96"] = 190.9088
    workbook["Output_财务"]["N96"] = 225.5222
    workbook["Output_财务"]["O96"] = 261.9912

    workbook["资产负债表"]["P87"] = -254.40379986948815
    workbook["资产负债表"]["Q87"] = -212.49920600099574
    workbook["资产负债表"]["R87"] = -151.68032766494616
    workbook["资产负债表"]["S87"] = -40.61004012678342
    workbook["资产负债表"]["T87"] = 106.96170401207013

    workbook["Output_产能"]["K6"] = 17089.000491903218
    workbook["Output_产能"]["L6"] = 17759.10054109354
    workbook["Output_产能"]["M6"] = 18496.210595202894
    workbook["Output_产能"]["N6"] = 19307.031654723185
    workbook["Output_产能"]["O6"] = 20198.934820195504
    workbook["Output_产能"]["P6"] = 21180.028302215054

    workbook["现金流量表"]["P26"] = 10.026264529263258
    workbook["现金流量表"]["Q26"] = 28.818878336049565
    workbook["现金流量表"]["R26"] = 79.07028753816275
    workbook["现金流量表"]["S26"] = 115.57174413885355
    workbook["现金流量表"]["T26"] = 146.1074630147732

    returns = workbook["回报测算-EVEBITDA（核心假设）"]
    returns["G19"] = 1130
    returns["R89"] = 3025.012305344657
    returns["G103"] = 3.469442322760885
    returns["G104"] = 0.2823092043399811

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.fixture()
def invalid_workbook() -> bytes:
    return b"not an xlsx file"
