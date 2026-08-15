from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .service import AnalyticsService


def build_mcp(service: AnalyticsService | None = None) -> FastMCP:
    service = service or AnalyticsService(load_settings(require_api_key=False))
    mcp = FastMCP("profit-agent-demo")

    @mcp.tool()
    def describe_profit_schema() -> str:
        """profit_daily의 컬럼, 회사 용어, 지표 계산식, 주문상태를 설명합니다."""
        return service.describe_profit_schema()

    @mcp.tool()
    def get_profit_summary(start_date: str, end_date: str, group_by: list[str] | None = None, metrics: list[str] | None = None, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """기간별 profit_daily 지표를 차원별로 집계합니다."""
        return service.get_profit_summary(start_date, end_date, group_by, metrics, filters)

    @mcp.tool()
    def get_profit_trend(start_date: str, end_date: str, grain: str = "day", filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """일별 또는 월별 결제금액·지출액·영업이익 추이를 반환합니다."""
        return service.get_profit_trend(start_date, end_date, grain, filters)

    @mcp.tool()
    def get_top_products(start_date: str, end_date: str, metric: str = "profit", limit: int = 20, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """대표상품 기준으로 지정 지표의 상위 상품을 반환합니다."""
        return service.get_top_products(start_date, end_date, metric, limit, filters)

    return mcp


def main() -> None:
    build_mcp().run(transport="stdio")
