import re
from datetime import date
from typing import Any


DIMENSIONS = {
    "product_id", "item_id", "item_seq", "team_name", "brand_name",
    "category_name1", "category_name2", "category_name3", "category_name4",
    "color", "product_name", "category_unit_name", "shop_id", "shop_group",
    "shop_name", "order_status", "order_date",
}
METRICS = {
    "unit_quantity", "sku_quantity", "payment_amount", "supply_amount",
    "supply_cost", "delivery_fee", "margin_amount", "ad_cost", "extra_cost", "profit",
}


def validate_relation(relation: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", relation):
        raise ValueError("테이블 함수 이름은 schema.function 형식이어야 합니다")
    return relation


def build_aggregate_query(
    start_date: date,
    end_date: date,
    *,
    relation: str = "analytics.profit_daily",
    group_by: list[str] | None = None,
    metrics: list[str] | None = None,
    filters: dict[str, Any] | None = None,
) -> tuple[str, list[Any]]:
    if start_date > end_date:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다")
    if (end_date - start_date).days > 366:
        raise ValueError("한 번의 조회 기간은 366일을 초과할 수 없습니다")
    validate_relation(relation)
    group_by = group_by or []
    metrics = metrics or ["payment_amount", "profit"]
    filters = filters or {}
    unknown_groups = set(group_by) - DIMENSIONS
    unknown_metrics = set(metrics) - METRICS
    unknown_filters = set(filters) - (DIMENSIONS - {"order_date"})
    if unknown_groups:
        raise ValueError(f"허용되지 않은 그룹 기준: {', '.join(sorted(unknown_groups))}")
    if unknown_metrics:
        raise ValueError(f"허용되지 않은 지표: {', '.join(sorted(unknown_metrics))}")
    if unknown_filters:
        raise ValueError(f"허용되지 않은 필터 컬럼: {', '.join(sorted(unknown_filters))}")

    select_parts = [f'"{column}"' for column in group_by]
    select_parts += [f'SUM("{metric}") AS "{metric}"' for metric in metrics]
    if not select_parts:
        select_parts = ["COUNT(*) AS row_count"]

    clauses: list[str] = []
    params: list[Any] = [start_date, end_date]
    for column, value in filters.items():
        if isinstance(value, list):
            if not value:
                raise ValueError(f"필터 값이 비어 있습니다: {column}")
            clauses.append(f'"{column}" = ANY(%s)')
        else:
            clauses.append(f'"{column}" = %s')
        params.append(value)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    group_columns = ", ".join(f'"{column}"' for column in group_by)
    group = f" GROUP BY {group_columns}" if group_by else ""
    order = f' ORDER BY "{metrics[0]}" DESC' if metrics else ""
    query = (
        f"SELECT {', '.join(select_parts)} FROM {relation}(%s, %s)"
        f"{where}{group}{order} LIMIT 1000"
    )
    return query, params
