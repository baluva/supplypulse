-- mart_monthly_performance : KPIs supply chain & finance agreges par mois.
-- Vue de pilotage : volume, ventes, profit, marge, taux de retard, delai moyen.
CREATE OR REPLACE TABLE mart_monthly_performance AS
SELECT
    order_month,
    order_year,
    COUNT(DISTINCT order_id)                                   AS nb_orders,
    COUNT(*)                                                   AS nb_lines,
    ROUND(SUM(sales), 2)                                       AS sales,
    ROUND(SUM(profit), 2)                                      AS profit,
    -- Marge nette (% du CA)
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 1)      AS margin_pct,
    -- Taux de retard sur les livraisons non annulees
    ROUND(100.0 * SUM(CASE WHEN is_late THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN is_canceled THEN 0 ELSE 1 END), 0), 1) AS late_rate_pct,
    -- Taux a l'heure (a temps + en avance)
    ROUND(100.0 * SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN is_canceled THEN 0 ELSE 1 END), 0), 1) AS on_time_rate_pct,
    -- Ecart moyen entre delai reel et planifie (jours)
    ROUND(AVG(delay_days), 2)                                  AS avg_delay_days
FROM fct_sales
GROUP BY 1, 2
ORDER BY 1;
