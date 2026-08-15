#!/usr/bin/env python3
"""Generate deterministic, reviewed CSV assets for the public demo database.

PostgreSQL never runs this generator. It imports the checked-in CSV files via
COPY. Private data contributes aggregate seasonality and operational shape only;
no source rows, identifiers, product names, brands, or account mappings are used.
"""

from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
DATA_DIR = ROOT / "demo_db" / "data"
SEED = 20260815

FOOD_MONTH = {1: 1.102, 2: 1.004, 3: 1.042, 4: 1.174, 5: 1.120, 6: 0.944,
                7: 0.834, 8: 0.902, 9: 1.037, 10: 0.912, 11: 0.967, 12: 0.961}
APPLIANCE_MONTH = {1: 1.538, 2: 0.914, 3: 0.590, 4: 0.459, 5: 0.508, 6: 0.393,
                    7: 0.340, 8: 0.843, 9: 1.054, 10: 2.016, 11: 1.839, 12: 1.506}
FOOD_DOW = {1: 1.159, 2: 1.084, 3: 1.044, 4: 1.049, 5: 0.915, 6: 0.812, 7: 0.936}
APPLIANCE_DOW = {1: 1.144, 2: 1.072, 3: 1.120, 4: 1.018, 5: 0.904, 6: 0.770, 7: 0.972}

SHOPS = [
    (1, "200001", "스마트스토어", "스마트스토어", "오픈마켓", "https://smartstore.naver.com", 0.035),
    (2, "200002", "쿠팡", "쿠팡", "오픈마켓", "https://www.coupang.com", 0.040),
    (3, "200003", "11번가", "11번가", "오픈마켓", "https://www.11st.co.kr", 0.038),
    (4, "200004", "G마켓", "G마켓", "오픈마켓", "https://www.gmarket.co.kr", 0.042),
    (5, "200005", "옥션", "옥션", "오픈마켓", "https://www.auction.co.kr", 0.042),
    (6, "200006", "카카오톡 선물하기", "카카오톡 선물하기", "선물", "https://gift.kakao.com", 0.050),
]

SOLDAM_FOODS = [
    ("양조간장", "장류", "간장", 9900), ("재래식된장", "장류", "된장", 12900),
    ("태양초고추장", "장류", "고추장", 13900), ("구수한쌈장", "장류", "쌈장", 8900),
    ("떡볶이양념", "소스류", "조리소스", 7900), ("참기름", "식용유지", "참기름", 15900),
    ("들기름", "식용유지", "들기름", 16900), ("볶음참깨", "조미식품", "깨", 6900),
    ("고운고춧가루", "조미식품", "고춧가루", 14900), ("천일염", "조미식품", "소금", 10000),
    ("매실청", "차·음료", "청", 14900), ("유자차", "차·음료", "과일차", 11900),
    ("생강차", "차·음료", "전통차", 11900), ("보리차", "차·음료", "침출차", 5900),
    ("옥수수차", "차·음료", "침출차", 5900), ("현미누룽지", "곡물가공", "누룽지", 8900),
    ("찹쌀누룽지", "곡물가공", "누룽지", 9900), ("김부각", "스낵", "부각", 6900),
    ("다시마부각", "스낵", "부각", 6900), ("인절미스낵", "스낵", "곡물스낵", 4900),
    ("구운김", "수산가공", "김", 8900), ("김자반", "수산가공", "김자반", 6900),
    ("자른미역", "수산가공", "미역", 7900), ("육수용다시마", "수산가공", "다시마", 7900),
    ("건표고버섯", "농산가공", "건버섯", 12900), ("멸치육수팩", "조미식품", "육수팩", 9900),
    ("황태육수팩", "조미식품", "육수팩", 10900), ("사골곰탕", "국·탕", "곰탕", 5900),
    ("소고기미역국", "국·탕", "국", 5900), ("육개장", "국·탕", "탕", 6900),
    ("설렁탕", "국·탕", "탕", 6900), ("갈비탕", "국·탕", "탕", 8900),
    ("된장찌개", "찌개", "찌개", 5900), ("김치찌개", "찌개", "찌개", 5900),
    ("순두부찌개", "찌개", "찌개", 5900), ("비빔장", "소스류", "면소스", 6900),
    ("냉면육수", "소스류", "육수", 4900), ("메밀국수", "면류", "건면", 7900),
    ("칼국수면", "면류", "생면", 5900), ("쌀떡볶이떡", "떡류", "떡", 6900),
    ("현미쌀", "양곡", "쌀", 19900), ("찰보리", "양곡", "잡곡", 9900),
    ("혼합잡곡", "양곡", "잡곡", 15900), ("서리태", "양곡", "콩", 17900),
    ("볶음콩가루", "곡물가공", "곡물분말", 8900), ("전통약과", "과자", "한과", 6900),
    ("찹쌀유과", "과자", "한과", 7900), ("현미쌀과자", "과자", "쌀과자", 5900),
    ("곡물강정", "과자", "강정", 6900), ("참깨김스낵", "과자", "김스낵", 5900),
]

