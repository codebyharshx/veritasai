"""Maps router — GET /api/map/{capability}"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Literal

router = APIRouter()


def get_spark():
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


@router.get("/map/{capability}")
async def get_map_data(
    capability: str,
    granularity: Literal["pin_code", "district"] = "district",
):
    """
    Get geographic data for choropleth map showing medical desert severity.

    Returns regions color-coded by distance to nearest verified facility:
    - green: <50km
    - yellow: 50-100km
    - red: >100km
    """
    try:
        spark = get_spark()

        # Check if geo_lookup table exists
        try:
            geo_df = spark.table("workspace.veritas_dev.geo_lookup")
            geo_df = geo_df.filter(geo_df.capability == capability)

            if granularity == "district":
                # Aggregate to district level (take worst severity)
                from pyspark.sql import functions as F

                severity_order = F.when(F.col("desert_severity") == "red", 3) \
                    .when(F.col("desert_severity") == "yellow", 2) \
                    .otherwise(1)

                geo_df = geo_df.withColumn("severity_rank", severity_order)
                geo_df = geo_df.groupBy("pin_code").agg(
                    F.max("severity_rank").alias("max_severity"),
                    F.min("distance_km").alias("min_distance"),
                    F.first("nearest_facility_id").alias("nearest_facility_id"),
                    F.first("nearest_trust_score").alias("nearest_trust_score"),
                )

            rows = geo_df.collect()

            return {
                "capability": capability,
                "granularity": granularity,
                "region_count": len(rows),
                "regions": [
                    {
                        "pin_code": r.pin_code if hasattr(r, 'pin_code') else None,
                        "distance_km": r.distance_km if hasattr(r, 'distance_km') else r.min_distance,
                        "desert_severity": r.desert_severity if hasattr(r, 'desert_severity') else (
                            "red" if r.max_severity == 3 else "yellow" if r.max_severity == 2 else "green"
                        ),
                        "nearest_facility_id": r.nearest_facility_id,
                        "nearest_trust_score": r.nearest_trust_score,
                    }
                    for r in rows
                ]
            }

        except Exception:
            # geo_lookup table doesn't exist yet, return facility locations instead
            facilities_df = spark.table("workspace.veritas_dev.facilities_raw")

            rows = facilities_df.select(
                "facility_id", "facility_name", "state", "district",
                "latitude", "longitude", "facility_type"
            ).collect()

            return {
                "capability": capability,
                "granularity": "facilities",
                "message": "geo_lookup not computed yet, returning facility locations",
                "facility_count": len(rows),
                "facilities": [
                    {
                        "facility_id": r.facility_id,
                        "facility_name": r.facility_name,
                        "state": r.state,
                        "district": r.district,
                        "latitude": r.latitude,
                        "longitude": r.longitude,
                        "facility_type": r.facility_type,
                    }
                    for r in rows[:500]  # Limit for performance
                ]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/map/capabilities")
async def list_capabilities():
    """List all available capabilities for map filtering."""
    try:
        spark = get_spark()

        # Get unique capabilities from structured extractions
        df = spark.table("workspace.veritas_dev.facilities_structured")

        # This would need to parse JSON and extract unique capabilities
        # For now, return common capability types
        return {
            "capabilities": [
                "emergency_surgery",
                "dialysis",
                "oncology",
                "trauma",
                "obstetrics",
                "icu",
                "pediatrics",
                "cardiology",
                "orthopedics",
                "general_medicine",
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
