# ADF Pipeline Flow — Complete Visual Reference

> This document shows the exact activity flow for all 5 ADF pipelines, with activity names matching the actual JSON definitions.

---

## 1. pl_master — Master Orchestration Pipeline

This is the entry point. It runs 4 child pipelines in sequence. If ANY child fails, it sends a webhook alert to Logic Apps.

```mermaid
flowchart LR
    A["Execute_Source_To_Bronze
    (ExecutePipeline)"] -->|Succeeded| B["Execute_Landing_To_Bronze
    (ExecutePipeline)"]
    B -->|Succeeded| C["Execute_Bronze_To_Silver
    (ExecutePipeline)"]
    C -->|Succeeded| D["Execute_Silver_To_Gold
    (ExecutePipeline)"]
    
    A -->|Failed| E["Alert_On_Failure
    (WebActivity → Logic Apps)"]
    B -->|Failed| E
    C -->|Failed| E
    D -->|Failed| E

    style A fill:#0078D4,color:#fff
    style B fill:#0078D4,color:#fff
    style C fill:#0078D4,color:#fff
    style D fill:#0078D4,color:#fff
    style E fill:#D32F2F,color:#fff
```

**Activities explained**:
| Activity Name | Type | What It Does |
|--------------|------|-------------|
| Execute_Source_To_Bronze | ExecutePipeline | Calls `pl_source_to_bronze` — waits for completion |
| Execute_Landing_To_Bronze | ExecutePipeline | Calls `pl_landing_to_bronze` — waits for completion |
| Execute_Bronze_To_Silver | ExecutePipeline | Calls `pl_bronze_to_silver` — waits for completion |
| Execute_Silver_To_Gold | ExecutePipeline | Calls `pl_silver_to_gold` — waits for completion |
| Alert_On_Failure | WebActivity | POSTs to Logic Apps webhook URL → sends Teams/email alert with pipeline name + run ID |

---

## 2. pl_source_to_bronze — Metadata-Driven SQL Ingestion

This is the most complex pipeline. It reads a config file, filters active tables, and uses a ForEach loop to process each table in parallel.

### Outer Flow (before ForEach)

```mermaid
flowchart LR
    A["Lookup_Config
    (Lookup)
    Reads load_config.csv"] -->|Succeeded| B["Filter_Active_Tables
    (Filter)
    Keeps is_active = 1"]
    B -->|Succeeded| C["ForEach_Table
    (ForEach)
    Parallel, batchCount=5
    10 tables in 2 batches"]
    
    style A fill:#0078D4,color:#fff
    style B fill:#0078D4,color:#fff
    style C fill:#0078D4,color:#fff
```

### Inside ForEach — Activity Flow for EACH Table

```mermaid
flowchart TD
    A["Get_Metadata_FileExists
    (GetMetadata)
    Check: does parquet file exist in bronze?"] -->|Succeeded| B{"If_File_Exists_Archive
    (IfCondition)
    Does file exist?"}
    
    B -->|"True (file exists)"| C["Archive_File
    (Copy Activity)
    Copy to bronze/path/archive/yyyy/MM/dd/"]
    B -->|"False (no file)"| D{"If_LoadType
    (IfCondition)
    Is loadtype = Full?"}
    C --> D

    D -->|"True (Full Load)"| E["Full_Load_Copy
    (Copy Activity)
    SELECT *, datasource FROM table"]
    E -->|Succeeded| F["Audit_Full_Load
    (Script Activity)
    INSERT INTO audit.load_logs"]

    D -->|"False (Incremental)"| G["Fetch_Last_Watermark
    (Script Activity)
    SELECT MAX loaddate FROM audit.load_logs"]
    G -->|Succeeded| H["Incremental_Load_Copy
    (Copy Activity)
    SELECT * WHERE watermark >= last_date"]
    H -->|Succeeded| I["Audit_Incremental_Load
    (Script Activity)
    INSERT INTO audit.load_logs"]

    style A fill:#0078D4,color:#fff
    style B fill:#FF8C00,color:#fff
    style C fill:#107C10,color:#fff
    style D fill:#FF8C00,color:#fff
    style E fill:#107C10,color:#fff
    style F fill:#5C2D91,color:#fff
    style G fill:#5C2D91,color:#fff
    style H fill:#107C10,color:#fff
    style I fill:#5C2D91,color:#fff
```

**Activity color legend**: 🟦 Blue = Metadata/Filter | 🟧 Orange = If Condition | 🟩 Green = Copy Activity | 🟪 Purple = Script Activity

