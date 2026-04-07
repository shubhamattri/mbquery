import os
import yaml
from pathlib import Path
from mbquery.config.store import ConfigStore
from mbquery.config.models import Profile, AuthConfig, LLMConfig


def test_store_init_creates_dir(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    assert store.config_dir.exists()
    assert (tmp_config_dir / "schema_cache").exists()


def test_store_load_empty(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    config = store.load()
    assert config.active_profile is None
    assert config.profiles == {}


def test_store_save_and_load(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    config = store.load()
    config.active_profile = "prod"
    config.profiles["prod"] = Profile(
        name="prod",
        url="https://metabase.example.com",
        auth=AuthConfig(method="api-key", api_key="mb_test"),
        default_db=2,
    )
    store.save(config)

    config_file = tmp_config_dir / "config.yaml"
    assert config_file.exists()
    assert oct(config_file.stat().st_mode & 0o777) == "0o600"

    loaded = store.load()
    assert loaded.active_profile == "prod"
    assert loaded.profiles["prod"].url == "https://metabase.example.com"
    assert loaded.profiles["prod"].auth.api_key == "mb_test"


def test_store_add_profile(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="staging", url="https://staging.metabase.com", auth_method="session", email="test@test.com", password="secret")
    config = store.load()
    assert "staging" in config.profiles
    assert config.active_profile == "staging"


def test_store_add_second_profile_does_not_switch(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    store.add_profile(name="dev", url="https://dev.mb.com", auth_method="api-key", api_key="mb_2")
    config = store.load()
    assert config.active_profile == "prod"


def test_store_switch_profile(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    store.add_profile(name="dev", url="https://dev.mb.com", auth_method="api-key", api_key="mb_2")
    store.switch_profile("dev")
    config = store.load()
    assert config.active_profile == "dev"


def test_store_switch_nonexistent_raises(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    import pytest
    with pytest.raises(ValueError, match="Profile 'nope' not found"):
        store.switch_profile("nope")


def test_store_remove_profile(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    store.remove_profile("prod")
    config = store.load()
    assert "prod" not in config.profiles
    assert config.active_profile is None


def test_store_list_profiles(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    store.add_profile(name="dev", url="https://dev.mb.com", auth_method="api-key", api_key="mb_2")
    names = store.list_profiles()
    assert set(names) == {"prod", "dev"}


def test_store_get_active_profile(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    profile = store.get_active_profile()
    assert profile.name == "prod"
    assert profile.url == "https://prod.mb.com"


def test_store_get_active_profile_none_raises(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    import pytest
    with pytest.raises(ValueError, match="No active profile"):
        store.get_active_profile()


def test_store_set_llm(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.set_llm(provider="gemini", model="gemini-2.0-flash", api_key="AIza_test")
    config = store.load()
    assert config.llm is not None
    assert config.llm.provider == "gemini"
    assert config.llm.model == "gemini-2.0-flash"


def test_store_env_var_override(tmp_config_dir: Path, monkeypatch):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    monkeypatch.setenv("MBQUERY_URL", "https://env.mb.com")
    monkeypatch.setenv("MBQUERY_API_KEY", "mb_env_key")
    profile = store.resolve_profile()
    assert profile.url == "https://env.mb.com"
    assert profile.auth.api_key == "mb_env_key"
