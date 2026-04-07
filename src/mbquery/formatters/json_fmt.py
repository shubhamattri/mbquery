"""JSON and JSONL formatters."""
import json
from mbquery.core.queries import QueryResult

def format_json(result: QueryResult) -> str:
    rows = []
    for row in result.rows:
        obj = {}
        for i, col in enumerate(result.columns):
            obj[col["name"]] = row[i]
        rows.append(obj)
    return json.dumps(rows, indent=2, default=str)

def format_jsonl(result: QueryResult) -> str:
    lines = []
    for row in result.rows:
        obj = {}
        for i, col in enumerate(result.columns):
            obj[col["name"]] = row[i]
        lines.append(json.dumps(obj, default=str))
    return "\n".join(lines)
