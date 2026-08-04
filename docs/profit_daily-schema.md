# `profit_daily` 스키마 상세 설명

이 문서는 공개 데모가 기대하는 일반화된 테이블 함수 계약입니다. 특정 회사의 실제 스키마 문서가 아니며, 실제 데이터베이스에 적용할 때는 자신의 반환 컬럼과 계산 규칙을 검증해야 합니다.

## 호출 계약

```sql
SELECT *
FROM schema.profit_daily(
  DS_START_DATE => DATE '2026-07-01',
  DS_END_DATE => DATE '2026-07-31'
);
```

에이전트는 함수 이름을 `PROFIT_DAILY_FUNCTION`에서 읽고 `schema.function` 정규식으로 검증합니다. 날짜 값은 SQL parameter로 전달합니다.

## 컬럼 사전

| 컬럼 | 표시명 | 유형 | 분석 의미 |
|---|---|---|---|
| `product_id` | 상품코드 | 차원 | SKU 또는 상품코드 |
| `item_id` | 대표상품코드 | 차원 | 여러 SKU를 묶는 대표상품코드 |
| `item_seq` | 순번 | 차원 | 대표상품 내 순번 |
| `team_name` | 담당팀 | 차원 | 상품 또는 판매를 담당하는 조직 |
| `brand_name` | 브랜드명 | 차원 | 브랜드. 고정 enum이 아닐 수 있음 |
| `category_name1` | 대분류 | 차원 | 가장 상위 상품 분류 |
| `category_name2` | 중분류 | 차원 | 대분류 하위 분류 |
| `category_name3` | 소분류 | 차원 | 대표상품 분석에 자주 사용하는 분류 |
| `category_name4` | 세분류 | 차원 | SKU 수준의 세부 분류 |
| `color` | 색상 | 차원 | 상품 색상 |
| `product_name` | 상품명 | 차원 | 상품 이름 |
| `category_unit_name` | 단위상품명 | 차원 | 단위 또는 구성 정보가 포함된 상품명 |
| `shop_id` | 판매처코드 | 차원 | 판매처 코드 |
| `shop_group` | 쇼핑몰 그룹 | 차원 | 판매처를 묶은 상위 그룹 |
| `shop_name` | 채널 | 차원 | 고객에게 노출되는 판매 채널 |
| `order_status` | 주문상태 | 차원 | 정상·반품·광고·비용 등 상태 코드 |
| `order_date` | 주문일 | 차원 | 일별 추이와 기간 필터 기준 |
| `unit_quantity` | 세트수량 | 지표 | 세트·박스 기준 수량 |
| `sku_quantity` | 확정수량 | 지표 | SKU 기준 확정 수량 |
| `payment_amount` | 결제금액 | 지표 | 고객 결제 기준 금액 |
| `supply_amount` | 정산금액 | 지표 | 정산 기준 금액 |
| `supply_cost` | 원가*수량 | 지표 | 원가와 수량을 반영한 합계 |
| `delivery_fee` | 배송비 | 지표 | 배송에 관련된 비용 |
| `margin_amount` | 마진금액 | 지표 | 정산금액에서 원가와 배송비를 뺀 금액 |
| `ad_cost` | 광고비 | 지표 | 광고 집행 비용 |
| `extra_cost` | 지출액 | 지표 | 광고비 이외의 추가 비용·고정지출 |
| `profit` | 영업이익 | 지표 | 마진금액에서 광고비와 지출액을 뺀 금액 |

## 계층과 집계 단위

- `item_id`와 `item_seq`는 대표상품 수준의 코드와 순번입니다.
- `category_name3`까지는 대표상품 단위 분석에 활용할 수 있습니다.
- `category_name4`, `product_id`, `color`는 SKU 단위 분석에 적합합니다.
- `shop_id`는 판매처코드이고 `shop_name`은 사람이 읽는 채널명입니다.
- `brand_name`은 새 값이 추가될 수 있으므로 코드에 브랜드 목록을 하드코딩하지 않습니다.

## 금액 계산

```text
margin_amount = supply_amount - supply_cost - delivery_fee
profit = supply_amount - supply_cost - delivery_fee - ad_cost - extra_cost
profit = margin_amount - ad_cost - extra_cost
```

`payment_amount`와 `supply_amount`는 서로 다른 개념일 수 있습니다. 수수료·할인·정산 조정이 데이터 파이프라인에서 어떻게 처리되는지 확인한 뒤 사용자 질문에 답해야 합니다.

## 주문 상태

`semantic_schema.yml`에는 테스트를 위한 일반 예시 코드가 있습니다. 실제 상태 코드가 다르면 다음 항목을 함께 수정해야 합니다.

1. `semantic_schema.yml`의 `order_statuses`
2. README의 주문 상태 표
3. 데이터 파이프라인의 금액·수량 부호 규칙
4. 테스트 fixture 및 질문 예시

특히 반품·교환·취소가 음수로 저장되는지, 별도 상태 행으로 저장되는지에 따라 영업이익 계산 결과가 달라질 수 있습니다.

## 실제 데이터 연결 전 점검표

- [ ] 함수가 `date, date` 두 매개변수를 받는가?
- [ ] 반환 컬럼 이름과 타입이 문서와 일치하는가?
- [ ] `profit`과 `margin_amount`가 이미 계산된 컬럼인가?
- [ ] 반품·취소·교환의 부호와 상태 코드가 정의되어 있는가?
- [ ] `brand_name`, `shop_name`, `product_name`에 개인정보가 들어 있지 않은가?
- [ ] 에이전트용 DB 계정이 read-only인가?
- [ ] 외부 공개 환경에서 실제 행·상품명·브랜드명이 노출되지 않는가?
