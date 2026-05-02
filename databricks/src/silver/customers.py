# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - Customers (CDM + Quality + SCD Type 2)
# MAGIC Processes customer data from two stores with different schemas.

# COMMAND ----------

from pyspark.sql import functions as F
import sys
sys.path.append('/Workspace/Repos/ecommerce-data-lakehouse/databricks')
from utils.transformations import *
from utils.config import Config

# COMMAND ----------

df_a = spark.read.parquet(Config.get_bronze_path(Config.STORE_A, 'customers'))
df_b = spark.read.parquet(Config.get_bronze_path(Config.STORE_B, 'customer_info'))

# COMMAND ----------

# CDM Mapping - Store B different column names to standard
store_b_mapping = {
    'CustID': 'CustomerID', 'FName': 'FirstName', 'LName': 'LastName',
    'EmailAddr': 'Email', 'PhoneNum': 'Phone', 'Street': 'Address',
    'Town': 'City', 'Region': 'State', 'PostalCode': 'ZipCode',
    'CreateDt': 'CreatedDate', 'UpdateDt': 'ModifiedDate'
}
df_b_cdm = apply_cdm_mapping(df_b, store_b_mapping)
df_merged = df_a.unionByName(df_b_cdm)

# COMMAND ----------

df_keyed = generate_surrogate_key(df_merged, ['CustomerID'], output_col='customer_key')
df_clean = standardize_strings(df_keyed, ['FirstName', 'LastName', 'City'])
df_dedup = deduplicate(df_clean, ['customer_key'], 'ModifiedDate')
df_quality = apply_quality_checks(df_dedup, ['CustomerID', 'Email', 'FirstName'])

# COMMAND ----------

df_final = df_quality.withColumnRenamed('CreatedDate', 'src_created_date').withColumnRenamed('ModifiedDate', 'src_modified_date')
df_final = add_audit_columns(df_final)
scd2_merge(spark, df_final, Config.get_silver_table('customers'), 'customer_key',
    ['FirstName', 'LastName', 'Email', 'Phone', 'Address', 'City', 'State', 'ZipCode'])
print('Silver customers updated (SCD2)')
