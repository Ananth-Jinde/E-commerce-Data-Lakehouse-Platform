# Databricks notebook source
import dlt
from pyspark.sql import functions as F

@dlt.table(name="dim_customer", comment="Customer dimension - current records only",
    table_properties={"quality": "gold"})
@dlt.expect_or_drop("valid_key", "customer_key IS NOT NULL")
@dlt.expect_or_drop("valid_email", "Email IS NOT NULL")
def dim_customer():
    return (spark.table("ecommerce_catalog.silver.customers")
        .filter((F.col("is_current") == True) & (F.col("is_quarantined") == False))
        .select("customer_key", F.col("CustomerID").alias("src_customer_id"),
            "FirstName", "LastName", "Email", "Phone", "Address", "City", "State", "ZipCode", "datasource"))
