-- mart_category_finance : rentabilite par departement / categorie produit.
-- Angle controle de gestion : CA, profit, marge, remise moyenne, volume.
CREATE OR REPLACE TABLE mart_category_finance AS
SELECT
    department_name,
    category_name,
    COUNT(*)                                                  AS nb_lines,
    SUM(quantity)                                             AS units_sold,
    ROUND(SUM(sales), 2)                                      AS sales,
    ROUND(SUM(profit), 2)                                     AS profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 1)     AS margin_pct,
    -- Remise moyenne accordee (% du prix)
    ROUND(100.0 * AVG(discount_rate), 1)                      AS avg_discount_pct,
    -- Taux de retard de la categorie
    ROUND(100.0 * SUM(CASE WHEN is_late THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN is_canceled THEN 0 ELSE 1 END), 0), 1) AS late_rate_pct
FROM fct_sales
GROUP BY 1, 2
ORDER BY sales DESC;
