import yaml
import pytest
from typer.testing import CliRunner
from mbquery.cli.app import app

runner = CliRunner()

@pytest.fixture(autouse=True)
def setup_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    (config_dir / "schema_cache").mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return config_dir

def test_config_list_empty():
    result = runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    assert "No profiles" in result.output

def test_config_add_and_list():
    result = runner.invoke(app, ["config", "add", "prod", "--url", "https://metabase.example.com", "--api-key", "mb_test123"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    assert "prod" in result.output

def test_config_switch():
    runner.invoke(app, ["config", "add", "prod", "--url", "https://prod.mb.com", "--api-key", "mb_1"])
    runner.invoke(app, ["config", "add", "dev", "--url", "https://dev.mb.com", "--api-key", "mb_2"])
    result = runner.invoke(app, ["config", "switch", "dev"])
    assert result.exit_code == 0
    assert "dev" in result.output

def test_config_switch_nonexistent():
    result = runner.invoke(app, ["config", "switch", "nope"])
    assert result.exit_code == 1
