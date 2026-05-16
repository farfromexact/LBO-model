from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from lbo.schemas.models import FinancialStatementTable


def metric_line_chart(table: FinancialStatementTable) -> Figure:
    row_name, values = next(iter(table.rows.items()))
    data = pd.DataFrame(
        {
            "Period": table.periods,
            "Value": values,
            "Metric": row_name,
        }
    )
    figure = px.line(
        data,
        x="Period",
        y="Value",
        markers=True,
        title=f"{table.name} Trend",
    )
    figure.update_layout(yaxis_title=table.unit or "Value", xaxis_title=None)
    return figure

