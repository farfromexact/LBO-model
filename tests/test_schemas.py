from __future__ import annotations

import pytest
from pydantic import ValidationError

from lbo.schemas import (
    CoreSheets,
    FinancialStatementTable,
    MetricValue,
    ModelSnapshot,
    ReconciliationItem,
    ReturnModel,
    SourceRef,
)


def source_ref() -> SourceRef:
    return SourceRef(
        workbook="model.xlsx",
        sheet="Output_财务",
        range="P4",
        label="Revenue",
        unit="USD mm",
        extraction_method="configured_cell",
    )


def test_metric_requires_source_ref() -> None:
    with pytest.raises(ValidationError):
        MetricValue(key="revenue", display_name="Revenue", value=1, source=None)  # type: ignore[arg-type]


def test_model_snapshot_validates_traceable_metrics() -> None:
    metric = MetricValue(
        key="revenue",
        display_name="Revenue",
        value=100,
        period="2030",
        unit="USD mm",
        source=source_ref(),
    )
    snapshot = ModelSnapshot(
        workbook_name="model.xlsx",
        scenario="Base",
        sheets=["Output_财务"],
        core_sheets=CoreSheets(financial_output="Output_财务"),
        metrics={"revenue": metric},
        tables={},
        return_model=ReturnModel(),
        reconciliation=[
            ReconciliationItem(
                metric_key="revenue",
                metric_name="Revenue",
                excel_value=100,
                python_value=None,
                source=source_ref(),
            )
        ],
    )

    assert snapshot.metrics["revenue"].source.display == "Output_财务!P4"
    assert snapshot.reconciliation[0].status == "Pending Python engine"


def test_financial_statement_table_width_validation() -> None:
    with pytest.raises(ValidationError):
        FinancialStatementTable(
            name="Revenue",
            periods=["2029", "2030"],
            rows={"Revenue": [100]},
            source=source_ref(),
        )

