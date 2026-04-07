"""Config file management — load, save, CRUD profiles."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from mbquery.config.models import AppConfig, AuthConfig, LLMConfig, Profile


def _default_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "mbquery"
    return Path.home() / ".config" / "mbquery"


class ConfigStore:
    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or _default_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.config_dir / "schema_cache").mkdir(exist_ok=True)
        self._config_file = self.config_dir / "config.yaml"

    def load(self) -> AppConfig:
        if not self._config_file.exists():
            return AppConfig.empty()
        with open(self._config_file) as f:
            data = yaml.safe_load(f)
        if not data:
            return AppConfig.empty()
        return AppConfig.from_dict(data)

    def save(self, config: AppConfig) -> None:
        with open(self._config_file, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
        self._config_file.chmod(0o600)

    def add_profile(self, name: str, url: str, auth_method: str, api_key: str | None = None, email: str | None = None, password: str | None = None, default_db: int | None = None) -> Profile:
        config = self.load()
        auth = AuthConfig(method=auth_method, api_key=api_key, email=email, password=password)
        profile = Profile(name=name, url=url.rstrip("/"), auth=auth, default_db=default_db)
        is_first = len(config.profiles) == 0
        config.profiles[name] = profile
        if is_first:
            config.active_profile = name
        self.save(config)
        return profile

    def remove_profile(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ValueError(f"Profile '{name}' not found")
        del config.profiles[name]
        if config.active_profile == name:
            config.active_profile = next(iter(config.profiles), None)
        self.save(config)

    def switch_profile(self, name: str) -> None:
        config = self.load()
        if name not in config.profiles:
            raise ValueError(f"Profile '{name}' not found. Available: {list(config.profiles.keys())}")
        config.active_profile = name
        self.save(config)

    def list_profiles(self) -> list[str]:
        config = self.load()
        return list(config.profiles.keys())

    def get_active_profile(self) -> Profile:
        config = self.load()
        if not config.active_profile or config.active_profile not in config.profiles:
            raise ValueError("No active profile. Run: mbquery config init")
        return config.profiles[config.active_profile]

    def set_llm(self, provider: str, model: str, api_key: str | None = None, base_url: str | None = None) -> None:
        config = self.load()
        config.llm = LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url)
        self.save(config)

    def get_llm(self) -> LLMConfig | None:
        config = self.load()
        return config.llm

    def resolve_profile(self, profile_name: str | None = None) -> Profile:
        """Resolve profile with precedence: flag > env vars > active profile."""
        if profile_name:
            config = self.load()
            if profile_name not in config.profiles:
                raise ValueError(f"Profile '{profile_name}' not found")
            return config.profiles[profile_name]

        env_url = os.environ.get("MBQUERY_URL")
        env_key = os.environ.get("MBQUERY_API_KEY")
        if env_url and env_key:
            env_db = os.environ.get("MBQUERY_DEFAULT_DB")
            return Profile(
                name="__env__",
                url=env_url.rstrip("/"),
                auth=AuthConfig(method="api-key", api_key=env_key),
                default_db=int(env_db) if env_db else None,
            )

        return self.get_active_profile()
