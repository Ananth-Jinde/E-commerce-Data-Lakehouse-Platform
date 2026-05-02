# Databricks notebook source
import dlt
from pyspark.sql import functions as F


@dlt.table(
    name="dim_date",
    comment="Generated date dimension (2023-2026). Not from any source system.",
    table_properties={"quality": "gold"},
)
def dim_date():
    df = spark.sql("SELECT explode(sequence(to_date('2023-01-01'), to_date('2026-12-31'), interval 1 day)) AS full_date")
    return (
        df
        .withColumn("date_key", F.date_format("full_date", "yyyyMMdd").cast("int"))
        .withColumn("day_of_week", F.dayofweek("full_date"))
        .withColumn("day_name", F.date_format("full_date", "EEEE"))
        .withColumn("month_number", F.month("full_date"))
        .withColumn("month_name", F.date_format("full_date", "MMMM"))
        .withColumn("quarter", F.quarter("full_date"))
        .withColumn("year", F.year("full_date"))
        .withColumn("is_weekend", F.when(F.dayofweek("full_date").isin(1, 7), True).otherwise(False))
        .withColumn("fiscal_quarter", F.concat(F.lit("FQ"), F.quarter("full_date")))
        .withColumn("fiscal_year",
            F.when(F.month("full_date") >= 4, F.year("full_date") + 1)
            .otherwise(F.year("full_date")))
    )
