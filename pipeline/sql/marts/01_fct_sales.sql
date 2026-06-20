-- fct_sales : table de faits conforme au grain ligne de commande.
-- C'est la table servie au dashboard (filtrage interactif) et la base de tous
-- les agregats. Materialisee pour la performance.
CREATE OR REPLACE TABLE fct_sales AS
SELECT
    order_id,
    order_item_id,
    order_ts,
    shipping_ts,
    order_month,
    order_year,
    days_real,
    days_scheduled,
    delay_days,
    delivery_status,
    shipping_mode,
    late_risk,
    is_late,
    is_on_time,
    is_canceled,
    order_status,
    market,
    order_region,
    order_country,
    customer_segment,
    department_name,
    category_name,
    product_name,
    payment_type,
    sales,
    order_total,
    profit,
    profit_ratio,
    discount,
    discount_rate,
    quantity
FROM stg_sales
-- On ecarte les rares lignes a la date non parsable
WHERE order_ts IS NOT NULL;
