# Project Flow — E-Commerce Data Lakehouse Platform

## Complete Data Flow Diagram

```
┌─────────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│   Azure SQL DB      │     │   Azure SQL DB      │     │   CSV File       │
│   Store A           │     │   Store B           │     │   Product Reviews │
│   (ecom-store-a)    │     │   (ecom-store-b)    │     │   (external)     │
│                     │     │                     │     │                  │
│  ┌───────────────┐  │     │  ┌───────────────┐  │     │  5,000 reviews   │
│  │ customers     │  │     │  │ customer_info │  │     │  with ratings    │
│  │ products      │  │     │  │ product_catalog│ │     │  1-5 stars       │
│  │ orders        │  │     │  │ order_log     │  │     │                  │
│  │ order_items   │  │     │  │ order_details │  │     │                  │
│  │ product_cats  │  │     │  │ product_cats  │  │     │                  │
│  └───────────────┘  │     │  └───────────────┘  │     │                  │
└────────┬────────────┘     └─────────┬───────────┘     └────────┬─────────┘
         │                            │                          │
         │  SQL Queries               │  SQL Queries             │  CSV Upload
         │  (Full or Incremental)     │  (Full or Incremental)   │  to Landing
         ▼                            ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AZURE DATA FACTORY (pl_master)                         │
│                                                                             │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐    │
│  │ pl_source_to_bronze│→ │pl_landing_to_bronze│→ │ pl_bronze_to_silver│→   │
│  │                    │  │                    │  │                    │    │
│  │ Lookup Config CSV  │  │ Copy CSV→Parquet   │  │ Trigger Databricks │    │
│  │ Filter active=1    │  │ landing/reviews.csv│  │ 6 notebooks with   │    │
│  │ ForEach (5 parallel)│ │ → bronze/reviews/  │  │ dependency graph   │    │
│  │  ├─ Archive old    │  │   .parquet         │  │                    │    │
│  │  ├─ Full/Inc Load  │  │                    │  │ ┌──┐ ┌──┐ ┌──┐   │    │
│  │  └─ Audit Log      │  │                    │  │ │C │ │P │ │PC│   │    │
│  └────────────────────┘  └────────────────────┘  │ └┬─┘ └┬─┘ └──┘   │    │
│                                                   │  │    │          │    │
│  ┌────────────────────┐                          │  ▼    ▼          │    │
│  │ pl_silver_to_gold  │                          │ ┌──┐ ┌──┐       │    │
│  │                    │                          │ │O │ │PR│       │    │
│  │ Trigger DLT        │                          │ └┬─┘ └──┘       │    │
│  │ Pipeline           │                          │  │              │    │
│  │                    │                          │  ▼              │    │
│  │                    │←─────────────────────────│ ┌──┐           │    │
│  └────────────────────┘                          │ │OI│           │    │
│                                                   │ └──┘           │    │
│  Alert_On_Failure ──→ Logic App Webhook ──→ 📧    └────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
         │                                                    │
         ▼                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ADLS GEN2 (stecommercedatalake)                       │
│                                                                             │
│  ┌─────────┐    ┌─────────────┐    ┌───────────────┐    ┌──────────────┐  │
│  │ LANDING │    │   BRONZE    │    │    SILVER     │    │     GOLD     │  │
│  │         │    │             │    │               │    │              │  │
│  │ reviews │    │ store_a/    │    │ customers     │    │ dim_customer │  │
│  │ .csv    │───→│  customers  │───→│  (SCD2+CDM)  │───→│ dim_product  │  │
│  │         │    │  products   │    │ products      │    │ dim_date     │  │
│  └─────────┘    │  orders     │    │  (SCD2+CDM)  │    │ dim_prod_cat │  │
│                 │  order_items│    │ orders        │    │ fact_orders  │  │
│  ┌──────────┐   │  prod_cats  │    │  (Inc Append) │    │              │  │
│  │ CONFIGS  │   │ store_b/    │    │ order_items   │    │ Star Schema  │  │
│  │          │   │  cust_info  │    │  (Inc Append) │    │ for BI       │  │
│  │ load_    │   │  prod_cat   │    │ prod_cats     │    │              │  │
│  │ config   │   │  order_log  │    │  (Full Load)  │    │ 7 Business   │  │
│  │ .csv     │   │  order_det  │    │ prod_reviews  │    │ Queries      │  │
│  │          │   │  prod_cats  │    │  (Inc Append) │    │              │  │
│  └──────────┘   │ prod_reviews│    │               │    │              │  │
│                 │ archive/    │    │ is_quarantined│    │ DLT expect   │  │
│                 │  yyyy/MM/dd/│    │ is_current    │    │ _or_drop     │  │
│                 └─────────────┘    └───────────────┘    └──────────────┘  │
│                                                                             │
│  Format: CSV       Format: Parquet    Format: Delta      Format: Delta     │
│                    + Snappy comp.     + Unity Catalog     + DLT managed     │
└─────────────────────────────────────────────────────────────────────────────┘
         │                                                    │
         ▼                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  AZURE DATABRICKS (Processing Engine)                       │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Silver Layer Notebooks                         │ │
│  │                                                                        │ │
│  │  For EACH Silver notebook:                                            │ │
│  │  1. Read Bronze Parquet (both stores)                                 │ │
│  │  2. Apply CDM mapping (rename Store B cols → Store A standard)        │ │
│  │  3. Union both stores into single DataFrame                           │ │
│  │  4. Generate surrogate key (ID + datasource)                          │ │
│  │  5. Standardize strings (trim + proper case)                          │ │
│  │  6. Deduplicate (window function, keep latest)                        │ │
│  │  7. Quality checks (flag nulls → is_quarantined)                      │ │
│  │  8. Additional checks (price>0, rating 1-5, qty>0)                    │ │
│  │  9. Add audit columns (inserted_date, modified_date, is_current)      │ │
│  │  10. Write: SCD2 merge / Incremental append / Full overwrite          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Gold Layer (DLT)                               │ │
│  │                                                                        │ │
│  │  dim_customer: Silver customers WHERE is_current AND NOT quarantined  │ │
│  │  dim_product:  Silver products WHERE is_current AND NOT quarantined   │ │
│  │  dim_date:     GENERATED (2023-2026, fiscal year, is_weekend)         │ │
│  │  dim_prod_cat: Silver categories WHERE NOT quarantined                │ │
│  │  fact_orders:  JOIN(orders + order_items) with FK references          │ │
│  │                                                                        │ │
│  │  DLT Expectations: NULL checks (DROP), Price>0 (DROP), Amount>0 (WARN)│ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Utils: transformations.py (8 functions), config.py (centralized)     │ │
│  │  Tests: test_transformations.py (7 test classes, pytest + local Spark)│ │
│  │  DAB: databricks.yml (dev/prod targets), job.yml, pipeline.yml       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SECURITY ARCHITECTURE                                 │
│                                                                             │
│  ┌─────────────┐   ┌──────────────────┐   ┌────────────────────────────┐  │
│  │ Key Vault   │   │ Access Connector │   │ Unity Catalog              │  │
│  │             │   │                  │   │                            │  │
│  │ Secrets:    │   │ Managed Identity │   │ External Locations:        │  │
│  │ ├─ SQL conn │──→│ (no keys in code)│──→│ ├─ bronze_location         │  │
│  │ ├─ DB token │   │                  │   │ ├─ silver_location         │  │
│  │ └─ ADLS key │   │ Storage Blob     │   │ └─ gold_location           │  │
│  │             │   │ Data Contributor │   │                            │  │
│  │ RBAC:       │   │ role on ADLS     │   │ Storage Credential:        │  │
│  │ ADF → Secrets│   │                  │   │ ecom_storage_credential    │  │
│  │    User role │   │                  │   │                            │  │
│  └─────────────┘   └──────────────────┘   └────────────────────────────┘  │
│                                                                             │
│  DAB Production: Service Principal (ecommerce-pipeline-sp)                 │
│  Permissions: CAN_VIEW (data-engineering-team), CAN_MANAGE (admins)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase-by-Phase Detailed Flow

### Phase 1: Data Generation (One-Time Setup)

```
generate_store_a.py ──→ store_a_ddl.sql + store_a_initial_load.sql ──→ Azure SQL (ecom-store-a)
generate_store_b.py ──→ store_b_ddl.sql + store_b_initial_load.sql ──→ Azure SQL (ecom-store-b)
generate_reviews.py ──→ product_reviews.csv ──→ Upload to ADLS landing/product_reviews/
```

| Generator | Seed | Volume | Schema Style |
|-----------|------|--------|-------------|
| Store A | Faker.seed(42) | 2K customers, 500 products, 8K orders, 20K items | Standard (`CustomerID`, `FirstName`) |
| Store B | Faker.seed(99) | 1.5K customers, 400 products, 6K orders, 15K items | Non-standard (`CustID`, `FName`) |
| Reviews | random.seed(42) | 5K reviews across both stores | Flat CSV with `ReviewID`, `Rating` |

---

### Phase 2: Source → Bronze Ingestion (ADF: `pl_source_to_bronze`)

**Detailed activity flow** for each of the 10 tables:

```
load_config.csv
    ↓
