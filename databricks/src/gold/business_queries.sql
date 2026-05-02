-- Business Analytics Queries (Gold Layer Star Schema)

-- 1. Monthly Revenue Trend
SELECT d.year, d.month_name, COUNT(DISTINCT f.order_key) AS total_orders,
    ROUND(SUM(f.LineTotal), 2) AS total_revenue
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_date d ON f.FK_DateKey = d.date_key
GROUP BY d.year, d.month_name, d.month_number ORDER BY d.year, d.month_number;

-- 2. Top 10 Products by Revenue
SELECT p.ProductName, p.Category, SUM(f.Quantity) AS qty_sold,
    ROUND(SUM(f.LineTotal), 2) AS revenue
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_product p ON f.FK_ProductKey = p.product_key
GROUP BY p.ProductName, p.Category ORDER BY revenue DESC LIMIT 10;

-- 3. Customer Lifetime Value
SELECT c.customer_key, CONCAT(c.FirstName, ' ', c.LastName) AS name,
    c.State, COUNT(DISTINCT f.order_key) AS orders, ROUND(SUM(f.LineTotal), 2) AS clv
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_customer c ON f.FK_CustomerKey = c.customer_key
GROUP BY c.customer_key, c.FirstName, c.LastName, c.State ORDER BY clv DESC LIMIT 20;

-- 4. Revenue by Category (Quarterly)
SELECT p.Category, d.year, d.fiscal_quarter, ROUND(SUM(f.LineTotal), 2) AS revenue
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_product p ON f.FK_ProductKey = p.product_key
JOIN ecommerce_catalog.gold.dim_date d ON f.FK_DateKey = d.date_key
GROUP BY p.Category, d.year, d.fiscal_quarter ORDER BY d.year, d.fiscal_quarter;

-- 5. Payment Method Analysis
SELECT f.PaymentMethod, COUNT(DISTINCT f.order_key) AS orders,
    ROUND(AVG(f.OrderTotalAmount), 2) AS avg_order_value
FROM ecommerce_catalog.gold.fact_orders f GROUP BY f.PaymentMethod ORDER BY orders DESC;

-- 6. Store Comparison
SELECT f.datasource, d.year, ROUND(SUM(f.LineTotal), 2) AS revenue
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_date d ON f.FK_DateKey = d.date_key
GROUP BY f.datasource, d.year ORDER BY d.year;

-- 7. Weekend vs Weekday Sales
SELECT CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(DISTINCT f.order_key) AS orders, ROUND(SUM(f.LineTotal), 2) AS revenue
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_date d ON f.FK_DateKey = d.date_key
GROUP BY d.is_weekend;
