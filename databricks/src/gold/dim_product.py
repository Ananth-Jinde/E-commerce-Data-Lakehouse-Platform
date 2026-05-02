# Databricks notebook source
import dlt
from pyspark.sql import functions as F

@dlt.table(name="dim_product", comment="Product dimension with current pricing",
    table_properties={"quality": "gold"})
@dlt.expect_or_drop("valid_key", "product_key IS NOT NULL")
@dlt.expect_or_drop("positive_price", "Price > 0")
def dim_product():
    return (spark.table("ecommerce_catalog.silver.products")
        .filter((F.col("is_current") == True) & (F.col("is_quarantined") == False))
        .select("product_key", F.col("ProductID").alias("src_product_id"),
            "ProductName", "Category", "SubCategory", "Price", "StockQty", "Supplier", "datasource"))
