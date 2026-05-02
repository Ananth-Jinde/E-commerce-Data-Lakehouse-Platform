# Databricks notebook source
import dlt
from pyspark.sql import functions as F


@dlt.table(
    name="fact_orders",
    comment="Order fact table. Grain: one row per order item.",
    table_properties={"quality": "gold"},
)
@dlt.expect_or_drop("valid_order", "order_key IS NOT NULL")
@dlt.expect_or_drop("valid_customer", "FK_CustomerKey IS NOT NULL")
@dlt.expect("positive_amount", "LineTotal > 0", on_violation="WARN")
def fact_orders():
    orders = spark.table("ecommerce_catalog.silver.orders").filter(F.col("is_quarantined") == False)
    items = spark.table("ecommerce_catalog.silver.order_items").filter(F.col("is_quarantined") == False)
    return (
        items.alias("oi")
        .join(orders.alias("o"), F.col("oi.FK_OrderKey") == F.col("o.order_key"), "inner")
        .select(
            F.col("oi.order_item_key"),
            F.col("o.order_key"),
            F.col("o.FK_CustomerKey"),
            F.col("oi.FK_ProductKey"),
            F.date_format(F.col("o.OrderDate"), "yyyyMMdd").cast("int").alias("FK_DateKey"),
            F.col("oi.Quantity"),
            F.col("oi.UnitPrice"),
            F.col("oi.Discount"),
            F.col("oi.LineTotal"),
            F.col("o.TotalAmount").alias("OrderTotalAmount"),
            F.col("o.PaymentMethod"),
            F.col("o.Status").alias("OrderStatus"),
            F.col("o.datasource"),
            F.current_timestamp().alias("refreshed_at"),
        )
    )
