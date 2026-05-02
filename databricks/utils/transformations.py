"""Reusable Transformation Utilities for the E-Commerce Data Lakehouse."""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable
from typing import Dict, List, Optional


def apply_cdm_mapping(df: DataFrame, column_mapping: Dict[str, str]) -> DataFrame:
    """Rename columns to match Common Data Model standard."""
    for source_col, target_col in column_mapping.items():
        if source_col in df.columns:
            df = df.withColumnRenamed(source_col, target_col)
    return df


def generate_surrogate_key(df: DataFrame, key_columns: List[str],
                           datasource_col: str = "datasource",
                           output_col: str = "surrogate_key") -> DataFrame:
    """Generate composite surrogate key from key columns + datasource."""
    key_parts = [F.col(c).cast("string") for c in key_columns] + [F.col(datasource_col)]
    return df.withColumn(output_col, F.concat_ws("-", *key_parts))


def apply_quality_checks(df: DataFrame, not_null_columns: List[str],
                         output_col: str = "is_quarantined") -> DataFrame:
    """Flag records with null/empty critical fields for quarantine."""
    conditions = [F.col(c).isNull() | (F.trim(F.col(c)) == "") for c in not_null_columns]
    combined = conditions[0]
    for cond in conditions[1:]:
        combined = combined | cond
    return df.withColumn(output_col, combined)


def add_audit_columns(df: DataFrame) -> DataFrame:
    """Add inserted_date, modified_date, is_current audit columns."""
    return (df
        .withColumn("inserted_date", F.current_timestamp())
        .withColumn("modified_date", F.current_timestamp())
        .withColumn("is_current", F.lit(True)))


def scd2_merge(spark: SparkSession, source_df: DataFrame, target_table: str,
               key_column: str, compare_columns: List[str]) -> None:
    """Perform SCD Type 2 merge using Delta Lake MERGE INTO."""
    if not DeltaTable.isDeltaTable(spark, target_table):
        source_df.write.format("delta").mode("overwrite").saveAsTable(target_table)
        return

    target = DeltaTable.forName(spark, target_table)
    change_conditions = " OR ".join([f"target.{c} <> source.{c}" for c in compare_columns])

    # Step 1: Expire changed records
    target.alias("target").merge(
        source_df.alias("source"),
        f"target.{key_column} = source.{key_column} AND target.is_current = true"
    ).whenMatchedUpdate(
        condition=change_conditions,
        set={"is_current": F.lit(False), "modified_date": F.current_timestamp()}
    ).execute()

    # Step 2: Insert new/changed records
    target.alias("target").merge(
        source_df.alias("source"),
        f"target.{key_column} = source.{key_column} AND target.is_current = true"
    ).whenNotMatchedInsertAll().execute()


def drop_columns(df: DataFrame, columns: List[str]) -> DataFrame:
    """Safely drop columns (ignores missing ones)."""
    existing = [c for c in columns if c in df.columns]
    return df.drop(*existing)


def standardize_strings(df: DataFrame, columns: List[str]) -> DataFrame:
    """Trim whitespace and convert to proper case."""
    for col_name in columns:
        if col_name in df.columns:
            df = df.withColumn(col_name, F.initcap(F.trim(F.col(col_name))))
    return df


def deduplicate(df: DataFrame, key_columns: List[str],
                order_column: str, ascending: bool = False) -> DataFrame:
    """Remove duplicates keeping latest (or earliest) record."""
    order_expr = F.col(order_column).asc() if ascending else F.col(order_column).desc()
    window = Window.partitionBy(key_columns).orderBy(order_expr)
    return df.withColumn("_rn", F.row_number().over(window)).filter(F.col("_rn") == 1).drop("_rn")
