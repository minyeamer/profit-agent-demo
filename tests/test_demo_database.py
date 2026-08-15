import csv
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "demo_db" / "data"


def read_csv(name):
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_demo_database_assets_define_csv_backed_demo_contract():
    compose = (ROOT / "docker-compose.demo.yml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.demo.example").read_text(encoding="utf-8")
    schema = (ROOT / "demo_db" / "001_schema.sql").read_text(encoding="utf-8")
    loader = (ROOT / "demo_db" / "002_load.sql").read_text(encoding="utf-8")
    mcp_script = (ROOT / "scripts" / "run_mcp.sh").read_text(encoding="utf-8")
    streamlit_script = (ROOT / "scripts" / "run_demo_streamlit.sh").read_text(encoding="utf-8")

    assert "demo-postgres" in compose
    assert 'profiles: ["container"]' in compose
    assert "15432:5432" in compose
    assert "PGDATABASE=profit_demo" in env_example
    assert "CREATE SCHEMA IF NOT EXISTS analytics" in schema
    assert "CREATE SCHEMA IF NOT EXISTS demo" in schema
    assert "xfm_sales" not in schema
    for table in ("sales_daily", "extra_profit", "product", "shop"):
        assert f"CREATE TABLE IF NOT EXISTS demo.{table}" in schema
        assert f"COPY demo.{table}" in loader
    assert "generate_series" not in loader
    assert "ORIGINAL_${name}" in mcp_script
    assert "127.0.0.1" in streamlit_script
    assert "API_TYPE" in streamlit_script
    assert "API_KEY" in streamlit_script


def test_products_distinguish_representative_items_from_skus():
    products = read_csv("demo.product.csv")
    item_count = Counter()
    sku_count = Counter()
    item_ids_by_brand = defaultdict(set)
    for row in products:
        item_ids_by_brand[row["brand_name"]].add(row["item_id"])
        sku_count[row["brand_name"]] += 1
        assert re.fullmatch(r"1\d{5}", row["product_id"])
        assert re.fullmatch(r"[A-Z]{8}", row["item_id"])
    item_count.update({brand: len(ids) for brand, ids in item_ids_by_brand.items()})

    assert item_count == {
        "솔담건강": 50,
        "한결웰빙": 20,
        "루미에르홈": 10,
        "들꽃찬": 5,
        "모노에어": 5,
    }
    assert sku_count["솔담건강"] == 50
    assert sku_count["한결웰빙"] == 20
    assert sku_count["들꽃찬"] == 5
    assert sku_count["루미에르홈"] > item_count["루미에르홈"]
    assert sku_count["모노에어"] > item_count["모노에어"]


def test_product_names_categories_and_options_are_business_plausible():
    products = read_csv("demo.product.csv")
    prohibited = ("홍삼", "프로바이오틱스", "루테인", "오메가", "비타민", "콜라겐", "유산균", "밀크씨슬", "아연", "건강기능")
    food_names = set()
    appliance_options = defaultdict(set)

    for row in products:
        assert not re.search(r"\d+호(?:\s|$)", row["product_name"])
        if row["team_name"] == "식품팀":
            food_names.add((row["brand_name"], row["product_name"]))
            assert not any(term in row["product_name"] or term in row["category_name2"] or term in row["category_name3"] for term in prohibited)
            assert row["category_name4"] == ""
            assert row["color"] == ""
        else:
            assert row["color"] in {"화이트", "베이지", "차콜", "블랙", "실버", "민트", "네이비"}
            assert row["category_name4"] in {"단품", "2개 세트", "본품+소모품"}
            appliance_options[row["item_id"]].add((row["category_name4"], row["color"]))

    assert len(food_names) == 75
    assert all(len(options) >= 2 for options in appliance_options.values())


def test_shop_and_sales_identifiers_and_dates_are_valid():
    products = read_csv("demo.product.csv")
    shops = read_csv("demo.shop.csv")
    sales = read_csv("demo.sales_daily.csv")
    product_ids = {row["product_id"] for row in products}
    shop_ids = {row["shop_id"] for row in shops}

    assert all(re.fullmatch(r"2\d{5}", shop_id) for shop_id in shop_ids)
    assert all(row["product_id"] in product_ids for row in sales if row["product_id"] != "199999")
    sold_product_ids = {row["product_id"] for row in sales if int(row["order_status"]) == 0}
    assert product_ids <= sold_product_ids
    assert all(row["shop_id"] in shop_ids for row in sales)
    assert min(row["order_date"] for row in sales) == "2025-08-01"
    assert max(row["order_date"] for row in sales) == "2026-07-31"
    assert {row["shop_name"] for row in shops} >= {"스마트스토어", "쿠팡", "11번가"}


def test_sales_use_integer_quantities_stable_prices_and_realistic_cost_rules():
    sales = read_csv("demo.sales_daily.csv")
    statuses = {int(row["order_status"]) for row in sales}
    unit_prices = defaultdict(set)
    extra_cost_rows = 0

    assert statuses >= {0, 1, 2, 3, 5, 6, 7, 8, 9}
    for row in sales:
        status = int(row["order_status"])
        quantity = Decimal(row["sku_quantity"])
        payment = int(Decimal(row["payment_amount"]))
        delivery = int(Decimal(row["delivery_fee"]))
        extra = int(Decimal(row["extra_cost"]))
        assert quantity == quantity.to_integral_value()
        assert delivery == 0 or (2_000 <= delivery <= 5_000 and delivery % 500 == 0)
        if status == 0:
            assert quantity > 0
            unit_price = payment // int(quantity)
            assert payment == unit_price * int(quantity)
            assert unit_price % 100 == 0
            unit_prices[row["product_id"]].add(unit_price)
        else:
            assert payment == 0
        if extra > 0:
            extra_cost_rows += 1
            assert status == 9
        elif status != 9:
            assert extra == 0

    assert extra_cost_rows / len(sales) < 0.03
    assert max(map(len, unit_prices.values())) <= 3


def test_popular_products_outsell_long_tail_products():
    products = read_csv("demo.product.csv")
    sales = read_csv("demo.sales_daily.csv")
    product_by_id = {row["product_id"]: row for row in products}
    revenue_by_item = defaultdict(int)
    item_seq = {}
    items_by_brand = defaultdict(set)

    for row in products:
        item_seq[row["item_id"]] = int(row["item_seq"])
        items_by_brand[row["brand_name"]].add(row["item_id"])
    for row in sales:
        if int(row["order_status"]) == 0:
            product = product_by_id[row["product_id"]]
            revenue_by_item[product["item_id"]] += int(Decimal(row["payment_amount"]))

    for brand, item_ids in items_by_brand.items():
        ordered = sorted(item_ids, key=lambda item_id: item_seq[item_id])
        bucket = max(1, len(ordered) // 5)
        top = sum(revenue_by_item[item_id] for item_id in ordered[:bucket])
        bottom = sum(revenue_by_item[item_id] for item_id in ordered[-bucket:])
        popular_cut = max(1, len(ordered) * 2 // 5)
        popular_floor = min(revenue_by_item[item_id] for item_id in ordered[:popular_cut])
        long_tail_ceiling = max(revenue_by_item[item_id] for item_id in ordered[-popular_cut:])
        assert bottom > 0, brand
        assert top > bottom * 2, brand
        assert popular_floor > long_tail_ceiling, brand
