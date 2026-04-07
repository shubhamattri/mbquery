import json
import time
import pytest
import respx
from pathlib import Path
from mbquery.core.schema_cache import SchemaCache
from mbquery.core.client import MetabaseClient
from mbquery.config.models import Profile, AuthConfig

@pytest.fixture
def client():
    return MetabaseClient(Profile(name="test", url="https://metabase.test.com", auth=AuthConfig(method="api-key", api_key="mb_testkey"), default_db=2))

@pytest.fixture
def cache_dir(tmp_path):
    d = tmp_path / "schema_cache"
    d.mkdir()
    return d

MOCK_METADATA = {
    "id": 2, "name": "Production",
    "tables": [
        {"id": 10, "name": "users", "schema": "public", "fields": [
            {"id": 100, "name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"id": 101, "name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ]},
        {"id": 11, "name": "orders", "schema": "public", "fields": [
            {"id": 200, "name": "id", "base_type": "type/Integer", "semantic_type": None},
        ]},
    ],
}

@respx.mock
def test_schema_cache_fetch_and_cache(client, cache_dir):
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    cache = SchemaCache(cache_dir)
    schema = cache.get_schema(client, database_id=2, profile_name="test")
    assert len(schema["tables"]) == 2
    assert schema["tables"][0]["name"] == "users"
    assert (cache_dir / "test_2.json").exists()

@respx.mock
def test_schema_cache_uses_disk_cache(client, cache_dir):
    cache_file = cache_dir / "test_2.json"
    cached = {"database_id": 2, "tables": [{"name": "cached_table", "fields": []}], "cached_at": time.time()}
    cache_file.write_text(json.dumps(cached))
    cache = SchemaCache(cache_dir)
    schema = cache.get_schema(client, database_id=2, profile_name="test")
    assert len(respx.calls) == 0
    assert schema["tables"][0]["name"] == "cached_table"

@respx.mock
def test_schema_cache_refresh_bypasses_cache(client, cache_dir):
    cache_file = cache_dir / "test_2.json"
    cached = {"database_id": 2, "tables": [{"name": "stale"}], "cached_at": time.time()}
    cache_file.write_text(json.dumps(cached))
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    cache = SchemaCache(cache_dir)
    schema = cache.get_schema(client, database_id=2, profile_name="test", force_refresh=True)
    assert schema["tables"][0]["name"] == "users"

@respx.mock
def test_schema_cache_expired_ttl(client, cache_dir):
    cache_file = cache_dir / "test_2.json"
    cached = {"database_id": 2, "tables": [{"name": "old"}], "cached_at": time.time() - 100000}
    cache_file.write_text(json.dumps(cached))
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    cache = SchemaCache(cache_dir, ttl_seconds=3600)
    schema = cache.get_schema(client, database_id=2, profile_name="test")
    assert schema["tables"][0]["name"] == "users"

def test_schema_to_prompt_context(cache_dir):
    cache = SchemaCache(cache_dir)
    schema = {"database_id": 2, "tables": [{"name": "users", "fields": [{"name": "id", "base_type": "type/Integer"}, {"name": "email", "base_type": "type/Text"}]}]}
    prompt = cache.schema_to_prompt_context(schema)
    assert "users" in prompt
    assert "id" in prompt
    assert "email" in prompt