HANGYEOL_FOODS = [
    ("토마토파스타소스", "소스류", "파스타소스", 8900), ("로제파스타소스", "소스류", "파스타소스", 9900),
    ("바질페스토", "소스류", "페스토", 11900), ("엑스트라버진올리브유", "식용유지", "올리브유", 18900),
    ("발사믹드레싱", "소스류", "드레싱", 9900), ("그래놀라", "시리얼", "그래놀라", 12900),
    ("오트밀", "시리얼", "오트밀", 9900), ("통밀크래커", "과자", "크래커", 5900),
    ("견과믹스", "견과류", "혼합견과", 14900), ("건과일믹스", "과일가공", "건과일", 12900),
    ("땅콩버터", "잼류", "땅콩버터", 10900), ("딸기잼", "잼류", "과일잼", 8900),
    ("블루베리잼", "잼류", "과일잼", 9900), ("아카시아꿀", "당류", "꿀", 16900),
    ("메이플시럽", "당류", "시럽", 14900), ("즉석카레", "즉석식품", "카레", 4900),
    ("짜장소스", "즉석식품", "짜장", 4900), ("콘수프", "즉석식품", "수프", 3900),
    ("양송이스프", "즉석식품", "수프", 3900), ("감자수프", "즉석식품", "수프", 3900),
]

DEULKKOT_FOODS = [
    ("들깨미역국", "국·탕", "국", 6900), ("소고기무국", "국·탕", "국", 6900),
    ("버섯불고기", "반찬", "불고기", 10900), ("곤드레나물밥", "즉석밥", "나물밥", 5900),
    ("묵은지볶음", "반찬", "볶음", 7900),
]

LUMIERE_APPLIANCES = [
    ("무선청소기", "청소가전", "청소기", 249000), ("공기청정기", "계절가전", "공기청정기", 329000),
    ("초음파가습기", "계절가전", "가습기", 89000), ("전기포트", "주방가전", "전기포트", 59000),
    ("미니오븐", "주방가전", "오븐", 149000), ("서큘레이터", "계절가전", "서큘레이터", 119000),
    ("핸디스팀다리미", "생활가전", "다리미", 79000), ("디지털주방저울", "주방가전", "주방저울", 39900),
    ("멀티전기그릴", "주방가전", "전기그릴", 139000), ("음식물처리기", "주방가전", "음식물처리기", 499000),
]

MONOAIR_APPLIANCES = [
    ("BLDC헤어드라이어", "이미용가전", "헤어드라이어", 129000),
    ("팝업토스터", "주방가전", "토스터", 69000),
    ("음파전동칫솔", "이미용가전", "전동칫솔", 89000),
    ("무선미니선풍기", "계절가전", "선풍기", 39900),
    ("스마트멀티쿠커", "주방가전", "멀티쿠커", 159000),
]

