# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Product Categories (Full Load)

# COMMAND ----------

from pyspark.sql import functions as F
import sys
sys.path.append('/Workspace/Repos/ecommerce-data-lakehouse/databricks')
from utils.transformations import apply_cdm_mapping, apply_quality_checks
from utils.config import Config

# COMMAND ----------

df_a = spark.read.parquet(Config.get_bronze_path(Config.STORE_A, 'product_categories'))
df_b = spark.read.parquet(Config.get_bronze_path(Config.STORE_B, 'product_categories'))

store_b_mapping = {'CatID': 'CategoryID', 'CatName': 'CategoryName', 'ParentCat': 'ParentCategory'}
df_b_cdm = apply_cdm_mapping(df_b, store_b_mapping)
df_merged = df_a.unionByName(df_b_cdm)
df_merged = df_merged.withColumn('category_key', F.concat_ws('-', F.col('CategoryID'), F.col('datasource')))
df_quality = apply_quality_checks(df_merged, ['CategoryID', 'CategoryName'])

df_quality.write.format('delta').mode('overwrite').saveAsTable(Config.get_silver_table('product_categories'))
print('Silver product_categories refreshed (full load)')
