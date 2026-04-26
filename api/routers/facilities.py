"""Facilities router — GET /api/facilities/{facility_id}"""
import json
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter()

# Database connection will be injected
# For now, using mock data structure
def get_spark():
    """Get Spark session - to be configured for Databricks Connect or local."""
    # This will be replaced with actual Databricks connection
    from pyspark.sql import SparkSession
    return SparkSession.builder.getOrCreate()


@router.get("/facilities/{facility_id}")
async def get_facility(facility_id: str):
    """
    Get detailed facility information including:
    - Basic info (name, location, type)
    - Structured extraction (capabilities, staff, equipment)
    - Trust score
    - Citations
    - Contradictions
    """
    try:
        spark = get_spark()

        # Get raw facility data
        raw_df = spark.table("workspace.veritas_dev.facilities_raw")
        raw_row = raw_df.filter(raw_df.facility_id == facility_id).collect()

        if not raw_row:
            raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found")

        raw = raw_row[0]

        # Get structured extraction
        structured_df = spark.table("workspace.veritas_dev.facilities_structured")
        structured_row = structured_df.filter(structured_df.facility_id == facility_id).collect()

        capabilities = []
        staff = []
        equipment = []
        operational_hours = None

        if structured_row:
            s = structured_row[0]
            capabilities = json.loads(s.verified_capabilities_json) if s.verified_capabilities_json else []
            staff = json.loads(s.staff_json) if s.staff_json else []
            equipment = json.loads(s.equipment_json) if s.equipment_json else []
            operational_hours = s.operational_hours

        # Get trust score
        trust_df = spark.table("workspace.veritas_dev.trust_scores")
        trust_row = trust_df.filter(trust_df.facility_id == facility_id).collect()

        trust_score = None
        if trust_row:
            trust_score = trust_row[0].trust_score

        # Get citations
        citations_df = spark.table("workspace.veritas_dev.citations")
        citations = [
            {
                "citation_id": c.citation_id,
                "claim_type": c.claim_type,
                "claim_text": c.claim_text,
                "source_sentence": c.source_sentence,
            }
            for c in citations_df.filter(citations_df.facility_id == facility_id).collect()
        ]

        # Get contradictions
        contras_df = spark.table("workspace.veritas_dev.contradictions")
        contradictions = [
            {
                "contradiction_id": c.contradiction_id,
                "claim": c.claim,
                "evidence_gap": c.evidence_gap,
                "trust_impact": c.trust_impact,
                "severity": c.severity,
            }
            for c in contras_df.filter(contras_df.facility_id == facility_id).collect()
        ]

        return {
            "facility_id": raw.facility_id,
            "facility_name": raw.facility_name,
            "state": raw.state,
            "district": raw.district,
            "pin_code": raw.pin_code,
            "latitude": raw.latitude,
            "longitude": raw.longitude,
            "facility_type": raw.facility_type,
            "bed_count": raw.bed_count,
            "unstructured_notes": raw.unstructured_notes,
            "verified_capabilities": capabilities,
            "staff": staff,
            "equipment": equipment,
            "operational_hours": operational_hours,
            "trust_score": trust_score,
            "citations": citations,
            "contradictions": contradictions,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facilities")
async def list_facilities(
    state: Optional[str] = None,
    district: Optional[str] = None,
    facility_type: Optional[str] = None,
    min_trust_score: Optional[int] = None,
    limit: int = 100,
):
    """List facilities with optional filters."""
    try:
        spark = get_spark()

        df = spark.table("workspace.veritas_dev.facilities_raw")

        if state:
            df = df.filter(df.state == state)
        if district:
            df = df.filter(df.district == district)
        if facility_type:
            df = df.filter(df.facility_type == facility_type)

        # Join with trust scores if filtering by score
        if min_trust_score:
            trust_df = spark.table("workspace.veritas_dev.trust_scores")
            df = df.join(trust_df, on="facility_id", how="inner")
            df = df.filter(df.trust_score >= min_trust_score)

        rows = df.limit(limit).collect()

        return {
            "count": len(rows),
            "facilities": [
                {
                    "facility_id": r.facility_id,
                    "facility_name": r.facility_name,
                    "state": r.state,
                    "district": r.district,
                    "facility_type": r.facility_type,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                }
                for r in rows
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
