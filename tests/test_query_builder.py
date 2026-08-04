from datetime import date

import pytest
import yaml

from profit_agent_demo.query_builder import build_aggregate_query


SCHEMA = yaml.safe_load(open("semantic_schema.yml", encoding="utf-8"))


def test_public_schema_contains_business_terms_without_private_brand_names():
    fields = SCHEMA["fields"]
    assert fields["product_id"]["display_name"] == "상품코드"
    assert fields["item_id"]["display_name"] == "대표상품코드"
    assert fields["shop_id"]["display_name"] == "판매처코드"
    assert fields["extra_cost"]["display_name"] == "지출액"
    assert fields["sku_quantity"]["display_name"] == "확정수량"
    assert fields["unit_quantity"]["display_name"] == "세트수량"
    assert "brand_name" in fields
    assert "private" not in open("semantic_schema.yml", encoding="utf-8").read().lower()


def test_query_builder_aggregates_by_brand_without_hardcoded_brand_filter():
    query, params = build_aggregate_query(
        date(2026, 7, 1), date(2026, 7, 31),
        relation="demo_schema.profit_daily",
        group_by=["brand_name"],
        metrics=["ad_cost", "extra_cost"],
    )

    assert "demo_schema.profit_daily(%s, %s)" in query
    assert 'GROUP BY "brand_name"' in query
    assert 'SUM("ad_cost") AS "ad_cost"' in query
    assert 'SUM("extra_cost") AS "extra_cost"' in query
    assert params == [date(2026, 7, 1), date(2026, 7, 31)]


def test_query_builder_rejects_unknown_identifiers_and_long_ranges():
    with pytest.raises(ValueError, match="허용되지 않은"):
        build_aggregate_query(date(2026, 1, 1), date(2026, 1, 2), group_by=["password"])
    with pytest.raises(ValueError, match="366일"):
        build_aggregate_query(date(2025, 1, 1), date(2026, 1, 3))
