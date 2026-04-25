"""Stage 2 — Structured Extraction pipeline for Veritas.

Extracts structured capability data from unstructured facility notes
using Llama 3.3 70B via Databricks AI Gateway.
"""
import json
import re
import uuid
import asyncio
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel, Field

# These will be imported from the api module
import sys
sys.path.insert(0, '/Workspace/Repos/harshitagarwal048@gmail.com/Veritas-AI-Lifeline')

from api.llm_client import get_llm_client, MODEL_CHAT
from api.schemas import ExtractionOutput, VerifiedCapability, StaffMember, Equipment, Citation


# Extraction prompt template from Section 2.4
EXTRACTION_PROMPT = """You are extracting structured capability data from an Indian medical facility record. The notes may be inconsistent, multilingual, or contradictory. Your job is to extract what is *claimed* in the notes, with confidence scores reflecting how strongly each claim is supported.

IMPORTANT DEFINITIONS:
- "capabilities" means clinical services delivered (e.g. "obstetric care", "X-ray imaging", "in-patient ward", "emergency surgery"). NOT facility type, bed count, or operating hours.
- "staff" means people, with roles and specialties — NOT operating hours.
- "equipment" means physical items, marked functional or broken.

Facility name: {facility_name}
Facility type: {facility_type}
Notes:
{unstructured_notes}

Extract a structured profile matching this JSON schema:
{{
  "verified_capabilities": [
    {{
      "capability": "string - clinical service name",
      "confidence": 0.0-1.0,
      "evidence_sentence": "exact quote from notes",
      "evidence_offset": 0
    }}
  ],
  "staff": [
    {{
      "role": "string",
      "specialty": "string or null",
      "availability_hours": "string or null"
    }}
  ],
  "equipment": [
    {{
      "item": "string",
      "functional": true/false,
      "note": "string or null"
    }}
  ],
  "operational_hours": "string or null",
  "last_update_mentioned": "string or null"
}}

Rules:
1. For each capability, include the exact sentence from the notes that supports it
2. Confidence 0.8-1.0 = explicitly stated, 0.5-0.79 = implied, 0.3-0.49 = weak/ambiguous
3. Do not invent capabilities not mentioned in the notes
4. If a capability is contradicted elsewhere, lower confidence and note in evidence_sentence

Return ONLY the JSON object. No preamble, no explanation, no code fences."""


def clean_json_response(response: str) -> str:
    """Clean LLM response to extract valid JSON.

    Llama tends to wrap JSON in ```json blocks even when instructed not to.
    """
    # Remove markdown code fences
    response = re.sub(r'^```json\s*', '', response.strip())
    response = re.sub(r'^```\s*', '', response)
    response = re.sub(r'\s*```$', '', response)

    # Try to find JSON object boundaries
    start = response.find('{')
    end = response.rfind('}')

    if start != -1 and end != -1:
        response = response[start:end + 1]

    return response


def extract_single_facility(
    client,
    facility_id: str,
    facility_name: str,
    facility_type: str,
    unstructured_notes: str,
) -> tuple[Optional[ExtractionOutput], list[Citation], Optional[str]]:
    """Extract structured data from a single facility's notes.

    Returns:
        tuple of (ExtractionOutput or None, list of Citations, error message or None)
    """
    if not unstructured_notes or not unstructured_notes.strip():
        return None, [], "Empty unstructured_notes"

    prompt = EXTRACTION_PROMPT.format(
        facility_name=facility_name,
        facility_type=facility_type,
        unstructured_notes=unstructured_notes,
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent extraction
            max_tokens=2000,
        )

        raw_output = response.choices[0].message.content
        cleaned = clean_json_response(raw_output)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return None, [], f"JSON parse error: {e}. Raw: {raw_output[:200]}"

        # Parse into Pydantic model
        extraction = ExtractionOutput(
            verified_capabilities=[
                VerifiedCapability(**cap) for cap in data.get("verified_capabilities", [])
            ],
            staff=[
                StaffMember(**s) for s in data.get("staff", [])
            ],
            equipment=[
                Equipment(**eq) for eq in data.get("equipment", [])
            ],
            operational_hours=data.get("operational_hours"),
            last_update_mentioned=data.get("last_update_mentioned"),
        )

        # Generate citations for each capability
        citations = []
        for cap in extraction.verified_capabilities:
            citation = Citation(
                citation_id=str(uuid.uuid4()),
                facility_id=facility_id,
                claim_type="capability",
                claim_text=cap.capability,
                source_sentence=cap.evidence_sentence,
                source_offset_start=cap.evidence_offset,
                source_offset_end=cap.evidence_offset + len(cap.evidence_sentence),
            )
            citations.append(citation)

        return extraction, citations, None

    except Exception as e:
        return None, [], f"API error: {str(e)}"


