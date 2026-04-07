import json
import time

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
    schema_cache_dir = config_dir / "schema_cache"
    schema_cache_dir.mkdir()
    schema = {"database_id": 2, "tables": [{"name": "users", "fields": [{"name": "id", "base_type": "type/Integer"}, {"name": "email", "base_type": "type/Text"}]}], "cached_at": time.time()}
    (schema_cache_dir / "test_2.json").write_text(json.dumps(schema))
    config = {
        "active_profile": "test",
        "profiles": {"test": {"url": "https://metabase.test.com", "auth": {"method": "api-key", "api_key": "mb_testkey"}, "default_db": 2}},
        "llm": {"provider": "gemini", "model": "gemini-2.0-flash", "api_key": "AIza_test", "base_url": None},
        "defaults": {"format": "table", "limit": 100, "redact_pii": False},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


def _extract_json(output: str) -> str:
    """Extract the JSON portion from CLI output that may contain Rich stderr messages."""
    lines = output.splitlines()
    # Find the first line that starts a JSON array or object
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            return "\n".join(lines[i:])
    return output


@respx.mock
def test_ask_generates_and_executes():
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={"candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) FROM users"}]}}]})
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[42]], "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["ask", "--format", "json", "how many users are there"])
    assert result.exit_code == 0
    data = json.loads(_extract_json(result.output))
    assert data[0]["count"] == 42


@respx.mock
def test_ask_show_sql_flag():
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={"candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) FROM users"}]}}]})
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[42]], "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["ask", "--show-sql", "--format", "json", "count users"])
    assert result.exit_code == 0
    data = json.loads(_extract_json(result.output))
    assert data[0]["count"] == 42


def test_ask_no_llm_configured(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery_nollm"
    config_dir.mkdir()
    (config_dir / "schema_cache").mkdir()
    config = {
        "active_profile": "test",
        "profiles": {"test": {"url": "https://metabase.test.com", "auth": {"method": "api-key", "api_key": "mb_testkey"}, "default_db": 2}},
        "defaults": {"format": "table", "limit": 100, "redact_pii": False},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir.parent))
    result = runner.invoke(app, ["ask", "count users"])
    assert result.exit_code == 1
