# VERITAS — Truth Layer for Indian Healthcare

**Hack-Nation 5th Global AI Hackathon · Databricks Track · April 25-26, 2026**

A single-document PRD + TRD optimized for Claude Code as the primary build assistant. Read top to bottom before writing any code. Each section is self-contained and can be re-referenced during the build.

**Pre-build environment validation completed:** Databricks Free Edition workspace is provisioned in EU region. Unity Catalog enabled with `veritas_dev` schema. Foundation models accessed via Databricks AI Gateway through OpenAI-compatible client. The GPT-5 family is rate-limited to zero on Free Edition; Llama 3.3 70B is the validated working chat model. BGE-large-en is the validated working embeddings model. All cost/billing is internal to the Databricks Free Edition allocation — no external API keys required.

---

## Part 1 — Product Requirements Document (PRD)

### 1.1 Problem Statement

India has 10,000+ medical facilities serving 1.4 billion people, 70% of whom live in rural areas. Each facility is described in a free-form record that mixes structured metadata (name, location, bed count) with unstructured notes (equipment status, staff availability, capability claims). The records are inconsistent, partially stale, and frequently contradictory — a facility may claim "advanced surgery" while listing no anesthesiologist; another may claim "24/7 emergency" while operational notes specify weekday-only hours. No existing system reconciles claims against evidence at scale, leaving patients, NGOs, and government planners unable to answer the simple question: *where is the nearest facility that can actually deliver the care a person needs right now?*

### 1.2 Product Vision

Veritas is a trust layer over Indian healthcare facility data. It turns 10,000 messy records into a verified, queryable map of where help actually exists — surfacing capability gaps (medical deserts), flagging contradictions between claims and evidence, and answering compound natural-language queries about facility capabilities with full traceability back to source text.

### 1.3 Target Users

The MVP serves three personas, all accessing the same web application through different tabs:

The **NGO Mission Planner** uses Veritas to identify medical deserts across regions, prioritize where to deploy resources, and verify that target facilities are actually capable before committing supplies or staff. They land on the geographic explorer first.

The **Government/Public Health Analyst** uses Veritas to audit capability claims at scale, identify systemic contradictions in facility reporting, and produce evidence-based reports about regional access gaps. They live in the facility inspector and analytics views.

The **On-the-ground Worker** (community health worker, ambulance dispatcher, frontline doctor) uses Veritas to ask compound natural-language queries about facility capability and reach, with answers grounded in verified evidence. They use the natural-language query tab.

### 1.4 Core Value Proposition

A single sentence the demo must communicate within thirty seconds: *Veritas converts unverified facility claims into trust-scored, evidence-linked capability profiles, then makes them queryable as a map, an inspector, and a chat — every answer traceable to the exact sentence in the source record that justifies it.*

### 1.5 Three Tabs, One Data Spine

The product is a single web application with three primary surfaces, all reading from the same underlying verified-truth layer.

#### Tab 1 — Geographic Explorer

A choropleth map of India showing medical desert severity, configurable by capability type. The user selects a capability filter (emergency surgery, dialysis, oncology, trauma, obstetrics, ICU). The map redraws color-coded by distance to the nearest *verified* facility offering that capability — green under 50 km, yellow 50-100 km, deep red over 100 km. PIN code or district granularity. Click any region to open a side panel showing facility counts, verification stats, and the nearest verified facility for the selected capability with its distance and trust score.

The geographic explorer answers the question: *where are the gaps?*

#### Tab 2 — Facility Inspector

A search-and-detail view for individual facilities. Search by name or click any facility marker on the map. The detail view shows three stacked sections. *Verified Capabilities* lists each capability with its trust score and the exact source-text sentence that supports the claim, hyperlinked to the original record. *Flagged Contradictions* lists each claim where evidence is missing or conflicting, with the contradiction described in plain language and the trust impact quantified. *Trust Reasoning* is collapsible — when expanded, it shows the full Advocate-vs-Skeptic debate transcript that produced the trust score, plus the Judge agent's final synthesis.

The facility inspector answers the question: *can I trust what this facility claims?*

#### Tab 3 — Natural-Language Query

A chat interface accepting compound queries that combine capability, location, and operational constraints. *"Find facilities in rural Bihar that can perform an emergency appendectomy and have a doctor available outside business hours."* The agent returns a ranked list of facilities, each with a one-sentence justification and a "Show reasoning" link that expands to display the full retrieval-and-ranking trace via MLflow.

The natural-language query tab answers the question: *given a real-world need, where should this person actually go?*

### 1.6 Mandatory Differentiators

Three features must be visible in the demo to differentiate Veritas from a competent MedDesert AI clone.

