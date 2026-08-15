-- Static, reviewed public data import. No procedural or generated SQL data.
TRUNCATE TABLE demo.sales_daily, demo.extra_profit, demo.product, demo.shop;

COPY demo.product (
    product_id, item_id, item_seq, team_name, brand_name,
    category_name1, category_name2, category_name3, category_name4,
    color, product_name, unit_name, unit_scale
) FROM '/docker-entrypoint-initdb.d/data/demo.product.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

COPY demo.shop (
    shop_seq, shop_id, shop_alias, shop_name, corp_name,
    shop_group, shop_url, scm_url, commission_rate
) FROM '/docker-entrypoint-initdb.d/data/demo.shop.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

COPY demo.sales_daily (
    product_id, shop_id, order_status, sku_quantity, payment_amount,
    supply_amount, supply_cost, delivery_fee, ad_cost, extra_cost, order_date
) FROM '/docker-entrypoint-initdb.d/data/demo.sales_daily.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

COPY demo.extra_profit (product_id, shop_id, profit, ymd)
FROM '/docker-entrypoint-initdb.d/data/demo.extra_profit.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

ANALYZE demo.sales_daily;
ANALYZE demo.extra_profit;
ANALYZE demo.product;
ANALYZE demo.shop;
