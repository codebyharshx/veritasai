# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 2 — Structured Extraction
# MAGIC
# MAGIC Extracts structured capabilities, staff, and equipment from facility notes
# MAGIC using Llama 3.3 70B via Databricks AI Gateway.
# MAGIC
# MAGIC **Source:** Section 2.4 Stage 2 of VERITAS_PRD_TRD.md

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install dependencies

# COMMAND ----------

%pip install openai pydantic mlflow --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Configuration - adjust these for testing vs full run
SAMPLE_SIZE = 5  # Set to None for full dataset, or a number for testing
SOURCE_TABLE = "workspace.veritas_dev.facilities_raw"
TARGET_TABLE = "workspace.veritas_dev.facilities_structured"
CITATIONS_TABLE = "workspace.veritas_dev.citations"
MAX_CONCURRENT = 3  # Very low for Free Edition rate limits (has retry logic)
OVERWRITE = True

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup MLflow and imports

# COMMAND ----------

import mlflow

# Enable MLflow autolog for all OpenAI calls
mlflow.openai.autolog()

# Set experiment for tracking
mlflow.set_experiment("/Shared/veritas-extraction")

# COMMAND ----------

import sys
sys.path.insert(0, '/Workspace/Repos/harshitagarwal048@gmail.com/Veritas-AI-Lifeline')

# Force fresh import
modules_to_remove = [key for key in sys.modules.keys() if 'pipelines' in key or 'api' in key]
for mod in modules_to_remove:
    del sys.modules[mod]

from pipelines.extraction import run_extraction, preview_extractions

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test LLM Connection

# COMMAND ----------

# Quick test that the LLM is accessible
from api.llm_client import get_llm_client, MODEL_CHAT

client = get_llm_client()
response = client.chat.completions.create(
    model=MODEL_CHAT,
    messages=[{"role": "user", "content": "Say 'LLM ready' in exactly 2 words."}],
    max_tokens=10,
)
print(f"LLM test: {response.choices[0].message.content}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Extraction

# COMMAND ----------

stats = run_extraction(
    spark=spark,
    source_table=SOURCE_TABLE,
    target_table=TARGET_TABLE,
    citations_table=CITATIONS_TABLE,
    sample_size=SAMPLE_SIZE,
    max_concurrent=MAX_CONCURRENT,
    overwrite=OVERWRITE,
)

# COMMAND ----------

# Print summary
print("\n" + "="*60)
print("EXTRACTION SUMMARY")
print("="*60)
print(f"Source: {stats['source_table']}")
print(f"Target: {stats['target_table']}")
print(f"Total facilities: {stats['total_facilities']}")
print(f"Successful extractions: {stats['successful_extractions']}")
print(f"Failed extractions: {stats['failed_extractions']}")
print(f"Total citations generated: {stats['total_citations']}")
print("="*60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Results

# COMMAND ----------

preview_extractions(spark, TARGET_TABLE, num_rows=3)

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Citations

# COMMAND ----------

citations_df = spark.table(CITATIONS_TABLE)
print(f"Total citations: {citations_df.count()}")
citations_df.show(5, truncate=50)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Extraction Detail

# COMMAND ----------

# Show detailed extraction for one facility
import json

df = spark.table(TARGET_TABLE)
sample = df.limit(1).collect()[0]

# Parse JSON strings
capabilities = json.loads(sample.verified_capabilities_json) if sample.verified_capabilities_json else []
staff = json.loads(sample.staff_json) if sample.staff_json else []
equipment = json.loads(sample.equipment_json) if sample.equipment_json else []

print(f"Facility ID: {sample.facility_id}")
print(f"\nVerified Capabilities ({len(capabilities)}):")
for cap in capabilities:
    print(f"  - {cap['capability']}")
    print(f"    Confidence: {cap['confidence']}")
    evidence = cap.get('evidence_sentence', '')[:80]
    print(f"    Evidence: \"{evidence}...\"")

print(f"\nStaff ({len(staff)}):")
for s in staff:
    print(f"  - {s['role']} ({s.get('specialty', 'N/A')})")

print(f"\nEquipment ({len(equipment)}):")
for eq in equipment:
    status = "functional" if eq.get('functional', True) else "non-functional"
    print(f"  - {eq['item']} ({status})")

print(f"\nOperational Hours: {sample.operational_hours}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC Once the sample looks correct:
# MAGIC 1. Change `SAMPLE_SIZE = None` to run on full dataset
# MAGIC 2. Re-run extraction (will take 30-60 minutes for 10K facilities)
# MAGIC 3. Proceed to Stage 3 (Trust Debate)
