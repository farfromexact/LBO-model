from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure

from lbo.engine.adjustment_engine import ValueCreationBridgeResult
from lbo.schemas.standard_model import SensitivityMatrix, StandardModel


def operating_trend_chart(model: StandardModel) -> Figure:
    rows: list[dict[str, object]] = []
    for series_name, label in [
        ("revenue", "Revenue"),
        ("ebitda", "EBITDA"),
        ("fcf", "FCF"),
        ("capex", "Capex"),
        ("net_debt", "Net Debt"),
    ]:
        series = getattr(model.financials, series_name)
        if not series:
            continue
        for period, metric in sorted(series.items()):
            if metric.value is not None:
                rows.append({"Period": period, "Metric": label, "Value": metric.value})
    if not rows:
        return _empty_figure("Operating Trend")
    data = pd.DataFrame(rows)
    figure = px.line(data, x="Period", y="Value", color="Metric", markers=True, title="Revenue / EBITDA / FCF / Capex / Net Debt")
    figure.update_layout(xaxis_title=None, yaxis_title=model.metadata.unit or "Value", legend_title_text=None)
    return figure


def sensitivity_heatmap(matrix: SensitivityMatrix) -> Figure:
    text = [[_format_cell(value, matrix.metric) for value in row] for row in matrix.values]
    figure = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=[str(value) for value in matrix.col_values],
            y=[str(value) for value in matrix.row_values],
            text=text,
            texttemplate="%{text}",
            colorscale="RdYlGn",
            reversescale=False,
        )
    )
    figure.update_layout(title=matrix.title, xaxis_title=matrix.col_axis_name, yaxis_title=matrix.row_axis_name)
    return figure


def value_creation_bridge_chart(bridge: ValueCreationBridgeResult) -> Figure:
    values = [
        bridge.entry_equity_value,
        bridge.ebitda_growth,
        bridge.multiple_expansion,
        bridge.deleveraging,
        bridge.dividends,
        bridge.exit_equity_value,
    ]
    if all(value is None for value in values):
        return _empty_figure("Value Creation Bridge")
    figure = go.Figure(
        go.Waterfall(
            name="Value Creation",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "relative", "total"],
            x=["Entry Equity", "EBITDA Growth", "Multiple Expansion", "Deleveraging", "Dividends", "Exit Equity"],
            y=[0 if value is None else value for value in values],
            connector={"line": {"color": "rgba(100,100,100,0.5)"}},
        )
    )
    figure.update_layout(title="Value Creation Bridge", showlegend=False, xaxis_title=None, yaxis_title="Equity Value")
    return figure


def debt_paydown_waterfall(model: StandardModel) -> Figure:
    net_debt = model.debt.net_debt if model.debt else model.financials.net_debt
    if not net_debt or len(net_debt) < 2:
        return _empty_figure("Debt Paydown Waterfall")
    periods = sorted(net_debt.items())
    opening = periods[0][1].value
    ending = periods[-1][1].value
    if not isinstance(opening, (int, float)) or not isinstance(ending, (int, float)):
        return _empty_figure("Debt Paydown Waterfall")
    figure = go.Figure(
        go.Waterfall(
            name="Debt",
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=[f"Opening {periods[0][0]}", "Net Paydown / Cash Build", f"Ending {periods[-1][0]}"],
            y=[opening, ending - opening, ending],
            connector={"line": {"color": "rgba(100,100,100,0.5)"}},
        )
    )
    figure.update_layout(title="Debt Paydown Waterfall", showlegend=False, xaxis_title=None, yaxis_title="Net Debt")
    return figure


def _format_cell(value: float | None, metric: str) -> str:
    if value is None:
        return ""
    if metric == "IRR":
        return f"{value:.1%}"
    if metric == "MOIC":
        return f"{value:.2f}x"
    return f"{value:,.1f}"


def _empty_figure(title: str) -> Figure:
    figure = go.Figure()
    figure.update_layout(title=title, xaxis={"visible": False}, yaxis={"visible": False})
    figure.add_annotation(text="Missing data", x=0.5, y=0.5, showarrow=False)
    return figure
