from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure

from lbo.schemas.models import DebtModel, FinancialStatementTable, SensitivityTable, ValueCreationBridge


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
    measure = ["absolute", "relative", "relative", "relative", "relative", "relative", "total"]
    x = [
        "Entry Equity Value",
        "EBITDA Growth",
        "Multiple Expansion / Contraction",
        "Deleveraging",
        "Dividends / Cash Distribution",
        "Tax Leakage",
        "Exit Equity Value",
    ]
    y = [
        bridge.entry_equity_value,
        bridge.ebitda_growth,
        bridge.multiple_expansion,
        bridge.deleveraging,
        bridge.dividends,
        bridge.tax_leakage,
        bridge.exit_equity_value,
    ]
    figure = go.Figure(
        go.Waterfall(
            name="Value Creation",
            orientation="v",
            measure=measure,
            x=x,
            y=y,
            connector={"line": {"color": "rgba(120,120,120,0.5)"}},
        )
    )
    figure.update_layout(
        title="Value Creation Bridge",
        yaxis_title="Equity Value",
        xaxis_title=None,
        showlegend=False,
    )
    return figure


def debt_paydown_waterfall(debt_model: DebtModel) -> Figure:
    if not debt_model.periods:
        return go.Figure()

    opening_debt = debt_model.periods[0].opening_debt
    mandatory_repayment = sum(period.repayment for period in debt_model.periods)
    ending_debt = debt_model.periods[-1].ending_debt
    figure = go.Figure(
        go.Waterfall(
            name="Debt Paydown",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Opening Debt", "New Debt", "Mandatory Repayment", "Cash Sweep", "Ending Debt"],
            y=[opening_debt, 0.0, -mandatory_repayment, 0.0, ending_debt],
            connector={"line": {"color": "rgba(120,120,120,0.5)"}},
        )
    )
    figure.update_layout(
        title="Debt Paydown Waterfall",
        yaxis_title="Debt",
        xaxis_title=None,
        showlegend=False,
    )
    return figure


def operating_trend_chart(tables: dict[str, FinancialStatementTable]) -> Figure:
    rows: list[dict[str, object]] = []
    for key, name in [("revenue", "Revenue"), ("ebitda", "EBITDA"), ("cash_flow", "FCF / Cash Flow")]:
        table = tables.get(key)
        if table is None:
            continue
        values = next(iter(table.rows.values()))
        for period, value in zip(table.periods, values):
            rows.append({"Period": period, "Metric": name, "Value": value})

    data = pd.DataFrame(rows)
    figure = px.line(data, x="Period", y="Value", color="Metric", markers=True, title="Revenue / EBITDA / FCF Trend")
    figure.update_layout(yaxis_title="Value", xaxis_title=None)
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
