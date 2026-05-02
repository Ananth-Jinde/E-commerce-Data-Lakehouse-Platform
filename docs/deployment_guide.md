# Deployment Guide — Azure E-Commerce Data Lakehouse

This guide provides step-by-step instructions to deploy and run the entire pipeline.

---

## Prerequisites

- Azure Subscription with sufficient credits
- Azure CLI installed (`az login`)
- Databricks CLI installed (`pip install databricks-cli`)
- Python 3.10+ with pip
- Git installed

---

## Step 1: Create Azure Resources

### 1.1 Resource Group
```bash
az group create --name rg-ecommerce-data --location eastus
```

### 1.2 Storage Account (ADLS Gen2)
```bash
az storage account create \
  --name stecommercedatalake \
  --resource-group rg-ecommerce-data \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hns true  # Hierarchical namespace for ADLS Gen2
```

### 1.3 Create Containers
```bash
az storage container create --name landing --account-name stecommercedatalake
az storage container create --name bronze --account-name stecommercedatalake
az storage container create --name silver --account-name stecommercedatalake
az storage container create --name gold --account-name stecommercedatalake
az storage container create --name configs --account-name stecommercedatalake
```

### 1.4 Azure SQL Databases (x2)
```bash
# Create SQL Server
az sql server create \
  --name sql-ecommerce-server \
  --resource-group rg-ecommerce-data \
  --location eastus \
  --admin-user sqladmin \
  --admin-password <YourStrongPassword>

# Create Database — Store A
az sql db create --resource-group rg-ecommerce-data --server sql-ecommerce-server --name ecom-store-a --service-objective S0

# Create Database — Store B
az sql db create --resource-group rg-ecommerce-data --server sql-ecommerce-server --name ecom-store-b --service-objective S0
```

### 1.5 Azure Key Vault
```bash
az keyvault create \
  --name kv-ecommerce-data \
  --resource-group rg-ecommerce-data \
  --location eastus

# Store secrets (SQL connections + ADLS key for ADF)
az keyvault secret set --vault-name kv-ecommerce-data --name sql-store-a-connection-string --value "<your-store-a-connection-string>"
az keyvault secret set --vault-name kv-ecommerce-data --name sql-store-b-connection-string --value "<your-store-b-connection-string>"
az keyvault secret set --vault-name kv-ecommerce-data --name adls-storage-access-key --value "<your-storage-key>"
```

### 1.6 Azure Data Factory
```bash
az datafactory create \
  --resource-group rg-ecommerce-data \
  --factory-name adf-ecommerce-pipeline \
  --location eastus
```

### 1.7 Azure Databricks Workspace
```bash
az databricks workspace create \
  --resource-group rg-ecommerce-data \
  --name dbw-ecommerce-analytics \
  --location eastus \
  --sku premium
```

---

## Step 2: Generate & Load Source Data

### 2.1 Install Faker
```bash
cd data_generator
pip install -r requirements.txt
```

### 2.2 Generate SQL Scripts
```bash
python generate_store_a.py
python generate_store_b.py
python generate_reviews.py
```

### 2.3 Execute DDL Scripts
Connect to each Azure SQL database and run:
- `adf/source_scripts/store_a_ddl.sql` → on `ecom-store-a`
- `adf/source_scripts/store_b_ddl.sql` → on `ecom-store-b`

### 2.4 Execute Initial Load Scripts
- `adf/source_scripts/store_a_initial_load.sql` → on `ecom-store-a`
- `adf/source_scripts/store_b_initial_load.sql` → on `ecom-store-b`

### 2.5 Upload Config & Review Files
```bash
# Upload load_config.csv to configs container
az storage blob upload --account-name stecommercedatalake --container-name configs --file configs/load_config.csv --name emr/load_config.csv

# Upload product_reviews.csv to landing container
az storage blob upload --account-name stecommercedatalake --container-name landing --file configs/product_reviews.csv --name product_reviews/product_reviews.csv
```

---

## Step 3: Configure Databricks

### 3.1 Create Unity Catalog
1. Navigate to Databricks workspace → Data → Create Catalog
2. Name: `ecommerce_catalog`
3. Create schemas: `bronze`, `silver`, `gold`, `audit`

