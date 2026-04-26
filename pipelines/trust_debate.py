"""Stage 3 — Trust Debate pipeline for Veritas.

Runs Advocate/Skeptic/Judge debate for each facility to produce trust scores.
Uses Llama 3.3 70B via Databricks AI Gateway.
"""
import json
import re
import uuid
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, '/Workspace/Repos/harshitagarwal048@gmail.com/Veritas-AI-Lifeline')

from api.llm_client import get_llm_client, MODEL_CHAT


# Prompt templates from Section 2.4
ADVOCATE_PROMPT = """You are an advocate arguing that this medical facility is trustworthy. You have the structured capability profile and the original notes. Argue persuasively for each capability claim, citing the strongest supporting evidence. Be honest about weak claims but defend strong ones vigorously.

Facility: {facility_name}
Facility Type: {facility_type}

Structured Profile:
{structured_profile}

Original Notes:
{unstructured_notes}

Return a 3-5 sentence advocate argument. Cite specific evidence sentences in quotes. Do not exceed 200 words."""


SKEPTIC_PROMPT = """You are a skeptic arguing that this medical facility may not be what it claims. Look for contradictions, missing evidence, and operational gaps. A facility claiming "advanced surgery" with no anesthesiologist listed is a red flag. A facility claiming "24/7 emergency" with weekday-only staff hours is a red flag.

Facility: {facility_name}
Facility Type: {facility_type}

Structured Profile:
{structured_profile}

Original Notes:
{unstructured_notes}

Return a 3-5 sentence skeptic argument. List specific contradictions or evidence gaps. Quantify trust impact for each (e.g. "-10 points: claims X, no Y"). Do not exceed 200 words.

Also return a JSON array of contradictions found:
CONTRADICTIONS_JSON: [
  {{"claim": "what they claim", "evidence_gap": "what's missing", "trust_impact": -10, "severity": "high/medium/low"}}
]"""


JUDGE_PROMPT = """You are an impartial judge. Two agents have argued about this facility's trustworthiness. Read both, weigh the evidence, and produce a final trust score (0-100) with a 2-3 sentence justification.

Facility: {facility_name}

Advocate's Argument:
{advocate_argument}

Skeptic's Argument:
{skeptic_argument}

Scoring guide:
- 80-100: claims well-supported, no significant contradictions
- 60-79:  most claims supported, minor gaps
- 40-59:  meaningful contradictions, partial evidence
- 20-39:  major contradictions or missing evidence for high-stakes claims
- 0-19:   claims largely unsupported or contradicted

Return ONLY this JSON (no other text):
{{"trust_score": <int 0-100>, "reasoning": "<2-3 sentences>"}}"""


def clean_json_response(response: str) -> str:
    """Extract JSON from LLM response."""
    response = re.sub(r'^```json\s*', '', response.strip())
    response = re.sub(r'^```\s*', '', response)
    response = re.sub(r'\s*```$', '', response)

    start = response.find('{')
    end = response.rfind('}')

    if start != -1 and end != -1:
        return response[start:end + 1]
    return response


