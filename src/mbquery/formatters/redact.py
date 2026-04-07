"""PII redaction for query results."""
from __future__ import annotations

from mbquery.core.queries import QueryResult

PII_SEMANTIC_TYPES = frozenset({
    "type/Email", "type/Name", "type/Phone", "type/Address", "type/City",
    "type/State", "type/ZipCode", "type/Country", "type/Latitude",
    "type/Longitude", "type/Birthdate", "type/AvatarURL",
})

REDACTED = "[REDACTED]"

def redact_pii(result: QueryResult) -> QueryResult:
    pii_indices = {i for i, col in enumerate(result.columns) if col.get("semantic_type") in PII_SEMANTIC_TYPES}
    if not pii_indices:
        return result
    new_rows = [[REDACTED if i in pii_indices else val for i, val in enumerate(row)] for row in result.rows]
    return QueryResult(columns=result.columns, rows=new_rows, row_count=result.row_count)
