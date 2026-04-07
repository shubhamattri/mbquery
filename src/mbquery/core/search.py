"""Search operations."""
from __future__ import annotations

from mbquery.core.client import MetabaseClient


def search(client: MetabaseClient, query: str, model_type: str | None = None) -> list[dict]:
    params: dict = {"q": query}
    if model_type:
        params["models"] = model_type
    resp = client.get("/api/search", params=params)
    if isinstance(resp, dict):
        return resp.get("data", [])
    return resp
