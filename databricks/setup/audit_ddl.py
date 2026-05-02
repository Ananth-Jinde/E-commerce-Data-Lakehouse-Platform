# Databricks notebook source
# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS audit;
# MAGIC CREATE TABLE IF NOT EXISTS audit.load_logs (
# MAGIC     id BIGINT GENERATED ALWAYS AS IDENTITY,
# MAGIC     data_source STRING, tablename STRING,
# MAGIC     numberofrowscopied INT, watermarkcolumnname STRING,
# MAGIC     loaddate TIMESTAMP
# MAGIC );
