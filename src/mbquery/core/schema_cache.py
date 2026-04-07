"""Schema auto-discovery and caching."""
from __future__ import annotations

import json
import time
from pathlib import Path

from mbquery.core.client import MetabaseClient
from mbquery.core.database import get_database_metadata


class SchemaCache:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 86400):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds

    def _cache_path(self, profile_name: str, database_id: int) -> Path:
        return self.cache_dir / f"{profile_name}_{database_id}.json"

    def _read_cache(self, profile_name: str, database_id: int) -> dict | None:
        path = self._cache_path(profile_name, database_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            cached_at = data.get("cached_at", 0)
            if time.time() - cached_at > self.ttl_seconds:
                return None
            return data
        except (json.JSONDecodeError, KeyError):
            return None

    def _write_cache(self, profile_name: str, database_id: int, schema: dict) -> None:
        path = self._cache_path(profile_name, database_id)
        schema["cached_at"] = time.time()
        path.write_text(json.dumps(schema, indent=2))

    def get_schema(self, client: MetabaseClient, database_id: int, profile_name: str, force_refresh: bool = False) -> dict:
        if not force_refresh:
            cached = self._read_cache(profile_name, database_id)
            if cached:
                return cached
        raw = get_database_metadata(client, database_id)
        schema = {
            "database_id": database_id,
            "tables": [
                {
                    "name": t["name"],
                    "schema": t.get("schema", "public"),
                    "fields": [
                        {"name": f["name"], "base_type": f.get("base_type"), "semantic_type": f.get("semantic_type")}
                        for f in t.get("fields", [])
                    ],
                }
                for t in raw.get("tables", [])
            ],
        }
        self._write_cache(profile_name, database_id, schema)
        return schema

    def schema_to_prompt_context(self, schema: dict) -> str:
        lines = ["Database schema:"]
        for table in schema.get("tables", []):
            fields_str = ", ".join(f"{f['name']} ({f.get('base_type', 'unknown')})" for f in table.get("fields", []))
            lines.append(f"  Table: {table['name']} — columns: {fields_str}")
        return "\n".join(lines)