BRANDS = [
    {"brand": "솔담건강", "prefix": "SDFD", "team": "식품팀", "items": SOLDAM_FOODS, "monthly": 1_000_000_000, "segment": "food"},
    {"brand": "한결웰빙", "prefix": "HWFD", "team": "식품팀", "items": HANGYEOL_FOODS, "monthly": 300_000_000, "segment": "food"},
    {"brand": "루미에르홈", "prefix": "LHAP", "team": "가전팀", "items": LUMIERE_APPLIANCES, "monthly": 100_000_000, "segment": "appliance"},
    {"brand": "들꽃찬", "prefix": "DCFD", "team": "식품팀", "items": DEULKKOT_FOODS, "monthly": 80_000_000, "segment": "food"},
    {"brand": "모노에어", "prefix": "MAAP", "team": "가전팀", "items": MONOAIR_APPLIANCES, "monthly": 50_000_000, "segment": "appliance"},
]


def alpha_code(number: int, width: int = 4) -> str:
    chars = []
    for _ in range(width):
        number, remainder = divmod(number, 26)
        chars.append(chr(65 + remainder))
    return "".join(reversed(chars))


def period_dates() -> list[date]:
    current = date(2025, 8, 1)
    result = []
    while current <= date(2026, 7, 31):
        result.append(current)
        current += timedelta(days=1)
    return result


def appliance_variants(brand_name: str, item_index: int) -> list[tuple[str, str, float, int]]:
    palettes = [
        ("화이트", "차콜", "베이지"), ("화이트", "실버", "블랙"),
        ("화이트", "민트", "베이지"), ("베이지", "네이비", "화이트"),
    ]
    colors = palettes[item_index % len(palettes)]
    if brand_name == "루미에르홈":
        return [("단품", colors[0], 1.00, 1), ("단품", colors[1], 1.00, 1), ("본품+소모품", colors[2], 1.10, 1)]
    return [("단품", colors[0], 1.00, 1), ("단품", colors[1], 1.00, 1),
            ("2개 세트", colors[0], 1.80, 2), ("2개 세트", colors[1], 1.80, 2)]


def build_products() -> tuple[list[dict[str, str]], dict[str, list[dict[str, Any]]]]:
    rows = []
    by_brand = defaultdict(list)
    product_number = 100001
    for brand in BRANDS:
        for item_index, (name, category2, category3, base_price) in enumerate(brand["items"]):
            item_id = brand["prefix"] + alpha_code(item_index)
            variants = [("", "", 1.0, 1)] if brand["segment"] == "food" else appliance_variants(brand["brand"], item_index)
            for variant_index, (category4, color, price_factor, unit_scale) in enumerate(variants):
                product_id = str(product_number)
                product_number += 1
                unit_price = round(base_price * price_factor / 100) * 100
                row = {
                    "product_id": product_id, "item_id": item_id, "item_seq": str(item_index + 1),
                    "team_name": brand["team"], "brand_name": brand["brand"],
                    "category_name1": "식품" if brand["segment"] == "food" else "가전",
                    "category_name2": category2, "category_name3": category3,
                    "category_name4": category4, "color": color,
                    "product_name": f"{brand['brand']} {name}",
                    "unit_name": "개", "unit_scale": str(unit_scale),
                }
                rows.append(row)
                by_brand[brand["brand"]].append({**row, "unit_price": unit_price,
                                                    "popularity": 1 / ((item_index + 1) ** 0.85),
                                                    "variant_weight": 1.0 if variant_index < 2 else 0.35})
    return rows, by_brand


