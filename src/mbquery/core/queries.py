"""SQL query execution against Metabase."""

from __future__ import annotations

import re
from dataclasses import dataclass

from mbquery.core.client import MetabaseClient

WRITE_KEYWORDS = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


@dataclass
class QueryResult:
    columns: list[dict]
    rows: list[list]
    row_count: int

    @property
    def column_names(self) -> list[str]:
        return [c["name"] for c in self.columns]

    def filter_fields(self, fields: list[str]) -> QueryResult:
        indices = []
        new_cols = []
        for i, col in enumerate(self.columns):
            if col["name"] in fields:
                indices.append(i)
                new_cols.append(col)
        new_rows = [[row[i] for i in indices] for row in self.rows]
        return QueryResult(columns=new_cols, rows=new_rows, row_count=self.row_count)


def is_write_query(sql: str) -> bool:
    return bool(WRITE_KEYWORDS.match(sql.strip()))


def execute_sql(client: MetabaseClient, sql: str, database_id: int, limit: int | None = None, block_writes: bool = False) -> QueryResult:
    if block_writes and is_write_query(sql):
        raise ValueError(f"Write queries are blocked. Query starts with: {sql.strip()[:30]}...")

    query = sql.strip().rstrip(";")
    if limit and not re.search(r"\bLIMIT\s+\d+", query, re.IGNORECASE):
        query = f"SELECT * FROM ({query}) _q LIMIT {limit}"

    payload = {"database": database_id, "type": "native", "native": {"query": query}}
    response = client.post("/api/dataset", json=payload)

    data = response.get("data", {})
    rows = data.get("rows", [])
    cols = data.get("cols", [])
    columns = [
        {"name": c.get("name", f"col_{i}"), "base_type": c.get("base_type"), "semantic_type": c.get("semantic_type")}
        for i, c in enumerate(cols)
    ]

    return QueryResult(columns=columns, rows=rows, row_count=response.get("row_count", len(rows)))
