"""Markdown table formatter."""
from mbquery.core.queries import QueryResult


def _escape_md_cell(value) -> str:
    s = str(value) if value is not None else "NULL"
    return s.replace("|", "\\|").replace("\n", " ")


def format_markdown(result: QueryResult) -> str:
    if not result.columns:
        return ""
    names = result.column_names
    lines = []
    lines.append("| " + " | ".join(names) + " |")
    lines.append("| " + " | ".join("---" for _ in names) + " |")
    for row in result.rows:
        cells = [_escape_md_cell(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