[Lookup_Config] → reads all 10 rows
    ↓
[Filter_Active_Tables] → keeps rows where is_active = 1
    ↓
[ForEach_Table] (parallel, batch=5)
    ├── Batch 1: tables 1-5 (simultaneously)
    └── Batch 2: tables 6-10 (simultaneously)
        ↓ (for each table)
    [Get_Metadata] → does customers.parquet already exist in bronze?
        ↓
    [If File Exists]
        ├── YES → [Archive_File] copy to bronze/store_a/archive/2025/03/18/customers.parquet
        └── NO → skip archive
        ↓
    [If LoadType]
        ├── FULL → SQL: "SELECT *, 'store-a' AS datasource FROM dbo.customers"
        │          → Write to bronze/store_a/customers.parquet
        │          → INSERT INTO audit.load_logs (rows_copied, loaddate)
        │
        └── INCREMENTAL → [Fetch_Last_Watermark]
                           SQL: "SELECT MAX(loaddate) FROM audit.load_logs
                                 WHERE data_source='store-a' AND tablename='dbo.customers'"
                           → Returns: 2025-03-15
                          → SQL: "SELECT *, 'store-a' AS datasource FROM dbo.customers
                                  WHERE ModifiedDate >= '2025-03-15'"
                          → Write to bronze/store_a/customers.parquet
                          → INSERT INTO audit.load_logs
