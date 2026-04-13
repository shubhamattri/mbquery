"""Integration test — verify full CLI works end-to-end."""
import json
import time

import pytest
import respx
import yaml
from typer.testing import CliRunner

from mbquery.cli.app import app

runner = CliRunner()

@pytest.fixture(autouse=True)
def full_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    schema_dir = config_dir / "schema_cache"
    schema_dir.mkdir()
    config = {"active_profile": "test", "profiles": {"test": {"url": "https://metabase.test.com", "auth": {"method": "api-key", "api_key": "mb_testkey"}, "default_db": 2}}, "llm": {"provider": "gemini", "model": "gemini-2.0-flash", "api_key": "AIza_test", "base_url": None}, "defaults": {"format": "table", "limit": 100, "redact_pii": True}}
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    schema = {"database_id": 2, "tables": [{"name": "users", "fields": [{"name": "id", "base_type": "type/Integer"}, {"name": "email", "base_type": "type/Text"}]}], "cached_at": time.time()}
    (schema_dir / "test_2.json").write_text(json.dumps(schema))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

@respx.mock
def test_full_sql_workflow():
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[1, "alice@test.com", "Alice"]], "cols": [{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"}, {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"}]}, "row_count": 1})
    result = runner.invoke(app, ["query", "--format", "json", "SELECT * FROM users"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["id"] == 1
    assert data[0]["email"] == "[REDACTED]"
    assert data[0]["name"] == "[REDACTED]"

@respx.mock
def test_full_nl_workflow():
    respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent").respond(json={"candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) AS total FROM users"}]}}]})
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[42]], "cols": [{"name": "total", "base_type": "type/Integer", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["ask", "--format", "json", "how many users are there"])
    assert result.exit_code == 0
    # Extract JSON from output (may have "Generating SQL..." prefix from stderr mixing)
    output = result.output.strip()
    json_start = output.find("[")
    if json_start >= 0:
        output = output[json_start:]
    data = json.loads(output)
    assert data[0]["total"] == 42

def test_all_commands_registered():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["query", "ask", "schema", "card", "dashboard", "search", "config", "serve", "login"]:
        assert cmd in result.output, f"Command '{cmd}' not found in help"

@respx.mock
def test_format_csv_output():
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[1, 100]], "cols": [{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "amount", "base_type": "type/Float", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["query", "--format", "csv", "SELECT 1"])
    assert result.exit_code == 0
    assert "id,amount" in result.output

@respx.mock
def test_format_markdown_output():
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[1, "test"]], "cols": [{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "name", "base_type": "type/Text", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["query", "--format", "markdown", "SELECT 1"])
    assert result.exit_code == 0
    assert "| id | name |" in result.output
