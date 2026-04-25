"""Stage 1 — Ingestion pipeline for Veritas.

Reads VF_Hackathon_Dataset_India_Large.xlsx, normalizes columns,
generates UUIDs for missing IDs, and writes to Delta table.
"""
import uuid
from datetime import datetime
from typing import Optional

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType,
    TimestampType,
)


# Delta table schema matching FacilityRaw from api/schemas/facilities.py
FACILITIES_RAW_SCHEMA = StructType([
    StructField("facility_id", StringType(), False),
    StructField("facility_name", StringType(), False),
    StructField("state", StringType(), False),
    StructField("district", StringType(), False),
    StructField("pin_code", StringType(), False),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("facility_type", StringType(), False),
    StructField("bed_count", IntegerType(), True),
    StructField("unstructured_notes", StringType(), False),
    StructField("ingested_at", TimestampType(), False),
])

# Expected column mappings from Excel to schema
# Keys are possible Excel column names (lowercase), values are schema field names
COLUMN_MAPPINGS = {
    # facility_id variations
    "facility_id": "facility_id",
    "facilityid": "facility_id",
    "facility id": "facility_id",
    "id": "facility_id",
    # facility_name variations
    "facility_name": "facility_name",
    "facilityname": "facility_name",
    "facility name": "facility_name",
    "name": "facility_name",
    # state
    "state": "state",
    # district
    "district": "district",
    # pin_code variations
    "pin_code": "pin_code",
    "pincode": "pin_code",
    "pin code": "pin_code",
    "pin": "pin_code",
    "postal_code": "pin_code",
    # latitude
    "latitude": "latitude",
    "lat": "latitude",
    # longitude
    "longitude": "longitude",
    "long": "longitude",
    "lng": "longitude",
    # facility_type variations
    "facility_type": "facility_type",
    "facilitytype": "facility_type",
    "facility type": "facility_type",
    "type": "facility_type",
    # bed_count variations
    "bed_count": "bed_count",
    "bedcount": "bed_count",
    "bed count": "bed_count",
    "beds": "bed_count",
    "number_of_beds": "bed_count",
    # unstructured_notes variations
    "unstructured_notes": "unstructured_notes",
    "notes": "unstructured_notes",
    "description": "unstructured_notes",
    "remarks": "unstructured_notes",
    "comments": "unstructured_notes",
    "details": "unstructured_notes",
}

# Required fields that cannot be null
REQUIRED_FIELDS = ["facility_name", "state", "district", "pin_code", "facility_type", "unstructured_notes"]


def normalize_column_name(col_name: str) -> Optional[str]:
    """Map an Excel column name to the schema field name."""
    normalized = col_name.lower().strip().replace("-", "_")
    return COLUMN_MAPPINGS.get(normalized)