```

**Config-driven behavior** — what happens for each table:

| Table | Load Type | Watermark | Store | Result in Bronze |
|-------|-----------|-----------|-------|-----------------|
| dbo.customers | Incremental | ModifiedDate | A | bronze/store_a/customers.parquet |
| dbo.products | Incremental | ModifiedDate | A | bronze/store_a/products.parquet |
| dbo.orders | Incremental | ModifiedDate | A | bronze/store_a/orders.parquet |
| dbo.order_items | Incremental | InsertDate | A | bronze/store_a/order_items.parquet |
| dbo.product_categories | Full | (none) | A | bronze/store_a/product_categories.parquet |
| dbo.customer_info | Incremental | UpdateDt | B | bronze/store_b/customer_info.parquet |
| dbo.product_catalog | Incremental | UpdateDt | B | bronze/store_b/product_catalog.parquet |
| dbo.order_log | Incremental | UpdateDt | B | bronze/store_b/order_log.parquet |
| dbo.order_details | Incremental | CreateDt | B | bronze/store_b/order_details.parquet |
| dbo.product_categories | Full | (none) | B | bronze/store_b/product_categories.parquet |

---

### Phase 3: Landing → Bronze (ADF: `pl_landing_to_bronze`)

```
landing/product_reviews/product_reviews.csv
    ↓
[Copy_Reviews_CSV_To_Parquet]
    ↓
bronze/product_reviews/product_reviews.parquet
```

Simple format conversion. CSV → Parquet with Snappy compression.

---

### Phase 4: Bronze → Silver Transformation (ADF: `pl_bronze_to_silver` → Databricks)

**Dependency execution order**:

```
Parallel Start:
├── customers.py (SCD2) ──────────────────────────┐
├── products.py (SCD2) ────────────────────┐       │
└── product_categories.py (Full Load)       │       │
                                            │       │