### Activities explained:
| Activity Name | Type | What It Does |
|--------------|------|-------------|
| Get_Metadata_FileExists | GetMetadata | Checks if `bronze/{targetpath}/{tablename}.parquet` already exists |
| If_File_Exists_Archive | IfCondition | If file exists → archive it. If not → skip to load. |
| Archive_File | Copy | Copies existing Parquet to `bronze/{targetpath}/archive/yyyy/MM/dd/{tablename}.parquet` |
| If_LoadType | IfCondition | Checks `item().loadtype == 'Full'` → branches to full or incremental |
| Full_Load_Copy | Copy | Runs: `SELECT *, 'store-a' AS datasource FROM dbo.customers` → writes Parquet |
| Audit_Full_Load | Script | `INSERT INTO audit.load_logs (data_source, tablename, numberofrowscopied, ...)` |
| Fetch_Last_Watermark | Script | `SELECT MAX(loaddate) FROM audit.load_logs WHERE data_source='store-a' AND tablename='dbo.customers'` |
| Incremental_Load_Copy | Copy | Runs: `SELECT *, 'store-a' AS datasource FROM dbo.customers WHERE ModifiedDate >= '2025-03-15'` → writes Parquet |
| Audit_Incremental_Load | Script | Same as Audit_Full_Load — logs rows copied and timestamp |

### Key points:
- **batchCount=5** means 5 tables process simultaneously. With 10 active tables, that's 2 batches.
- The **Script** activities run against `ls_delta_lake` linked service — they execute SQL on the Databricks audit table, NOT on the source SQL databases.
- The **Copy** activities use the parameterized `ds_azure_sql` (input) and `ds_parquet_bronze` (output) datasets.

---

## 3. pl_landing_to_bronze — Flat File Conversion

The simplest pipeline. One Copy activity converts CSV to Parquet.

```mermaid
flowchart LR
    A["Copy_Reviews_CSV_To_Parquet
    (Copy Activity)
    Source: landing/product_reviews/product_reviews.csv
    Sink: bronze/product_reviews/product_reviews.parquet"]

    style A fill:#107C10,color:#fff
```

**Activity**:
| Activity Name | Type | What It Does |
|--------------|------|-------------|
| Copy_Reviews_CSV_To_Parquet | Copy | Reads CSV from `landing` container → writes Parquet to `bronze/product_reviews/` |

---

## 4. pl_bronze_to_silver — Databricks Notebook Orchestration

Triggers 6 Databricks notebooks with a dependency graph. The notebooks that have no dependencies run in parallel. The ones with dependencies wait.

```mermaid
flowchart TD
    A["Silver_Customers
    (DatabricksNotebook)
    CDM + Quality + SCD2"] --> D["Silver_Orders
    (DatabricksNotebook)
    CDM + Quality + Incremental"]
    
    B["Silver_Products
    (DatabricksNotebook)
    CDM + Quality + SCD2"] --> E["Silver_Product_Reviews
    (DatabricksNotebook)
    Quality + Incremental"]
    
    C["Silver_Product_Categories
    (DatabricksNotebook)
    Full Load (overwrite)"]
    
    D --> F["Silver_Order_Items
    (DatabricksNotebook)
    CDM + Discount Normalization + Incremental"]
    B --> F

    style A fill:#0078D4,color:#fff
    style B fill:#0078D4,color:#fff
    style C fill:#0078D4,color:#fff
    style D fill:#0078D4,color:#fff
    style E fill:#0078D4,color:#fff
    style F fill:#0078D4,color:#fff
```

**Execution order** (determined by `dependsOn` in JSON):

| Execution Phase | Activities | Dependencies |
|----------------|-----------|-------------|
| Phase 1 (parallel) | Silver_Customers, Silver_Products, Silver_Product_Categories | None — all 3 start simultaneously |
| Phase 2 (after Phase 1) | Silver_Orders | Waits for Silver_Customers |
| Phase 2 (after Phase 1) | Silver_Product_Reviews | Waits for Silver_Products |
| Phase 3 (after Phase 2) | Silver_Order_Items | Waits for Silver_Orders AND Silver_Products |

**Why these dependencies?**
- `Silver_Orders` depends on `Silver_Customers` → because orders reference customer keys (FK)
- `Silver_Product_Reviews` depends on `Silver_Products` → because reviews reference product keys (FK)
- `Silver_Order_Items` depends on `Silver_Orders` AND `Silver_Products` → because order items reference both order keys and product keys (FKs)
- `Silver_Product_Categories` has NO dependencies → it's a standalone reference table

All 6 notebooks call `ls_databricks` linked service → which connects to the Databricks cluster.

---

## 5. pl_silver_to_gold — DLT Star Schema Build

Triggers a single Databricks notebook that runs the DLT/Declarative Pipeline to build the Gold star schema.

```mermaid
flowchart LR
    A["Run_Gold_DLT_Pipeline
    (DatabricksNotebook)
    Triggers DLT pipeline that builds:
    dim_customer, dim_product, dim_date,
    dim_product_category, fact_orders"]

    style A fill:#FFB900,color:#000
```