The **multi-agent trust debate** must be visible to the user, not buried in logs. Every trust score is produced by an Advocate agent arguing for the facility's claims, a Skeptic agent arguing against them, and a Judge agent synthesizing the verdict. The full transcript is exposed in the facility inspector under "Trust Reasoning."

**Row-level citations** must accompany every claim. Every capability listed, every contradiction flagged, every trust score must link back to the exact sentence in the source record that justifies it. Hovering or clicking any verified claim highlights the source text.

**MLflow tracing exposed as a product feature** must let the user see the agent's reasoning step by step. When a user clicks "Show reasoning" on a query result or "Why this score?" on a trust verdict, they see the actual agent trace — which prompts ran, which tools were called, what each step returned. This is implemented via `mlflow.openai.autolog()`, which auto-captures every LLM call as a queryable trace with no custom span code required.

### 1.7 Scope Boundaries (What Veritas Does Not Do)

Veritas does not provide medical advice. It does not recommend treatments. It does not replace clinical judgment. It does not auto-verify against external sources beyond the provided dataset. It does not modify or write back to the source records. It does not handle real-time facility availability (bed counts now, doctor on duty now) — only what the static record claims, scored against internal evidence.

These boundaries are important to state in the demo. Judges with public-health backgrounds will respect a project that knows what it isn't trying to do.

### 1.8 Success Metrics for the Demo

In the two-minute pitch window, the demo must demonstrate:

- The geographic explorer rendering with at least three capability filters working and visibly different desert maps for each.
- At least one facility inspector view with a verified capability list, a flagged contradiction with quantified trust impact, and an expandable Advocate/Skeptic/Judge transcript.
- At least two compound natural-language queries returning ranked facility lists with reasoning traces.
- A visible click-through path from any answer back to the source-text sentence that justifies it.

If any of these four are missing or broken at demo time, the submission is incomplete. Everything else is bonus.

### 1.9 Evaluation Criteria Mapping

Mapping back to the brief's published weights to ensure we optimize correctly:

*Discovery and Verification (35%)* — addressed by the structured extraction pipeline producing a clean capability profile per facility, plus the multi-agent trust debate producing scored verdicts.

*IDP Innovation (30%)* — addressed by the LLM-powered extraction over messy free-form Indian facility notes, with confidence-graded outputs and contradiction surfacing.

*Social Impact and Utility (25%)* — addressed by the geographic explorer's medical desert visualization and the natural-language query interface returning actionable ranked recommendations for NGO planners.

*User Experience and Transparency (10%)* — addressed by exposed MLflow traces, row-level citations, and the visible debate transcript in the facility inspector.

The trust-scoring debate and the citation system together address roughly 65% of the rubric. They are the priority investments.

---

## Part 2 — Technical Requirements Document (TRD)

### 2.1 Architecture Overview

Veritas is a five-layer pipeline plus a frontend. Each layer reads from the previous and writes to the next, with all intermediate state stored in Databricks Delta tables under Unity Catalog.

```
┌─────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Streamlit)                       │
│   Tab 1: Geographic Explorer  Tab 2: Inspector  Tab 3: Query     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       QUERY LAYER (FastAPI)                      │
│   /facilities  /trust/{id}  /map/{capability}  /query (LangGraph)│
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AGENT ORCHESTRATION (LangGraph)                 │
│   Extractor  ·  Advocate  ·  Skeptic  ·  Judge  ·  Query Critic  │
│         All traced via MLflow 3 (mlflow.openai.autolog)          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MODEL SERVING LAYER                        │
│            Databricks AI Gateway (OpenAI-compatible)             │
│   Chat: databricks-meta-llama-3-3-70b-instruct                   │
│   Embeddings: databricks-bge-large-en (1024-dim)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DATA LAYER (Delta + Vector Search)              │
│   facilities_raw  ·  facilities_structured  ·  trust_scores      │
│   contradictions  ·  citations  ·  geo_lookup  ·  vector_index   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack (Locked)

The stack is fixed at the start of the build. No changes after hour 4 unless something is fundamentally broken. The Databricks-native components are non-negotiable because Onno Van der Horst from Databricks is on the judging panel and will check.

**Platform:** Databricks Free Edition with Unity Catalog enabled. Workspace region: EU.

**Storage:** Delta Lake tables under Unity Catalog. All intermediate state is a Delta table, never a pickle file or local CSV. Catalog/schema path: `workspace.veritas_dev`.

**LLM serving:** Databricks AI Gateway is the sole inference path. A single chat model — `databricks-meta-llama-3-3-70b-instruct` — handles every reasoning task across the pipeline (Stage 2 extraction, Stage 3 Advocate/Skeptic/Judge debate, Stage 6 query intent/critic/explain). This was validated working at environment-check time; the GPT-5 family on Free Edition was rate-limited to zero and is not used. Embeddings via `databricks-bge-large-en` (1024 dimensions) for Stage 5 vector indexing — also validated working.

**LLM client library:** the standard `openai` Python package, pointed at `{databricks_host}/serving-endpoints` as `base_url`. AI Gateway endpoints are OpenAI-API-compatible, so all LLM code uses the standard OpenAI client interface (`client.chat.completions.create()`, `client.embeddings.create()`). This makes the codebase portable and natively compatible with `instructor`, LangChain, and LangGraph.

**Authentication:** workspace tokens fetched at runtime via `WorkspaceClient().config.authenticate()`. In notebooks, auth is automatic. In FastAPI/Streamlit, set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` env vars. No external API keys (no OpenAI, no Anthropic) are required for any production code path.

