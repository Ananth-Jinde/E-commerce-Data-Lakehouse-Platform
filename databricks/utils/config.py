"""
Centralized Configuration Module
Storage access is managed via Unity Catalog External Locations.
"""


class Config:
    """Centralized configuration for the E-Commerce Data Lakehouse."""

    # ── Unity Catalog ──
    CATALOG = "ecommerce_catalog"
    SILVER_SCHEMA = "silver"
    GOLD_SCHEMA = "gold"

    # ── Storage ──
    # Storage account name is not a secret — it's a public endpoint.
    # Access control is handled by Unity Catalog External Locations.
    STORAGE_ACCOUNT = "stecomdatalakedev"

    # ── Data Sources ──
    STORE_A = "store-a"
    STORE_B = "store-b"

    @classmethod
    def get_bronze_path(cls, datasource, table_name):
        """Build the ADLS path for a bronze layer table.
        Access is granted via Unity Catalog External Location (not storage keys).
        """
        target = "store_a" if datasource == cls.STORE_A else "store_b"
        return f"abfss://bronze@{cls.STORAGE_ACCOUNT}.dfs.core.windows.net/{target}/{table_name}"

    @classmethod
    def get_silver_table(cls, table_name):
        """Get fully qualified Unity Catalog table name for silver."""
        return f"{cls.CATALOG}.{cls.SILVER_SCHEMA}.{table_name}"

    @classmethod
    def get_gold_table(cls, table_name):
        """Get fully qualified Unity Catalog table name for gold."""
        return f"{cls.CATALOG}.{cls.GOLD_SCHEMA}.{table_name}"
