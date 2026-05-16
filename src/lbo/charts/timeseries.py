from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure

from lbo.schemas.models import FinancialStatementTable, SensitivityTable, ValueCreationBridge


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


def value_creation_bridge_chart(bridge: ValueCreationBridge) -> Figure:
    data = pd.DataFrame(
        {
            "Driver": ["EBITDA Growth", "Multiple Expansion", "Debt Paydown", "Tax Leakage"],
            "Value": [
                bridge.ebitda_growth,
                bridge.multiple_expansion,
                bridge.debt_paydown,
                bridge.tax_leakage,
            ],
        }
    )
    figure = px.bar(data, x="Driver", y="Value", title="Value Creation Bridge")
    figure.update_layout(yaxis_title="Equity value impact", xaxis_title=None)
    return figure


def sensitivity_heatmap(table: SensitivityTable) -> Figure:
    text = [
        ["" if value is None else f"{value:.1%}" for value in row]
        for row in table.values
    ]
    figure = go.Figure(
        data=go.Heatmap(
            z=table.values,
            x=[f"{multiple:.1f}x" for multiple in table.exit_multiples],
            y=[f"{multiple:.1f}x" for multiple in table.entry_multiples],
            text=text,
            texttemplate="%{text}",
            colorscale="RdYlGn",
        )
    )
    figure.update_layout(
        title="IRR Sensitivity",
        xaxis_title="Exit Multiple",
        yaxis_title="Entry Multiple",
    )
    return figure
