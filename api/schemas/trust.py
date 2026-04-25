"""Pydantic schemas for trust scoring — Section 2.3 of PRD/TRD."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# trust_scores — output of Advocate/Skeptic/Judge debate
# =============================================================================

class TrustScore(BaseModel):
    """Trust score record for a facility."""
    facility_id: str = Field(..., description="FK to facilities_raw")
    trust_score: int = Field(..., ge=0, le=100, description="Final trust score 0-100")
    advocate_argument: str = Field(..., description="Full text of advocate's argument")
    skeptic_argument: str = Field(..., description="Full text of skeptic's argument")
    judge_reasoning: str = Field(..., description="Judge's synthesis and final verdict")
    mlflow_run_id: Optional[str] = Field(None, description="Links to the MLflow trace")
    debated_at: datetime


# =============================================================================
# contradictions — surfaced by Skeptic, normalized for display
# =============================================================================

class Contradiction(BaseModel):
    """A contradiction or evidence gap identified by the Skeptic."""
    contradiction_id: str = Field(..., description="UUID")
    facility_id: str
    claim: str = Field(..., description="What the facility claims")
    evidence_gap: str = Field(..., description="What evidence is missing or conflicting")
    trust_impact: int = Field(..., le=0, description="Negative integer, points deducted")
    severity: Literal["low", "medium", "high"]
    source_sentence: str = Field(..., description="Source text related to this contradiction")


# =============================================================================
# LLM output schemas for debate agents (for instructor)
# =============================================================================

class AdvocateOutput(BaseModel):
    """Schema for Advocate agent output."""
    argument: str = Field(..., max_length=1000, description="3-5 sentence argument for trustworthiness")


class SkepticContradiction(BaseModel):
    """A single contradiction identified by the Skeptic."""
    claim: str = Field(..., description="What is being claimed")
    evidence_gap: str = Field(..., description="What evidence is missing or conflicting")
    trust_impact: int = Field(..., le=0, description="Points to deduct, e.g. -10")
    severity: Literal["low", "medium", "high"]
    source_sentence: str = Field(..., description="Related source text")


class SkepticOutput(BaseModel):
    """Schema for Skeptic agent output."""
    argument: str = Field(..., max_length=1000, description="3-5 sentence argument against claims")
    contradictions: list[SkepticContradiction] = Field(default_factory=list)


class JudgeOutput(BaseModel):
    """Schema for Judge agent output."""
    trust_score: int = Field(..., ge=0, le=100)
    reasoning: str = Field(..., max_length=500, description="2-3 sentence justification")