def run_extraction(
    spark,
    source_table: str = "workspace.veritas_dev.facilities_raw",
    target_table: str = "workspace.veritas_dev.facilities_structured",
    citations_table: str = "workspace.veritas_dev.citations",
    sample_size: Optional[int] = None,
    max_concurrent: int = 10,  # Conservative for Free Edition rate limits
    overwrite: bool = True,
) -> dict:
    """
    Run the extraction pipeline.

    Args:
        spark: SparkSession instance
        source_table: Source Delta table with raw facilities
        target_table: Target table for structured extractions
        citations_table: Target table for citations
        sample_size: If set, only process first N facilities
        max_concurrent: Max concurrent LLM calls
        overwrite: If True, overwrite existing tables

    Returns:
        dict with extraction statistics
    """
    print(f"[Stage 2] Starting extraction from {source_table}")

    # Read source data
    df = spark.table(source_table)

    if sample_size:
        df = df.limit(sample_size)
        print(f"[Stage 2] Sampling {sample_size} facilities for testing")

    # Collect to driver for LLM processing
    # (In production, this would be distributed via Spark UDFs)
    facilities = df.select(
        "facility_id",
        "facility_name",
        "facility_type",
        "unstructured_notes"
    ).collect()

    total = len(facilities)
    print(f"[Stage 2] Processing {total} facilities with {max_concurrent} concurrent calls")

    # Initialize LLM client
    client = get_llm_client()

    # Process facilities with thread pool
    results = []
    all_citations = []
    errors = []

    def process_facility(row):
        extraction, citations, error = extract_single_facility(
            client,
            row.facility_id,
            row.facility_name,
            row.facility_type,
            row.unstructured_notes,
        )
        return row.facility_id, extraction, citations, error

    completed = 0
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {
            executor.submit(process_facility, row): row.facility_id
            for row in facilities
        }

        for future in as_completed(futures):
            facility_id = futures[future]
            try:
                fid, extraction, citations, error = future.result()

                if extraction:
                    results.append({
                        "facility_id": fid,
                        "verified_capabilities": [c.model_dump() for c in extraction.verified_capabilities],
                        "staff": [s.model_dump() for s in extraction.staff],
                        "equipment": [e.model_dump() for e in extraction.equipment],
                        "operational_hours": extraction.operational_hours,
                        "last_update_mentioned": extraction.last_update_mentioned,
                        "extraction_model": MODEL_CHAT,
                        "extracted_at": datetime.utcnow(),
                    })
                    all_citations.extend([c.model_dump() for c in citations])
                else:
                    errors.append({"facility_id": fid, "error": error})

            except Exception as e:
                errors.append({"facility_id": facility_id, "error": str(e)})

            completed += 1
            if completed % 50 == 0 or completed == total:
                print(f"[Stage 2] Progress: {completed}/{total} ({100*completed/total:.1f}%)")

    print(f"[Stage 2] Extraction complete. Success: {len(results)}, Errors: {len(errors)}")

    # Write results to Delta tables
    if results:
        import pandas as pd

        # Convert to Spark DataFrame and write
        pdf_results = pd.DataFrame(results)
        sdf_results = spark.createDataFrame(pdf_results)

        write_mode = "overwrite" if overwrite else "append"
        sdf_results.write.format("delta").mode(write_mode).saveAsTable(target_table)
        print(f"[Stage 2] Wrote {len(results)} rows to {target_table}")

    if all_citations:
        import pandas as pd

        pdf_citations = pd.DataFrame(all_citations)
        sdf_citations = spark.createDataFrame(pdf_citations)

        write_mode = "overwrite" if overwrite else "append"
        sdf_citations.write.format("delta").mode(write_mode).saveAsTable(citations_table)
        print(f"[Stage 2] Wrote {len(all_citations)} citations to {citations_table}")

    # Print sample errors
    if errors:
        print(f"\n[Stage 2] Sample errors (first 5):")
        for err in errors[:5]:
            print(f"  - {err['facility_id']}: {err['error'][:100]}")

    stats = {
        "source_table": source_table,
        "target_table": target_table,
        "total_facilities": total,
        "successful_extractions": len(results),
        "failed_extractions": len(errors),
        "total_citations": len(all_citations),
        "errors": errors,
    }

    return stats


def preview_extractions(
    spark,
    table_name: str = "workspace.veritas_dev.facilities_structured",
    num_rows: int = 3,
) -> None:
    """Preview extraction results."""
    print(f"\n[Preview] First {num_rows} extractions from {table_name}:")
    df = spark.table(table_name)

    rows = df.limit(num_rows).collect()

    for row in rows:
        print(f"\n{'='*60}")
        print(f"Facility: {row.facility_id}")
        print(f"Capabilities: {len(row.verified_capabilities)}")
        for cap in row.verified_capabilities[:3]:
            print(f"  - {cap['capability']} (conf: {cap['confidence']})")
        if len(row.verified_capabilities) > 3:
            print(f"  ... and {len(row.verified_capabilities) - 3} more")
        print(f"Staff: {len(row.staff)}")
        print(f"Equipment: {len(row.equipment)}")