**Vector store:** Mosaic AI Vector Search synced from a Delta table of facility profiles. The `databricks-bge-large-en` embedding endpoint is provisioned and queryable, so auto-embedding from the Delta sync index works natively. ChromaDB is acceptable for local development only — the production demo runs on Mosaic AI Vector Search.

**Agent orchestration:** LangGraph for multi-step agent flows (extractor, debate, query). State is a typed Pydantic model. Every node's LLM call is automatically traced via `mlflow.openai.autolog()`.

**Observability:** MLflow 3 with experiment tracking and tracing enabled. Crucially, calling `mlflow.openai.autolog()` once at module import auto-captures every OpenAI-compatible LLM call as a trace — input messages, output, latency, token counts. This single line satisfies the "MLflow tracing as product feature" differentiator from Section 1.6 with no custom span wrapping. Traces are queryable from the UI via `mlflow.search_traces()`.

**Backend API:** FastAPI on Databricks Apps or a local uvicorn server during development. Endpoints documented below.

**Frontend:** Streamlit. Folium for the choropleth map, Plotly for any auxiliary charts. Streamlit chosen over Next.js because (a) it ships in 5x less time for hackathon timeframes, (b) it deploys natively as a Databricks App, (c) judges accept Streamlit demos when the underlying logic is strong.

**Geospatial:** H3 indexing for fast spatial joins, OpenStreetMap-based isochrones via the `osmnx` library if time permits. Fallback to haversine straight-line distance if isochrones blow up.

