CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS demo;

-- Public demo dependency graph:
-- analytics.profit_daily -> analytics.profit_base
-- -> demo.sales_daily + demo.extra_profit
-- -> demo.product + demo.shop
CREATE TABLE IF NOT EXISTS demo.sales_daily (
    product_id text NOT NULL,
    shop_id text NOT NULL,
    order_status integer NOT NULL,
    sku_quantity numeric(14, 2),
    payment_amount numeric(14, 2),
    supply_amount numeric(14, 2),
    supply_cost numeric(14, 2),
    delivery_fee numeric(14, 2),
    ad_cost numeric(14, 2),
    extra_cost numeric(14, 2),
    order_date date NOT NULL
);

CREATE TABLE IF NOT EXISTS demo.extra_profit (
    product_id text NOT NULL,
    shop_id text NOT NULL,
    profit bigint NOT NULL,
    ymd date NOT NULL
);

CREATE TABLE IF NOT EXISTS demo.product (
    product_id text PRIMARY KEY,
    item_id text,
    item_seq bigint,
    team_name text,
    brand_name text,
    category_name1 text,
    category_name2 text,
    category_name3 text,
    category_name4 text,
    color text,
    product_name text,
    unit_name text,
    unit_scale numeric(14, 2)
);

CREATE TABLE IF NOT EXISTS demo.shop (
    shop_seq bigint PRIMARY KEY,
    shop_id text UNIQUE NOT NULL,
    shop_alias text,
    shop_name text,
    corp_name text,
    shop_group text,
    shop_url text,
    scm_url text,
    commission_rate numeric(8, 5)
);

CREATE INDEX IF NOT EXISTS demo_sales_daily_order_date_idx ON demo.sales_daily (order_date);
CREATE INDEX IF NOT EXISTS demo_sales_daily_product_date_idx ON demo.sales_daily (product_id, order_date);
CREATE INDEX IF NOT EXISTS demo_extra_profit_ymd_idx ON demo.extra_profit (ymd);

CREATE OR REPLACE FUNCTION analytics.profit_base(ds_start_date date, ds_end_date date)
RETURNS TABLE (
    product_id text, shop_id text, order_status integer, sku_quantity numeric,
    payment_amount numeric, supply_amount numeric, supply_cost numeric,
    delivery_fee numeric, margin_amount numeric, ad_cost numeric,
    extra_cost numeric, profit numeric, order_date date
)
LANGUAGE sql STABLE AS $$
    WITH sales_daily AS (
        SELECT product_id, shop_id, order_status,
            CASE WHEN order_status = 0 THEN COALESCE(sku_quantity, 0) ELSE 0 END AS sku_quantity,
            CASE WHEN shop_id = 'adop9000' THEN 0 WHEN order_status = 0 THEN COALESCE(payment_amount, 0) ELSE 0 END AS payment_amount,
            CASE WHEN order_status = 0 THEN COALESCE(supply_amount, 0) ELSE 0 END AS supply_amount,
            CASE WHEN order_status IN (0, 2, 6) THEN COALESCE(supply_cost, 0) ELSE 0 END AS supply_cost,
            CASE WHEN order_status IN (0, 1, 2, 5, 7) THEN COALESCE(delivery_fee, 0) ELSE 0 END AS delivery_fee,
            COALESCE(ad_cost, 0) AS ad_cost, COALESCE(extra_cost, 0) AS extra_cost, order_date
        FROM demo.sales_daily
        WHERE order_date BETWEEN ds_start_date AND ds_end_date
    )
    SELECT product_id, shop_id, order_status, sku_quantity, payment_amount, supply_amount,
        supply_cost, delivery_fee, supply_amount - supply_cost - delivery_fee AS margin_amount,
        ad_cost, extra_cost, supply_amount - supply_cost - delivery_fee - ad_cost - extra_cost AS profit, order_date
    FROM sales_daily
$$;

