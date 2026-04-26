"""Trust router — GET /api/trust/{facility_id}/debate"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()


def get_spark():
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


@router.get("/trust/{facility_id}/debate")
async def get_trust_debate(facility_id: str):
    """
    Get the full Advocate/Skeptic/Judge debate transcript for a facility.

    This is the "Trust Reasoning" section shown in the Facility Inspector.
    It's a key differentiator — making the AI's reasoning visible to users.
    """
    try:
        spark = get_spark()

        # Get trust score record
        trust_df = spark.table("workspace.veritas_dev.trust_scores")
        trust_row = trust_df.filter(trust_df.facility_id == facility_id).collect()

        if not trust_row:
            raise HTTPException(
                status_code=404,
                detail=f"No trust debate found for facility {facility_id}"
            )

        t = trust_row[0]

        # Get facility name for context
        raw_df = spark.table("workspace.veritas_dev.facilities_raw")
        raw_row = raw_df.filter(raw_df.facility_id == facility_id).collect()
        facility_name = raw_row[0].facility_name if raw_row else "Unknown"

        # Build MLflow trace URL if available
        mlflow_trace_url = None
        if hasattr(t, 'mlflow_run_id') and t.mlflow_run_id:
            # This would be configured based on MLflow tracking server URL
            mlflow_trace_url = f"/mlflow/#/experiments/0/runs/{t.mlflow_run_id}"

        return {
            "facility_id": facility_id,
            "facility_name": facility_name,
            "trust_score": t.trust_score,
            "advocate_argument": t.advocate_argument,
            "skeptic_argument": t.skeptic_argument,
            "judge_reasoning": t.judge_reasoning,
            "mlflow_trace_url": mlflow_trace_url,
            "debated_at": str(t.debated_at) if t.debated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trust/stats")
async def get_trust_stats():
    """Get aggregate trust score statistics."""
    try:
        spark = get_spark()

        trust_df = spark.table("workspace.veritas_dev.trust_scores")

        from pyspark.sql import functions as F

        stats = trust_df.agg(
            F.count("*").alias("total"),
            F.avg("trust_score").alias("avg_score"),
            F.min("trust_score").alias("min_score"),
            F.max("trust_score").alias("max_score"),
            F.stddev("trust_score").alias("stddev_score"),
        ).collect()[0]

        # Score distribution
        distribution = trust_df.groupBy(
            ((F.col("trust_score") / 20).cast("int") * 20).alias("bucket")
        ).count().orderBy("bucket").collect()

        return {
            "total_facilities": stats.total,
            "average_score": round(stats.avg_score, 1) if stats.avg_score else None,
            "min_score": stats.min_score,
            "max_score": stats.max_score,
            "stddev": round(stats.stddev_score, 1) if stats.stddev_score else None,
            "distribution": {
                f"{int(d.bucket)}-{int(d.bucket)+19}": d["count"]
                for d in distribution
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