**Schemas:** Pydantic v2 models for every LLM input/output contract. The `instructor` library on top of the OpenAI-compatible client for guaranteed schema-valid outputs. Note: Llama 3.3 70B does not natively support OpenAI's strict structured outputs mode, so `instructor`'s Mode.JSON or Mode.MD_JSON should be used instead of Mode.TOOLS. Output JSON must be defensively parsed (strip ```json fences if present, since Llama tends to wrap JSON output even when instructed not to).

### 2.3 Data Schemas

The pipeline writes seven Delta tables under Unity Catalog schema `workspace.veritas_dev`. All schemas are defined explicitly here so the build can proceed in parallel across modules.

**`facilities_raw`** — direct ingestion of the Virtue Foundation dataset, one row per facility, no transformations.

```
facility_id          STRING        (primary key, generated as UUID if missing)
facility_name        STRING
state                STRING
district             STRING
pin_code             STRING
latitude             DOUBLE
longitude            DOUBLE
facility_type        STRING        (PHC, CHC, district hospital, private clinic, etc.)
bed_count            INT
unstructured_notes   STRING        (the free-form text field — primary extraction input)
ingested_at          TIMESTAMP
```

**`facilities_structured`** — output of the extractor agent, one row per facility, structured.

```
facility_id              STRING        (FK to facilities_raw)
verified_capabilities    ARRAY<STRUCT<
                            capability: STRING,
                            confidence: DOUBLE,
                            evidence_sentence: STRING,
                            evidence_offset: INT
                         >>
staff                    ARRAY<STRUCT<
                            role: STRING,
                            specialty: STRING,
                            availability_hours: STRING
                         >>
equipment                ARRAY<STRUCT<
                            item: STRING,
                            functional: BOOLEAN,
                            note: STRING
                         >>
operational_hours        STRING
last_update_mentioned    STRING        (nullable — date if mentioned in notes)
extraction_model         STRING        (which model produced this row)
extracted_at             TIMESTAMP
```

**`trust_scores`** — output of the Advocate/Skeptic/Judge debate, one row per facility.

```
facility_id              STRING        (FK to facilities_raw)
trust_score              INT           (0-100)
advocate_argument        STRING        (full text)
skeptic_argument         STRING        (full text)
judge_reasoning          STRING        (full synthesis)
mlflow_run_id            STRING        (links to the trace)
debated_at               TIMESTAMP
```

**`contradictions`** — surfaced by the Skeptic, normalized for display.

```
contradiction_id         STRING        (UUID)
facility_id              STRING
claim                    STRING        (what the facility claims)
evidence_gap             STRING        (what evidence is missing or conflicting)
trust_impact             INT           (negative integer, points deducted)
severity                 STRING        (low, medium, high)
source_sentence          STRING
```

**`citations`** — every verified claim is paired with its source sentence for the UI's hover-to-see-evidence feature.

```
citation_id              STRING
facility_id              STRING
claim_type               STRING        (capability, staff, equipment, operational)
claim_text               STRING
source_sentence          STRING
source_offset_start      INT
source_offset_end        INT
```

**`geo_lookup`** — precomputed nearest-verified-facility for each PIN code × capability combination.

```
pin_code                 STRING
capability               STRING
nearest_facility_id      STRING
distance_km              DOUBLE
travel_time_minutes      INT           (nullable — populated if isochrones built)
nearest_trust_score      INT
desert_severity          STRING        (green, yellow, red)
```

**`facility_embeddings`** — Mosaic AI Vector Search index source.

```
facility_id              STRING        (primary key)
profile_text             STRING        (concatenated structured profile for embedding)
embedding                ARRAY<FLOAT>  (1024-dim, auto-generated by bge-large-en via Vector Search Delta sync)
```

### 2.4 Pipeline Stages — Detailed

Six stages run in sequence at startup, plus two interactive stages serving the live application. All chat calls use `databricks-meta-llama-3-3-70b-instruct`. All embedding calls use `databricks-bge-large-en`.

#### Stage 0 — LLM Client Helper (foundation module, written first)

Before any pipeline stage, generate `api/llm_client.py` containing:

```python
"""LLM client for Veritas — Databricks AI Gateway via OpenAI-compatible interface."""
import mlflow
from openai import OpenAI
from databricks.sdk import WorkspaceClient

# Free MLflow tracing for every chat completion / embedding call.
# This satisfies the "MLflow tracing as product feature" differentiator.
mlflow.openai.autolog()

# Single source of truth for model assignments.
MODEL_CHAT = "databricks-meta-llama-3-3-70b-instruct"
MODEL_EMBEDDING = "databricks-bge-large-en"

def get_llm_client() -> OpenAI:
    """Returns an OpenAI-compatible client pointed at Databricks AI Gateway."""
    w = WorkspaceClient()
    auth = w.config.authenticate()
    token = auth["Authorization"].replace("Bearer ", "")
    return OpenAI(
        api_key=token,
        base_url=f"{w.config.host}/serving-endpoints",
    )
```

Every other module imports from here. If a model name changes, one constant updates and everything follows.

#### Stage 1 — Ingestion

A Databricks notebook reads `VF_Hackathon_Dataset_India_Large.xlsx` from `/Volumes/workspace/veritas_dev/raw_data/`, generates UUIDs for any rows missing IDs, normalizes column names, and writes `workspace.veritas_dev.facilities_raw`. Estimated runtime: under 2 minutes.

#### Stage 2 — Structured Extraction (LLM-heavy)

For each row in `facilities_raw`, send the unstructured notes to Llama 3.3 70B with a Pydantic schema demanding the structured output described in `facilities_structured`. Prompt template:

```
You are extracting structured capability data from an Indian medical facility 
record. The notes may be inconsistent, multilingual, or contradictory. Your job 
is to extract what is *claimed* in the notes, with confidence scores reflecting 
how strongly each claim is supported.

IMPORTANT DEFINITIONS:
- "capabilities" means clinical services delivered (e.g. "obstetric care", 
  "X-ray imaging", "in-patient ward", "emergency surgery"). NOT facility type, 
  bed count, or operating hours.
- "staff" means people, with roles and specialties — NOT operating hours.
- "equipment" means physical items, marked functional or broken.

Facility name: {facility_name}
Facility type: {facility_type}
Notes:
{unstructured_notes}

Extract a structured profile matching the schema. For each capability, include 
the exact sentence from the notes that supports it, and a confidence score 
between 0.0 and 1.0 reflecting how clearly the claim is stated. Do not invent 
capabilities not mentioned in the notes. If a capability is mentioned but 
contradicted elsewhere in the notes, lower the confidence and note the 
contradiction in the evidence_sentence field.

Return only the JSON object matching the schema. No preamble, no code fences.
```

The category-disambiguation block (capabilities vs. metadata vs. staff) is critical — without it, smaller models conflate facility type with clinical capability. Even with 70B, include it for safety.

Run via `instructor` with `Mode.MD_JSON` for schema enforcement (Llama doesn't natively support OpenAI's strict tools-mode structured outputs). Parallelize across 20 concurrent calls (more conservative than 50 because of Free Edition rate limits — adjust upward if no throttling observed). Implement retry-with-exponential-backoff on 429 / rate-limit errors. Write each result to `facilities_structured` and the citation entries to `citations`. Estimated runtime: 30-60 minutes for 10,000 rows depending on observed rate limits.

#### Stage 3 — Trust Debate (LLM-heavy, parallelizable)

For each facility in `facilities_structured`, run a three-agent debate. All three agents use the same Llama 3.3 70B endpoint with different system prompts.

The **Advocate prompt**:

```
You are an advocate arguing that this medical facility is trustworthy. You have 
the structured capability profile and the original notes. Argue persuasively 
for each capability claim, citing the strongest supporting evidence. Be honest 
about weak claims but defend strong ones vigorously.

Facility profile: {structured_profile}
Original notes: {unstructured_notes}

Return a 3-5 sentence advocate argument. Cite specific evidence sentences in 
quotes. Do not exceed 200 words.
```

The **Skeptic prompt**:

```
You are a skeptic arguing that this medical facility may not be what it claims. 
Look for contradictions, missing evidence, and operational gaps. A facility 
claiming "advanced surgery" with no anesthesiologist listed is a red flag. A 
facility claiming "24/7 emergency" with weekday-only staff hours is a red flag.

Facility profile: {structured_profile}
Original notes: {unstructured_notes}

Return a 3-5 sentence skeptic argument. List specific contradictions or evidence 
gaps. Quantify trust impact for each (e.g. "-10 points: claims X, no Y"). Do 
not exceed 200 words.
```

The **Judge prompt**:

```
You are an impartial judge. Two agents have argued about this facility's 
trustworthiness. Read both, weigh the evidence, and produce a final trust score 
(0-100) with a 2-3 sentence justification.

Advocate: {advocate_argument}
Skeptic: {skeptic_argument}

Scoring guide:
- 80-100: claims well-supported, no significant contradictions
- 60-79:  most claims supported, minor gaps
- 40-59:  meaningful contradictions, partial evidence
- 20-39:  major contradictions or missing evidence for high-stakes claims
- 0-19:   claims largely unsupported or contradicted

Return JSON: { "trust_score": <int>, "reasoning": "<2-3 sentences>" }
```

Each call is auto-traced by `mlflow.openai.autolog()`. The MLflow run_id from each Judge call is captured in `trust_scores.mlflow_run_id` so the UI can deep-link to the trace. The Skeptic's contradiction-listing output is parsed and written to `contradictions`. Estimated runtime: 60-120 minutes for 10,000 facilities at 3 LLM calls each (30,000 calls total) under Free Edition rate limits.

**Volume risk:** 30,000 calls is the largest LLM volume in the pipeline and is where Free Edition rate limits are most likely to bite. The drop-glass response (per Section 2.8) is to run the full debate only on a 1,500-facility sample concentrated in demo states, and apply single-pass scoring (one direct judge call with internal reasoning, no debate) to the remaining 8,500. The geographic explorer can still render all 10K with single-pass scores; only the facility inspector needs the full debate transcript, and only for facilities a judge will actually click on during the demo.

#### Stage 4 — Geographic Computation (no LLM)

For each PIN code in the dataset, compute the nearest verified facility for each capability type. "Verified" means trust_score ≥ 60 and the capability is in `verified_capabilities` with confidence ≥ 0.7. Write to `geo_lookup`. Use H3 indexing for the spatial join. If isochrones are built, populate `travel_time_minutes`; otherwise leave null and use straight-line `distance_km`. Estimated runtime: 5-10 minutes.

#### Stage 5 — Vector Indexing

Concatenate each facility's structured profile into a single text blob (`profile_text`) and write to `workspace.veritas_dev.facility_embeddings`. Create a Mosaic AI Vector Search endpoint and a Delta sync index over this table, configured with `databricks-bge-large-en` as the embedding model. The endpoint auto-embeds and keeps the index synced. Estimated runtime: 10-15 minutes including endpoint provisioning (Vector Search has known provisioning lag — start this stage early in parallel with other work).

#### Stage 6 — Live Query Agent (interactive, called per user query)

When a user submits a natural-language query in Tab 3, a LangGraph workflow runs:

1. **Parse intent** — Llama 3.3 70B call extracts capability, location, and constraints from the query into a structured Pydantic object.
2. **Retrieve** — query Mosaic AI Vector Search with the parsed intent for top-20 candidate facilities.
3. **Filter** — apply hard constraints (location proximity, trust score floor, capability match).
4. **Rank** — score remaining candidates by a weighted combination of trust score, capability confidence, and inverse distance.
5. **Critic** — Llama 3.3 70B call reviews the top-5 candidates against the original query and rejects any that don't actually match user intent. If <3 remain after the critic, loop back to retrieve with a broadened query.
6. **Explain** — Llama 3.3 70B call generates a one-sentence justification per facility.

Every step is auto-traced via `mlflow.openai.autolog()`. The full trace ID is returned to the UI alongside the results so the user can click "Show reasoning" and see the underlying agent steps.

#### Stage 7 — Live Trust Drill-down (interactive)

When a user clicks "Why this score?" in the facility inspector, the API returns the cached `advocate_argument`, `skeptic_argument`, and `judge_reasoning` from `trust_scores`, plus the MLflow trace URL for the original debate run.

### 2.5 API Endpoints

FastAPI service exposes the following endpoints, all returning JSON.

```
GET  /api/facilities/{facility_id}
     → returns structured profile, trust score, citations, contradictions

GET  /api/map/{capability}?granularity=pin_code|district
     → returns geo_lookup data filtered to the requested capability,
       formatted for Folium choropleth rendering

POST /api/query
     body: { "query": "<natural language>", "max_results": 5 }
     → runs the LangGraph workflow, returns ranked facilities + reasoning trace

GET  /api/trust/{facility_id}/debate
     → returns full advocate/skeptic/judge transcript with MLflow trace URL

GET  /api/citation/{citation_id}
     → returns source sentence with character offsets for highlighting

GET  /api/health
     → liveness check, returns model serving status and table row counts
```

### 2.6 Frontend Component Architecture (Streamlit)

A single Streamlit app with three tabs implemented as `st.tabs(["Map", "Inspector", "Ask"])`. Shared state via `st.session_state`.

**Tab 1 (Map):** Folium map embedded via `streamlit-folium`. Sidebar: capability selector dropdown, granularity radio (PIN code / district), trust-score floor slider. Map updates on selector change by hitting `/api/map/{capability}`. Click on a region opens a side panel showing facility list; click on a facility marker switches to Tab 2 with that facility selected.

**Tab 2 (Inspector):** Facility selector at top (autocomplete search). Three stacked sections rendered from `/api/facilities/{id}`. Verified Capabilities section: each capability is a card with claim, confidence, and a hoverable evidence link. Flagged Contradictions: each contradiction is a card with claim, gap, and trust impact in a colored badge. Trust Reasoning: a collapsible expander showing the full debate transcript with the Advocate/Skeptic/Judge sections clearly labeled, plus an "Open in MLflow" link.

**Tab 3 (Ask):** Chat-style interface using `st.chat_input` and `st.chat_message`. User types a query, results render as a numbered list of facility cards with name, distance, trust score, and one-sentence justification. Each card has a "Show reasoning" expander that fetches and displays the MLflow trace for that query run.

### 2.7 Build Sequence — 24-Hour Plan

The hackathon runs Saturday 1 PM ET to Sunday 9 AM ET. Translated to Munich local time: Saturday 7 PM to Sunday 3 PM. That's 20 hours of build, with 4 hours buffer at the end for demo polish, video recording, and submission. Below is hour-by-hour.

**Hours 0-2 (Setup) — partially complete pre-build**
Pre-build validation already confirmed: workspace provisioned, Unity Catalog enabled, `veritas_dev` schema created, `raw_data` volume created, dataset uploaded to `/Volumes/workspace/veritas_dev/raw_data/`, Llama 3.3 70B chat working via OpenAI-compatible client, BGE-large-en embeddings working, MLflow tracking URI accessible.

Remaining at hour 0: configure repo structure, write `api/llm_client.py` (Stage 0), generate Pydantic schemas (Section 2.3), set up `.env` with workspace credentials.

Repo structure:
```
veritas/
├── notebooks/        (Databricks notebooks for pipeline stages)
├── api/              (FastAPI service)
│   ├── main.py
│   ├── llm_client.py (Stage 0 — written first)
│   ├── routers/
│   ├── agents/       (LangGraph workflows)
│   └── schemas/      (Pydantic models)
├── frontend/         (Streamlit app)
│   ├── app.py
│   └── tabs/
├── pipelines/        (extraction, trust, geo, indexing as Python modules)
├── prompts/          (all prompt templates as .md files)
└── tests/            (smoke tests for each stage)
```

**Hours 2-5 (Ingestion + Extraction Pipeline)**
Stage 1 ingestion notebook. Stage 2 extraction with full Pydantic schema and `instructor` (Mode.MD_JSON). Test on first 10 rows, then 100, then trigger the full 10,000-row run in the background. While extraction runs, move on. Watch for rate-limit errors — if observed, throttle parallelism from 20 to 10 concurrent calls.

**Hours 5-9 (Trust Debate Pipeline)**
Build the Advocate/Skeptic/Judge LangGraph workflow with MLflow autolog. Test on 5 facilities end-to-end. Verify the debate transcript reads coherently and the trust scores look defensible. Once verified, kick off the trust debate run on either a sample of 1,500 facilities (safe path, recommended) or all 10,000 (ambitious path) in the background.

Decision rule at hour 8: if you've spent more than 90 minutes debugging the debate workflow, drop to single-pass trust scoring (one LLM call producing the score directly with internal reasoning) and move on. The debate is a differentiator, not a hill to die on.

**Hours 9-12 (Geo Computation + Vector Indexing)**
Stage 4 geo computation. Stage 5 vector indexing with Mosaic AI Vector Search using `databricks-bge-large-en` as the embedding model. Both should run cleanly if the structured table is populated. Verify a top-K query against the vector index returns sensible results.

**Hours 12-16 (Backend API + Live Query Agent)**
Build FastAPI service with all six endpoints. Implement the LangGraph live query workflow (Stage 6). Test each endpoint with curl. Confirm MLflow traces are captured and queryable via `mlflow.search_traces()`.

**Hours 16-20 (Frontend Build)**
Build all three Streamlit tabs. Wire to the backend. Test the click-through flows: map → inspector → query → reasoning trace. Make sure citations render with hoverable evidence text.

**Hours 20-22 (Polish + Bug Fix)**
Tighten the UI. Fix the most visible bugs. Add a project header with the one-sentence value prop. Clean up any unhandled errors that would show in the demo.

**Hours 22-24 (Demo Recording + Submission)**
Script the 2-minute demo. Record twice, pick the better take. Write the README. Submit.

### 2.8 Decision Rules and Drop-Glass Decisions

Pre-committed decisions to avoid mid-build paralysis. When any of these triggers fire, execute the predetermined response without re-debating.

*If Stage 2 extraction hits sustained rate limiting:* throttle parallelism to 10 concurrent, then 5 if needed. If still bottlenecked at hour 6, sample down to 2,500 facilities and proceed.

*If the trust debate workflow takes more than 90 minutes to debug at hour 8:* drop to single-pass trust scoring (one Judge-style call, no Advocate/Skeptic). The Trust Reasoning panel in the UI then shows just the Judge's reasoning instead of the full debate. Mention the debate as a future-work feature in the demo.

*If trust debate Stage 3 isn't done by hour 14:* sample down to 1,500 facilities concentrated in 3-4 demo states (Bihar, Uttar Pradesh, Maharashtra, Karnataka). Apply single-pass trust scoring to the remaining 8,500. The geographic map renders all 10K; the inspector only deep-dives the 1,500 sampled set, which covers the demo regions.

*If MLflow tracing in the UI breaks at hour 18:* show traces in a side-by-side terminal in the demo video instead of inline in the app. The autolog data is still captured in MLflow even if the UI integration fails.

*If isochrone modeling adds more than 30 minutes at hour 11:* drop to haversine straight-line distance. Mention isochrones as future work.

*If Vector Search endpoint provisioning fails at hour 9-10:* fall back to ChromaDB local with `databricks-bge-large-en` embeddings called explicitly via `client.embeddings.create()`. Vector Search is preferred but ChromaDB is a clean fallback.

*If Llama 3.3 70B itself becomes rate-limited mid-build:* try `databricks-meta-llama-3-1-8b-instruct` as a fallback chat model. Quality drops on category disambiguation, so strengthen the extraction prompt's definitions section if forced to use 8B. Update `MODEL_CHAT` in `api/llm_client.py` — every other module follows automatically.

*If anything else breaks at hour 20+:* don't fix it. Cut that feature from the demo script.

### 2.9 Cost Budget

All inference and embeddings run through Databricks AI Gateway under Free Edition's foundation model allocation. Total external billing: **$0**. There is no OpenAI direct API key required, no Anthropic key, no third-party LLM provider in any code path.

The constraint that replaces dollar cost is **Free Edition rate limits**. Monitor for 429 responses. The fallbacks in Section 2.8 are designed around volume reduction (sample down) or model substitution within Databricks, never provider switching.

The only marginal external cost: if isochrone modeling pulls map tiles from OSM, that's free but rate-limited at the OSM tile server level. Bounded.

### 2.10 What Claude Code Should Do First

When Claude Code is invoked at the start of the build, the first four actions are:

1. Read this entire document end-to-end.
2. Create the repo structure described in section 2.7.
3. Generate `api/llm_client.py` per Stage 0 in section 2.4 — this is the foundation module every other piece imports.
4. Generate the Pydantic schemas in `api/schemas/` from the data schemas in section 2.3 — these are the contracts every pipeline stage and API endpoint depends on.

After that, follow the Build Sequence in section 2.7 hour by hour. At the start of each hour block, re-read the relevant section to ensure no scope drift.

### 2.11 What "Done" Looks Like

The submission is complete when:

- A working Streamlit app runs locally and on Databricks Apps.
- All three tabs render without crashes.
- The map shows colored desert severity for at least three capabilities.
- The inspector shows verified capabilities, contradictions, and the trust debate transcript for at least 100 facilities (ideally all of them).
- The query tab returns ranked results with reasoning for at least 5 sample queries pre-tested in the demo script.
- A 2-minute demo video is recorded showing all three tabs in use.
- The README explains the architecture, the differentiators, and how to reproduce.
- The repo is pushed to GitHub with a clean commit history.

The submission is *winning* when, in addition:

- Every claim in the UI is hyperlinked back to the exact source sentence in the original notes.
- The Advocate/Skeptic/Judge transcript reads convincingly to a non-technical observer.
- MLflow traces are visible inline in the UI when a user clicks "Show reasoning."
- The demo clearly demonstrates a compound natural-language query being answered with full transparency.
- The pitch narrative explicitly credits the Databricks-native stack: *"Veritas runs entirely on open Llama 3.3 70B served through Databricks AI Gateway, with native Mosaic AI embeddings, governed by Unity Catalog. Zero external API dependencies."*

---

## Part 3 — Prompt Library (Append-only Reference)

All LLM prompts used in production are versioned in `prompts/` as separate markdown files so they can be edited without touching code. The build order is:

`prompts/extraction.md` — extracts structured profiles from unstructured notes.
`prompts/advocate.md` — argues for facility trustworthiness.
`prompts/skeptic.md` — argues against facility claims, surfaces contradictions.
`prompts/judge.md` — synthesizes advocate and skeptic into a final trust score.
`prompts/query_intent.md` — parses a user query into structured intent.
`prompts/query_critic.md` — reviews ranked results for relevance to the query.
`prompts/query_explain.md` — generates per-facility justifications for the user.

The full text of each prompt is in section 2.4 above. They are reproduced as standalone files for ease of iteration during the build.

All prompts target `databricks-meta-llama-3-3-70b-instruct` and assume Llama-style chat formatting (system + user messages). They include explicit instructions to return JSON without code fences, since Llama tends to wrap JSON output in ```json ... ``` blocks even when instructed not to. Defensive parsing (regex-strip fences before `json.loads()`) is required.

---

## Part 4 — Validated Environment Snapshot

This is the ground truth at hour 0, established during pre-build validation.

**Databricks workspace:** Free Edition, EU region, Unity Catalog enabled.
**Catalog/schema:** `workspace.veritas_dev`.
**Volume:** `/Volumes/workspace/veritas_dev/raw_data/` containing `VF_Hackathon_Dataset_India_Large.xlsx`.
**Validated chat endpoint:** `databricks-meta-llama-3-3-70b-instruct` (clean JSON extraction, properly disambiguates capabilities from metadata).
**Validated embedding endpoint:** `databricks-bge-large-en` (1024 dimensions).
**Rate-limited (do not use):** the entire `databricks-gpt-5-*` family (rate limit of 0 on Free Edition).
**Auth pattern:** `WorkspaceClient().config.authenticate()` extracts a Bearer token; pass to `OpenAI(api_key=token, base_url=f"{host}/serving-endpoints")`.
**MLflow tracing:** enabled via single line `mlflow.openai.autolog()` at module import.
**Other available chat models (untested but listed):** `databricks-meta-llama-3-1-8b-instruct` (smaller, faster, weaker on categorization), `databricks-meta-llama-3.1-405b-instruct` (largest, slowest, may also be rate-limited), `databricks-llama-4-maverick`, `databricks-qwen3-next-80b-a3b-instruct`. Try as fallbacks only if 70B fails.

If anything in this snapshot stops working mid-build, refer to Section 2.8 drop-glass rules.

---

*End of document. Total length intentional — every section has been needed by the build at least once. When in doubt, re-read.*