Sequential:                                 │       │
├── orders.py (Incremental) ←───────────────┘───────┘ (needs customer keys)
├── product_reviews.py (Incremental) ←──────┘         (needs product keys)
└── order_items.py (Incremental) ←──────────────────── (needs order + product keys)
```

**Each Silver notebook follows this pattern**:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Silver Notebook Flow                                │
│                                                                            │
│  ┌─────────────┐    ┌─────────────┐                                      │
│  │ Read Bronze  │    │ Read Bronze  │                                      │
│  │ Store A      │    │ Store B      │                                      │
│  │ (customers)  │    │ (cust_info)  │                                      │
│  └──────┬───────┘    └──────┬───────┘                                      │
│         │                   │                                              │
│         │                   ▼                                              │
│         │           ┌──────────────────┐                                   │
│         │           │ CDM Mapping      │  CustID → CustomerID              │
│         │           │ (rename cols)    │  FName → FirstName                │
│         │           └──────┬───────────┘  LName → LastName ...            │
│         │                  │                                               │
│         ▼                  ▼                                               │
│  ┌──────────────────────────────┐                                         │
│  │ Union (unionByName)          │  Stack both stores into one DataFrame   │
│  └──────────────┬───────────────┘                                         │
│                 │                                                          │
│                 ▼                                                          │
│  ┌──────────────────────────────┐                                         │
│  │ Generate Surrogate Key       │  CustomerID + "-" + datasource          │
│  │ e.g., CUST-A-00001-store-a  │  Ensures cross-store uniqueness         │
│  └──────────────┬───────────────┘                                         │
│                 │                                                          │
│                 ▼                                                          │
│  ┌──────────────────────────────┐                                         │
│  │ Standardize Strings          │  Trim whitespace + proper case          │
│  │ " JOHN " → "John"           │  Consistent formatting                  │
│  └──────────────┬───────────────┘                                         │
│                 │                                                          │
│                 ▼                                                          │
│  ┌──────────────────────────────┐                                         │
│  │ Deduplicate                  │  Window function: partition by key,     │
│  │ (keep latest record)        │  order by ModifiedDate DESC,            │
│  │                              │  row_number() = 1 → keep               │
│  └──────────────┬───────────────┘                                         │
│                 │                                                          │
│                 ▼                                                          │
│  ┌──────────────────────────────┐                                         │
│  │ Quality Checks               │  Flag nulls/empties:                    │
│  │ is_quarantined = True/False  │  CustomerID, Email, FirstName checked   │
│  │ (quarantine, not drop!)      │  Additional: Price>0, Rating 1-5       │
│  └──────────────┬───────────────┘                                         │
│                 │                                                          │
│                 ▼                                                          │
│  ┌──────────────────────────────┐                                         │
│  │ Add Audit Columns            │  inserted_date, modified_date,          │
│  │                              │  is_current = True                      │
│  └──────────────┬───────────────┘                                         │
│                 │                                                          │
│                 ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Write to Silver Delta Table                                         │  │
│  │                                                                      │  │
│  │  Dimensions (customers, products):                                  │  │
│  │  └─ SCD2 Merge (2-step):                                           │  │
│  │     Step 1: MERGE + whenMatchedUpdate(is_current=false)             │  │
│  │     Step 2: MERGE + whenNotMatchedInsertAll()                       │  │
│  │                                                                      │  │
│  │  Transactions (orders, order_items, reviews):                       │  │
│  │  └─ Incremental Append: MERGE + whenNotMatchedInsertAll() only      │  │
│  │                                                                      │  │
│  │  Reference (product_categories):                                    │  │
│  │  └─ Full Overwrite: .mode("overwrite").saveAsTable(...)             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 5: Silver → Gold Star Schema (ADF: `pl_silver_to_gold` → DLT)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    Delta Live Tables (DLT) Pipeline                        │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │ dim_customer      │  │ dim_product      │  │ dim_product_category   │  │
│  │                   │  │                   │  │                        │  │
│  │ Source: Silver    │  │ Source: Silver    │  │ Source: Silver          │  │
│  │ customers         │  │ products          │  │ product_categories     │  │
│  │                   │  │                   │  │                        │  │
│  │ Filter:           │  │ Filter:           │  │ Filter:                │  │
│  │ is_current=true   │  │ is_current=true   │  │ is_quarantined=false   │  │
│  │ is_quarantined=   │  │ is_quarantined=   │  │                        │  │
│  │ false             │  │ false             │  │ Expectations:          │  │
│  │                   │  │                   │  │ valid_key NOT NULL      │  │
│  │ Expectations:     │  │ Expectations:     │  │                        │  │
│  │ valid_key NOT NULL│  │ valid_key NOT NULL│  └───────────┬────────────┘  │
│  │ valid_email       │  │ positive_price>0 │              │              │
│  │ NOT NULL          │  │                   │              │              │
│  └───────────┬───────┘  └───────┬───────────┘              │              │
│              │                  │                           │              │
│              │                  │                           │              │
│  ┌───────────┼──────────────────┼───────────────────────────┼──────────┐  │
│  │           ▼                  ▼                           ▼          │  │
│  │                     fact_orders                                     │  │
│  │                                                                     │  │
│  │  Source: Silver orders INNER JOIN Silver order_items                │  │
│  │  ON FK_OrderKey = order_key                                        │  │
│  │                                                                     │  │
│  │  FK_CustomerKey → dim_customer.customer_key                        │  │
│  │  FK_ProductKey  → dim_product.product_key                          │  │
│  │  FK_DateKey     → dim_date.date_key (derived from OrderDate)       │  │
│  │                                                                     │  │
│  │  Grain: 1 row per ORDER ITEM                                      │  │
│  │  Expectations: valid_order NOT NULL, valid_customer NOT NULL        │  │
│  │                positive_amount > 0 (WARN only)                     │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌────────────────────────────────────────┐                               │
│  │ dim_date (GENERATED)                   │                               │
│  │                                        │                               │
│  │ NOT from any source system!            │                               │
│  │ sequence(2023-01-01, 2026-12-31)       │                               │
│  │                                        │                               │
│  │ Columns:                               │                               │
│  │ date_key (int), full_date, day_of_week │                               │
│  │ day_name, month_name, quarter, year    │                               │
│  │ is_weekend, fiscal_quarter, fiscal_year│                               │
│  └────────────────────────────────────────┘                               │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 6: Business Analytics (SQL Queries on Gold)

The star schema enables these 7 analytical queries:

| # | Query | What It Answers | Tables Joined |
|---|-------|----------------|--------------|
| 1 | Monthly Revenue Trend | How is revenue changing over time? | fact_orders + dim_date |
| 2 | Top 10 Products | Which products generate the most revenue? | fact_orders + dim_product |
| 3 | Customer Lifetime Value | Who are our most valuable customers? | fact_orders + dim_customer |
| 4 | Category Performance (Quarterly) | Which categories grow/decline each quarter? | fact_orders + dim_product + dim_product_category + dim_date |
| 5 | Payment Method Analysis | Average order value by payment type? | fact_orders (grouped by PaymentMethod) |
| 6 | Store Comparison | How does Store A perform vs Store B? | fact_orders (grouped by datasource) |
| 7 | Weekend vs Weekday Sales | Do weekends generate more revenue? | fact_orders + dim_date (is_weekend) |

---

## Schema Heterogeneity Resolution — CDM Mapping Table

This is the complete mapping of how Store B's columns are renamed to match Store A's standard:

### Customers
| Store B Column | → | Store A Standard |
|---------------|---|-----------------|
| `CustID` | → | `CustomerID` |
| `FName` | → | `FirstName` |
| `LName` | → | `LastName` |
| `EmailAddr` | → | `Email` |
| `PhoneNum` | → | `Phone` |
| `Street` | → | `Address` |
| `Town` | → | `City` |
| `Region` | → | `State` |
| `PostalCode` | → | `ZipCode` |
| `CreateDt` | → | `CreatedDate` |
| `UpdateDt` | → | `ModifiedDate` |

### Products
| Store B Column | → | Store A Standard |
|---------------|---|-----------------|
| `ProdID` | → | `ProductID` |
| `ProdName` | → | `ProductName` |
| `Cat` | → | `Category` |
| `SubCat` | → | `SubCategory` |
| `ListPrice` | → | `Price` |
| `AvailableQty` | → | `StockQty` |
| `VendorName` | → | `Supplier` |

### Orders
| Store B Column | → | Store A Standard |
|---------------|---|-----------------|
| `OrdID` | → | `OrderID` |
| `CustID` | → | `CustomerID` |
| `OrdDate` | → | `OrderDate` |
| `ShipDt` | → | `ShipDate` |
| `OrdStatus` | → | `Status` |
| `GrandTotal` | → | `TotalAmount` |
| `PayMode` | → | `PaymentMethod` |
| `ShipAddr` | → | `ShippingAddress` |

### Order Items
| Store B Column | → | Store A Standard | Special Handling |
|---------------|---|-----------------|-----------------|
| `DetailID` | → | `OrderItemID` | |
| `OrdID` | → | `OrderID` | |
| `ProdID` | → | `ProductID` | |
| `Qty` | → | `Quantity` | |
| `Price` | → | `UnitPrice` | |
| `DiscountPct` | → | `Discount` | **÷ 100** (15.0 → 0.15) |
| `Amount` | → | `LineTotal` | |
| `CreateDt` | → | `InsertDate` | |

---

## SCD2 Merge — How Historical Tracking Works

### Scenario: Customer moves from New York to Miami

**Before incremental load (Silver `customers` table)**:
| customer_key | City | is_current | inserted_date | modified_date |
|-------------|------|------------|---------------|---------------|
| CUST-A-00001-store-a | New York | **true** | 2025-01-15 | 2025-01-15 |

**Incremental load brings in**:
| customer_key | City | ... |
|-------------|------|-----|
| CUST-A-00001-store-a | **Miami** | ... |

**SCD2 Step 1 — Expire old record**:
```sql
MERGE target USING source
  ON target.customer_key = source.customer_key AND target.is_current = true
