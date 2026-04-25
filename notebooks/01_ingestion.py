# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 1 — Ingestion
# MAGIC
# MAGIC Reads `VF_Hackathon_Dataset_India_Large.xlsx` from the Volume, normalizes columns,
# MAGIC generates UUIDs for missing facility IDs, and writes to `workspace.veritas_dev.facilities_raw`.
# MAGIC
# MAGIC **Source:** Section 2.4 Stage 1 of VERITAS_PRD_TRD.md

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Configuration - adjust these for testing vs full run
SAMPLE_SIZE = 10  # Set to None for full dataset, or a number for testing
SOURCE_PATH = "/Volumes/workspace/veritas_dev/raw_data/VF_Hackathon_Dataset_India_Large.xlsx"
TARGET_TABLE = "workspace.veritas_dev.facilities_raw"
OVERWRITE = True  # Set to False to append instead of overwrite

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install dependencies

# COMMAND ----------

%pip install openpyxl --quiet

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Ingestion

# COMMAND ----------

import sys
sys.path.insert(0, '/Workspace/Repos/veritas/Veritas-AI-Lifeline')  # Adjust if needed

# Import the ingestion module
from pipelines.ingestion import run_ingestion, preview_data

# COMMAND ----------

# Run the ingestion pipeline
stats = run_ingestion(
    spark=spark,
    source_path=SOURCE_PATH,
    target_table=TARGET_TABLE,
    sample_size=SAMPLE_SIZE,
    overwrite=OVERWRITE,
)

# COMMAND ----------

# Print summary statistics
print("\n" + "="*60)
print("INGESTION SUMMARY")
print("="*60)
print(f"Source: {stats['source_path']}")
print(f"Target: {stats['target_table']}")
print(f"Original rows in Excel: {stats['original_row_count']}")
print(f"Rows processed: {stats['sampled_row_count']}")
print(f"Valid rows written: {stats['valid_row_count']}")
print(f"Rows skipped (missing required fields): {stats['skipped_row_count']}")
print(f"UUIDs generated: {stats['generated_uuid_count']}")
print(f"Final table row count: {stats['final_table_count']}")
print("="*60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Ingested Data

# COMMAND ----------

# Preview the data
preview_data(spark, TARGET_TABLE, num_rows=10)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Data Quality

# COMMAND ----------

# Check for any remaining data quality issues
df = spark.table(TARGET_TABLE)

print("Data Quality Checks:")
print("-" * 40)

# Check for null values in required fields
required_fields = ["facility_id", "facility_name", "state", "district", "pin_code", "facility_type", "unstructured_notes"]
for field in required_fields:
    null_count = df.filter(df[field].isNull()).count()
    print(f"  {field}: {null_count} nulls")

# Check facility_id uniqueness
total = df.count()
unique_ids = df.select("facility_id").distinct().count()
print(f"\nUniqueness check:")
print(f"  Total rows: {total}")
print(f"  Unique facility_ids: {unique_ids}")
print(f"  Duplicates: {total - unique_ids}")

# Check geographic coverage
print(f"\nGeographic coverage:")
states = df.select("state").distinct().count()
districts = df.select("district").distinct().count()
print(f"  Unique states: {states}")
print(f"  Unique districts: {districts}")

# Check for facilities with lat/long
with_coords = df.filter(df.latitude.isNotNull() & df.longitude.isNotNull()).count()
print(f"\nFacilities with coordinates: {with_coords} / {total} ({100*with_coords/total:.1f}%)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample of unstructured_notes field
# MAGIC
# MAGIC This is the primary input for Stage 2 extraction.

# COMMAND ----------

# Show a few examples of unstructured_notes
sample_notes = df.select("facility_name", "facility_type", "unstructured_notes").limit(3).collect()

for i, row in enumerate(sample_notes, 1):
    print(f"\n{'='*60}")
    print(f"Example {i}: {row.facility_name} ({row.facility_type})")
    print(f"{'='*60}")
    print(row.unstructured_notes[:500] if row.unstructured_notes else "No notes")
    if row.unstructured_notes and len(row.unstructured_notes) > 500:
        print(f"... [{len(row.unstructured_notes) - 500} more characters]")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC Once the sample looks correct:
# MAGIC 1. Change `SAMPLE_SIZE = None` to run on full dataset
# MAGIC 2. Re-run all cells
# MAGIC 3. Proceed to Stage 2 (Structured Extraction)
