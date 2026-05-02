# Project Flow — Azure E-Commerce Data Lakehouse

## Overview

This document explains the **end-to-end data flow** and the reasoning behind each architectural decision in the E-Commerce Data Lakehouse project.

---

## Business Context

An e-commerce company operates **two regional stores** (Store A and Store B), each with its own database system using **different schemas**. Additionally, product reviews arrive as flat CSV files from an external review aggregation service.

The goal: build a unified data platform that ingests from all sources, standardizes the data, tracks historical changes, and produces a **star schema** optimized for business analytics.

---

## Data Flow: Step by Step

### 1. Source Systems → Landing/Bronze (ADF)

**What happens:**
- The `pl_master` pipeline orchestrates 4 child pipelines sequentially
- `pl_source_to_bronze` reads `load_config.csv` to determine which tables to process
- For each table, it checks if data already exists in Bronze:
  - If YES → archives the old file to `bronze/{path}/archive/yyyy/MM/dd/`
  - Then checks load type (Full vs Incremental):
    - **Full**: `SELECT * FROM table` → writes to Bronze as Parquet
    - **Incremental**: Queries audit table for last watermark → `SELECT * WHERE watermark >= last_date`
  - After each copy, logs metadata to `audit.load_logs`
- `pl_landing_to_bronze` converts CSV flat files to Parquet

**Why this design:**
- **Metadata-driven**: Adding a new table requires only a config file update — no pipeline changes
- **Audit table watermarks**: Industry-standard approach (vs JSON files) — queryable and debuggable
- **Archive before overwrite**: Full auditability — you can always recover previous data
- **Parallel ForEach**: 10 tables processed in batches of 5 for performance

### 2. Bronze → Silver (Databricks)

**What happens:**
- Each Silver notebook reads from **both stores** in Bronze
- Applies **CDM (Common Data Model)** to map different column names to a unified schema
- Generates **surrogate keys** (e.g., `CUST-A-00001-store-a`) for cross-source uniqueness
- Applies **data quality checks** — flags bad records with `is_quarantined = true`
- For dimension tables (customers, products): **SCD Type 2** merge tracks historical changes
- For transaction tables (orders, order_items): **incremental append** (no SCD2 needed)
- For reference tables (categories): **full load** (truncate + insert)

**Why SCD2 in Silver (not Gold):**
- Silver is the "single source of truth" — all historical tracking happens here
- Gold layer just filters `is_current = true` for the current snapshot
- This is industry standard

### 3. Silver → Gold (Delta Live Tables)

**What happens:**
- DLT pipeline reads from Silver Delta tables
- Creates dimension tables filtering `is_current = true AND is_quarantined = false`
- Generates `dim_date` (computed, not from any source — standard DW practice)
- Builds `fact_orders` by joining orders + order_items with FK references to all dimensions
- DLT expectations enforce data quality (e.g., `Price > 0`, `customer_key IS NOT NULL`)

**Why DLT for Gold:**
- Built-in data quality expectations with three levels (WARN, DROP, FAIL)
- Automatic lineage tracking
- Auto-optimization of Delta tables

---

## Security Architecture

```
                    ┌─────────────────────┐
                    │   Azure Key Vault   │
                    │                     │
                    │ ● SQL conn strings  │
                    │ ● Databricks tokens │
                    └──────┬──────────────┘
                           │
                      ┌────┴───┐
                      │  ADF   │  ← reads secrets via KV linked service
                      │ Linked │
                      │ Svc KV │
                      └────────┘

   ┌───────────────┐     ┌──────────────────────────┐
   │Access Connector│────▶│  Unity Catalog            │
   │(Managed ID)   │     │                          │
   │               │     │ ● Storage Credential     │
   │ Has RBAC role │     │ ● External Locations     │
   │ on ADLS       │     │ ● Table-level ACLs       │
   └───────────────┘     └──────────────────────────┘
```

**How it works:**
- **ADF** reads SQL passwords from Key Vault (linked service reference)
- **Databricks** accesses ADLS via Unity Catalog External Locations — no keys in code
- External Locations use an **Access Connector** (managed identity with RBAC role on storage)

---

## Reusable Utility Functions

The `utils/transformations.py` module provides 8 functions:

| Function | Purpose |
|----------|---------|
| `apply_cdm_mapping()` | Rename columns to match CDM standard |
| `generate_surrogate_key()` | Create composite keys from ID + datasource |
| `apply_quality_checks()` | Flag records with null/empty critical fields |
| `add_audit_columns()` | Add inserted_date, modified_date, is_current |
| `scd2_merge()` | Reusable SCD Type 2 MERGE INTO logic |
| `drop_columns()` | Safely drop columns (ignores missing) |
| `standardize_strings()` | Trim + proper case for string fields |
| `deduplicate()` | Window-based dedup keeping latest record |

All functions are **unit tested** with pytest (see `tests/test_transformations.py`).

---

## ADLS Container Layout

```
stecommercedatalake/
├── landing/              ← Raw flat files (CSV)
│   └── product_reviews/
├── configs/              ← Pipeline metadata
│   └── emr/load_config.csv
├── bronze/               ← Parquet files (immutable source of truth)
│   ├── store_a/
│   │   ├── customers/
│   │   ├── products/
│   │   ├── orders/
│   │   ├── order_items/
│   │   ├── product_categories/
│   │   └── archive/      ← Date-partitioned archives
│   ├── store_b/
│   │   ├── customer_info/
│   │   ├── product_catalog/
│   │   └── ...
│   └── product_reviews/
├── silver/               ← Delta tables (CDM + Quality + SCD2)
└── gold/                 ← Delta tables (Star schema)
```
