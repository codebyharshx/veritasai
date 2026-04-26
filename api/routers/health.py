"""Health router — GET /api/health"""
from fastapi import APIRouter
from typing import Literal

router = APIRouter()


def get_spark():
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


@router.get("/health")
async def health_check():
    """
    Liveness check returning:
    - Overall status
    - Model serving status
    - Table row counts
    """
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    issues = []

    # Check Spark/Delta tables
    table_counts = {}
    tables_to_check = [
        "workspace.veritas_dev.facilities_raw",
        "workspace.veritas_dev.facilities_structured",
        "workspace.veritas_dev.trust_scores",
        "workspace.veritas_dev.citations",
        "workspace.veritas_dev.contradictions",
    ]

    try:
        spark = get_spark()

        for table in tables_to_check:
            try:
                count = spark.table(table).count()
                table_counts[table.split(".")[-1]] = count
            except Exception as e:
                table_counts[table.split(".")[-1]] = -1
                issues.append(f"Table {table} not accessible: {str(e)[:50]}")

    except Exception as e:
        status = "unhealthy"
        issues.append(f"Spark connection failed: {str(e)[:50]}")

    # Check LLM availability
    model_serving_status = "unknown"
    try:
        from api.llm_client import get_llm_client, MODEL_CHAT

        client = get_llm_client()
        response = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        if response.choices:
            model_serving_status = "available"
        else:
            model_serving_status = "degraded"
            issues.append("LLM returned empty response")
    except Exception as e:
        model_serving_status = "unavailable"
        issues.append(f"LLM error: {str(e)[:50]}")
        status = "degraded"

    # Determine overall status
    if table_counts.get("facilities_raw", 0) == 0:
        status = "degraded"
        issues.append("No facilities data loaded")

    if any(v == -1 for v in table_counts.values()):
        status = "degraded"

    if model_serving_status == "unavailable":
        status = "degraded"

    return {
        "status": status,
        "model_serving_status": model_serving_status,
        "table_counts": table_counts,
        "issues": issues if issues else None,
    }


@router.get("/health/tables")
async def table_details():
    """Get detailed table information."""
    try:
        spark = get_spark()

        tables = {}

        # Facilities raw
        try:
            df = spark.table("workspace.veritas_dev.facilities_raw")
            tables["facilities_raw"] = {
                "count": df.count(),
                "columns": df.columns,
            }
        except:
            tables["facilities_raw"] = {"error": "Not found"}

        # Facilities structured
        try:
            df = spark.table("workspace.veritas_dev.facilities_structured")
            tables["facilities_structured"] = {
                "count": df.count(),
                "columns": df.columns,
            }
        except:
            tables["facilities_structured"] = {"error": "Not found"}

        # Trust scores
        try:
            df = spark.table("workspace.veritas_dev.trust_scores")
            from pyspark.sql import functions as F
            stats = df.agg(
                F.count("*").alias("count"),
                F.avg("trust_score").alias("avg_score"),
            ).collect()[0]
            tables["trust_scores"] = {
                "count": stats["count"],
                "avg_trust_score": round(stats.avg_score, 1) if stats.avg_score else None,
            }
        except:
            tables["trust_scores"] = {"error": "Not found"}

        # Citations
        try:
            df = spark.table("workspace.veritas_dev.citations")
            tables["citations"] = {"count": df.count()}
        except:
            tables["citations"] = {"error": "Not found"}

        # Contradictions
        try:
            df = spark.table("workspace.veritas_dev.contradictions")
            tables["contradictions"] = {"count": df.count()}
        except:
            tables["contradictions"] = {"error": "Not found"}

        return {"tables": tables}

    except Exception as e:
        return {"error": str(e)}
