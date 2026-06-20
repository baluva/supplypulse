-- mart_shipping_mode : performance logistique par mode d'expedition.
-- Met en evidence le paradoxe metier : les modes "rapides" sont les plus en
-- retard (insight cle du dataset).
CREATE OR REPLACE TABLE mart_shipping_mode AS
SELECT
    shipping_mode,
    COUNT(*)                                                  AS nb_lines,
    ROUND(100.0 * SUM(CASE WHEN is_late THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN is_canceled THEN 0 ELSE 1 END), 0), 1) AS late_rate_pct,
    ROUND(AVG(days_real), 2)                                  AS avg_days_real,
    ROUND(AVG(days_scheduled), 2)                             AS avg_days_scheduled,
    ROUND(AVG(delay_days), 2)                                 AS avg_delay_days,
    ROUND(SUM(sales), 2)                                      AS sales,
    ROUND(SUM(profit), 2)                                     AS profit
FROM fct_sales
GROUP BY 1
ORDER BY late_rate_pct DESC;
