# Databricks notebook source
# MAGIC %md
# MAGIC # Stage 3 — Trust Debate
# MAGIC
# MAGIC Runs Advocate/Skeptic/Judge debate for each facility to produce trust scores.
# MAGIC This is the **key differentiator** — the debate transcript is shown in the UI.
# MAGIC
# MAGIC **Source:** Section 2.4 Stage 3 of VERITAS_PRD_TRD.md

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

# Configuration
SAMPLE_SIZE = 3  # Set to None for full run, small number for testing
RAW_TABLE = "workspace.veritas_dev.facilities_raw"
STRUCTURED_TABLE = "workspace.veritas_dev.facilities_structured"
TARGET_TABLE = "workspace.veritas_dev.trust_scores"
CONTRADICTIONS_TABLE = "workspace.veritas_dev.contradictions"
MAX_CONCURRENT = 5  # Each debate = 3 LLM calls, so keep low
OVERWRITE = True

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup MLflow

# COMMAND ----------

import mlflow
mlflow.openai.autolog()
mlflow.set_experiment("/Shared/veritas-trust-debate")

# COMMAND ----------

import sys
sys.path.insert(0, '/Workspace/Repos/harshitagarwal048@gmail.com/Veritas-AI-Lifeline')

# Force fresh import
modules_to_remove = [key for key in sys.modules.keys() if 'pipelines' in key or 'api' in key]
for mod in modules_to_remove:
    del sys.modules[mod]

from pipelines.trust_debate import run_trust_debate, preview_trust_scores

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Prerequisites

# COMMAND ----------

# Check that Stage 2 extraction is complete
structured_count = spark.table(STRUCTURED_TABLE).count()
print(f"Facilities with extracted data: {structured_count}")

if structured_count == 0:
    raise Exception("Stage 2 extraction not complete! Run 02_extraction first.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Trust Debate

# COMMAND ----------

stats = run_trust_debate(
    spark=spark,
    raw_table=RAW_TABLE,
    structured_table=STRUCTURED_TABLE,
    target_table=TARGET_TABLE,
    contradictions_table=CONTRADICTIONS_TABLE,
    sample_size=SAMPLE_SIZE,
    max_concurrent=MAX_CONCURRENT,
    overwrite=OVERWRITE,
)

# COMMAND ----------

# Print summary
print("\n" + "="*60)
print("TRUST DEBATE SUMMARY")
print("="*60)
print(f"Total facilities: {stats['total_facilities']}")
print(f"Successful debates: {stats['successful_debates']}")
print(f"Failed debates: {stats['failed_debates']}")
print(f"Contradictions found: {stats['total_contradictions']}")
print(f"Average trust score: {stats['avg_trust_score']:.1f}/100")
print("="*60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Results

# COMMAND ----------

preview_trust_scores(spark, TARGET_TABLE, num_rows=3)

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Contradictions

# COMMAND ----------

contras_df = spark.table(CONTRADICTIONS_TABLE)
print(f"Total contradictions: {contras_df.count()}")
contras_df.show(10, truncate=50)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Full Debate Transcript
# MAGIC
# MAGIC This is what users see in the "Trust Reasoning" section of the Facility Inspector.

# COMMAND ----------

df = spark.table(TARGET_TABLE)
sample = df.orderBy("trust_score").limit(1).collect()[0]  # Get lowest score

print(f"{'='*60}")
print(f"FACILITY TRUST DEBATE")
print(f"{'='*60}")
print(f"Facility ID: {sample.facility_id}")
print(f"Final Trust Score: {sample.trust_score}/100")
print(f"{'='*60}")

print(f"\n📢 ADVOCATE ARGUMENT:")
print(f"{'-'*40}")
print(sample.advocate_argument)

print(f"\n🔍 SKEPTIC ARGUMENT:")
print(f"{'-'*40}")
print(sample.skeptic_argument)

print(f"\n⚖️ JUDGE'S VERDICT:")
print(f"{'-'*40}")
print(sample.judge_reasoning)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC Once sample looks correct:
# MAGIC 1. Change `SAMPLE_SIZE = None` for full run
# MAGIC 2. Full run: ~90-120 min for 10K facilities (3 LLM calls each = 30K calls)
# MAGIC 3. Proceed to Stage 4 (Geographic Computation)
# MAGIC
# MAGIC **Drop-glass rule (Section 2.8):** If debate takes >90 min to debug, drop to single-pass scoring.
