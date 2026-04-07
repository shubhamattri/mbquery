import json

import pytest
import respx
import yaml
from typer.testing import CliRunner

from mbquery.cli.app import app

runner = CliRunner()

@pytest.fixture(autouse=True)
def setup_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    (config_dir / "schema_cache").mkdir()
    config = {"active_profile": "test", "profiles": {"test": {"url": "https://metabase.test.com", "auth": {"method": "api-key", "api_key": "mb_testkey"}, "default_db": 2}}, "defaults": {"format": "table", "limit": 100, "redact_pii": False}}
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

MOCK_DB_LIST = {"data": [{"id": 1, "name": "Staging", "engine": "postgres"}, {"id": 2, "name": "Production", "engine": "postgres"}]}
MOCK_METADATA = {"id": 2, "name": "Production", "tables": [{"id": 10, "name": "users", "schema": "public", "fields": [{"id": 100, "name": "id", "base_type": "type/Integer", "semantic_type": None}, {"id": 101, "name": "email", "base_type": "type/Text", "semantic_type": "type/Email"}]}, {"id": 11, "name": "orders", "schema": "public", "fields": [{"id": 200, "name": "id", "base_type": "type/Integer", "semantic_type": None}]}]}

@respx.mock
def test_schema_databases():
    respx.get("https://metabase.test.com/api/database").respond(json=MOCK_DB_LIST)
    result = runner.invoke(app, ["schema", "databases", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_schema_tables():
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    result = runner.invoke(app, ["schema", "tables", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_schema_fields():
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    result = runner.invoke(app, ["schema", "fields", "users", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_schema_refresh():
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    result = runner.invoke(app, ["schema", "refresh"])
    assert result.exit_code == 0
