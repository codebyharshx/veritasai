"""Pydantic schemas for natural-language query — Section 2.4 Stage 6."""
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Query intent parsing (Stage 6 Step 1)
# =============================================================================

class QueryIntent(BaseModel):
    """Parsed intent from a natural-language query."""
    capabilities: list[str] = Field(
        default_factory=list,
        description="Required capabilities, e.g. ['emergency surgery', 'anesthesiology']"
    )
    location_state: Optional[str] = Field(None, description="State filter if mentioned")
    location_district: Optional[str] = Field(None, description="District filter if mentioned")
    location_pin_code: Optional[str] = Field(None, description="PIN code filter if mentioned")
    max_distance_km: Optional[float] = Field(None, description="Maximum distance constraint")
    min_trust_score: Optional[int] = Field(None, ge=0, le=100, description="Minimum trust score")
    operational_constraints: list[str] = Field(
        default_factory=list,
        description="E.g. ['24/7', 'weekends', 'after hours']"
    )
    raw_query: str = Field(..., description="Original query text for reference")


# =============================================================================
# Query critic output (Stage 6 Step 5)
# =============================================================================

class CriticDecision(BaseModel):
    """Critic's decision on a single facility candidate."""
    facility_id: str
    relevant: bool = Field(..., description="Whether this facility matches the query intent")
    reason: str = Field(..., description="Why it matches or doesn't match")


class CriticOutput(BaseModel):
    """Schema for Query Critic agent output."""
    decisions: list[CriticDecision]
    should_broaden: bool = Field(
        False,
        description="True if <3 relevant results and query should be broadened"
    )


# =============================================================================
# Query explanation (Stage 6 Step 6)
# =============================================================================

class FacilityExplanation(BaseModel):
    """One-sentence justification for why a facility was ranked."""
    facility_id: str
    justification: str = Field(..., description="One-sentence explanation for the user")


class ExplainOutput(BaseModel):
    """Schema for Query Explain agent output."""
    explanations: list[FacilityExplanation]
