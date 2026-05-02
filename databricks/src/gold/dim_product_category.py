# Databricks notebook source
import dlt
from pyspark.sql import functions as F

@dlt.table(name="dim_product_category", comment="Product category hierarchy",
    table_properties={"quality": "gold"})
@dlt.expect_or_drop("valid_key", "category_key IS NOT NULL")
def dim_product_category():
    return (spark.table("ecommerce_catalog.silver.product_categories")
        .filter(F.col("is_quarantined") == False)
        .select("category_key", F.col("CategoryID").alias("src_category_id"),
            "CategoryName", "ParentCategory", "datasource"))