WHEN MATCHED AND target.City <> source.City
  THEN UPDATE SET is_current = false, modified_date = current_timestamp()
```

**SCD2 Step 2 — Insert new record**:
```sql
MERGE target USING source
  ON target.customer_key = source.customer_key AND target.is_current = true
WHEN NOT MATCHED
  THEN INSERT ALL  -- (now possible because Step 1 made old record is_current=false)
```

**After SCD2 merge**:
| customer_key | City | is_current | inserted_date | modified_date |
|-------------|------|------------|---------------|---------------|
| CUST-A-00001-store-a | New York | **false** | 2025-01-15 | **2025-03-18** |
| CUST-A-00001-store-a | **Miami** | **true** | **2025-03-18** | 2025-03-18 |

**Gold layer** (`dim_customer`) only shows `WHERE is_current = true` → sees "Miami" only.

---

## Audit Trail — How We Track Pipeline Runs

Every ADF data load writes to `audit.load_logs`:

| id | data_source | tablename | numberofrowscopied | watermarkcolumnname | loaddate |
|----|------------|-----------|-------------------|--------------------|---------| 
| 1 | store-a | dbo.customers | 2000 | ModifiedDate | 2025-03-15 10:00:00 |
| 2 | store-a | dbo.products | 500 | ModifiedDate | 2025-03-15 10:00:00 |
| ... | ... | ... | ... | ... | ... |
| 11 | store-a | dbo.customers | 3 | ModifiedDate | 2025-03-18 10:00:00 |

The incremental load uses `MAX(loaddate)` from this table to determine the watermark for the next run. On run #2, the pipeline queries: `SELECT MAX(loaddate) FROM audit.load_logs WHERE data_source='store-a' AND tablename='dbo.customers'` → gets `2025-03-15 10:00:00` → then queries: `SELECT * FROM dbo.customers WHERE ModifiedDate >= '2025-03-15'`.

---

## Security Flow

```
ADF Pipeline Execution:
├── ADF managed identity → Key Vault (Key Vault Secrets User role)
│   ├── Reads: sql-store-a-connection-string → connects to Azure SQL
│   ├── Reads: sql-store-b-connection-string → connects to Azure SQL
│   ├── Reads: adls-storage-access-key → writes to ADLS
│   └── Reads: databricks-access-token → triggers Databricks notebooks
│
└── Databricks Notebook Execution:
    ├── Access Connector (managed identity) → Storage Blob Data Contributor on ADLS
    ├── Unity Catalog External Location → maps ADLS paths to catalog namespace
    └── Storage Credential → bridges Access Connector to External Locations

DAB Deployment:
├── Dev: Developer's personal PAT → deploys to user workspace folder
└── Prod: Service Principal (ecommerce-pipeline-sp) → deploys to shared production path
    ├── Permissions: CAN_VIEW (data-engineering-team)
    └── Permissions: CAN_MANAGE (data-platform-admins)
```

No storage keys, connection strings, or tokens exist in any code file. Everything is in Key Vault (for ADF) or managed via Access Connector (for Databricks).
