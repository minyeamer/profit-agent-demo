import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from .config import Settings
from .db import Database
from .query_builder import build_aggregate_query, build_top_dimension_trend_query, build_top_product_trend_query, build_trend_query

SCHEMA_PATH = Path(__file__).parents[2] / "semantic_schema.yml"


class AnalyticsService:
    def __init__(self, settings: Settings, database: Any | None = None):
        self.settings = settings
        self.database = database or Database(settings)

    def describe_profit_schema(self) -> str:
        return json.dumps(yaml.safe_load(SCHEMA_PATH.read_text()), ensure_ascii=False, indent=2)

    def get_profit_summary(
        self,
        start_date: str,
        end_date: str,
        group_by: list[str] | None = None,
        metrics: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start, end = _parse_date_range(start_date, end_date)
        query, params = build_aggregate_query(
            start, end, relation=self.settings.profit_daily_function,
            group_by=group_by, metrics=metrics, filters=filters,
        )
        rows = self.database.fetch(query, params)
        return {
            "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "group_by": group_by or [],
            "metrics": metrics or ["payment_amount", "profit"],
            "filters": filters or {},
            "row_count": len(rows),
            "rows": _jsonable(rows),
        }

    def get_profit_trend(
        self,
        start_date: str,
        end_date: str,
        grain: str = "day",
        group_by: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        chart_type: str | None = None,
    ) -> dict[str, Any]:
        start, end = _parse_date_range(start_date, end_date)
        query, params = build_trend_query(
            start,
            end,
            relation=self.settings.profit_daily_function,
            grain=grain,
            group_by=group_by,
            filters=filters,
        )
        rows = self.database.fetch(query, params)
        result = {
            "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "grain": grain,
            "group_by": group_by or [],
            "metrics": ["payment_amount", "extra_cost", "profit"],
            "filters": filters or {},
            "row_count": len(rows),
            "rows": _jsonable(rows),
        }
        if chart_type is not None:
            if chart_type not in {"line", "bar", "stacked_bar"}:
                raise ValueError("지원하지 않는 차트 유형입니다")
            dimension = (group_by or ["order_date"])[0]
            labels = {"brand_name": "브랜드", "shop_group": "쇼핑몰 그룹", "shop_name": "판매처"}
            result["chart"] = {
                "kind": chart_type,
                "title": f"{'일별' if grain == 'day' else '월별'} {labels.get(dimension, dimension)}별 결제금액",
                "x_column": "period",
                "series_column": dimension,
                "value_column": "payment_amount",
            }
        return result

    def get_top_products(
        self,
        start_date: str,
        end_date: str,
        metric: str = "profit",
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if metric not in {"profit", "payment_amount", "extra_cost", "ad_cost", "margin_amount"}:
            raise ValueError("허용되지 않은 상품 순위 지표입니다")
        if not 1 <= limit <= 100:
            raise ValueError("limit은 1에서 100 사이여야 합니다")
        result = self.get_profit_summary(
            start_date, end_date,
            ["item_id", "item_seq", "product_name", "brand_name"], [metric], filters,
        )
        result["rows"] = result["rows"][:limit]
        result["row_count"] = len(result["rows"])
        return result

    def get_top_product_trend(
        self,
        start_date: str,
        end_date: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        start, end = _parse_date_range(start_date, end_date)
        query, params = build_top_product_trend_query(
            start,
            end,
            relation=self.settings.profit_daily_function,
            metric="payment_amount",
            limit=limit,
            filters=filters,
        )
        rows = self.database.fetch(query, params)
        return {
            "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "group_by": ["product_name"],
            "metrics": ["payment_amount"],
            "filters": filters or {},
            "row_count": len(rows),
            "rows": _jsonable(rows),
            "chart": {
                "kind": "line",
                "title": "일별 상위 상품 결제금액",
                "x_column": "period",
                "series_column": "product_name",
                "value_column": "payment_amount",
            },
        }

    def get_top_dimension_trend(
        self, start_date: str, end_date: str, dimension: str, limit: int = 10,
        filters: dict[str, Any] | None = None, chart_type: str = "line",
    ) -> dict[str, Any]:
        start, end = _parse_date_range(start_date, end_date)
        query, params = build_top_dimension_trend_query(
            start, end, relation=self.settings.profit_daily_function,
            dimension=dimension, limit=limit, filters=filters,
        )
        rows = _jsonable(self.database.fetch(query, params))
        if chart_type not in {"line", "bar", "stacked_bar"}:
            raise ValueError("지원하지 않는 차트 유형입니다")
        labels = {"shop_group": "쇼핑몰 그룹", "shop_name": "판매처", "brand_name": "브랜드", "team_name": "담당팀"}
        return {
            "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "group_by": [dimension], "metrics": ["payment_amount"], "filters": filters or {},
            "row_count": len(rows), "rows": rows,
            "chart": {"kind": chart_type, "title": f"일별 상위 {labels.get(dimension, dimension)} 결제금액",
                        "x_column": "period", "series_column": dimension, "value_column": "payment_amount"},
        }

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        functions = {
            "describe_profit_schema": self.describe_profit_schema,
            "get_profit_summary": self.get_profit_summary,
            "get_profit_trend": self.get_profit_trend,
            "get_top_products": self.get_top_products,
            "get_top_product_trend": self.get_top_product_trend,
            "get_top_dimension_trend": self.get_top_dimension_trend,
        }
        if name not in functions:
            raise ValueError(f"허용되지 않은 분석 도구입니다: {name}")
        return functions[name](**arguments)


def _parse_date_range(start_value: str, end_value: str) -> tuple[date, date]:
    try:
        start, end = date.fromisoformat(start_value), date.fromisoformat(end_value)
    except ValueError as exc:
        raise ValueError("날짜 형식은 YYYY-MM-DD여야 합니다") from exc
    if start > end:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다")
    return start, end


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": {"name": "describe_profit_schema", "description": "profit_daily의 컬럼, 회사 용어, 계산식, 주문상태를 설명합니다.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_profit_summary", "description": "기간별 profit_daily 지표를 차원별로 집계합니다. 날짜는 양 끝을 포함합니다.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "group_by": {"type": "array", "items": {"type": "string"}}, "metrics": {"type": "array", "items": {"type": "string"}}, "filters": {"type": "object", "additionalProperties": True}}, "required": ["start_date", "end_date"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_profit_trend", "description": "일별 또는 월별 결제금액·지출액·영업이익 추이를 반환합니다. 사용자가 그래프를 요청하면 chart_type을 line, bar, stacked_bar 중 의미에 맞게 지정합니다. stacked_bar는 차원별 매출 비중을 비교할 때 사용합니다.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "grain": {"type": "string", "enum": ["day", "month"]}, "group_by": {"type": "array", "items": {"type": "string"}, "maxItems": 1}, "filters": {"type": "object", "additionalProperties": True}, "chart_type": {"type": "string", "enum": ["line", "bar", "stacked_bar"]}}, "required": ["start_date", "end_date"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_top_products", "description": "대표상품 기준으로 지정 지표의 상위 상품을 반환합니다.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "metric": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "filters": {"type": "object", "additionalProperties": True}}, "required": ["start_date", "end_date"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_top_product_trend", "description": "기간 전체 결제금액 상위 대표상품의 일별 결제금액 추이를 반환합니다. 상위 상품의 일별 그래프 요청에 사용합니다.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}, "filters": {"type": "object", "additionalProperties": True}}, "required": ["start_date", "end_date"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_top_dimension_trend", "description": "반드시 사용자가 상위 N개를 명시했을 때만 사용합니다. 지정 차원의 기간 전체 결제금액 상위 항목에 대한 일별 추이를 반환합니다. 상위 N이 없는 일반 브랜드·판매처 추이는 get_profit_trend를 사용하세요.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "dimension": {"type": "string", "enum": ["brand_name", "shop_group", "shop_name", "team_name", "category_name1", "category_name2", "category_name3", "category_name4"]}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}, "filters": {"type": "object", "additionalProperties": True}, "chart_type": {"type": "string", "enum": ["line", "bar", "stacked_bar"]}}, "required": ["start_date", "end_date", "dimension", "limit"], "additionalProperties": False}}},
    ]