def monthly_targets(brand: dict) -> dict[tuple[int, int], int]:
    factors = FOOD_MONTH if brand["segment"] == "food" else APPLIANCE_MONTH
    months = [(2025, month) for month in range(8, 13)] + [(2026, month) for month in range(1, 8)]
    normalizer = sum(factors[month] for _, month in months) / 12
    values = [round(brand["monthly"] * factors[month] / normalizer / 100) * 100 for _, month in months]
    values[-1] += brand["monthly"] * 12 - sum(values)
    return dict(zip(months, values))


def make_row(product_id: str, shop_id: str, status: int, quantity: int, payment: int,
            supply: int, supply_cost: int, delivery: int, ad_cost: int,
            extra_cost: int, order_date: date) -> dict[str, str]:
    return {"product_id": product_id, "shop_id": shop_id, "order_status": str(status),
            "sku_quantity": str(quantity), "payment_amount": str(payment),
            "supply_amount": str(supply), "supply_cost": str(supply_cost),
            "delivery_fee": str(delivery), "ad_cost": str(ad_cost),
            "extra_cost": str(extra_cost), "order_date": order_date.isoformat()}


def status_rows(normal_rows: list[dict[str, str]], product_meta: dict[str, dict[str, Any]], rng: random.Random) -> list[dict[str, str]]:
    rows = []
    schedules = [(1, 97), (2, 233), (3, 71), (5, 487), (6, 191), (7, 389)]
    for index, normal in enumerate(normal_rows):
        meta = product_meta[normal["product_id"]]
        unit_cost = round(meta["unit_price"] * 0.58 / 100) * 100
        for status, modulus in schedules:
            if (index + int(normal["product_id"])) % modulus != 0:
                continue
            quantity = 1 if status in {1, 2, 6} else 0
            supply_cost = unit_cost if status in {2, 6} else 0
            delivery = rng.choice([2000, 2500, 3000, 3500, 4000, 4500, 5000]) if status in {1, 2, 5, 7} else 0
            rows.append(make_row(normal["product_id"], normal["shop_id"], status, quantity,
                                0, 0, supply_cost, delivery, 0, 0,
                                date.fromisoformat(normal["order_date"])))
    return rows