def run_ingestion(
    spark: SparkSession,
    source_path: str = "/Volumes/workspace/veritas_dev/raw_data/VF_Hackathon_Dataset_India_Large.xlsx",
    target_table: str = "workspace.veritas_dev.facilities_raw",
    sample_size: Optional[int] = None,
    overwrite: bool = True,
) -> dict:
    """
    Run the ingestion pipeline.

    Args:
        spark: SparkSession instance
        source_path: Path to the Excel file in Databricks Volume
        target_table: Full table name (catalog.schema.table)
        sample_size: If set, only process first N rows (for testing)
        overwrite: If True, overwrite existing table; if False, append

    Returns:
        dict with ingestion statistics
    """
    print(f"[Stage 1] Starting ingestion from {source_path}")

    # Read Excel file using pandas (Spark doesn't natively read Excel)
    print("[Stage 1] Reading Excel file...")
    pdf = pd.read_excel(source_path)
    original_count = len(pdf)
    print(f"[Stage 1] Read {original_count} rows from Excel")

    # Sample if requested
    if sample_size is not None:
        pdf = pdf.head(sample_size)
        print(f"[Stage 1] Sampling first {sample_size} rows for testing")

    # Show original columns for debugging
    print(f"[Stage 1] Original columns: {list(pdf.columns)}")

    # Normalize column names
    column_map = {}
    unmapped_columns = []
    for col in pdf.columns:
        mapped = normalize_column_name(col)
        if mapped:
            column_map[col] = mapped
        else:
            unmapped_columns.append(col)

    if unmapped_columns:
        print(f"[Stage 1] Warning: Unmapped columns (will be ignored): {unmapped_columns}")

    print(f"[Stage 1] Column mapping: {column_map}")

    # Rename columns
    pdf = pdf.rename(columns=column_map)

    # Keep only mapped columns that exist in our schema
    schema_fields = [f.name for f in FACILITIES_RAW_SCHEMA.fields if f.name != "ingested_at"]
    existing_fields = [f for f in schema_fields if f in pdf.columns]
    missing_fields = [f for f in schema_fields if f not in pdf.columns]

    if missing_fields:
        print(f"[Stage 1] Warning: Missing fields in source data: {missing_fields}")
        # Add missing columns with None values
        for field in missing_fields:
            pdf[field] = None

    # Select only schema fields
    pdf = pdf[schema_fields]

    # Generate UUIDs for missing facility_id
    null_id_mask = pdf["facility_id"].isna() | (pdf["facility_id"] == "")
    null_id_count = null_id_mask.sum()
    if null_id_count > 0:
        print(f"[Stage 1] Generating UUIDs for {null_id_count} rows with missing facility_id")
        pdf.loc[null_id_mask, "facility_id"] = [str(uuid.uuid4()) for _ in range(null_id_count)]

    # Convert pin_code to string (it might be numeric)
    pdf["pin_code"] = pdf["pin_code"].astype(str).str.replace(r"\.0$", "", regex=True)

    # Convert bed_count to nullable int
    pdf["bed_count"] = pd.to_numeric(pdf["bed_count"], errors="coerce").astype("Int64")

    # Convert lat/long to float
    pdf["latitude"] = pd.to_numeric(pdf["latitude"], errors="coerce")
    pdf["longitude"] = pd.to_numeric(pdf["longitude"], errors="coerce")

    # Add ingestion timestamp
    pdf["ingested_at"] = datetime.utcnow()

    # Identify rows with missing required fields
    skipped_rows = []
    for idx, row in pdf.iterrows():
        missing = []
        for field in REQUIRED_FIELDS:
            val = row.get(field)
            if pd.isna(val) or val == "" or val == "None":
                missing.append(field)
        if missing:
            skipped_rows.append({
                "index": idx,
                "facility_id": row.get("facility_id", "N/A"),
                "missing_fields": missing,
            })

    # Filter out rows with missing required fields
    valid_mask = ~pdf.index.isin([r["index"] for r in skipped_rows])
    pdf_valid = pdf[valid_mask].copy()

    print(f"[Stage 1] Valid rows: {len(pdf_valid)}, Skipped rows: {len(skipped_rows)}")

    if skipped_rows:
        print("[Stage 1] Skipped rows due to missing required fields:")
        for row in skipped_rows[:10]:  # Show first 10
            print(f"  - Index {row['index']}, ID: {row['facility_id']}, Missing: {row['missing_fields']}")
        if len(skipped_rows) > 10:
            print(f"  ... and {len(skipped_rows) - 10} more")

    # Convert to Spark DataFrame
    print("[Stage 1] Converting to Spark DataFrame...")

    # Handle the Int64 nullable type for Spark
    pdf_valid["bed_count"] = pdf_valid["bed_count"].astype(object).where(pdf_valid["bed_count"].notna(), None)

    sdf = spark.createDataFrame(pdf_valid)

    # Cast columns to match schema
    sdf = sdf.select(
        F.col("facility_id").cast(StringType()),
        F.col("facility_name").cast(StringType()),
        F.col("state").cast(StringType()),
        F.col("district").cast(StringType()),
        F.col("pin_code").cast(StringType()),
        F.col("latitude").cast(DoubleType()),
        F.col("longitude").cast(DoubleType()),
        F.col("facility_type").cast(StringType()),
        F.col("bed_count").cast(IntegerType()),
        F.col("unstructured_notes").cast(StringType()),
        F.col("ingested_at").cast(TimestampType()),
    )

    # Write to Delta table
    print(f"[Stage 1] Writing to Delta table: {target_table}")
    write_mode = "overwrite" if overwrite else "append"
    sdf.write.format("delta").mode(write_mode).saveAsTable(target_table)

    # Verify write
    final_count = spark.table(target_table).count()
    print(f"[Stage 1] Successfully wrote {final_count} rows to {target_table}")

    # Return statistics
    stats = {
        "source_path": source_path,
        "target_table": target_table,
        "original_row_count": original_count,
        "sampled_row_count": len(pdf) if sample_size else original_count,
        "valid_row_count": len(pdf_valid),
        "skipped_row_count": len(skipped_rows),
        "final_table_count": final_count,
        "skipped_rows": skipped_rows,
        "generated_uuid_count": null_id_count,
    }

    return stats


def preview_data(
    spark: SparkSession,
    table_name: str = "workspace.veritas_dev.facilities_raw",
    num_rows: int = 5,
) -> None:
    """Preview data from the ingested table."""
    print(f"\n[Preview] First {num_rows} rows from {table_name}:")
    df = spark.table(table_name)
    df.show(num_rows, truncate=50)

    print(f"\n[Preview] Schema:")
    df.printSchema()

    print(f"\n[Preview] Row count: {df.count()}")


# For running directly in a Databricks notebook
if __name__ == "__main__":
    # This block runs when executed as a script in Databricks
    # spark is automatically available in Databricks notebooks
    pass
