-- stg_sales : modele de staging au grain "ligne de commande".
-- Renomme les colonnes du CSV brut en snake_case, parse les dates (format
-- M/D/YYYY HH:MM), type les mesures et derive les flags logistiques utilises
-- par les marts. Source : table brute dataco_raw (DataCo Smart Supply Chain).
CREATE OR REPLACE VIEW stg_sales AS
SELECT
    "Order Id"                                                   AS order_id,
    "Order Item Id"                                              AS order_item_id,
    strptime("order date (DateOrders)", '%m/%d/%Y %H:%M')       AS order_ts,
    strptime("shipping date (DateOrders)", '%m/%d/%Y %H:%M')    AS shipping_ts,
    DATE_TRUNC('month', strptime("order date (DateOrders)", '%m/%d/%Y %H:%M')) AS order_month,
    CAST(strftime(strptime("order date (DateOrders)", '%m/%d/%Y %H:%M'), '%Y') AS INTEGER) AS order_year,

    -- Logistique
    CAST("Days for shipping (real)"      AS INTEGER)             AS days_real,
    CAST("Days for shipment (scheduled)" AS INTEGER)            AS days_scheduled,
    CAST("Days for shipping (real)" AS INTEGER)
        - CAST("Days for shipment (scheduled)" AS INTEGER)      AS delay_days,
    "Delivery Status"                                           AS delivery_status,
    "Shipping Mode"                                             AS shipping_mode,
    CAST("Late_delivery_risk" AS INTEGER)                       AS late_risk,
    -- Flags derives
    ("Delivery Status" = 'Late delivery')                       AS is_late,
    ("Delivery Status" IN ('Shipping on time', 'Advance shipping')) AS is_on_time,
    ("Delivery Status" = 'Shipping canceled')                   AS is_canceled,

    -- Dimensions
    "Order Status"                                              AS order_status,
    "Market"                                                    AS market,
    "Order Region"                                              AS order_region,
    "Order Country"                                             AS order_country,
    "Customer Segment"                                          AS customer_segment,
    "Department Name"                                           AS department_name,
    "Category Name"                                             AS category_name,
    "Product Name"                                              AS product_name,
    "Type"                                                      AS payment_type,

    -- Mesures financieres (reelles)
    CAST("Sales" AS DOUBLE)                                     AS sales,
    CAST("Order Item Total" AS DOUBLE)                          AS order_total,
    CAST("Order Profit Per Order" AS DOUBLE)                    AS profit,
    CAST("Order Item Profit Ratio" AS DOUBLE)                   AS profit_ratio,
    CAST("Order Item Discount" AS DOUBLE)                       AS discount,
    CAST("Order Item Discount Rate" AS DOUBLE)                  AS discount_rate,
    CAST("Order Item Quantity" AS INTEGER)                      AS quantity
FROM dataco_raw;