def build_sales(by_brand: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    rng = random.Random(SEED)
    dates = period_dates()
    normal_rows = []
    cost_rows = []
    product_meta = {str(sku["product_id"]): sku for skus in by_brand.values() for sku in skus}
    for brand in BRANDS:
        skus = by_brand[brand["brand"]]
        dow_factors = FOOD_DOW if brand["segment"] == "food" else APPLIANCE_DOW
        for (year, month), target in monthly_targets(brand).items():
            candidates = []
            month_dates = [day for day in dates if (day.year, day.month) == (year, month)]
            promo_days = {month_dates[4], month_dates[min(14, len(month_dates) - 1)], month_dates[-3]}
            for day in month_dates:
                for sku in skus:
                    promotion = day in promo_days and int(sku["item_seq"]) <= max(1, len(brand["items"]) // 5)
                    unit_price = round(int(sku["unit_price"]) * (0.9 if promotion else 1.0) / 100) * 100
                    weight = float(sku["popularity"]) * float(sku["variant_weight"]) * dow_factors[day.isoweekday()] * (0.82 + rng.random() * 0.36)
                    candidates.append({"day": day, "sku": sku, "unit_price": unit_price,
                                        "weight": weight, "quantity": 0})
            # Guarantee at least one sale for every SKU each month so all
            # category/color/package variants are represented in sales_daily.
            guaranteed = {}
            for candidate in candidates:
                product_id = candidate["sku"]["product_id"]
                if product_id not in guaranteed:
                    candidate["quantity"] = 1
                    guaranteed[product_id] = candidate
            guaranteed_revenue = sum(candidate["unit_price"] for candidate in guaranteed.values())

            scale = (target - guaranteed_revenue) / sum(
                candidate["weight"] for candidate in candidates
            )
            for candidate in candidates:
                # Popularity controls revenue share; quantity is derived from
                # the SKU's stable unit price rather than the other way around.
                expected = scale * candidate["weight"] / candidate["unit_price"]
                candidate["quantity"] += math.floor(expected)
                candidate["fraction"] = expected - math.floor(expected)

            current = sum(candidate["quantity"] * candidate["unit_price"] for candidate in candidates)
            residual = target - current
            ranked = sorted(candidates, key=lambda value: value["fraction"], reverse=True)
            # Largest-remainder allocation: rotate through all candidates so
            # low prices cannot absorb the entire monthly rounding remainder.
            while True:
                progress = False
                for candidate in ranked:
                    if candidate["unit_price"] <= residual:
                        candidate["quantity"] += 1
                        residual -= candidate["unit_price"]
                        progress = True
                if not progress:
                    break
            for candidate in candidates:
                quantity = candidate["quantity"]
                if quantity <= 0:
                    continue
                sku = candidate["sku"]
                payment = candidate["unit_price"] * quantity
                supply = round(payment * 0.925 / 100) * 100
                unit_cost = round(candidate["unit_price"] * (0.57 + rng.random() * 0.04) / 100) * 100
                supply_cost = unit_cost * quantity
                delivery = rng.choice([2000, 2500, 3000, 3500, 4000, 4500, 5000])
                shop_id = SHOPS[(candidate["day"].toordinal() + int(sku["product_id"])) % len(SHOPS)][1]
                normal_rows.append(make_row(sku["product_id"], shop_id, 0, quantity, payment,
                                            supply, supply_cost, delivery, 0, 0, candidate["day"]))
            promoted = sorted(skus, key=lambda sku: int(sku["item_seq"]))[:max(1, len(brand["items"]) // 5)]
            for offset, sku in enumerate(promoted):
                day = month_dates[min(6 + offset, len(month_dates) - 1)]
                ad_cost = round(target * (0.002 + 0.0003 * offset) / 100) * 100
                cost_rows.append(make_row(str(sku["product_id"]), SHOPS[offset % len(SHOPS)][1], 8, 0,
                                        0, 0, 0, 0, ad_cost, 0, day))
            expense_skus = promoted[:max(1, len(promoted) // 4)]
            for offset, sku in enumerate(expense_skus):
                day = month_dates[min(20 + offset, len(month_dates) - 1)]
                extra_cost = round((180000 + target * 0.00015 * (offset + 1)) / 100) * 100
                cost_rows.append(make_row(str(sku["product_id"]), SHOPS[(offset + 2) % len(SHOPS)][1], 9, 0,
                                        0, 0, 0, 0, 0, extra_cost, day))
    return normal_rows + status_rows(normal_rows, product_meta, rng) + cost_rows


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / name).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    products, by_brand = build_products()
    sales = build_sales(by_brand)
    shops = [{"shop_seq": str(seq), "shop_id": shop_id, "shop_alias": alias,
            "shop_name": name, "corp_name": "데모 유통", "shop_group": group,
            "shop_url": url, "scm_url": "", "commission_rate": f"{rate:.5f}"}
                for seq, shop_id, alias, name, group, url, rate in SHOPS]
    months = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]
    extra = [{"product_id": "199999", "shop_id": SHOPS[index % len(SHOPS)][1],
            "profit": str((-1 if index % 3 else 1) * (250000 + index * 40000)),
            "ymd": date(2025 if month >= 8 else 2026, month, 28).isoformat()}
                for index, month in enumerate(months)]
    write_csv("demo.product.csv", products, list(products[0]))
    write_csv("demo.sales_daily.csv", sales, list(sales[0]))
    write_csv("demo.shop.csv", shops, list(shops[0]))
    write_csv("demo.extra_profit.csv", extra, list(extra[0]))
    print(f"items={len({row['item_id'] for row in products})} skus={len(products)} sales={len(sales)} shops={len(shops)} extra_profit={len(extra)}")


if __name__ == "__main__":
    main()
