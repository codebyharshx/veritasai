"""Pydantic schemas for API requests and responses — Section 2.5."""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from .facilities import FacilityStructured, VerifiedCapability
from .trust import TrustScore, Contradiction
from .citations import Citation
from .geographic import GeoLookup


# =============================================================================
# GET /api/facilities/{facility_id}
# =============================================================================

class FacilityDetailResponse(BaseModel):
    """Response for GET /api/facilities/{facility_id}."""
    facility_id: str
    facility_name: str
    state: str
    district: str
    pin_code: str
    latitude: Optional[float]
    longitude: Optional[float]
    facility_type: str
    bed_count: Optional[int]
    unstructured_notes: str

    # Structured extraction
    verified_capabilities: list[VerifiedCapability]
    staff: list[dict]  # Simplified for API response
    equipment: list[dict]
    operational_hours: Optional[str]

    # Trust scoring
    trust_score: Optional[int]

    # Citations for this facility
    citations: list[Citation]

    # Contradictions for this facility
    contradictions: list[Contradiction]


# =============================================================================
# GET /api/map/{capability}
# =============================================================================

class MapDataResponse(BaseModel):
    """Response for GET /api/map/{capability}."""
    capability: str
    granularity: Literal["pin_code", "district"]
    regions: list[GeoLookup]


# =============================================================================
# POST /api/query
# =============================================================================

class QueryRequest(BaseModel):
    """Request body for POST /api/query."""
    query: str = Field(..., description="Natural language query")
    max_results: int = Field(default=5, ge=1, le=20)


class QueryResultFacility(BaseModel):
    """A single facility in query results."""
    facility_id: str
    facility_name: str
    state: str
    district: str
    distance_km: Optional[float]
    trust_score: Optional[int]
    justification: str = Field(..., description="One-sentence explanation")
    matching_capabilities: list[str]


class QueryResponse(BaseModel):
    """Response for POST /api/query."""
    query: str
    results: list[QueryResultFacility]
    mlflow_trace_id: Optional[str] = Field(None, description="For 'Show reasoning' link")


# =============================================================================
# GET /api/trust/{facility_id}/debate
# =============================================================================

class TrustDebateResponse(BaseModel):
    """Response for GET /api/trust/{facility_id}/debate."""
    facility_id: str
    trust_score: int
    advocate_argument: str
    skeptic_argument: str
    judge_reasoning: str
    mlflow_trace_url: Optional[str] = Field(None, description="Link to MLflow trace")


# =============================================================================
# GET /api/citation/{citation_id}
# =============================================================================

class CitationResponse(BaseModel):
    """Response for GET /api/citation/{citation_id}."""
    citation_id: str
    facility_id: str
    claim_type: str
    claim_text: str
    source_sentence: str
    source_offset_start: int
    source_offset_end: int


# =============================================================================
# GET /api/health
# =============================================================================

class HealthResponse(BaseModel):
    """Response for GET /api/health."""
    status: Literal["healthy", "degraded", "unhealthy"]
    model_serving_status: str
    table_counts: dict[str, int] = Field(
        ...,
        description="Row counts for each Delta table"
    )