**Activity**:
| Activity Name | Type | What It Does |
|--------------|------|-------------|
| Run_Gold_DLT_Pipeline | DatabricksNotebook | Calls `/Repos/.../gold/run_gold_layer` which triggers the DLT pipeline. DLT builds all 5 Gold tables with quality expectations. |

---

## Complete End-to-End Flow (All 5 Pipelines Combined)

```mermaid
flowchart TD
    subgraph pl_master["pl_master (Master Orchestration)"]
        direction LR
        M1["Execute_Source_To_Bronze"] -->|Succeeded| M2["Execute_Landing_To_Bronze"]
        M2 -->|Succeeded| M3["Execute_Bronze_To_Silver"]
        M3 -->|Succeeded| M4["Execute_Silver_To_Gold"]
        M1 & M2 & M3 & M4 -->|Failed| MF["Alert_On_Failure → Logic Apps"]
    end

    subgraph pl_source_to_bronze["pl_source_to_bronze (SQL → Bronze)"]
        S1["Lookup_Config"] --> S2["Filter_Active_Tables"]
        S2 --> S3["ForEach_Table (batch=5)"]
        subgraph ForEach["Inside ForEach (per table)"]
            F1["Get_Metadata_FileExists"] --> F2{"If_File_Exists_Archive"}
            F2 -->|"Exists"| F3["Archive_File"]
            F3 --> F4{"If_LoadType"}
            F2 -->|"Not exists"| F4
            F4 -->|"Full"| F5["Full_Load_Copy"] --> F6["Audit_Full_Load"]
            F4 -->|"Incremental"| F7["Fetch_Last_Watermark"] --> F8["Incremental_Load_Copy"] --> F9["Audit_Incremental_Load"]
        end
    end

    subgraph pl_landing_to_bronze["pl_landing_to_bronze (CSV → Bronze)"]
        L1["Copy_Reviews_CSV_To_Parquet"]
    end

    subgraph pl_bronze_to_silver["pl_bronze_to_silver (Bronze → Silver)"]
        B1["Silver_Customers"] --> B4["Silver_Orders"]
        B2["Silver_Products"] --> B5["Silver_Product_Reviews"]
        B3["Silver_Product_Categories"]
        B4 --> B6["Silver_Order_Items"]
        B2 --> B6
    end

    subgraph pl_silver_to_gold["pl_silver_to_gold (Silver → Gold)"]
        G1["Run_Gold_DLT_Pipeline"]
    end

    M1 -.-> pl_source_to_bronze
    M2 -.-> pl_landing_to_bronze
    M3 -.-> pl_bronze_to_silver
    M4 -.-> pl_silver_to_gold
```

---

## Activity Type Reference

| Activity Type | Icon in ADF Studio | Purpose |
|--------------|-------------------|---------|
| ExecutePipeline | Blue rectangle with nested square | Calls another pipeline and waits for it |
| Lookup | Magnifying glass | Reads data from a dataset (returns rows) |
| Filter | Funnel | Filters rows based on a condition |
| ForEach | Loop arrows | Iterates over items (parallel or sequential) |
| GetMetadata | Info circle | Checks file properties (exists, size, etc.) |
| IfCondition | Diamond | Branches based on true/false expression |
| Copy | Two-page copy icon | Copies data from source dataset to sink dataset |
| Script | Document icon | Runs SQL script against a linked service |
| WebActivity | Globe icon | Sends HTTP request (used for Logic Apps webhook) |
| DatabricksNotebook | Databricks logo | Runs a notebook on a Databricks cluster |

---

## Linked Services Used

| Linked Service | Used By | Connects To |
|---------------|---------|------------|
| `ls_key_vault` | All other linked services | Azure Key Vault (stores all secrets) |
| `ls_azure_sql_store_a` | Copy activities (Store A tables) | Azure SQL Database `ecom-store-a` |
| `ls_azure_sql_store_b` | Copy activities (Store B tables) | Azure SQL Database `ecom-store-b` |
| `ls_adls_gen2` | Copy activities (Bronze read/write) | ADLS Gen2 storage account |
| `ls_delta_lake` | Script activities (audit table) | Databricks SQL endpoint (for audit.load_logs) |
| `ls_databricks` | DatabricksNotebook activities | Databricks workspace + cluster |

---

## Datasets Used

| Dataset | Type | Parameterized? | Used As |
|---------|------|---------------|---------|
| `ds_config_csv` | DelimitedText | No — fixed path to `configs/emr/load_config.csv` | Source for Lookup_Config |
| `ds_azure_sql` | AzureSqlTable | Yes — `SchemaName`, `TableName` parameters | Source for Copy activities (SQL → Parquet) |
| `ds_parquet_bronze` | Parquet | Yes — `Container`, `FolderPath`, `FileName` parameters | Sink for Copy activities (writes Parquet to ADLS) |
| `ds_delta_audit` | DeltaLakeTable | No — fixed to `audit.load_logs` | Used by Script activities for audit logging |
