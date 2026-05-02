# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Product Reviews (From Flat File)

# COMMAND ----------

from pyspark.sql import functions as F
import sys
sys.path.append('/Workspace/Repos/ecommerce-data-lakehouse/databricks')
from utils.transformations import apply_quality_checks, add_audit_columns, deduplicate
from utils.config import Config
from delta.tables import DeltaTable

# COMMAND ----------

bronze_path = f'abfss://bronze@{Config.STORAGE_ACCOUNT}.dfs.core.windows.net/product_reviews/'
df = spark.read.parquet(bronze_path)

df_quality = apply_quality_checks(df, ['ReviewID', 'ProductID', 'CustomerID', 'Rating'])
df_quality = df_quality.withColumn('is_quarantined',
    F.when((F.col('Rating') < 1) | (F.col('Rating') > 5), True).otherwise(F.col('is_quarantined')))
df_quality = df_quality.withColumn('Rating', F.col('Rating').cast('int')).withColumn('ReviewDate', F.col('ReviewDate').cast('date'))
df_final = add_audit_columns(df_quality)
df_dedup = deduplicate(df_final, ['ReviewID'], 'ReviewDate')

target = Config.get_silver_table('product_reviews')
if DeltaTable.isDeltaTable(spark, target):
    DeltaTable.forName(spark, target).alias('t').merge(df_dedup.alias('s'), 't.ReviewID = s.ReviewID').whenNotMatchedInsertAll().execute()
else:
    df_dedup.write.format('delta').mode('overwrite').saveAsTable(target)
print('Silver product_reviews updated')
