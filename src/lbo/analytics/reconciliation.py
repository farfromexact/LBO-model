from __future__ import annotations

from lbo.schemas.models import ModelSnapshot


def reconciliation_rows(snapshot: ModelSnapshot) -> list[dict[str, object]]:
    return [
        {
            "Metric": item.metric_name,
            "Excel Value": item.excel_value,
            "Python Value": item.python_value,
            "Variance": item.variance,
            "Status": item.status,
            "Source": item.source.display,
            "Label": item.source.label,
        }
        for item in snapshot.reconciliation
    ]

