# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Order Items (CDM + Quality + Incremental Append)

# COMMAND ----------

from pyspark.sql import functions as F
import sys
sys.path.append('/Workspace/Repos/ecommerce-data-lakehouse/databricks')
from utils.transformations import *
from utils.config import Config
from delta.tables import DeltaTable

# COMMAND ----------

df_a = spark.read.parquet(Config.get_bronze_path(Config.STORE_A, 'order_items'))
df_b = spark.read.parquet(Config.get_bronze_path(Config.STORE_B, 'order_details'))

store_b_mapping = {
    'DetailID': 'OrderItemID', 'OrdID': 'OrderID', 'ProdID': 'ProductID',
    'Qty': 'Quantity', 'Price': 'UnitPrice', 'DiscountPct': 'Discount',
    'Amount': 'LineTotal', 'CreateDt': 'InsertDate'
}
df_b_cdm = apply_cdm_mapping(df_b, store_b_mapping)
df_b_cdm = df_b_cdm.withColumn('Discount', F.col('Discount') / 100)  # Normalize: % to fraction
df_merged = df_a.unionByName(df_b_cdm)

# COMMAND ----------

df_keyed = generate_surrogate_key(df_merged, ['OrderItemID'], output_col='order_item_key')
df_keyed = df_keyed.withColumn('FK_OrderKey', F.concat_ws('-', F.col('OrderID'), F.col('datasource')))
df_keyed = df_keyed.withColumn('FK_ProductKey', F.concat_ws('-', F.col('ProductID'), F.col('datasource')))
df_quality = apply_quality_checks(df_keyed, ['OrderItemID', 'OrderID', 'ProductID', 'Quantity'])
df_quality = df_quality.withColumn('is_quarantined', F.when(F.col('Quantity') <= 0, True).otherwise(F.col('is_quarantined')))
df_final = df_quality.withColumnRenamed('InsertDate', 'src_insert_date')
df_final = add_audit_columns(df_final)

target = Config.get_silver_table('order_items')
if DeltaTable.isDeltaTable(spark, target):
    DeltaTable.forName(spark, target).alias('t').merge(df_final.alias('s'), 't.order_item_key = s.order_item_key').whenNotMatchedInsertAll().execute()
else:
    df_final.write.format('delta').mode('overwrite').saveAsTable(target)
print('Silver order_items updated')
