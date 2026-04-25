# Query Intent Prompt

Parses a user query into structured intent.

## System Message

You are parsing a natural-language query about Indian medical facilities into structured search parameters. Extract the capabilities being requested, any location constraints, and any operational constraints.

## User Message Template

User query: {query}

Parse this query into structured intent. Extract:
- capabilities: list of clinical services needed (e.g. "emergency surgery", "dialysis")
- location_state: state name if mentioned
- location_district: district name if mentioned
- location_pin_code: PIN code if mentioned
- max_distance_km: maximum distance if mentioned
- min_trust_score: minimum trust score if mentioned (default null)
- operational_constraints: list of timing constraints (e.g. "24/7", "weekends", "after hours")

Return only the JSON object matching the schema. No preamble, no code fences.
