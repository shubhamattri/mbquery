"""Database, table, and field operations."""
from __future__ import annotations
from mbquery.core.client import MetabaseClient


def list_databases(client: MetabaseClient) -> list[dict]:
    resp = client.get("/api/database")
    return resp.get("data", resp) if isinstance(resp, dict) else resp


def get_database_metadata(client: MetabaseClient, database_id: int) -> dict:
    return client.get(f"/api/database/{database_id}", params={"include": "tables.fields"})


def list_tables(client: MetabaseClient, database_id: int) -> list[dict]:
    metadata = get_database_metadata(client, database_id)
    return metadata.get("tables", [])


def get_table_fields(client: MetabaseClient, table_id: int) -> list[dict]:
    metadata = client.get(f"/api/table/{table_id}/query_metadata")
    return metadata.get("fields", [])
