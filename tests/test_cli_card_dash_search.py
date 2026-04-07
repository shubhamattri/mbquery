import json
import yaml
import pytest
import respx
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

@respx.mock
def test_card_list():
    respx.get("https://metabase.test.com/api/card").respond(json=[{"id": 1, "name": "Monthly Revenue", "collection_id": 5, "display": "table"}, {"id": 2, "name": "User Count", "collection_id": 5, "display": "scalar"}])
    result = runner.invoke(app, ["card", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_card_run():
    respx.post("https://metabase.test.com/api/card/1/query").respond(json={"data": {"rows": [[50000]], "cols": [{"name": "revenue", "base_type": "type/Float", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["card", "run", "1", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["revenue"] == 50000

@respx.mock
def test_card_run_by_name():
    respx.get("https://metabase.test.com/api/card").respond(json=[{"id": 1, "name": "Monthly Revenue", "collection_id": 5, "display": "table"}])
    respx.post("https://metabase.test.com/api/card/1/query").respond(json={"data": {"rows": [[50000]], "cols": [{"name": "revenue", "base_type": "type/Float", "semantic_type": None}]}, "row_count": 1})
    result = runner.invoke(app, ["card", "run", "Monthly Revenue", "--format", "json"])
    assert result.exit_code == 0

@respx.mock
def test_dashboard_list():
    respx.get("https://metabase.test.com/api/dashboard").respond(json=[{"id": 10, "name": "Sales Dashboard", "collection_id": 3}, {"id": 11, "name": "Ops Dashboard", "collection_id": 3}])
    result = runner.invoke(app, ["dashboard", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_dashboard_show():
    respx.get("https://metabase.test.com/api/dashboard/10").respond(json={"id": 10, "name": "Sales", "dashcards": [{"id": 100, "card": {"id": 1, "name": "Revenue"}, "size_x": 6, "size_y": 4}, {"id": 101, "card": {"id": 2, "name": "Users"}, "size_x": 6, "size_y": 4}]})
    result = runner.invoke(app, ["dashboard", "show", "10", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_search():
    respx.get("https://metabase.test.com/api/search").respond(json={"data": [{"id": 1, "name": "Revenue Card", "model": "card"}, {"id": 10, "name": "Revenue Dashboard", "model": "dashboard"}]})
    result = runner.invoke(app, ["search", "revenue", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2

@respx.mock
def test_search_with_type_filter():
    respx.get("https://metabase.test.com/api/search").respond(json={"data": [{"id": 1, "name": "Revenue Card", "model": "card"}]})
    result = runner.invoke(app, ["search", "revenue", "--type", "card", "--format", "json"])
    assert result.exit_code == 0
