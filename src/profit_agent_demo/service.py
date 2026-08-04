import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from .config import Settings
from .db import Database
from .query_builder import build_aggregate_query

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
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if grain == "day":
            return self.get_profit_summary(
                start_date, end_date, ["order_date"],
                ["payment_amount", "extra_cost", "profit"], filters,
            ) | {"grain": "day"}
        if grain != "month":
            raise ValueError("grain은 day 또는 month여야 합니다")
        start, end = _parse_date_range(start_date, end_date)
        query = (
            f"SELECT date_trunc('month', order_date)::date AS period, "
            f"SUM(payment_amount) AS payment_amount, SUM(extra_cost) AS extra_cost, "
            f"SUM(profit) AS profit FROM {self.settings.profit_daily_function}(%s, %s)"
        )
        params: list[Any] = [start, end]
        clauses = []
        allowed = {"brand_name", "team_name", "shop_name", "shop_group", "order_status"}
        for column, value in (filters or {}).items():
            if column not in allowed:
                raise ValueError(f"월별 추이에서 허용되지 않은 필터 컬럼: {column}")
            clauses.append(f'"{column}" = %s')
            params.append(value)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " GROUP BY 1 ORDER BY 1 LIMIT 1000"
        rows = self.database.fetch(query, params)
        return {
            "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "grain": "month", "row_count": len(rows), "rows": _jsonable(rows),
        }

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

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        functions = {
            "describe_profit_schema": self.describe_profit_schema,
            "get_profit_summary": self.get_profit_summary,
            "get_profit_trend": self.get_profit_trend,
            "get_top_products": self.get_top_products,
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
        {"type": "function", "function": {"name": "get_profit_trend", "description": "일별 또는 월별 결제금액·지출액·영업이익 추이를 반환합니다.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "grain": {"type": "string", "enum": ["day", "month"]}, "filters": {"type": "object", "additionalProperties": True}}, "required": ["start_date", "end_date"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_top_products", "description": "대표상품 기준으로 지정 지표의 상위 상품을 반환합니다.", "parameters": {"type": "object", "properties": {"start_date": {"type": "string"}, "end_date": {"type": "string"}, "metric": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "filters": {"type": "object", "additionalProperties": True}}, "required": ["start_date", "end_date"], "additionalProperties": False}}},
    ]
