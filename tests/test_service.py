from types import SimpleNamespace

from profit_agent_demo.service import AnalyticsService


class FakeDatabase:
    def __init__(self):
        self.query = ""
        self.params = []

    def fetch(self, query, params):
        self.query = query
        self.params = params
        return [
            {"period": "2026-01-01", "brand_name": "솔담건강", "payment_amount": 100000, "extra_cost": 0, "profit": 30000},
            {"period": "2026-01-01", "brand_name": "한결웰빙", "payment_amount": 50000, "extra_cost": 0, "profit": 15000},
        ]


def test_monthly_brand_trend_returns_chart_ready_rows():
    database = FakeDatabase()
    service = AnalyticsService(SimpleNamespace(profit_daily_function="analytics.profit_daily"), database)

    result = service.get_profit_trend(
        "2026-01-01",
        "2026-07-31",
        grain="month",
        group_by=["brand_name"],
    )

    assert result["grain"] == "month"
    assert result["group_by"] == ["brand_name"]
    assert result["metrics"] == ["payment_amount", "extra_cost", "profit"]
    assert result["rows"][0]["period"] == "2026-01-01"
    assert "date_trunc('month', order_date)::date AS period" in database.query
    assert '"brand_name"' in database.query


def test_daily_brand_trend_can_return_bar_chart_contract():
    database = FakeDatabase()
    service = AnalyticsService(SimpleNamespace(profit_daily_function="analytics.profit_daily"), database)

    result = service.get_profit_trend(
        "2026-07-01", "2026-07-07", grain="day", group_by=["brand_name"],
        chart_type="stacked_bar",
    )

    assert result["chart"]["kind"] == "stacked_bar"
    assert result["chart"]["series_column"] == "brand_name"


def test_top_product_daily_trend_returns_explicit_line_chart_contract():
    database = FakeDatabase()
    service = AnalyticsService(SimpleNamespace(profit_daily_function="analytics.profit_daily"), database)

    result = service.get_top_product_trend("2026-07-01", "2026-07-31", limit=10)

    assert result["chart"] == {
        "kind": "line",
        "title": "일별 상위 상품 결제금액",
        "x_column": "period",
        "series_column": "product_name",
        "value_column": "payment_amount",
    }
    assert "WITH top_products AS" in database.query


def test_top_dimension_trend_maps_shop_name_to_a_chart_contract():
    database = FakeDatabase()
    service = AnalyticsService(SimpleNamespace(profit_daily_function="analytics.profit_daily"), database)

    result = service.get_top_dimension_trend("2026-07-01", "2026-07-31", "shop_name", limit=5)

    assert result["group_by"] == ["shop_name"]
    assert result["chart"]["series_column"] == "shop_name"
    assert result["chart"]["title"] == "일별 상위 판매처 결제금액"
    assert '"shop_name"' in database.query