def extract_contradictions(skeptic_response: str) -> list:
    """Extract contradictions JSON from skeptic's response."""
    # Look for CONTRADICTIONS_JSON marker
    match = re.search(r'CONTRADICTIONS_JSON:\s*(\[.*?\])', skeptic_response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any JSON array in the response
    match = re.search(r'\[.*?\]', skeptic_response, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list) and len(data) > 0 and 'claim' in str(data[0]):
                return data
        except json.JSONDecodeError:
            pass

    return []


def run_debate_for_facility(
    client,
    facility_id: str,
    facility_name: str,
    facility_type: str,
    structured_profile: str,
    unstructured_notes: str,
) -> tuple[Optional[dict], Optional[str]]:
    """Run the full Advocate/Skeptic/Judge debate for one facility.

    Returns:
        tuple of (result dict or None, error message or None)
    """
    try:
        # Step 1: Advocate
        advocate_response = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[{"role": "user", "content": ADVOCATE_PROMPT.format(
                facility_name=facility_name,
                facility_type=facility_type,
                structured_profile=structured_profile,
                unstructured_notes=unstructured_notes,
            )}],
            temperature=0.3,
            max_tokens=500,
        )
        advocate_argument = advocate_response.choices[0].message.content

        # Step 2: Skeptic
        skeptic_response = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[{"role": "user", "content": SKEPTIC_PROMPT.format(
                facility_name=facility_name,
                facility_type=facility_type,
                structured_profile=structured_profile,
                unstructured_notes=unstructured_notes,
            )}],
            temperature=0.3,
            max_tokens=600,
        )
        skeptic_argument = skeptic_response.choices[0].message.content
        contradictions = extract_contradictions(skeptic_argument)

        # Step 3: Judge
        judge_response = client.chat.completions.create(
            model=MODEL_CHAT,
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                facility_name=facility_name,
                advocate_argument=advocate_argument,
                skeptic_argument=skeptic_argument,
            )}],
            temperature=0.1,
            max_tokens=300,
        )
        judge_raw = judge_response.choices[0].message.content

        # Parse judge response
        try:
            judge_data = json.loads(clean_json_response(judge_raw))
            trust_score = int(judge_data.get("trust_score", 50))
            judge_reasoning = judge_data.get("reasoning", judge_raw)
        except (json.JSONDecodeError, ValueError):
            # Fallback: try to extract score from text
            score_match = re.search(r'(\d{1,3})', judge_raw)
            trust_score = int(score_match.group(1)) if score_match else 50
            judge_reasoning = judge_raw

        # Clamp score to 0-100
        trust_score = max(0, min(100, trust_score))

        result = {
            "facility_id": facility_id,
            "trust_score": trust_score,
            "advocate_argument": advocate_argument,
            "skeptic_argument": skeptic_argument,
            "judge_reasoning": judge_reasoning,
            "contradictions": contradictions,
            "debated_at": datetime.utcnow(),
        }

        return result, None

    except Exception as e:
        return None, str(e)


