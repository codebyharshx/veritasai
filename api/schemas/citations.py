"""Pydantic schemas for citations — Section 2.3 of PRD/TRD."""
from typing import Literal
from pydantic import BaseModel, Field


# =============================================================================
# citations — every verified claim paired with source sentence
# =============================================================================

class Citation(BaseModel):
    """Citation linking a claim to its source text for hover-to-see-evidence."""
    citation_id: str
    facility_id: str
    claim_type: Literal["capability", "staff", "equipment", "operational"]
    claim_text: str = Field(..., description="The claim being made")
    source_sentence: str = Field(..., description="Exact source sentence from notes")
    source_offset_start: int = Field(..., description="Character offset where source starts")
    source_offset_end: int = Field(..., description="Character offset where source ends")
