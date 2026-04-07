"""Output formatting for query results."""
from mbquery.core.queries import QueryResult
from mbquery.formatters.table import format_table
from mbquery.formatters.csv_fmt import format_csv
from mbquery.formatters.json_fmt import format_json, format_jsonl
from mbquery.formatters.markdown import format_markdown

FORMATS = {"table": format_table, "csv": format_csv, "json": format_json, "jsonl": format_jsonl, "markdown": format_markdown}

def format_result(result: QueryResult, fmt: str) -> str:
    formatter = FORMATS.get(fmt)
    if not formatter:
        raise ValueError(f"Unknown format: '{fmt}'. Valid: {', '.join(FORMATS.keys())}")
    return formatter(result)