CREATE OR REPLACE FUNCTION analytics.profit_daily(ds_start_date date, ds_end_date date)
RETURNS TABLE (
    product_id text, item_id text, item_seq bigint, team_name text, brand_name text,
    category_name1 text, category_name2 text, category_name3 text, category_name4 text,
    color text, product_name text, category_unit_name text, shop_id text, shop_group text,
    shop_name text, order_status text, unit_quantity numeric, sku_quantity numeric,
    payment_amount numeric, supply_amount numeric, supply_cost numeric, delivery_fee numeric,
    margin_amount numeric, ad_cost numeric, extra_cost numeric, profit numeric, order_date date
)
LANGUAGE sql STABLE AS $$
    WITH order_status_mapping(code, label) AS (
        VALUES (0, '정상'), (1, '반품'), (2, '교환'), (3, '취소'),
               (5, '빈박스'), (6, '증정'), (7, '배송'), (8, '광고'), (9, '비용')
    ), enriched_sales AS (
        SELECT fact.product_id, COALESCE(item.item_id, 'NA-AAAAAA-00') AS item_id,
            COALESCE(item.item_seq, 99999999)::bigint AS item_seq,
            COALESCE(item.team_name, '담당팀 없음') AS team_name,
            COALESCE(item.brand_name, '브랜드 없음') AS brand_name,
            COALESCE(item.category_name1, '-') AS category_name1, COALESCE(item.category_name2, '-') AS category_name2,
            COALESCE(item.category_name3, '-') AS category_name3, COALESCE(item.category_name4, '-') AS category_name4,
            COALESCE(item.color, '-') AS color, COALESCE(item.product_name, '매칭 불가 상품') AS product_name,
            COALESCE(CASE WHEN item.unit_name IS NULL THEN item.category_name3 ELSE item.category_name3 || ' (' || item.unit_name || ')' END, '-') AS category_unit_name,
            fact.shop_id, COALESCE(shop.shop_group, '-') AS shop_group, COALESCE(shop.shop_alias, '-') AS shop_name,
            COALESCE(status.label, '알 수 없음') AS order_status,
            COALESCE(fact.sku_quantity * COALESCE(item.unit_scale, 1), 0) AS unit_quantity,
            fact.sku_quantity, fact.payment_amount, fact.supply_amount, fact.supply_cost, fact.delivery_fee,
            fact.margin_amount, fact.ad_cost, fact.extra_cost, fact.profit, fact.order_date
        FROM analytics.profit_base(ds_start_date, ds_end_date) AS fact
        LEFT JOIN demo.product AS item ON fact.product_id = item.product_id
        LEFT JOIN demo.shop AS shop ON fact.shop_id = shop.shop_id
        LEFT JOIN order_status_mapping AS status ON fact.order_status = status.code
    ), extra_profit_daily AS (
        SELECT extra.product_id, 'NA-AAAAAA-00' AS item_id, 99999999::bigint AS item_seq,
            '담당팀 없음' AS team_name, '브랜드 없음' AS brand_name,
            '-' AS category_name1, '-' AS category_name2, '-' AS category_name3, '-' AS category_name4,
            '-' AS color, '매칭 불가 상품' AS product_name, '-' AS category_unit_name,
            extra.shop_id, COALESCE(shop.shop_group, '-') AS shop_group, COALESCE(shop.shop_alias, '-') AS shop_name,
            '정상' AS order_status, 0::numeric AS unit_quantity, 0::numeric AS sku_quantity,
            0::numeric AS payment_amount, 0::numeric AS supply_amount, 0::numeric AS supply_cost,
            0::numeric AS delivery_fee, 0::numeric AS margin_amount, 0::numeric AS ad_cost,
            0::numeric AS extra_cost, extra.profit::numeric AS profit, extra.ymd AS order_date
        FROM demo.extra_profit AS extra
        LEFT JOIN demo.shop AS shop ON extra.shop_id = shop.shop_id
        WHERE extra.ymd BETWEEN ds_start_date AND ds_end_date
    )
    SELECT * FROM enriched_sales UNION ALL SELECT * FROM extra_profit_daily
$$;
