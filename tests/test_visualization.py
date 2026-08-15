from profit_agent_demo.visualization import build_chart_frame, build_chart_spec
from profit_agent_demo.web_app import render_analysis_result


def test_monthly_brand_payment_summary_becomes_multi_series_line_chart():
    result = {
        "period": {"start_date": "2026-01-01", "end_date": "2026-07-31"},
        "group_by": ["order_date", "brand_name"],
        "metrics": ["payment_amount"],
        "filters": {},
        "row_count": 4,
        "rows": [
            {"order_date": "2026-01-01", "brand_name": "솔담건강", "payment_amount": 100000},
            {"order_date": "2026-01-01", "brand_name": "한결웰빙", "payment_amount": 50000},
            {"order_date": "2026-02-01", "brand_name": "솔담건강", "payment_amount": 120000},
            {"order_date": "2026-02-01", "brand_name": "한결웰빙", "payment_amount": 60000},
        ],
    }

    chart = build_chart_spec("get_profit_summary", result)

    assert chart is not None
    assert chart.kind == "line"
    assert chart.x_column == "order_date"
    assert chart.series_column == "brand_name"
    assert chart.value_column == "payment_amount"
    assert chart.title == "월별 브랜드별 결제금액"

    frame = build_chart_frame(chart, result["rows"])

    assert list(frame.columns) == ["솔담건강", "한결웰빙"]
    assert frame.loc["2026-01-01", "솔담건강"] == 100000
    assert frame.loc["2026-02-01", "한결웰빙"] == 60000


def test_monthly_brand_trend_becomes_multi_series_line_chart():
    result = {
        "grain": "month",
        "group_by": ["brand_name"],
        "metrics": ["payment_amount", "extra_cost", "profit"],
        "rows": [
            {"period": "2026-01-01", "brand_name": "솔담건강", "payment_amount": 100000},
            {"period": "2026-01-01", "brand_name": "한결웰빙", "payment_amount": 50000},
        ],
    }

    chart = build_chart_spec("get_profit_trend", result)

    assert chart is not None
    assert chart.x_column == "period"
    assert chart.series_column == "brand_name"
    assert chart.value_column == "payment_amount"
    assert chart.title == "월별 브랜드별 결제금액"


def test_explicit_chart_contract_supports_daily_top_product_lines():
    result = {
        "chart": {
            "kind": "line",
            "title": "일별 상위 상품 결제금액",
            "x_column": "period",
            "series_column": "product_name",
            "value_column": "payment_amount",
        },
        "rows": [
            {"period": "2026-07-01", "product_name": "상품 A", "payment_amount": 100000},
            {"period": "2026-07-01", "product_name": "상품 B", "payment_amount": 50000},
        ],
    }

    chart = build_chart_spec("get_top_product_trend", result)

    assert chart is not None
    assert chart.kind == "line"
    assert chart.x_column == "period"
    assert chart.series_column == "product_name"
    assert chart.value_column == "payment_amount"


def test_explicit_bar_and_stacked_bar_contracts_are_supported():
    for kind in ("bar", "stacked_bar"):
        result = {
            "chart": {
                "kind": kind,
                "title": "일별 결제금액",
                "x_column": "period",
                "series_column": "brand_name",
                "value_column": "payment_amount",
            },
            "rows": [
                {"period": "2026-07-01", "brand_name": "솔담건강", "payment_amount": 100000},
                {"period": "2026-07-02", "brand_name": "솔담건강", "payment_amount": 120000},
            ],
        }
        chart = build_chart_spec("get_profit_trend", result)
        assert chart is not None
        assert chart.kind == kind


def test_chart_frame_excludes_series_with_no_payment_amount():
    chart = build_chart_spec(
        "get_profit_trend",
        {
            "grain": "month",
            "group_by": ["brand_name"],
            "metrics": ["payment_amount"],
            "rows": [
                {"period": "2026-01-01", "brand_name": "솔담건강", "payment_amount": 100000},
                {"period": "2026-02-01", "brand_name": "솔담건강", "payment_amount": 120000},
                {"period": "2026-01-01", "brand_name": "브랜드 없음", "payment_amount": 0},
                {"period": "2026-02-01", "brand_name": "브랜드 없음", "payment_amount": 0},
            ],
        },
    )

    assert chart is not None
    frame = build_chart_frame(
        chart,
        [
            {"period": "2026-01-01", "brand_name": "솔담건강", "payment_amount": 100000},
            {"period": "2026-02-01", "brand_name": "솔담건강", "payment_amount": 120000},
            {"period": "2026-01-01", "brand_name": "브랜드 없음", "payment_amount": 0},
            {"period": "2026-02-01", "brand_name": "브랜드 없음", "payment_amount": 0},
        ],
    )

    assert list(frame.columns) == ["솔담건강"]


class FakeStreamlit:
    def __init__(self):
        self.captions = []
        self.line_charts = []
        self.dataframes = []
        self.dataframe_kwargs = []

    def caption(self, value):
        self.captions.append(value)

    def line_chart(self, value):
        self.line_charts.append(value)

    def dataframe(self, value, **kwargs):
        self.dataframes.append(value)
        self.dataframe_kwargs.append(kwargs)


def test_renderer_shows_monthly_brand_line_chart_with_table_and_conditions():
    result = {
        "period": {"start_date": "2026-01-01", "end_date": "2026-07-31"},
        "group_by": ["order_date", "brand_name"],
        "metrics": ["payment_amount"],
        "filters": {},
        "row_count": 4,
        "rows": [
            {"order_date": "2026-01-01", "brand_name": "솔담건강", "payment_amount": 100000},
            {"order_date": "2026-01-01", "brand_name": "한결웰빙", "payment_amount": 50000},
            {"order_date": "2026-02-01", "brand_name": "솔담건강", "payment_amount": 120000},
            {"order_date": "2026-02-01", "brand_name": "한결웰빙", "payment_amount": 60000},
        ],
    }
    ui = FakeStreamlit()

    render_analysis_result(ui, "get_profit_summary", result)

    assert ui.line_charts
    assert list(ui.line_charts[0].columns) == ["솔담건강", "한결웰빙"]
    assert ui.dataframes
    assert ui.dataframe_kwargs == [{"width": "stretch", "hide_index": True}]
    assert "기간: 2026-01-01 ~ 2026-07-31" in ui.captions
    assert "집계 기준: order_date, brand_name" in ui.captions
