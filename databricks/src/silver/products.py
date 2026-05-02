# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Products (CDM + Quality + SCD Type 2)

# COMMAND ----------

from pyspark.sql import functions as F
import sys
sys.path.append('/Workspace/Repos/ecommerce-data-lakehouse/databricks')
from utils.transformations import *
from utils.config import Config

# COMMAND ----------

df_a = spark.read.parquet(Config.get_bronze_path(Config.STORE_A, 'products'))
df_b = spark.read.parquet(Config.get_bronze_path(Config.STORE_B, 'product_catalog'))

# COMMAND ----------

store_b_mapping = {
    'ProdID': 'ProductID', 'ProdName': 'ProductName', 'Cat': 'Category',
    'SubCat': 'SubCategory', 'ListPrice': 'Price', 'AvailableQty': 'StockQty',
    'VendorName': 'Supplier', 'CreateDt': 'CreatedDate', 'UpdateDt': 'ModifiedDate'
}
df_b_cdm = apply_cdm_mapping(df_b, store_b_mapping)
df_merged = df_a.unionByName(df_b_cdm)

# COMMAND ----------

df_keyed = generate_surrogate_key(df_merged, ['ProductID'], output_col='product_key')
df_clean = standardize_strings(df_keyed, ['ProductName', 'Category', 'SubCategory'])
df_dedup = deduplicate(df_clean, ['product_key'], 'ModifiedDate')
df_quality = apply_quality_checks(df_dedup, ['ProductID', 'ProductName', 'Price'])
df_quality = df_quality.withColumn('is_quarantined', F.when(F.col('Price') <= 0, True).otherwise(F.col('is_quarantined')))

# COMMAND ----------

df_final = df_quality.withColumnRenamed('CreatedDate', 'src_created_date').withColumnRenamed('ModifiedDate', 'src_modified_date')
df_final = add_audit_columns(df_final)
scd2_merge(spark, df_final, Config.get_silver_table('products'), 'product_key',
    ['ProductName', 'Category', 'SubCategory', 'Price', 'StockQty', 'Supplier'])
print('Silver products updated (SCD2)')
