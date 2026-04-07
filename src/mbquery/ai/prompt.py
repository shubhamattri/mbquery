"""NL→SQL prompt builder."""
from __future__ import annotations


def build_nl_to_sql_prompt(question: str, schema_context: str, hints: str | None = None) -> str:
    parts = [
        "You are a PostgreSQL expert. Convert the following natural language query to SQL.",
        "",
        schema_context,
    ]
    if hints:
        parts.append("")
        parts.append(f"Additional context:\n{hints}")
    parts.extend([
        "",
        f"User query: {question}",
        "",
        "CRITICAL: Return ONLY the raw SQL query. No explanations, no markdown code blocks,",
        "no comments. Start directly with SELECT, INSERT, UPDATE, DELETE, WITH, or other SQL keyword.",
    ])
    return "\n".join(parts)
