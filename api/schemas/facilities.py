"""Pydantic schemas for facility data — Section 2.3 of PRD/TRD."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# facilities_raw — direct ingestion of Virtue Foundation dataset
# =============================================================================

class FacilityRaw(BaseModel):
    """Raw facility record as ingested from the dataset."""
    facility_id: str = Field(..., description="Primary key, generated as UUID if missing")
    facility_name: str
    state: str
    district: str
    pin_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    facility_type: str = Field(..., description="PHC, CHC, district hospital, private clinic, etc.")
    bed_count: Optional[int] = None
    unstructured_notes: str = Field(..., description="Free-form text field — primary extraction input")
    ingested_at: datetime


# =============================================================================
# facilities_structured — output of extractor agent
# =============================================================================

class VerifiedCapability(BaseModel):
    """A single capability extracted from facility notes."""
    capability: str = Field(..., description="Clinical service delivered, e.g. 'obstetric care', 'X-ray imaging'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="How strongly the claim is supported")
    evidence_sentence: str = Field(..., description="Exact sentence from notes that supports this claim")
    evidence_offset: int = Field(..., description="Character offset in original notes where evidence starts")


class StaffMember(BaseModel):
    """A staff member extracted from facility notes."""
    role: Optional[str] = Field(None, description="Job title or role")
    specialty: Optional[str] = Field(None, description="Medical specialty if applicable")
    availability_hours: Optional[str] = Field(None, description="Working hours if mentioned")


class Equipment(BaseModel):
    """Equipment item extracted from facility notes."""
    item: str = Field(..., description="Name of equipment")
    functional: bool = Field(..., description="Whether the equipment is working")
    note: Optional[str] = Field(None, description="Additional notes about condition")


class FacilityStructured(BaseModel):
    """Structured extraction output for a facility."""
    facility_id: str = Field(..., description="FK to facilities_raw")
    verified_capabilities: list[VerifiedCapability] = Field(default_factory=list)
    staff: list[StaffMember] = Field(default_factory=list)
    equipment: list[Equipment] = Field(default_factory=list)
    operational_hours: Optional[str] = None
    last_update_mentioned: Optional[str] = Field(None, description="Date if mentioned in notes")
    extraction_model: str = Field(..., description="Which model produced this row")
    extracted_at: datetime


# =============================================================================
# Extraction LLM output schema (for instructor)
# =============================================================================

class ExtractionOutput(BaseModel):
    """Schema for LLM extraction output — used with instructor."""
    verified_capabilities: list[VerifiedCapability] = Field(default_factory=list)
    staff: list[StaffMember] = Field(default_factory=list)
    equipment: list[Equipment] = Field(default_factory=list)
    operational_hours: Optional[str] = None
    last_update_mentioned: Optional[str] = None
