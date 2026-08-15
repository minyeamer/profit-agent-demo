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


def build_trend_query(
    start_date: date,
    end_date: date,
    *,
    relation: str = "analytics.profit_daily",
    grain: str = "day",
    group_by: list[str] | None = None,
    filters: dict[str, Any] | None = None,
) -> tuple[str, list[Any]]:
    if start_date > end_date:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다")
    if (end_date - start_date).days > 366:
        raise ValueError("한 번의 조회 기간은 366일을 초과할 수 없습니다")
    if grain not in {"day", "month"}:
        raise ValueError("grain은 day 또는 month여야 합니다")
    validate_relation(relation)
    group_by = group_by or []
    filters = filters or {}
    if len(group_by) > 1:
        raise ValueError("추이 조회의 추가 집계 기준은 하나만 허용됩니다")
    allowed_group_by = DIMENSIONS - {"order_date"}
    unknown_groups = set(group_by) - allowed_group_by
    unknown_filters = set(filters) - allowed_group_by
    if unknown_groups:
        raise ValueError(f"허용되지 않은 그룹 기준: {', '.join(sorted(unknown_groups))}")
    if unknown_filters:
        raise ValueError(f"허용되지 않은 필터 컬럼: {', '.join(sorted(unknown_filters))}")

    period_expression = "order_date" if grain == "day" else "date_trunc('month', order_date)::date"
    select_parts = [f"{period_expression} AS period"]
    select_parts += [f'"{column}"' for column in group_by]
    select_parts += [
        'SUM("payment_amount") AS "payment_amount"',
        'SUM("extra_cost") AS "extra_cost"',
        'SUM("profit") AS "profit"',
    ]
    params: list[Any] = [start_date, end_date]
    clauses: list[str] = []
    for column, value in filters.items():
        if isinstance(value, list):
            if not value:
                raise ValueError(f"필터 값이 비어 있습니다: {column}")
            clauses.append(f'"{column}" = ANY(%s)')
        else:
            clauses.append(f'"{column}" = %s')
        params.append(value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    positions = ", ".join(str(index) for index in range(1, len(group_by) + 2))
    query = (
        f"SELECT {', '.join(select_parts)} FROM {relation}(%s, %s)"
        f"{where} GROUP BY {positions} ORDER BY {positions} LIMIT 1000"
    )
    return query, params


def build_top_dimension_trend_query(
    start_date: date,
    end_date: date,
    *,
    relation: str = "analytics.profit_daily",
    dimension: str,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
) -> tuple[str, list[Any]]:
    if start_date > end_date:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다")
    if (end_date - start_date).days > 366:
        raise ValueError("한 번의 조회 기간은 366일을 초과할 수 없습니다")
    if dimension not in DIMENSIONS - {"order_date"}:
        raise ValueError(f"허용되지 않은 차원: {dimension}")
    if not 1 <= limit <= 20:
        raise ValueError("상위 차원 추이의 limit은 1에서 20 사이여야 합니다")
    validate_relation(relation)
    filters = filters or {}
    if set(filters) - (DIMENSIONS - {"order_date"}):
        raise ValueError("허용되지 않은 필터 컬럼입니다")

    def clauses(alias: str) -> tuple[str, list[Any]]:
        parts, values = [], []
        for column, value in filters.items():
            if isinstance(value, list):
                if not value:
                    raise ValueError(f"필터 값이 비어 있습니다: {column}")
                parts.append(f'{alias}."{column}" = ANY(%s)')
            else:
                parts.append(f'{alias}."{column}" = %s')
            values.append(value)
        return (f" WHERE {' AND '.join(parts)}" if parts else ""), values

    top_where, top_values = clauses("ranked")
    source_where, source_values = clauses("source")
    column = f'"{dimension}"'
    query = (
        f"WITH top_entities AS (SELECT {column} FROM {relation}(%s, %s) AS ranked{top_where} "
        f"GROUP BY {column} ORDER BY SUM(\"payment_amount\") DESC LIMIT %s) "
        f"SELECT source.order_date AS period, source.{column}, "
        f"SUM(source.\"payment_amount\") AS \"payment_amount\" "
        f"FROM {relation}(%s, %s) AS source JOIN top_entities AS top "
        f"ON source.{column} = top.{column}{source_where} "
        f"GROUP BY 1, source.{column} ORDER BY 1, \"payment_amount\" DESC LIMIT 1000"
    )
    return query, [start_date, end_date, *top_values, limit, start_date, end_date, *source_values]


def build_top_product_trend_query(
    start_date: date,
    end_date: date,
    *,
    relation: str = "analytics.profit_daily",
    metric: str = "payment_amount",
    limit: int = 10,
    filters: dict[str, Any] | None = None,
) -> tuple[str, list[Any]]:
    if start_date > end_date:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다")
    if (end_date - start_date).days > 366:
        raise ValueError("한 번의 조회 기간은 366일을 초과할 수 없습니다")
    if metric not in METRICS:
        raise ValueError(f"허용되지 않은 지표: {metric}")
    if not 1 <= limit <= 20:
        raise ValueError("상위 상품 추이의 limit은 1에서 20 사이여야 합니다")
    validate_relation(relation)
    filters = filters or {}
    allowed_filters = DIMENSIONS - {"order_date"}
    unknown_filters = set(filters) - allowed_filters
    if unknown_filters:
        raise ValueError(f"허용되지 않은 필터 컬럼: {', '.join(sorted(unknown_filters))}")

    def where_clause(alias: str) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        for column, value in filters.items():
            qualified = f'{alias}."{column}"'
            if isinstance(value, list):
                if not value:
                    raise ValueError(f"필터 값이 비어 있습니다: {column}")
                clauses.append(f"{qualified} = ANY(%s)")
            else:
                clauses.append(f"{qualified} = %s")
            values.append(value)
        return (f" WHERE {' AND '.join(clauses)}" if clauses else ""), values

    top_where, filter_values = where_clause("ranked")
    source_where, source_filter_values = where_clause("source")
    product_columns = ['"item_id"', '"item_seq"', '"product_name"', '"brand_name"']
    product_select = ", ".join(product_columns)
    source_products = ", ".join(f"source.{column}" for column in product_columns)
    query = (
        f"WITH top_products AS ("
        f"SELECT {product_select} FROM {relation}(%s, %s) AS ranked"
        f"{top_where} GROUP BY {product_select} "
        f"ORDER BY SUM(\"{metric}\") DESC LIMIT %s"
        f") SELECT source.order_date AS period, {source_products}, "
        f"SUM(source.\"payment_amount\") AS \"payment_amount\" "
        f"FROM {relation}(%s, %s) AS source "
        f"JOIN top_products AS top ON source.\"item_id\" = top.\"item_id\" "
        f"AND source.\"item_seq\" = top.\"item_seq\""
        f"{source_where} GROUP BY 1, {source_products} ORDER BY 1, \"payment_amount\" DESC LIMIT 1000"
    )
    params: list[Any] = [start_date, end_date, *filter_values, limit, start_date, end_date, *source_filter_values]
    return query, params
