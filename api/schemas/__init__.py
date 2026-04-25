"""Pydantic schemas for Veritas — all data contracts from Section 2.3."""

# Facility schemas
from .facilities import (
    FacilityRaw,
    FacilityStructured,
    VerifiedCapability,
    StaffMember,
    Equipment,
    ExtractionOutput,
)

# Trust scoring schemas
from .trust import (
    TrustScore,
    Contradiction,
    AdvocateOutput,
    SkepticContradiction,
    SkepticOutput,
    JudgeOutput,
)

# Citation schemas
from .citations import Citation

# Geographic schemas
from .geographic import GeoLookup, FacilityEmbedding

# Query schemas
from .query import (
    QueryIntent,
    CriticDecision,
    CriticOutput,
    FacilityExplanation,
    ExplainOutput,
)

# API request/response schemas
from .api import (
    FacilityDetailResponse,
    MapDataResponse,
    QueryRequest,
    QueryResponse,
    QueryResultFacility,
    TrustDebateResponse,
    CitationResponse,
    HealthResponse,
)

__all__ = [
    # Facilities
    "FacilityRaw",
    "FacilityStructured",
    "VerifiedCapability",
    "StaffMember",
    "Equipment",
    "ExtractionOutput",
    # Trust
    "TrustScore",
    "Contradiction",
    "AdvocateOutput",
    "SkepticContradiction",
    "SkepticOutput",
    "JudgeOutput",
    # Citations
    "Citation",
    # Geographic
    "GeoLookup",
    "FacilityEmbedding",
    # Query
    "QueryIntent",
    "CriticDecision",
    "CriticOutput",
    "FacilityExplanation",
    "ExplainOutput",
    # API
    "FacilityDetailResponse",
    "MapDataResponse",
    "QueryRequest",
    "QueryResponse",
    "QueryResultFacility",
    "TrustDebateResponse",
    "CitationResponse",
    "HealthResponse",
]
