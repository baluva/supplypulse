-- mart_region : performance commerciale & logistique par marche / region.
-- Croise les ventes, le profit et le taux de retard a la maille geographique.
CREATE OR REPLACE TABLE mart_region AS
SELECT
    market,
    order_region,
    COUNT(DISTINCT order_id)                                  AS nb_orders,
    ROUND(SUM(sales), 2)                                      AS sales,
    ROUND(SUM(profit), 2)                                     AS profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 1)     AS margin_pct,
    ROUND(100.0 * SUM(CASE WHEN is_late THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN is_canceled THEN 0 ELSE 1 END), 0), 1) AS late_rate_pct
FROM fct_sales
GROUP BY 1, 2
ORDER BY sales DESC;
