# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Orders (CDM + Quality + Incremental Append)

# COMMAND ----------

from pyspark.sql import functions as F
import sys
sys.path.append('/Workspace/Repos/ecommerce-data-lakehouse/databricks')
from utils.transformations import *
from utils.config import Config
from delta.tables import DeltaTable

# COMMAND ----------

df_a = spark.read.parquet(Config.get_bronze_path(Config.STORE_A, 'orders'))
df_b = spark.read.parquet(Config.get_bronze_path(Config.STORE_B, 'order_log'))

store_b_mapping = {
    'OrdID': 'OrderID', 'CustID': 'CustomerID', 'OrdDate': 'OrderDate',
    'ShipDt': 'ShipDate', 'OrdStatus': 'Status', 'GrandTotal': 'TotalAmount',
    'PayMode': 'PaymentMethod', 'ShipAddr': 'ShippingAddress',
    'CreateDt': 'InsertDate', 'UpdateDt': 'ModifiedDate'
}
df_b_cdm = apply_cdm_mapping(df_b, store_b_mapping)
df_merged = df_a.unionByName(df_b_cdm)

# COMMAND ----------

df_keyed = generate_surrogate_key(df_merged, ['OrderID'], output_col='order_key')
df_dedup = deduplicate(df_keyed, ['order_key'], 'ModifiedDate')
df_quality = apply_quality_checks(df_dedup, ['OrderID', 'CustomerID', 'OrderDate'])
df_quality = df_quality.withColumn('FK_CustomerKey', F.concat_ws('-', F.col('CustomerID'), F.col('datasource')))
df_final = df_quality.withColumnRenamed('InsertDate', 'src_insert_date').withColumnRenamed('ModifiedDate', 'src_modified_date')
df_final = add_audit_columns(df_final)

target = Config.get_silver_table('orders')
if DeltaTable.isDeltaTable(spark, target):
    DeltaTable.forName(spark, target).alias('t').merge(df_final.alias('s'), 't.order_key = s.order_key').whenNotMatchedInsertAll().execute()
else:
    df_final.write.format('delta').mode('overwrite').saveAsTable(target)
print('Silver orders updated')
