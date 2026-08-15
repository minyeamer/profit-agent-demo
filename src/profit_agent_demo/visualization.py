from dataclasses import dataclass
from typing import Any

import pandas as pd
import altair as alt

DISPLAY_NAMES = {
    "order_date": "월별",
    "brand_name": "브랜드별",
    "payment_amount": "결제금액",
}


@dataclass(frozen=True)
class ChartSpec:
    kind: str
    title: str
    x_column: str
    series_column: str | None
    value_column: str


def build_chart_spec(tool_name: str, result: dict[str, Any]) -> ChartSpec | None:
    group_by = result.get("group_by")
    metrics = result.get("metrics")
    rows = result.get("rows")
    explicit = result.get("chart")
    if isinstance(explicit, dict):
        kind = explicit.get("kind")
        title = explicit.get("title")
        x_column = explicit.get("x_column")
        series_column = explicit.get("series_column")
        value_column = explicit.get("value_column")
        if (
            kind in {"line", "bar", "stacked_bar"}
            and isinstance(title, str)
            and x_column in {"period", "order_date"}
            and isinstance(series_column, str)
            and isinstance(value_column, str)
            and isinstance(rows, list)
            and len(rows) >= 2
            and all(
                isinstance(row, dict)
                and row.get(x_column)
                and row.get(series_column)
                and isinstance(row.get(value_column), (int, float))
                for row in rows
            )
        ):
            return ChartSpec(kind, title, x_column, series_column, value_column)
    if tool_name == "get_profit_trend":
        if result.get("grain") != "month" or group_by != ["brand_name"]:
            return None
        if not isinstance(metrics, list) or "payment_amount" not in metrics:
            return None
        if not isinstance(rows, list) or len(rows) < 2:
            return None
        if not all(
            isinstance(row, dict)
            and row.get("period")
            and row.get("brand_name")
            and isinstance(row.get("payment_amount"), (int, float))
            for row in rows
        ):
            return None
        return ChartSpec(
            kind="line",
            title="월별 브랜드별 결제금액",
            x_column="period",
            series_column="brand_name",
            value_column="payment_amount",
        )
    if tool_name != "get_profit_summary":
        return None
    if group_by != ["order_date", "brand_name"] or metrics != ["payment_amount"]:
        return None
    if not isinstance(rows, list) or len(rows) < 2:
        return None
    if not all(
        isinstance(row, dict)
        and row.get("order_date")
        and row.get("brand_name")
        and isinstance(row.get("payment_amount"), (int, float))
        for row in rows
    ):
        return None
    return ChartSpec(
        kind="line",
        title="월별 브랜드별 결제금액",
        x_column="order_date",
        series_column="brand_name",
        value_column="payment_amount",
    )


def build_chart_frame(chart: ChartSpec, rows: list[dict[str, Any]]) -> pd.DataFrame:
    if chart.kind not in {"line", "bar", "stacked_bar"} or not chart.series_column:
        raise ValueError("지원하지 않는 다중 계열 차트 사양입니다")
    frame = pd.DataFrame(rows)
    frame[chart.x_column] = pd.to_datetime(frame[chart.x_column])
    pivoted = frame.pivot(index=chart.x_column, columns=chart.series_column, values=chart.value_column).sort_index()
    return pivoted.loc[:, (pivoted.fillna(0) != 0).any(axis=0)]


def build_stacked_bar_chart(chart: ChartSpec, rows: list[dict[str, Any]]) -> alt.Chart:
    if not chart.series_column:
        raise ValueError("누적 막대 그래프에 계열 기준이 필요합니다")
    series_column = chart.series_column
    frame = pd.DataFrame(rows)
    frame[chart.x_column] = pd.to_datetime(frame[chart.x_column])
    return (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            x=alt.X(f"{chart.x_column}:T", title=chart.x_column),
            y=alt.Y(f"sum({chart.value_column}):Q", title=chart.value_column),
            color=alt.Color(f"{series_column}:N", title=series_column),
            tooltip=[chart.x_column, series_column, chart.value_column],
        )
        .properties(title=chart.title)
    )
