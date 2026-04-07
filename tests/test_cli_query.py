import json
import pytest
import respx
import yaml
from typer.testing import CliRunner
from mbquery.cli.app import app
from pathlib import Path

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    (config_dir / "schema_cache").mkdir()
    config = {
        "active_profile": "test",
        "profiles": {
            "test": {
                "url": "https://metabase.test.com",
                "auth": {"method": "api-key", "api_key": "mb_testkey"},
                "default_db": 2,
            }
        },
        "defaults": {"format": "table", "limit": 100, "redact_pii": True},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


@respx.mock
def test_query_command_basic():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[42]], "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]},
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "SELECT COUNT(*) FROM users"])
    assert result.exit_code == 0
    assert "42" in result.output


@respx.mock
def test_query_command_json_format():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[1, "Alice"], [2, "Bob"]], "cols": [
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": None},
        ]},
        "row_count": 2,
    })
    result = runner.invoke(app, ["query", "--format", "json", "SELECT * FROM users"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["name"] == "Alice"


@respx.mock
def test_query_command_csv_format():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[1, "Alice"]], "cols": [
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": None},
        ]},
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "csv", "SELECT * FROM users"])
    assert result.exit_code == 0
    assert "id,name" in result.output
    assert "1,Alice" in result.output


@respx.mock
def test_query_command_with_pii_redaction():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[1, "alice@test.com"]], "cols": [
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ]},
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "json", "SELECT * FROM users"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["email"] == "[REDACTED]"


@respx.mock
def test_query_command_no_redact_flag():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[1, "alice@test.com"]], "cols": [
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ]},
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "json", "--no-redact", "SELECT * FROM users"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["email"] == "alice@test.com"


@respx.mock
def test_query_command_from_file(tmp_path):
    sql_file = tmp_path / "test.sql"
    sql_file.write_text("SELECT 1 as num")
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[1]], "cols": [{"name": "num", "base_type": "type/Integer", "semantic_type": None}]},
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--file", str(sql_file), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["num"] == 1
