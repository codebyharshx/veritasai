# Query Explain Prompt

Generates per-facility justifications for the user.

## System Message

You are generating user-facing explanations for why each facility was recommended in response to their query. Each explanation should be one clear sentence that connects the facility's capabilities to what the user asked for.

## User Message Template

Original query: {query}

Facilities to explain:
{facilities}

For each facility, write a one-sentence justification that:
- References the specific capability that matches the query
- Mentions the trust score if relevant
- Is written for a non-technical user

Return only the JSON object matching the schema. No preamble, no code fences.
