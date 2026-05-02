"""
Unit Tests for Reusable Transformation Utilities
Run: pytest tests/test_transformations.py -v
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType


@pytest.fixture(scope="session")
def spark():
    """Create a SparkSession for testing."""
    return (
        SparkSession.builder
        .master("local[*]")
        .appName("TransformationTests")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


# ─── Test: CDM Mapping ──────────────────────────────────────────

class TestApplyCdmMapping:
    def test_renames_columns(self, spark):
        from utils.transformations import apply_cdm_mapping

        data = [("C001", "John", "Doe")]
        df = spark.createDataFrame(data, ["CustID", "FName", "LName"])

        mapping = {"CustID": "CustomerID", "FName": "FirstName", "LName": "LastName"}
        result = apply_cdm_mapping(df, mapping)

        assert "CustomerID" in result.columns
        assert "FirstName" in result.columns
        assert "CustID" not in result.columns

    def test_ignores_missing_columns(self, spark):
        from utils.transformations import apply_cdm_mapping

        data = [("C001", "John")]
        df = spark.createDataFrame(data, ["CustID", "FName"])

        mapping = {"CustID": "CustomerID", "NonExistent": "Whatever"}
        result = apply_cdm_mapping(df, mapping)

        assert "CustomerID" in result.columns
        assert len(result.columns) == 2  # FName stays unchanged


# ─── Test: Surrogate Key Generation ─────────────────────────────

class TestGenerateSurrogateKey:
    def test_generates_composite_key(self, spark):
        from utils.transformations import generate_surrogate_key

        data = [("C001", "store-a"), ("C002", "store-b")]
        df = spark.createDataFrame(data, ["CustomerID", "datasource"])

        result = generate_surrogate_key(df, ["CustomerID"], output_col="customer_key")
        keys = [row.customer_key for row in result.collect()]

        assert keys[0] == "C001-store-a"
        assert keys[1] == "C002-store-b"


# ─── Test: Quality Checks ───────────────────────────────────────

class TestApplyQualityChecks:
    def test_flags_null_records(self, spark):
        from utils.transformations import apply_quality_checks

        data = [("C001", "john@email.com"), (None, "jane@email.com"), ("C003", None)]
        df = spark.createDataFrame(data, ["CustomerID", "Email"])

        result = apply_quality_checks(df, ["CustomerID", "Email"])
        quarantined = result.filter(F.col("is_quarantined") == True).count()

        assert quarantined == 2  # row 2 (null ID) and row 3 (null email)

    def test_clean_records_pass(self, spark):
        from utils.transformations import apply_quality_checks

        data = [("C001", "john@email.com"), ("C002", "jane@email.com")]
        df = spark.createDataFrame(data, ["CustomerID", "Email"])

        result = apply_quality_checks(df, ["CustomerID", "Email"])
        clean = result.filter(F.col("is_quarantined") == False).count()

        assert clean == 2


# ─── Test: Deduplication ────────────────────────────────────────

class TestDeduplicate:
    def test_keeps_latest_record(self, spark):
        from utils.transformations import deduplicate

        data = [
            ("C001", "2024-01-01", "Old Address"),
            ("C001", "2024-06-15", "New Address"),
            ("C002", "2024-03-01", "Only Address"),
        ]
        df = spark.createDataFrame(data, ["CustomerID", "ModifiedDate", "Address"])

        result = deduplicate(df, ["CustomerID"], "ModifiedDate", ascending=False)

        assert result.count() == 2
        c001 = result.filter(F.col("CustomerID") == "C001").collect()[0]
        assert c001.Address == "New Address"


# ─── Test: Drop Columns ────────────────────────────────────────

class TestDropColumns:
    def test_drops_existing_columns(self, spark):
        from utils.transformations import drop_columns

        data = [("C001", "John", "internal_field")]
        df = spark.createDataFrame(data, ["ID", "Name", "Secret"])

        result = drop_columns(df, ["Secret", "NonExistent"])

        assert "Secret" not in result.columns
        assert "ID" in result.columns
        assert len(result.columns) == 2


# ─── Test: Standardize Strings ──────────────────────────────────

class TestStandardizeStrings:
    def test_proper_case_and_trim(self, spark):
        from utils.transformations import standardize_strings

        data = [("  john  ", "  DOE  ")]
        df = spark.createDataFrame(data, ["FirstName", "LastName"])

        result = standardize_strings(df, ["FirstName", "LastName"])
        row = result.collect()[0]

        assert row.FirstName == "John"
        assert row.LastName == "Doe"


# ─── Test: Audit Columns ───────────────────────────────────────

class TestAddAuditColumns:
    def test_adds_three_columns(self, spark):
        from utils.transformations import add_audit_columns

        data = [("C001",)]
        df = spark.createDataFrame(data, ["ID"])

        result = add_audit_columns(df)

        assert "inserted_date" in result.columns
        assert "modified_date" in result.columns
        assert "is_current" in result.columns
        assert result.collect()[0].is_current is True
