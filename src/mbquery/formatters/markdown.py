"""Markdown table formatter."""
from mbquery.core.queries import QueryResult


def format_markdown(result: QueryResult) -> str:
    if not result.columns:
        return ""
    names = result.column_names
    lines = []
    lines.append("| " + " | ".join(names) + " |")
    lines.append("| " + " | ".join("---" for _ in names) + " |")
    for row in result.rows:
        cells = [str(v) if v is not None else "NULL" for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
