"""Card (saved question) operations."""
from __future__ import annotations
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult

def list_cards(client: MetabaseClient) -> list[dict]:
    return client.get("/api/card")

def run_card(client: MetabaseClient, card_id: int, parameters: dict | None = None) -> QueryResult:
    payload = {}
    if parameters:
        payload["parameters"] = [{"type": "category", "target": ["variable", ["template-tag", k]], "value": v} for k, v in parameters.items()]
    resp = client.post(f"/api/card/{card_id}/query", json=payload)
    data = resp.get("data", {})
    cols = data.get("cols", [])
    columns = [{"name": c.get("name", f"col_{i}"), "base_type": c.get("base_type"), "semantic_type": c.get("semantic_type")} for i, c in enumerate(cols)]
    return QueryResult(columns=columns, rows=data.get("rows", []), row_count=resp.get("row_count", len(data.get("rows", []))))