### 3.2 Create Access Connector
1. In Azure Portal → search "Access Connector for Azure Databricks" → Create
2. Place it in the same resource group `rg-ecommerce-data`
3. Go to ADLS storage account → Access Control (IAM) → Add role assignment
4. Assign **Storage Blob Data Contributor** role to the Access Connector's managed identity

### 3.3 Create Storage Credential
In Databricks SQL Editor:
```sql
CREATE STORAGE CREDENTIAL ecom_storage_credential
WITH (AZURE_MANAGED_IDENTITY = '/subscriptions/<sub-id>/resourceGroups/rg-ecommerce-data/providers/Microsoft.Databricks/accessConnectors/ecom-access-connector');
```

### 3.4 Create External Locations
```sql
CREATE EXTERNAL LOCATION bronze_location
  URL 'abfss://bronze@stecomdatalakedev.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL ecom_storage_credential);

CREATE EXTERNAL LOCATION silver_location
  URL 'abfss://silver@stecomdatalakedev.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL ecom_storage_credential);

CREATE EXTERNAL LOCATION gold_location
  URL 'abfss://gold@stecomdatalakedev.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL ecom_storage_credential);
```

### 3.5 Run Audit Table Setup
Execute `databricks/setup/audit_ddl.py` notebook.

---

## Step 4: Deploy Databricks Asset Bundles

```bash
cd databricks

# Update databricks.yml with your workspace URL
# Then deploy
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

---

## Step 5: Configure ADF

### 5.1 Connect ADF to Git (Optional but Recommended)
- ADF → Manage → Git configuration
- Connect to your GitHub repository

### 5.2 Create Linked Services
Import the JSON files from `adf/linked_services/` in this order:
1. `ls_key_vault.json` (first — others depend on it)
2. `ls_azure_sql_store_a.json`
3. `ls_azure_sql_store_b.json`
4. `ls_adls_gen2.json`
5. `ls_delta_lake.json`
6. `ls_databricks.json`

### 5.3 Create Datasets
Import from `adf/datasets/`:
- `ds_azure_sql.json`
- `ds_config_csv.json`
- `ds_parquet_bronze.json`
- `ds_delta_audit.json`

### 5.4 Create Pipelines
Import from `adf/pipelines/` in this order:
1. `pl_source_to_bronze.json`
2. `pl_landing_to_bronze.json`
3. `pl_bronze_to_silver.json`
4. `pl_silver_to_gold.json`
5. `pl_master.json` (last — references all child pipelines)

---

## Step 6: Run the Pipeline

### Initial Run
1. Navigate to ADF → Author → `pl_master`
2. Click **Debug** or **Add Trigger → Trigger Now**
3. Monitor each stage in the ADF Monitor tab

### Incremental Run (Day 2+)
1. Execute `store_a_incremental_load.sql` and `store_b_incremental_load.sql` against the SQL databases
2. Trigger `pl_master` again — the pipeline will detect changes via the audit table watermarks

---

## Step 7: Verify Results

### In Databricks
```sql
-- Check silver layer
SELECT COUNT(*) FROM ecommerce_catalog.silver.customers;
SELECT COUNT(*) FROM ecommerce_catalog.silver.orders;

-- Check SCD2 working
SELECT customer_key, COUNT(*) as versions
FROM ecommerce_catalog.silver.customers
GROUP BY customer_key
HAVING COUNT(*) > 1;

-- Check gold layer
SELECT * FROM ecommerce_catalog.gold.dim_customer LIMIT 10;
SELECT * FROM ecommerce_catalog.gold.fact_orders LIMIT 10;

-- Run business queries
-- See databricks/src/gold/business_queries.sql
```

### In ADF Monitor
- Check all 4 child pipelines completed successfully
- Verify row counts in audit.load_logs

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Key Vault access denied | Ensure ADF managed identity has **Key Vault Secrets User** role |
| Databricks can't read ADLS | Verify Access Connector has **Storage Blob Data Contributor** role |
| SCD2 merge fails | Ensure target table exists — first run should create it |
| DLT pipeline fails | Check Unity Catalog permissions on gold schema |
| Config not found | Verify load_config.csv is at `configs/emr/load_config.csv` in ADLS |