def run_trust_debate(
    spark,
    raw_table: str = "workspace.veritas_dev.facilities_raw",
    structured_table: str = "workspace.veritas_dev.facilities_structured",
    target_table: str = "workspace.veritas_dev.trust_scores",
    contradictions_table: str = "workspace.veritas_dev.contradictions",
    sample_size: Optional[int] = None,
    max_concurrent: int = 5,  # Lower concurrency for 3 LLM calls per facility
    overwrite: bool = True,
) -> dict:
    """
    Run the trust debate pipeline.

    Args:
        spark: SparkSession
        raw_table: Source table with raw facility data
        structured_table: Source table with extracted structured data
        target_table: Target table for trust scores
        contradictions_table: Target table for contradictions
        sample_size: If set, only process first N facilities
        max_concurrent: Max concurrent debates (each = 3 LLM calls)
        overwrite: If True, overwrite existing tables

    Returns:
        dict with debate statistics
    """
    print(f"[Stage 3] Starting trust debate")

    # Join raw and structured data
    raw_df = spark.table(raw_table)
    structured_df = spark.table(structured_table)

    joined_df = raw_df.join(
        structured_df,
        on="facility_id",
        how="inner"
    ).select(
        raw_df.facility_id,
        raw_df.facility_name,
        raw_df.facility_type,
        raw_df.unstructured_notes,
        structured_df.verified_capabilities_json,
        structured_df.staff_json,
        structured_df.equipment_json,
    )

    if sample_size:
        joined_df = joined_df.limit(sample_size)
        print(f"[Stage 3] Sampling {sample_size} facilities for testing")

    facilities = joined_df.collect()
    total = len(facilities)
    print(f"[Stage 3] Processing {total} facilities with {max_concurrent} concurrent debates")
    print(f"[Stage 3] Each debate = 3 LLM calls (Advocate + Skeptic + Judge)")

    # Initialize client
    client = get_llm_client()

    results = []
    all_contradictions = []
    errors = []

    def process_facility(row):
        # Build structured profile string
        caps = json.loads(row.verified_capabilities_json) if row.verified_capabilities_json else []
        staff = json.loads(row.staff_json) if row.staff_json else []
        equipment = json.loads(row.equipment_json) if row.equipment_json else []

        profile_parts = []
        if caps:
            profile_parts.append("Capabilities: " + ", ".join([c['capability'] for c in caps]))
        if staff:
            profile_parts.append("Staff: " + ", ".join([s['role'] for s in staff]))
        if equipment:
            profile_parts.append("Equipment: " + ", ".join([e['item'] for e in equipment]))

        structured_profile = "\n".join(profile_parts) if profile_parts else "No structured data extracted"

        return run_debate_for_facility(
            client,
            row.facility_id,
            row.facility_name,
            row.facility_type,
            structured_profile,
            row.unstructured_notes or "",
        )

    completed = 0
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = {executor.submit(process_facility, row): row.facility_id for row in facilities}

        for future in as_completed(futures):
            facility_id = futures[future]
            try:
                result, error = future.result()

                if result:
                    # Extract contradictions for separate table
                    contras = result.pop("contradictions", [])
                    for c in contras:
                        all_contradictions.append({
                            "contradiction_id": str(uuid.uuid4()),
                            "facility_id": facility_id,
                            "claim": c.get("claim", ""),
                            "evidence_gap": c.get("evidence_gap", ""),
                            "trust_impact": c.get("trust_impact", -5),
                            "severity": c.get("severity", "medium"),
                            "source_sentence": "",
                        })

                    results.append(result)
                else:
                    errors.append({"facility_id": facility_id, "error": error})

            except Exception as e:
                errors.append({"facility_id": facility_id, "error": str(e)})

            completed += 1
            if completed % 10 == 0 or completed == total:
                print(f"[Stage 3] Progress: {completed}/{total} ({100*completed/total:.1f}%)")

    print(f"[Stage 3] Debate complete. Success: {len(results)}, Errors: {len(errors)}")

    # Write results to Delta tables
    if results:
        import pandas as pd

        pdf_results = pd.DataFrame(results)
        sdf_results = spark.createDataFrame(pdf_results)

        write_mode = "overwrite" if overwrite else "append"
        sdf_results.write.format("delta").mode(write_mode).saveAsTable(target_table)
        print(f"[Stage 3] Wrote {len(results)} trust scores to {target_table}")

    if all_contradictions:
        import pandas as pd

        pdf_contras = pd.DataFrame(all_contradictions)
        sdf_contras = spark.createDataFrame(pdf_contras)

        write_mode = "overwrite" if overwrite else "append"
        sdf_contras.write.format("delta").mode(write_mode).saveAsTable(contradictions_table)
        print(f"[Stage 3] Wrote {len(all_contradictions)} contradictions to {contradictions_table}")

    if errors:
        print(f"\n[Stage 3] Sample errors (first 5):")
        for err in errors[:5]:
            print(f"  - {err['facility_id']}: {err['error'][:100]}")

    stats = {
        "total_facilities": total,
        "successful_debates": len(results),
        "failed_debates": len(errors),
        "total_contradictions": len(all_contradictions),
        "avg_trust_score": sum(r["trust_score"] for r in results) / len(results) if results else 0,
    }

    return stats


def preview_trust_scores(
    spark,
    table_name: str = "workspace.veritas_dev.trust_scores",
    num_rows: int = 5,
) -> None:
    """Preview trust scores with debate transcripts."""
    print(f"\n[Preview] Trust scores from {table_name}:")
    df = spark.table(table_name)

    # Show distribution
    print("\nScore Distribution:")
    df.groupBy(
        (df.trust_score / 20).cast("int") * 20
    ).count().orderBy("(CAST((trust_score / 20) AS INT) * 20)").show()

    rows = df.limit(num_rows).collect()

    for row in rows:
        print(f"\n{'='*60}")
        print(f"Facility: {row.facility_id}")
        print(f"Trust Score: {row.trust_score}/100")
        print(f"\nAdvocate: {row.advocate_argument[:200]}...")
        print(f"\nSkeptic: {row.skeptic_argument[:200]}...")
        print(f"\nJudge: {row.judge_reasoning}")
