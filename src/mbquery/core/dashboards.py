"""Dashboard operations."""
from __future__ import annotations

from mbquery.core.client import MetabaseClient


def list_dashboards(client: MetabaseClient) -> list[dict]:
    return client.get("/api/dashboard")

def get_dashboard(client: MetabaseClient, dashboard_id: int) -> dict:
    return client.get(f"/api/dashboard/{dashboard_id}")
