# Deployment Guide — Azure E-Commerce Data Lakehouse (Azure Portal UI)

This guide provides **step-by-step instructions using the Azure Portal UI** to deploy and run the entire pipeline. Every step includes where to click, what to fill in, and what to look for.

---

## Prerequisites

- Azure Subscription with sufficient credits
- Azure Portal access ([portal.azure.com](https://portal.azure.com))
- Python 3.10+ installed locally (for data generation only)
- Git installed (to clone the repository)
- A web browser (Edge, Chrome, or Firefox)

---

## Step 1: Create Azure Resources

### 1.1 Create a Resource Group

A resource group is a container that holds all related Azure resources.

1. Go to **Azure Portal** → search **"Resource groups"** in the top search bar
2. Click **"+ Create"**
3. Fill in:
   - **Subscription**: Select your subscription
   - **Resource group name**: `rg-ecommerce-data`
   - **Region**: `East US` (or your preferred region)
4. Click **"Review + create"** → **"Create"**

> **Why a Resource Group?**: It groups all project resources together. When you're done, you can delete the entire group to clean up everything at once.

---

### 1.2 Create Storage Account (ADLS Gen2)

ADLS Gen2 is where all your data lives — landing, bronze, silver, gold layers.

1. In Azure Portal → search **"Storage accounts"** → click **"+ Create"**
2. **Basics tab**:
   - **Resource group**: `rg-ecommerce-data`
   - **Storage account name**: `stecommercedatalake` (must be globally unique, lowercase, no hyphens)
   - **Region**: `East US` (same as resource group)
   - **Performance**: `Standard`
   - **Redundancy**: `Locally-redundant storage (LRS)` (cheapest for dev)
3. **Advanced tab**:
   - ⚠️ **Enable hierarchical namespace**: **CHECK THIS BOX** ← This is what makes it ADLS Gen2 instead of regular Blob Storage. Without this, folder-level operations don't work.
4. Click **"Review + create"** → **"Create"**
5. Once created, go to the storage account → **"Containers"** in the left sidebar
6. Create 5 containers (click **"+ Container"** for each):
   - `landing` — for raw flat files (CSV)
   - `bronze` — for Parquet files from source systems
   - `silver` — for Delta tables (CDM + SCD2)
   - `gold` — for Delta tables (star schema)
   - `configs` — for pipeline metadata files

> **Why Hierarchical Namespace?**: It enables ADLS Gen2 features like atomic directory operations, ACLs, and efficient rename operations. Without it, you just have Blob Storage which doesn't support these.

---

### 1.3 Create Azure SQL Databases (x2)

These simulate the two regional stores with different schemas.

1. In Azure Portal → search **"SQL databases"** → click **"+ Create"**
2. **Basics tab**:
   - **Resource group**: `rg-ecommerce-data`
   - **Database name**: `ecom-store-a`
   - **Server**: Click **"Create new"**
     - **Server name**: `sql-ecommerce-server` (globally unique)
     - **Location**: `East US`
     - **Authentication**: Select **"Use SQL authentication"**
     - **Server admin login**: `sqladmin`
     - **Password**: Choose a strong password (save this — you'll need it for Key Vault)
     - Click **"OK"**
   - **Want to use SQL elastic pool?**: No
   - **Workload environment**: `Development` (cheaper)
3. **Compute + storage** tab:
   - Click **"Configure database"** → Select **"Basic"** tier (cheapest, ~$5/month)
4. Click **"Review + create"** → **"Create"**
5. **Repeat for Store B**:
   - Same server (`sql-ecommerce-server`)
   - Database name: `ecom-store-b`
   - Same settings

6. **Configure Firewall** (required to connect from your local machine and ADF):
   - Go to the SQL Server (not database) → **"Networking"** in the left sidebar
   - Under **"Firewall rules"**, click **"+ Add your client IPv4 address"**
   - Toggle **"Allow Azure services and resources to access this server"** → **Yes** ← Essential for ADF to connect
   - Click **"Save"**

---

### 1.4 Create Azure Key Vault

Key Vault stores all secrets (SQL connection strings, Databricks tokens, storage keys).

1. In Azure Portal → search **"Key vaults"** → click **"+ Create"**
2. **Basics tab**:
   - **Resource group**: `rg-ecommerce-data`
   - **Key vault name**: `kv-ecommerce-data` (globally unique)
   - **Region**: `East US`
   - **Pricing tier**: `Standard`
3. **Access configuration tab**:
   - **Permission model**: Select **"Azure role-based access control (RBAC)"**
4. Click **"Review + create"** → **"Create"**

**Add Secrets to Key Vault**:

5. Go to the Key Vault → **"Secrets"** in the left sidebar → click **"+ Generate/Import"**
6. Add these 3 secrets (one at a time):

| Secret Name | Value | Where to Find It |
|-------------|-------|-------------------|
| `sql-store-a-connection-string` | `Server=tcp:sql-ecommerce-server.database.windows.net,1433;Initial Catalog=ecom-store-a;User ID=sqladmin;Password=<your-password>;` | Construct from your SQL server details |
| `sql-store-b-connection-string` | Same format but `Initial Catalog=ecom-store-b` | Same as above |
| `adls-storage-access-key` | The storage account access key | Storage account → "Access keys" → Copy key1 |

To find the **storage access key**: Go to your storage account → **"Access keys"** in the left sidebar → Click **"Show"** → Copy **key1**.

---

### 1.5 Create Azure Data Factory

ADF orchestrates the entire pipeline.

1. In Azure Portal → search **"Data factories"** → click **"+ Create"**
2. **Basics tab**:
   - **Resource group**: `rg-ecommerce-data`
   - **Name**: `adf-ecommerce-pipeline`
   - **Region**: `East US`
   - **Version**: V2
3. **Git configuration** tab:
   - Choose **"Configure Git later"** (you can connect it later)
4. Click **"Review + create"** → **"Create"**

**Grant ADF Access to Key Vault**:

5. Go to your Key Vault → **"Access control (IAM)"** → click **"+ Add role assignment"**
6. **Role**: Search for **"Key Vault Secrets User"** → Select it → Click **"Next"**
7. **Members**: Click **"+ Select members"** → Search for `adf-ecommerce-pipeline` (the ADF managed identity) → Select it → Click **"Select"** → **"Review + assign"**

> **Why?**: ADF needs permission to READ secrets from Key Vault. The "Key Vault Secrets User" role grants read-only access to secrets.

---

### 1.6 Create Azure Databricks Workspace

Databricks runs all the PySpark transformations.

1. In Azure Portal → search **"Azure Databricks"** → click **"+ Create"**
2. **Basics tab**:
   - **Resource group**: `rg-ecommerce-data`
   - **Workspace name**: `dbw-ecommerce-analytics`
   - **Region**: `East US`
   - **Pricing tier**: **Premium** (required for Unity Catalog)
3. Click **"Review + create"** → **"Create"**

> **Why Premium?**: Unity Catalog (required for governance, external locations, and DLT) is only available on Premium tier.

---

## Step 2: Generate & Load Source Data

### 2.1 Generate Data Locally

On your local machine:

```bash
cd data_generator
pip install faker
python generate_store_a.py
python generate_store_b.py
python generate_reviews.py
```

This creates:
- `adf/source_scripts/store_a_initial_load.sql` — 2,000 customers, 500 products, 8,000 orders, 20,000 order items
- `adf/source_scripts/store_b_initial_load.sql` — 1,500 customers, 400 products, 6,000 orders, 15,000 order details
- `configs/product_reviews.csv` — 5,000 product reviews

### 2.2 Execute DDL Scripts (Create Tables)

1. In Azure Portal → go to your SQL database `ecom-store-a` → click **"Query editor (preview)"** in the left sidebar
2. Login with `sqladmin` / your password
3. Copy-paste the contents of `adf/source_scripts/store_a_ddl.sql` → click **"Run"**
4. Repeat for `ecom-store-b` with `store_b_ddl.sql`

### 2.3 Execute Initial Load Scripts (Insert Data)

1. In the same Query editor for `ecom-store-a`:
   - Copy-paste the contents of `adf/source_scripts/store_a_initial_load.sql`
   - ⚠️ This is a large file — you may need to run it in batches (copy sections between `GO` statements)
   - Click **"Run"**
2. Repeat for `ecom-store-b` with `store_b_initial_load.sql`

### 2.4 Upload Config & Review Files to ADLS

1. Go to your storage account → **"Containers"**
2. Click on the **`configs`** container → Click **"+ Add directory"** → Name: `emr` → Enter the `emr` folder
3. Click **"Upload"** → Browse to `configs/load_config.csv` → Upload
4. Go back to **Containers** → Click **`landing`** container → **"+ Add directory"** → Name: `product_reviews` → Enter it
5. Click **"Upload"** → Browse to `configs/product_reviews.csv` → Upload

**Verify**: You should see:
- `configs/emr/load_config.csv`
- `landing/product_reviews/product_reviews.csv`

---

## Step 3: Configure Databricks

### 3.1 Create Unity Catalog

1. Open the Databricks workspace → click **"Data"** in the left sidebar
2. Click **"Create Catalog"** (or if using the metastore, you may need to enable Unity Catalog first)
3. **Catalog name**: `ecommerce_catalog`
4. Click **"Create"**
5. Inside the catalog, create 4 schemas:
   - Click the catalog name → **"Create Schema"**
   - Create: `bronze`, `silver`, `gold`, `audit`

### 3.2 Create Access Connector for Azure Databricks

The Access Connector provides a managed identity that Databricks uses to access ADLS.

1. In **Azure Portal** → search **"Access Connector for Azure Databricks"** → click **"+ Create"**
2. **Resource group**: `rg-ecommerce-data`
3. **Name**: `ecom-access-connector`
4. **Region**: `East US`
5. Click **"Review + create"** → **"Create"**

**Grant the Access Connector access to ADLS**:

6. Go to your **storage account** → **"Access control (IAM)"** → **"+ Add role assignment"**
7. **Role**: Search for **"Storage Blob Data Contributor"** → Select → **"Next"**
8. **Members**: Click **"+ Select members"** → Search for `ecom-access-connector` → Select → **"Review + assign"**

### 3.3 Create Storage Credential in Databricks

1. In Databricks workspace → open a **SQL Editor** (from the left sidebar → "SQL Editor")
2. Run:
```sql
CREATE STORAGE CREDENTIAL ecom_storage_credential
WITH (AZURE_MANAGED_IDENTITY = '/subscriptions/<your-sub-id>/resourceGroups/rg-ecommerce-data/providers/Microsoft.Databricks/accessConnectors/ecom-access-connector');
```

Replace `<your-sub-id>` with your Azure subscription ID. Find it in Azure Portal → Subscriptions.

### 3.4 Create External Locations

In the same SQL Editor, run:
```sql
CREATE EXTERNAL LOCATION bronze_location
  URL 'abfss://bronze@stecommercedatalake.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL ecom_storage_credential);

CREATE EXTERNAL LOCATION silver_location
  URL 'abfss://silver@stecommercedatalake.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL ecom_storage_credential);

CREATE EXTERNAL LOCATION gold_location
  URL 'abfss://gold@stecommercedatalake.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL ecom_storage_credential);
```

### 3.5 Create a Cluster

1. In Databricks → **"Compute"** in the left sidebar → **"Create Cluster"**
2. **Cluster name**: `ecom-cluster`
3. **Cluster mode**: Single Node (for development) or Multi Node
4. **Databricks Runtime Version**: 14.x or higher (with Delta Lake support)
5. **Node type**: `Standard_DS3_v2` (or similar, balance cost vs performance)
6. Click **"Create Cluster"**
7. **Note the Cluster ID** — you'll see it in the URL when you click on the cluster, or in the cluster details page. Format: `xxxx-xxxxxx-xxxxxxxx`

### 3.6 Connect Git Repository

1. In Databricks → **"Workspace"** → **"Repos"** → **"Add Repo"**
2. **Git repository URL**: Your GitHub repository URL
3. **Git provider**: GitHub
4. **Repository name**: `ecommerce-data-lakehouse`
5. Click **"Create Repo"**

### 3.7 Run Audit Table Setup

1. In Databricks → navigate to **Repos** → your repo → `databricks/setup/audit_ddl.py`
2. Click **"Run All"** (or Ctrl+Shift+Enter)
3. This creates the `audit` schema and `audit.load_logs` table

---

## Step 4: Deploy Databricks Asset Bundles

### 4.1 Update Configuration

1. Open `databricks/databricks.yml` in your editor
2. Update the `workspace.host` with your Databricks workspace URL
3. Update cluster IDs in `resources/ecommerce_dab.job.yml` with your cluster ID

### 4.2 Deploy (from your local terminal)

```bash
cd databricks

# Install the Databricks CLI (if not installed)
pip install databricks-cli

# Configure authentication
databricks configure --token
# Enter your workspace URL and a Personal Access Token (PAT)
# (Create a PAT in Databricks: User Settings → Developer → Access Tokens → Generate New Token)

# Validate the bundle
databricks bundle validate -t dev

# Deploy to development
databricks bundle deploy -t dev
```

### 4.3 Verify Deployment

1. In Databricks → **"Workflows"** → You should see `[dev] ecommerce_silver_transformation` job
2. Click on it to see the task dependency graph
3. In **"Delta Live Tables"** → You should see `[dev] ecommerce_gold_dlt_pipeline`

---

## Step 5: Configure Azure Data Factory

### 5.1 Open ADF Studio

1. In Azure Portal → go to your Data Factory → click **"Launch Studio"**
2. This opens the ADF authoring interface

### 5.2 Connect ADF to Git (Recommended)

1. In ADF Studio → click **"Manage"** (toolbox icon in the left sidebar) → **"Git configuration"**
2. **Repository type**: GitHub (or Azure DevOps)
3. Connect to your repository containing the `adf/` folder
4. **Collaboration branch**: `main`
5. **Root folder**: `/adf`

### 5.3 Create Linked Services

Go to **"Manage"** → **"Linked services"** → **"+ New"** for each:

**Order matters! Create in this exact order:**

1. **Key Vault** (first — others depend on it):
   - Search for **"Azure Key Vault"** → Select
   - **Name**: `ls_key_vault`
   - **Azure Key Vault URL**: `https://kv-ecommerce-data.vault.azure.net/`
   - Click **"Test connection"** → should succeed
   - Click **"Create"**

2. **Azure SQL — Store A**:
   - Search for **"Azure SQL Database"** → Select
   - **Name**: `ls_azure_sql_store_a`
   - **Connect via integration runtime**: AutoResolveIntegrationRuntime
   - **Account selection method**: From Azure subscription → Select your subscription, server, and database `ecom-store-a`
   - **Authentication type**: SQL Authentication
   - ⚠️ Instead of entering credentials directly, use **Azure Key Vault**:
     - **Connection string**: Select **"Azure Key Vault"**
     - **AKV linked service**: `ls_key_vault`
     - **Secret name**: `sql-store-a-connection-string`
   - Click **"Test connection"** → **"Create"**

3. **Azure SQL — Store B**: Same as above but name: `ls_azure_sql_store_b`, secret: `sql-store-b-connection-string`

4. **ADLS Gen2**:
   - Search for **"Azure Data Lake Storage Gen2"** → Select
   - **Name**: `ls_adls_gen2`
   - **URL**: `https://stecommercedatalake.dfs.core.windows.net/`
   - **Account key**: Select **"Azure Key Vault"** → `ls_key_vault` → Secret: `adls-storage-access-key`
   - **"Test connection"** → **"Create"**

5. **Delta Lake**:
   - Search for **"Azure Databricks Delta Lake"** → Select
   - **Name**: `ls_delta_lake`
   - **Domain**: Your Databricks workspace URL
   - **Access token**: Select **"Azure Key Vault"** → Secret: `databricks-access-token`
   - **Cluster ID**: Your cluster ID
   - **"Test connection"** → **"Create"**

6. **Databricks**:
   - Search for **"Azure Databricks"** → Select
   - **Name**: `ls_databricks`
   - **Workspace URL**: Your Databricks workspace URL
   - **Access token**: From Key Vault → Secret: `databricks-access-token`
   - **Existing interactive cluster**: Select your cluster ID
   - **"Test connection"** → **"Create"**

> **Important**: Before creating the Databricks linked service, you need to add the Databricks access token to Key Vault. In Databricks → User Settings → Developer → Access Tokens → Generate New Token → Copy it → Go to Key Vault → Add Secret: name `databricks-access-token`, value = the token.

### 5.4 Create Datasets

Go to **"Author"** (pencil icon) → **"Datasets"** → **"+ New dataset"** for each:

1. **ds_config_csv**: 
   - Type: **"Delimited Text"**
   - Linked service: `ls_adls_gen2`
   - File path: Container = `configs`, Folder = `emr`, File = `load_config.csv`
   - First row as header: Yes
   - Column delimiter: Comma

2. **ds_azure_sql**:
   - Type: **"Azure SQL Database"**
   - Linked service: `ls_azure_sql_store_a`
   - Add parameters: `SchemaName` (String, default: "dbo"), `TableName` (String)
   - Table → Use dynamic content: Schema = `@dataset().SchemaName`, Table = `@dataset().TableName`

3. **ds_parquet_bronze**:
   - Type: **"Parquet"**
   - Linked service: `ls_adls_gen2`
   - Add parameters: `Container` (String, default: "bronze"), `FolderPath` (String), `FileName` (String)
   - File path → Use dynamic content for all three parts
   - Compression: Snappy

4. **ds_delta_audit**:
   - Type: **"Azure Databricks Delta Lake"**
   - Linked service: `ls_delta_lake`
   - Database: `audit`, Table: `load_logs`

### 5.5 Create Pipelines

Go to **"Author"** → **"Pipelines"** → **"+ New pipeline"**. Create in this order:

1. **`pl_source_to_bronze`** — Import from `adf/pipelines/pl_source_to_bronze.json`
   - Or build manually following the pipeline JSON structure (Lookup → Filter → ForEach → activities inside)

2. **`pl_landing_to_bronze`** — Import from `adf/pipelines/pl_landing_to_bronze.json`

3. **`pl_bronze_to_silver`** — Import from `adf/pipelines/pl_bronze_to_silver.json`

4. **`pl_silver_to_gold`** — Import from `adf/pipelines/pl_silver_to_gold.json`

5. **`pl_master`** — Import from `adf/pipelines/pl_master.json` (LAST — references all child pipelines)

**To import a pipeline from JSON**:
1. In ADF Studio → **"Author"** → Right-click on **"Pipelines"** → **"Import from pipeline template"**
2. Or create a new pipeline → switch to **"Code"** view (the `{}` icon in the top right) → paste the JSON content → switch back to **"Design"** view

### 5.6 Publish All

Click **"Publish all"** at the top of ADF Studio to save and deploy all linked services, datasets, and pipelines.

---

## Step 6: Run the Pipeline

### 6.1 Initial Run

1. In ADF Studio → **"Author"** → Click on **`pl_master`**
2. Click **"Debug"** (for testing) or **"Add Trigger"** → **"Trigger Now"** (for a one-time run)
3. If `pl_master` has parameters (like `LogicAppWebhookUrl`), enter the value or leave the default
4. Click **"OK"** to start

### 6.2 Monitor the Run

1. Click **"Monitor"** in the left sidebar → **"Pipeline runs"**
2. You'll see `pl_master` running → click on it to see child pipeline status
3. Click on each child pipeline to see individual activity status:
   - **pl_source_to_bronze**: Watch the ForEach expand to show all 10 table loads
   - **pl_landing_to_bronze**: Should complete quickly (single file copy)
   - **pl_bronze_to_silver**: Watch the 6 Databricks notebook executions with their dependency ordering
   - **pl_silver_to_gold**: Watch the DLT pipeline trigger

4. Expected duration: ~15-30 minutes for the full pipeline (depends on cluster startup time and data volume)

### 6.3 Incremental Run (Day 2+)

1. In Azure Portal → go to `ecom-store-a` SQL database → **"Query editor"**
2. Run the contents of `adf/source_scripts/store_a_incremental_load.sql`
3. Repeat for `ecom-store-b` with `store_b_incremental_load.sql`
4. Go back to ADF → trigger `pl_master` again
5. The pipeline will detect changes via the audit table watermarks and only process new/changed rows
6. **Verify SCD2**: In Databricks, run:
```sql
SELECT customer_key, City, is_current, inserted_date, modified_date
FROM ecommerce_catalog.silver.customers
WHERE customer_key LIKE 'CUST-A-00001%'
ORDER BY inserted_date;
```
You should see TWO rows: the old record with `is_current = false` (New York) and the new record with `is_current = true` (Miami).

---

## Step 7: Verify Results

### 7.1 In Databricks SQL Editor

```sql
-- Check Silver layer row counts
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM ecommerce_catalog.silver.customers
UNION ALL
SELECT 'products', COUNT(*) FROM ecommerce_catalog.silver.products
UNION ALL
SELECT 'orders', COUNT(*) FROM ecommerce_catalog.silver.orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM ecommerce_catalog.silver.order_items
UNION ALL
SELECT 'product_categories', COUNT(*) FROM ecommerce_catalog.silver.product_categories
UNION ALL
SELECT 'product_reviews', COUNT(*) FROM ecommerce_catalog.silver.product_reviews;

-- Check Gold layer
SELECT * FROM ecommerce_catalog.gold.dim_customer LIMIT 10;
SELECT * FROM ecommerce_catalog.gold.dim_product LIMIT 10;
SELECT * FROM ecommerce_catalog.gold.dim_date LIMIT 10;
SELECT * FROM ecommerce_catalog.gold.fact_orders LIMIT 10;

-- Run a business query
SELECT d.year, d.month_name,
    COUNT(DISTINCT f.order_key) AS total_orders,
    ROUND(SUM(f.LineTotal), 2) AS total_revenue
FROM ecommerce_catalog.gold.fact_orders f
JOIN ecommerce_catalog.gold.dim_date d ON f.FK_DateKey = d.date_key
GROUP BY d.year, d.month_name, d.month_number
ORDER BY d.year, d.month_number;
```

### 7.2 In ADF Monitor

1. Go to **"Monitor"** → **"Pipeline runs"**
2. Verify all 4 child pipelines show ✅ **Succeeded**
3. Click on `pl_source_to_bronze` → check the ForEach → each table should show rows copied
4. Check `audit.load_logs` in Databricks:
```sql
SELECT * FROM ecommerce_catalog.audit.load_logs ORDER BY loaddate DESC;
```

### 7.3 Check Data Quality

```sql
-- Verify quarantine counts
SELECT is_quarantined, COUNT(*) as cnt
FROM ecommerce_catalog.silver.customers
GROUP BY is_quarantined;

-- Verify SCD2 is working (should have some is_current = false after incremental)
SELECT is_current, COUNT(*) as cnt
FROM ecommerce_catalog.silver.customers
GROUP BY is_current;
```

---

## Step 8: Set Up Scheduled Trigger (Optional)

### 8.1 Create a Schedule Trigger in ADF

1. In ADF Studio → **"Author"** → Click on `pl_master`
2. Click **"Add Trigger"** → **"New/Edit"** → **"+ New"**
3. **Name**: `trigger_daily_6am`
4. **Type**: Schedule
5. **Recurrence**: Every 1 Day
6. **Start time**: Set to 6:00 AM your timezone
7. Click **"OK"** → **"Publish all"**

### 8.2 Set Up Failure Alerting (Logic Apps)

1. In Azure Portal → search **"Logic Apps"** → **"+ Create"**
2. **Name**: `la-ecommerce-alerts`
3. **Trigger**: **"When a HTTP request is received"**
4. Add an action: **"Post message in a chat or channel"** (Microsoft Teams) or **"Send an email"** (Outlook)
5. Copy the **HTTP POST URL** from the Logic App trigger
6. Go to ADF → `pl_master` → update the `LogicAppWebhookUrl` parameter with this URL
7. **Publish all**

---

## Troubleshooting

| Issue | Where to Check | Solution |
|-------|---------------|----------|
| **Key Vault access denied** | ADF Monitor → activity error details | Ensure ADF managed identity has **"Key Vault Secrets User"** role on Key Vault |
| **Databricks can't read ADLS** | Databricks notebook error output | Verify Access Connector has **"Storage Blob Data Contributor"** role on storage account. Verify External Locations are created correctly. |
| **SQL connection fails** | ADF Linked Service → Test Connection | Check SQL Server firewall allows Azure services. Verify connection string secret in Key Vault is correct. |
| **SCD2 merge fails** | Databricks notebook error output | Ensure target table exists — first run creates it. Check if cluster has Delta Lake support. |
| **DLT pipeline fails** | Databricks → Delta Live Tables → Pipeline → Events | Check Unity Catalog permissions on gold schema. Verify Silver tables exist. |
| **Config not found** | ADF `pl_source_to_bronze` → Lookup_Config error | Verify `load_config.csv` is at `configs/emr/load_config.csv` in ADLS (not `configs/load_config.csv`) |
| **ForEach all tables fail** | ADF Monitor → ForEach → individual activities | Check the SQL Linked Service — the connection string might be wrong or expired |
| **Cluster startup slow** | Databricks → Compute | First run takes 5-10 min for cluster startup. Subsequent runs with warm cluster are faster. |

---

## Cost Optimization Tips

| Resource | Cost Tip |
|----------|----------|
| **SQL Databases** | Use Basic tier (~$5/month each). Switch to Serverless for auto-pause when idle. |
| **Storage Account** | LRS redundancy is cheapest. Clean up archive folders periodically. |
| **Databricks** | Use auto-termination (shut down cluster after 30 min idle). Use spot instances for dev. |
| **ADF** | Self-hosted IR is free. Pipeline runs cost ~$0.25 per activity run. |
| **Key Vault** | Standard tier is sufficient. Secret operations cost ~$0.03 per 10,000 operations. |

---

## Clean Up

To delete all resources and stop incurring costs:

1. In Azure Portal → search **"Resource groups"** → Click `rg-ecommerce-data`
2. Click **"Delete resource group"** → Type the resource group name to confirm → **"Delete"**

This deletes everything: SQL databases, storage account, ADF, Databricks, Key Vault — all in one action.
