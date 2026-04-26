"""Stage 5 — Vector Indexing pipeline for Veritas.

Creates embeddings for semantic search over facility profiles.
Uses databricks-bge-large-en for embeddings.
"""
import json
from datetime import datetime
from typing import Optional

import sys
sys.path.insert(0, '/Workspace/Repos/harshitagarwal048@gmail.com/Veritas-AI-Lifeline')

from api.llm_client import get_llm_client, MODEL_EMBEDDING


def build_profile_text(row) -> str:
    """Build a searchable text profile from facility data."""
    parts = []

    # Basic info
    parts.append(f"Facility: {row.facility_name}")
    parts.append(f"Type: {row.facility_type}")
    parts.append(f"Location: {row.district}, {row.state}")

    # Capabilities
    if hasattr(row, 'verified_capabilities_json') and row.verified_capabilities_json:
        try:
            caps = json.loads(row.verified_capabilities_json)
            cap_names = [c.get("capability", "") for c in caps if c.get("capability")]
            if cap_names:
                parts.append(f"Capabilities: {', '.join(cap_names)}")
        except:
            pass

    # Staff
    if hasattr(row, 'staff_json') and row.staff_json:
        try:
            staff = json.loads(row.staff_json)
            roles = [s.get("role", "") for s in staff if s.get("role")]
            if roles:
                parts.append(f"Staff: {', '.join(roles)}")
        except:
            pass

    # Equipment
    if hasattr(row, 'equipment_json') and row.equipment_json:
        try:
            equipment = json.loads(row.equipment_json)
            items = [e.get("item", "") for e in equipment if e.get("item")]
            if items:
                parts.append(f"Equipment: {', '.join(items)}")
        except:
            pass

    # Original notes (truncated)
    if hasattr(row, 'unstructured_notes') and row.unstructured_notes:
        notes = row.unstructured_notes[:500]
        parts.append(f"Description: {notes}")

    return "\n".join(parts)


def create_embeddings_batch(client, texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """Create embeddings for a batch of texts."""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        response = client.embeddings.create(
            model=MODEL_EMBEDDING,
            input=batch,
        )

        batch_embeddings = [e.embedding for e in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def run_vector_indexing(
    spark,
    raw_table: str = "workspace.veritas_dev.facilities_raw",
    structured_table: str = "workspace.veritas_dev.facilities_structured",
    target_table: str = "workspace.veritas_dev.facility_embeddings",
    sample_size: Optional[int] = None,
    batch_size: int = 20,
    overwrite: bool = True,
) -> dict:
    """
    Create vector embeddings for facility profiles.

    Args:
        spark: SparkSession
        raw_table: Source table with raw facility data
        structured_table: Source table with extracted capabilities
        target_table: Target table for embeddings
        sample_size: If set, only process first N facilities
        batch_size: Batch size for embedding API calls
        overwrite: If True, overwrite existing table

    Returns:
        dict with indexing statistics
    """
    print(f"[Stage 5] Starting vector indexing")
    print(f"[Stage 5] Embedding model: {MODEL_EMBEDDING}")

    # Load and join data
    raw_df = spark.table(raw_table)
    structured_df = spark.table(structured_table)

    joined = raw_df.join(structured_df, on="facility_id", how="inner")

    if sample_size:
        joined = joined.limit(sample_size)
        print(f"[Stage 5] Sampling {sample_size} facilities")

    facilities = joined.collect()
    total = len(facilities)
    print(f"[Stage 5] Processing {total} facilities")

    # Build profile texts
    print("[Stage 5] Building profile texts...")
    profiles = []
    for f in facilities:
        profile_text = build_profile_text(f)
        profiles.append({
            "facility_id": f.facility_id,
            "profile_text": profile_text,
        })

    # Create embeddings
    print("[Stage 5] Creating embeddings...")
    client = get_llm_client()

    texts = [p["profile_text"] for p in profiles]
    embeddings = []  # Initialize to empty list

    try:
        embeddings = create_embeddings_batch(client, texts, batch_size)

        # Add embeddings to profiles
        for i, emb in enumerate(embeddings):
            profiles[i]["embedding"] = emb

        print(f"[Stage 5] Created {len(embeddings)} embeddings")

    except Exception as e:
        print(f"[Stage 5] Warning: Embedding creation failed: {e}")
        print("[Stage 5] Saving profiles without embeddings (can be added later)")
        for p in profiles:
            p["embedding"] = None
        embeddings = []  # Reset to empty on failure

    # Write to Delta table
    import pandas as pd

    pdf = pd.DataFrame(profiles)

    # Convert embedding list to string for Delta storage
    # (Mosaic AI Vector Search will handle re-embedding if needed)
    if pdf["embedding"].iloc[0] is not None:
        pdf["embedding_json"] = pdf["embedding"].apply(lambda x: json.dumps(x) if x else None)
    else:
        pdf["embedding_json"] = None

    pdf = pdf.drop(columns=["embedding"])

    sdf = spark.createDataFrame(pdf)

    write_mode = "overwrite" if overwrite else "append"
    sdf.write.format("delta").mode(write_mode).saveAsTable(target_table)
    print(f"[Stage 5] Wrote {len(profiles)} rows to {target_table}")

    stats = {
        "total_facilities": total,
        "profiles_created": len(profiles),
        "embeddings_created": len(embeddings),
        "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
    }

    return stats


def search_similar(
    spark,
    query: str,
    table_name: str = "workspace.veritas_dev.facility_embeddings",
    top_k: int = 10,
) -> list[dict]:
    """
    Search for similar facilities using vector similarity.

    Note: For production, use Mosaic AI Vector Search.
    This is a simple cosine similarity implementation for testing.
    """
    import numpy as np

    # Get query embedding
    client = get_llm_client()
    response = client.embeddings.create(
        model=MODEL_EMBEDDING,
        input=[query],
    )
    query_embedding = np.array(response.data[0].embedding)

    # Load embeddings
    df = spark.table(table_name)
    rows = df.collect()

    # Calculate similarities
    results = []
    for row in rows:
        if row.embedding_json:
            emb = np.array(json.loads(row.embedding_json))
            # Cosine similarity
            similarity = np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb))
            results.append({
                "facility_id": row.facility_id,
                "similarity": float(similarity),
                "profile_text": row.profile_text[:200] + "...",
            })

    # Sort by similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)

    return results[:top_k]


def preview_embeddings(
    spark,
    table_name: str = "workspace.veritas_dev.facility_embeddings",
    num_rows: int = 5,
) -> None:
    """Preview embedding results."""
    print(f"\n[Preview] Embeddings from {table_name}:")

    df = spark.table(table_name)
    print(f"Total embeddings: {df.count()}")

    rows = df.limit(num_rows).collect()

    for row in rows:
        print(f"\n{'='*60}")
        print(f"Facility: {row.facility_id}")
        print(f"Profile (first 200 chars): {row.profile_text[:200]}...")
        if row.embedding_json:
            emb = json.loads(row.embedding_json)
            print(f"Embedding dimensions: {len(emb)}")
        else:
            print("Embedding: Not created")
