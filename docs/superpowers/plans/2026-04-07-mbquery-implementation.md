# mbquery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build mbquery — a Python CLI for querying Metabase via SQL or natural language, with MCP server mode and library API.

**Architecture:** Layered — `core/` (HTTP client + business logic) → `cli/` (Typer commands) + `mcp/` (MCP server) + `ai/` (pluggable LLM). Config at `~/.config/mbquery/`. Output via `formatters/`.

**Tech Stack:** Python 3.10+, typer, rich, httpx, pyyaml, mcp SDK (optional), hatchling build system, pytest, ruff.

---

## File Map

### New Files (all under `src/mbquery/`)

| File | Responsibility |
|------|---------------|
| `__init__.py` | Package root, version, library re-exports |
| `config/models.py` | Dataclasses: `Profile`, `LLMConfig`, `AppConfig`, `Defaults` |
| `config/store.py` | Load/save/add/remove/switch profiles in `~/.config/mbquery/config.yaml` |
| `core/client.py` | `MetabaseClient` — HTTP wrapper (get/post), auth (API key + session), auto-retry on 401 |
| `core/queries.py` | `execute_sql()` — send SQL to Metabase `/api/dataset`, return structured result |
| `core/database.py` | List databases, tables, fields, get table metadata |
| `core/cards.py` | List cards, run card by ID/name |
| `core/dashboards.py` | List dashboards, show dashboard, run all cards in dashboard |
| `core/search.py` | Search Metabase content |
| `core/schema_cache.py` | Pull schema from Metabase API, cache to `~/.config/mbquery/schema_cache/`, TTL-based refresh |
| `formatters/__init__.py` | `format_result()` dispatcher — picks formatter based on `--format` flag |
| `formatters/table.py` | Rich table output |
| `formatters/csv_fmt.py` | CSV output |
| `formatters/json_fmt.py` | JSON and JSONL output |
| `formatters/markdown.py` | Markdown table output |
| `formatters/redact.py` | PII redaction logic |
| `ai/base.py` | `LLMProvider` ABC with `generate_sql()` |
| `ai/openai_compat.py` | OpenAI-compatible provider (covers OpenAI, Ollama, Anthropic, vLLM) |
| `ai/gemini.py` | Google Gemini provider |
| `ai/prompt.py` | Build NL→SQL prompt from schema + hints + query |
| `cli/app.py` | Root Typer app, `main()`, global flags callback |
| `cli/query.py` | `mbquery query` command |
| `cli/ask.py` | `mbquery ask` command |
| `cli/schema.py` | `mbquery schema` command group |
| `cli/card.py` | `mbquery card` command group |
| `cli/dashboard.py` | `mbquery dashboard` command group |
| `cli/search.py` | `mbquery search` command |
| `cli/config_cmd.py` | `mbquery config` command group (init wizard, add, list, switch, set-llm, set-hints) |
| `cli/serve.py` | `mbquery serve` command |
| `mcp/server.py` | MCP server with 10 tools |
| `utils/resolve.py` | Name-or-ID resolution helper |
| `utils/tty.py` | TTY detection for auto-format |

### Top-Level Files

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Build config, deps, entry point, optional deps |
| `README.md` | Usage docs with examples |
| `LICENSE` | MIT license |
| `tests/conftest.py` | Shared fixtures (mock Metabase responses, tmp config dir) |

---

## Task 1: Project Scaffold + pyproject.toml + Config Models

**Files:**
- Create: `pyproject.toml`
- Create: `src/mbquery/__init__.py`
- Create: `src/mbquery/config/models.py`
- Create: `src/mbquery/config/__init__.py`
- Create: `LICENSE`
- Test: `tests/test_config_models.py`
- Test: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mbquery"
version = "0.1.0"
description = "The ultimate Metabase CLI — SQL, natural language queries, and MCP server"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Shubham Attri", email = "shubhamattri@outlook.com" },
]
keywords = ["metabase", "cli", "sql", "natural-language", "mcp"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Database",
]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "httpx>=0.25.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
mcp = ["mcp>=1.0.0"]
all = ["mbquery[mcp]"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.4", "respx>=0.21"]

[project.scripts]
mbquery = "mbquery.cli.app:main"

[project.urls]
Homepage = "https://github.com/shubhamattri/mbquery"
Repository = "https://github.com/shubhamattri/mbquery"
Issues = "https://github.com/shubhamattri/mbquery/issues"

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create LICENSE**

```
MIT License

Copyright (c) 2026 Shubham Attri

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Create `src/mbquery/__init__.py`**

```python
"""mbquery — The ultimate Metabase CLI."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Create `src/mbquery/config/__init__.py`**

```python
from mbquery.config.models import AppConfig, Defaults, LLMConfig, Profile, AuthConfig
from mbquery.config.store import ConfigStore

__all__ = ["AppConfig", "Defaults", "LLMConfig", "Profile", "AuthConfig", "ConfigStore"]
```

- [ ] **Step 5: Write failing test for config models**

Create `tests/conftest.py`:

```python
import os
import pytest
from pathlib import Path


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory for tests."""
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_profile() -> dict:
    return {
        "url": "https://metabase.example.com",
        "auth": {"method": "api-key", "api_key": "mb_test123"},
        "default_db": 2,
    }
```

Create `tests/test_config_models.py`:

```python
from mbquery.config.models import AppConfig, Defaults, LLMConfig, Profile, AuthConfig


def test_profile_from_dict(sample_profile):
    profile = Profile.from_dict("prod", sample_profile)
    assert profile.name == "prod"
    assert profile.url == "https://metabase.example.com"
    assert profile.auth.method == "api-key"
    assert profile.auth.api_key == "mb_test123"
    assert profile.default_db == 2


def test_profile_to_dict(sample_profile):
    profile = Profile.from_dict("prod", sample_profile)
    d = profile.to_dict()
    assert d["url"] == "https://metabase.example.com"
    assert d["auth"]["method"] == "api-key"
    assert d["auth"]["api_key"] == "mb_test123"
    assert d["default_db"] == 2


def test_profile_session_auth():
    profile = Profile.from_dict("dev", {
        "url": "https://dev.metabase.com",
        "auth": {"method": "session", "email": "a@b.com", "password": "secret"},
    })
    assert profile.auth.method == "session"
    assert profile.auth.email == "a@b.com"
    assert profile.auth.password == "secret"
    assert profile.default_db is None


def test_llm_config_from_dict():
    llm = LLMConfig.from_dict({
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "api_key": "AIza_test",
        "base_url": None,
    })
    assert llm.provider == "gemini"
    assert llm.model == "gemini-2.0-flash"
    assert llm.api_key == "AIza_test"
    assert llm.base_url is None


def test_llm_config_to_dict():
    llm = LLMConfig(provider="openai", model="gpt-4o", api_key="sk-test", base_url=None)
    d = llm.to_dict()
    assert d == {"provider": "openai", "model": "gpt-4o", "api_key": "sk-test", "base_url": None}


def test_defaults():
    d = Defaults()
    assert d.format == "table"
    assert d.limit == 100
    assert d.redact_pii is True


def test_app_config_empty():
    config = AppConfig.empty()
    assert config.active_profile is None
    assert config.profiles == {}
    assert config.llm is None
    assert config.defaults.format == "table"


def test_app_config_roundtrip():
    config = AppConfig.empty()
    config.active_profile = "prod"
    config.profiles["prod"] = Profile.from_dict("prod", {
        "url": "https://metabase.example.com",
        "auth": {"method": "api-key", "api_key": "mb_xxx"},
        "default_db": 2,
    })
    config.llm = LLMConfig(provider="gemini", model="gemini-2.0-flash", api_key="AIza", base_url=None)

    d = config.to_dict()
    restored = AppConfig.from_dict(d)

    assert restored.active_profile == "prod"
    assert restored.profiles["prod"].url == "https://metabase.example.com"
    assert restored.llm.provider == "gemini"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pip install -e ".[dev]" && pytest tests/test_config_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mbquery.config.models'`

- [ ] **Step 7: Implement config models**

Create `src/mbquery/config/models.py`:

```python
"""Configuration dataclasses for mbquery."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuthConfig:
    method: str  # "api-key" or "session"
    api_key: str | None = None
    email: str | None = None
    password: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> AuthConfig:
        return cls(
            method=data["method"],
            api_key=data.get("api_key"),
            email=data.get("email"),
            password=data.get("password"),
        )

    def to_dict(self) -> dict:
        d: dict = {"method": self.method}
        if self.method == "api-key":
            d["api_key"] = self.api_key
        elif self.method == "session":
            d["email"] = self.email
            d["password"] = self.password
        return d


@dataclass
class Profile:
    name: str
    url: str
    auth: AuthConfig
    default_db: int | None = None

    @classmethod
    def from_dict(cls, name: str, data: dict) -> Profile:
        return cls(
            name=name,
            url=data["url"],
            auth=AuthConfig.from_dict(data["auth"]),
            default_db=data.get("default_db"),
        )

    def to_dict(self) -> dict:
        d: dict = {"url": self.url, "auth": self.auth.to_dict()}
        if self.default_db is not None:
            d["default_db"] = self.default_db
        return d


@dataclass
class LLMConfig:
    provider: str  # "openai", "gemini"
    model: str
    api_key: str | None = None
    base_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> LLMConfig:
        return cls(
            provider=data["provider"],
            model=data["model"],
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
        )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
        }


@dataclass
class Defaults:
    format: str = "table"
    limit: int = 100
    redact_pii: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> Defaults:
        return cls(
            format=data.get("format", "table"),
            limit=data.get("limit", 100),
            redact_pii=data.get("redact_pii", True),
        )

    def to_dict(self) -> dict:
        return {"format": self.format, "limit": self.limit, "redact_pii": self.redact_pii}


@dataclass
class AppConfig:
    active_profile: str | None = None
    profiles: dict[str, Profile] = field(default_factory=dict)
    llm: LLMConfig | None = None
    defaults: Defaults = field(default_factory=Defaults)

    @classmethod
    def empty(cls) -> AppConfig:
        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        profiles = {}
        for name, pdata in data.get("profiles", {}).items():
            profiles[name] = Profile.from_dict(name, pdata)

        llm = None
        if data.get("llm"):
            llm = LLMConfig.from_dict(data["llm"])

        defaults = Defaults.from_dict(data.get("defaults", {}))

        return cls(
            active_profile=data.get("active_profile"),
            profiles=profiles,
            llm=llm,
            defaults=defaults,
        )

    def to_dict(self) -> dict:
        return {
            "active_profile": self.active_profile,
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
            "llm": self.llm.to_dict() if self.llm else None,
            "defaults": self.defaults.to_dict(),
        }
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_config_models.py -v`
Expected: All 8 tests PASS

- [ ] **Step 9: Commit**

```bash
cd ~/Dev/mbquery && git init && git add pyproject.toml LICENSE src/ tests/
git commit -m "feat: project scaffold with config models and tests"
```

---

## Task 2: Config Store (Load/Save/CRUD Profiles)

**Files:**
- Create: `src/mbquery/config/store.py`
- Test: `tests/test_config_store.py`

- [ ] **Step 1: Write failing tests for config store**

Create `tests/test_config_store.py`:

```python
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

    # Verify file permissions
    config_file = tmp_config_dir / "config.yaml"
    assert config_file.exists()
    assert oct(config_file.stat().st_mode & 0o777) == "0o600"

    # Reload and verify
    loaded = store.load()
    assert loaded.active_profile == "prod"
    assert loaded.profiles["prod"].url == "https://metabase.example.com"
    assert loaded.profiles["prod"].auth.api_key == "mb_test"


def test_store_add_profile(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(
        name="staging",
        url="https://staging.metabase.com",
        auth_method="session",
        email="test@test.com",
        password="secret",
    )
    config = store.load()
    assert "staging" in config.profiles
    assert config.active_profile == "staging"  # first profile becomes active


def test_store_add_second_profile_does_not_switch(tmp_config_dir: Path):
    store = ConfigStore(tmp_config_dir)
    store.add_profile(name="prod", url="https://prod.mb.com", auth_method="api-key", api_key="mb_1")
    store.add_profile(name="dev", url="https://dev.mb.com", auth_method="api-key", api_key="mb_2")
    config = store.load()
    assert config.active_profile == "prod"  # still first one


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_config_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mbquery.config.store'`

- [ ] **Step 3: Implement config store**

Create `src/mbquery/config/store.py`:

```python
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

    def add_profile(
        self,
        name: str,
        url: str,
        auth_method: str,
        api_key: str | None = None,
        email: str | None = None,
        password: str | None = None,
        default_db: int | None = None,
    ) -> Profile:
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

    def set_llm(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_config_store.py -v`
Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/config/store.py tests/test_config_store.py
git commit -m "feat: config store with profile CRUD and env var override"
```

---

## Task 3: HTTP Client + SQL Query Execution

**Files:**
- Create: `src/mbquery/core/__init__.py`
- Create: `src/mbquery/core/client.py`
- Create: `src/mbquery/core/queries.py`
- Test: `tests/test_client.py`
- Test: `tests/test_queries.py`

- [ ] **Step 1: Write failing tests for HTTP client**

Create `tests/test_client.py`:

```python
import httpx
import pytest
import respx
from mbquery.core.client import MetabaseClient
from mbquery.config.models import Profile, AuthConfig


@pytest.fixture
def api_key_profile() -> Profile:
    return Profile(
        name="test",
        url="https://metabase.test.com",
        auth=AuthConfig(method="api-key", api_key="mb_testkey"),
        default_db=2,
    )


@respx.mock
def test_client_get_with_api_key(api_key_profile):
    route = respx.get("https://metabase.test.com/api/user/current").respond(
        json={"id": 1, "email": "test@test.com", "first_name": "Test", "last_name": "User"}
    )
    client = MetabaseClient(api_key_profile)
    result = client.get("/api/user/current")
    assert result["email"] == "test@test.com"
    assert route.called
    assert route.calls[0].request.headers["x-api-key"] == "mb_testkey"


@respx.mock
def test_client_post(api_key_profile):
    respx.post("https://metabase.test.com/api/dataset").respond(
        json={"data": {"rows": [[42]], "cols": [{"name": "count"}]}}
    )
    client = MetabaseClient(api_key_profile)
    result = client.post("/api/dataset", json={"database": 2, "type": "native", "native": {"query": "SELECT 1"}})
    assert result["data"]["rows"] == [[42]]


@respx.mock
def test_client_raises_on_http_error(api_key_profile):
    respx.get("https://metabase.test.com/api/database").respond(status_code=401, json={"message": "Unauthorized"})
    client = MetabaseClient(api_key_profile)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("/api/database")


@respx.mock
def test_client_session_auth():
    profile = Profile(
        name="test",
        url="https://metabase.test.com",
        auth=AuthConfig(method="session", email="a@b.com", password="pass"),
    )
    respx.post("https://metabase.test.com/api/session").respond(json={"id": "sess_token_123"})
    respx.get("https://metabase.test.com/api/user/current").respond(
        json={"id": 1, "email": "a@b.com", "first_name": "A", "last_name": "B"}
    )
    client = MetabaseClient(profile)
    result = client.get("/api/user/current")
    assert result["email"] == "a@b.com"
    # Check session header was sent
    req = respx.calls[-1].request
    assert req.headers["x-metabase-session"] == "sess_token_123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mbquery.core.client'`

- [ ] **Step 3: Implement HTTP client**

Create `src/mbquery/core/__init__.py`:

```python
```

Create `src/mbquery/core/client.py`:

```python
"""HTTP client for Metabase API."""

from __future__ import annotations

import httpx

from mbquery.config.models import Profile


class MetabaseClient:
    def __init__(self, profile: Profile, verbose: bool = False):
        self.profile = profile
        self.verbose = verbose
        self._base_url = profile.url
        self._session_token: str | None = None
        self._http = httpx.Client(timeout=30.0)

        if profile.auth.method == "session":
            self._authenticate()

    def _authenticate(self) -> None:
        resp = self._http.post(
            f"{self._base_url}/api/session",
            json={"username": self.profile.auth.email, "password": self.profile.auth.password},
        )
        resp.raise_for_status()
        self._session_token = resp.json()["id"]

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.profile.auth.method == "api-key":
            headers["x-api-key"] = self.profile.auth.api_key or ""
        elif self._session_token:
            headers["x-metabase-session"] = self._session_token
        return headers

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self._base_url}{endpoint}"
        if self.verbose:
            import sys
            print(f"GET {url}", file=sys.stderr)
        resp = self._http.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, endpoint: str, json: dict | None = None) -> dict:
        url = f"{self._base_url}{endpoint}"
        if self.verbose:
            import sys
            print(f"POST {url}", file=sys.stderr)
        resp = self._http.post(url, headers=self._headers(), json=json)
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._http.close()

    def test_connection(self) -> dict:
        """Test connection by fetching current user. Returns user info dict."""
        return self.get("/api/user/current")
```

- [ ] **Step 4: Run client tests**

Run: `cd ~/Dev/mbquery && pytest tests/test_client.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Write failing tests for query execution**

Create `tests/test_queries.py`:

```python
import pytest
import respx
from mbquery.core.queries import execute_sql, QueryResult
from mbquery.core.client import MetabaseClient
from mbquery.config.models import Profile, AuthConfig


@pytest.fixture
def client():
    profile = Profile(
        name="test",
        url="https://metabase.test.com",
        auth=AuthConfig(method="api-key", api_key="mb_testkey"),
        default_db=2,
    )
    return MetabaseClient(profile)


@respx.mock
def test_execute_sql_returns_query_result(client):
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[100], [200]],
            "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}],
        },
        "row_count": 2,
    })
    result = execute_sql(client, "SELECT COUNT(*) FROM users", database_id=2)
    assert isinstance(result, QueryResult)
    assert result.columns == [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]
    assert result.rows == [[100], [200]]
    assert result.row_count == 2


@respx.mock
def test_execute_sql_with_limit(client):
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1]],
            "cols": [{"name": "id", "base_type": "type/Integer", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = execute_sql(client, "SELECT id FROM users", database_id=2, limit=10)
    # Verify the SQL was wrapped with LIMIT
    call_body = respx.calls[0].request.read()
    import json
    body = json.loads(call_body)
    assert "LIMIT 10" in body["native"]["query"]


@respx.mock
def test_execute_sql_error(client):
    respx.post("https://metabase.test.com/api/dataset").respond(status_code=400, json={
        "message": "Syntax error in SQL query"
    })
    with pytest.raises(Exception):
        execute_sql(client, "SELECTT bad", database_id=2)


def test_query_result_column_names():
    result = QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
        ],
        rows=[[1, "Alice"], [2, "Bob"]],
        row_count=2,
    )
    assert result.column_names == ["id", "name"]


def test_query_result_filter_fields():
    result = QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ],
        rows=[[1, "Alice", "a@b.com"], [2, "Bob", "b@c.com"]],
        row_count=2,
    )
    filtered = result.filter_fields(["id", "email"])
    assert filtered.column_names == ["id", "email"]
    assert filtered.rows == [[1, "a@b.com"], [2, "b@c.com"]]
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_queries.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mbquery.core.queries'`

- [ ] **Step 7: Implement query execution**

Create `src/mbquery/core/queries.py`:

```python
"""SQL query execution against Metabase."""

from __future__ import annotations

import re
from dataclasses import dataclass

from mbquery.core.client import MetabaseClient

# SQL keywords that indicate a write operation
WRITE_KEYWORDS = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


@dataclass
class QueryResult:
    columns: list[dict]
    rows: list[list]
    row_count: int

    @property
    def column_names(self) -> list[str]:
        return [c["name"] for c in self.columns]

    def filter_fields(self, fields: list[str]) -> QueryResult:
        """Return a new QueryResult with only the specified columns."""
        indices = []
        new_cols = []
        for i, col in enumerate(self.columns):
            if col["name"] in fields:
                indices.append(i)
                new_cols.append(col)
        new_rows = [[row[i] for i in indices] for row in self.rows]
        return QueryResult(columns=new_cols, rows=new_rows, row_count=self.row_count)


def is_write_query(sql: str) -> bool:
    """Check if SQL is a write operation."""
    return bool(WRITE_KEYWORDS.match(sql.strip()))


def execute_sql(
    client: MetabaseClient,
    sql: str,
    database_id: int,
    limit: int | None = None,
    block_writes: bool = False,
) -> QueryResult:
    """Execute SQL query via Metabase API and return structured result."""
    if block_writes and is_write_query(sql):
        raise ValueError(f"Write queries are blocked. Query starts with: {sql.strip()[:30]}...")

    query = sql.strip().rstrip(";")
    if limit and not re.search(r"\bLIMIT\s+\d+", query, re.IGNORECASE):
        query = f"SELECT * FROM ({query}) _q LIMIT {limit}"

    payload = {
        "database": database_id,
        "type": "native",
        "native": {"query": query},
    }

    response = client.post("/api/dataset", json=payload)

    data = response.get("data", {})
    rows = data.get("rows", [])
    cols = data.get("cols", [])
    columns = [
        {
            "name": c.get("name", f"col_{i}"),
            "base_type": c.get("base_type"),
            "semantic_type": c.get("semantic_type"),
        }
        for i, c in enumerate(cols)
    ]

    return QueryResult(
        columns=columns,
        rows=rows,
        row_count=response.get("row_count", len(rows)),
    )
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_queries.py -v`
Expected: All 5 tests PASS

- [ ] **Step 9: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/core/ tests/test_client.py tests/test_queries.py
git commit -m "feat: HTTP client and SQL query execution"
```

---

## Task 4: Output Formatters (All 6 Formats)

**Files:**
- Create: `src/mbquery/formatters/__init__.py`
- Create: `src/mbquery/formatters/table.py`
- Create: `src/mbquery/formatters/csv_fmt.py`
- Create: `src/mbquery/formatters/json_fmt.py`
- Create: `src/mbquery/formatters/markdown.py`
- Create: `src/mbquery/utils/__init__.py`
- Create: `src/mbquery/utils/tty.py`
- Test: `tests/test_formatters.py`

- [ ] **Step 1: Write failing tests for all formatters**

Create `tests/test_formatters.py`:

```python
import json
from mbquery.core.queries import QueryResult
from mbquery.formatters import format_result
from mbquery.formatters.table import format_table
from mbquery.formatters.csv_fmt import format_csv
from mbquery.formatters.json_fmt import format_json, format_jsonl
from mbquery.formatters.markdown import format_markdown


@pytest.fixture
def sample_result():
    return QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": None},
            {"name": "count", "base_type": "type/Integer", "semantic_type": None},
        ],
        rows=[[1, "Alice", 100], [2, "Bob", 200]],
        row_count=2,
    )


import pytest


def test_format_table(sample_result):
    output = format_table(sample_result)
    assert "id" in output
    assert "Alice" in output
    assert "Bob" in output


def test_format_csv(sample_result):
    output = format_csv(sample_result)
    lines = output.strip().split("\n")
    assert lines[0] == "id,name,count"
    assert lines[1] == "1,Alice,100"
    assert lines[2] == "2,Bob,200"


def test_format_json(sample_result):
    output = format_json(sample_result)
    data = json.loads(output)
    assert len(data) == 2
    assert data[0] == {"id": 1, "name": "Alice", "count": 100}
    assert data[1] == {"id": 2, "name": "Bob", "count": 200}


def test_format_jsonl(sample_result):
    output = format_jsonl(sample_result)
    lines = output.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1, "name": "Alice", "count": 100}
    assert json.loads(lines[1]) == {"id": 2, "name": "Bob", "count": 200}


def test_format_markdown(sample_result):
    output = format_markdown(sample_result)
    lines = output.strip().split("\n")
    assert "| id | name | count |" in lines[0]
    assert lines[1].startswith("| --")
    assert "| 1 | Alice | 100 |" in lines[2]


def test_format_result_dispatch(sample_result):
    csv_output = format_result(sample_result, fmt="csv")
    assert "id,name,count" in csv_output

    json_output = format_result(sample_result, fmt="json")
    data = json.loads(json_output)
    assert len(data) == 2


def test_format_result_invalid():
    result = QueryResult(columns=[], rows=[], row_count=0)
    with pytest.raises(ValueError, match="Unknown format"):
        format_result(result, fmt="xml")


def test_format_empty_result():
    result = QueryResult(
        columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}],
        rows=[],
        row_count=0,
    )
    csv_out = format_csv(result)
    assert csv_out.strip() == "id"

    json_out = format_json(result)
    assert json.loads(json_out) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_formatters.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement all formatters**

Create `src/mbquery/utils/__init__.py`:

```python
```

Create `src/mbquery/utils/tty.py`:

```python
"""TTY detection for auto-format selection."""

import sys


def is_tty() -> bool:
    """Return True if stdout is a terminal (not piped)."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def auto_format() -> str:
    """Return default format based on TTY detection."""
    return "table" if is_tty() else "json"
```

Create `src/mbquery/formatters/__init__.py`:

```python
"""Output formatting for query results."""

from mbquery.core.queries import QueryResult
from mbquery.formatters.table import format_table
from mbquery.formatters.csv_fmt import format_csv
from mbquery.formatters.json_fmt import format_json, format_jsonl
from mbquery.formatters.markdown import format_markdown

FORMATS = {
    "table": format_table,
    "csv": format_csv,
    "json": format_json,
    "jsonl": format_jsonl,
    "markdown": format_markdown,
}


def format_result(result: QueryResult, fmt: str) -> str:
    """Format a QueryResult using the specified format."""
    formatter = FORMATS.get(fmt)
    if not formatter:
        raise ValueError(f"Unknown format: '{fmt}'. Valid: {', '.join(FORMATS.keys())}")
    return formatter(result)
```

Create `src/mbquery/formatters/table.py`:

```python
"""Rich table formatter."""

from io import StringIO
from rich.console import Console
from rich.table import Table

from mbquery.core.queries import QueryResult


def format_table(result: QueryResult) -> str:
    """Format QueryResult as a rich table."""
    table = Table(show_header=True, header_style="bold cyan")
    for col in result.columns:
        table.add_column(col["name"])
    for row in result.rows:
        table.add_row(*[str(v) if v is not None else "NULL" for v in row])

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    console.print(table)
    return buf.getvalue()
```

Create `src/mbquery/formatters/csv_fmt.py`:

```python
"""CSV formatter."""

import csv
from io import StringIO

from mbquery.core.queries import QueryResult


def format_csv(result: QueryResult) -> str:
    """Format QueryResult as CSV."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(result.column_names)
    for row in result.rows:
        writer.writerow(row)
    return buf.getvalue()
```

Create `src/mbquery/formatters/json_fmt.py`:

```python
"""JSON and JSONL formatters."""

import json

from mbquery.core.queries import QueryResult


def format_json(result: QueryResult) -> str:
    """Format QueryResult as a JSON array of objects."""
    rows = []
    for row in result.rows:
        obj = {}
        for i, col in enumerate(result.columns):
            obj[col["name"]] = row[i]
        rows.append(obj)
    return json.dumps(rows, indent=2, default=str)


def format_jsonl(result: QueryResult) -> str:
    """Format QueryResult as JSON Lines (one JSON object per line)."""
    lines = []
    for row in result.rows:
        obj = {}
        for i, col in enumerate(result.columns):
            obj[col["name"]] = row[i]
        lines.append(json.dumps(obj, default=str))
    return "\n".join(lines)
```

Create `src/mbquery/formatters/markdown.py`:

```python
"""Markdown table formatter."""

from mbquery.core.queries import QueryResult


def format_markdown(result: QueryResult) -> str:
    """Format QueryResult as a markdown table."""
    if not result.columns:
        return ""
    names = result.column_names
    lines = []
    lines.append("| " + " | ".join(names) + " |")
    lines.append("| " + " | ".join("---" for _ in names) + " |")
    for row in result.rows:
        cells = [str(v) if v is not None else "NULL" for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_formatters.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/formatters/ src/mbquery/utils/ tests/test_formatters.py
git commit -m "feat: output formatters — table, csv, json, jsonl, markdown"
```

---

## Task 5: PII Redaction

**Files:**
- Create: `src/mbquery/formatters/redact.py`
- Test: `tests/test_redaction.py`

- [ ] **Step 1: Write failing tests for PII redaction**

Create `tests/test_redaction.py`:

```python
from mbquery.core.queries import QueryResult
from mbquery.formatters.redact import redact_pii, PII_SEMANTIC_TYPES


def test_pii_types_list():
    assert "type/Email" in PII_SEMANTIC_TYPES
    assert "type/Name" in PII_SEMANTIC_TYPES
    assert "type/Phone" in PII_SEMANTIC_TYPES
    assert "type/Integer" not in PII_SEMANTIC_TYPES


def test_redact_pii_masks_email_and_name():
    result = QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ],
        rows=[[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]],
        row_count=2,
    )
    redacted = redact_pii(result)
    assert redacted.rows[0][0] == 1  # id not redacted
    assert redacted.rows[0][1] == "[REDACTED]"
    assert redacted.rows[0][2] == "[REDACTED]"
    assert redacted.rows[1][1] == "[REDACTED]"


def test_redact_pii_no_pii_columns():
    result = QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "count", "base_type": "type/Integer", "semantic_type": None},
        ],
        rows=[[1, 100], [2, 200]],
        row_count=2,
    )
    redacted = redact_pii(result)
    assert redacted.rows == [[1, 100], [2, 200]]  # unchanged


def test_redact_pii_preserves_original():
    """Redaction returns a new result, does not mutate the original."""
    result = QueryResult(
        columns=[
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ],
        rows=[["alice@example.com"]],
        row_count=1,
    )
    redacted = redact_pii(result)
    assert result.rows[0][0] == "alice@example.com"  # original untouched
    assert redacted.rows[0][0] == "[REDACTED]"


def test_redact_pii_all_types():
    """Every PII type gets redacted."""
    columns = [
        {"name": f"col_{st.split('/')[-1]}", "base_type": "type/Text", "semantic_type": st}
        for st in PII_SEMANTIC_TYPES
    ]
    rows = [[f"value_{i}" for i in range(len(columns))]]
    result = QueryResult(columns=columns, rows=rows, row_count=1)
    redacted = redact_pii(result)
    for val in redacted.rows[0]:
        assert val == "[REDACTED]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_redaction.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement PII redaction**

Create `src/mbquery/formatters/redact.py`:

```python
"""PII redaction for query results."""

from __future__ import annotations

from mbquery.core.queries import QueryResult

PII_SEMANTIC_TYPES = frozenset({
    "type/Email",
    "type/Name",
    "type/Phone",
    "type/Address",
    "type/City",
    "type/State",
    "type/ZipCode",
    "type/Country",
    "type/Latitude",
    "type/Longitude",
    "type/Birthdate",
    "type/AvatarURL",
})

REDACTED = "[REDACTED]"


def redact_pii(result: QueryResult) -> QueryResult:
    """Return a new QueryResult with PII columns masked.

    Does not mutate the original result.
    """
    pii_indices = {
        i
        for i, col in enumerate(result.columns)
        if col.get("semantic_type") in PII_SEMANTIC_TYPES
    }

    if not pii_indices:
        return result

    new_rows = []
    for row in result.rows:
        new_row = [
            REDACTED if i in pii_indices else val
            for i, val in enumerate(row)
        ]
        new_rows.append(new_row)

    return QueryResult(
        columns=result.columns,
        rows=new_rows,
        row_count=result.row_count,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_redaction.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/formatters/redact.py tests/test_redaction.py
git commit -m "feat: PII redaction with semantic type detection"
```

---

## Task 6: CLI App Shell + `mbquery query` Command

**Files:**
- Create: `src/mbquery/cli/__init__.py`
- Create: `src/mbquery/cli/app.py`
- Create: `src/mbquery/cli/query.py`
- Test: `tests/test_cli_query.py`

- [ ] **Step 1: Write failing tests for CLI query command**

Create `tests/test_cli_query.py`:

```python
import json
import pytest
import respx
from typer.testing import CliRunner
from mbquery.cli.app import app
from pathlib import Path


runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_config(tmp_path, monkeypatch):
    """Set up a temp config with a test profile for all CLI tests."""
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    (config_dir / "schema_cache").mkdir()
    import yaml
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
        "data": {
            "rows": [[42]],
            "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "SELECT COUNT(*) FROM users"])
    assert result.exit_code == 0
    assert "42" in result.output


@respx.mock
def test_query_command_json_format():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1, "Alice"], [2, "Bob"]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
            ],
        },
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
        "data": {
            "rows": [[1, "Alice"]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
            ],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "csv", "SELECT * FROM users"])
    assert result.exit_code == 0
    assert "id,name" in result.output
    assert "1,Alice" in result.output


@respx.mock
def test_query_command_with_pii_redaction():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1, "alice@test.com"]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
            ],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "json", "SELECT * FROM users"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["email"] == "[REDACTED]"


@respx.mock
def test_query_command_no_redact_flag():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1, "alice@test.com"]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
            ],
        },
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
        "data": {
            "rows": [[1]],
            "cols": [{"name": "num", "base_type": "type/Integer", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--file", str(sql_file), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["num"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_query.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI app and query command**

Create `src/mbquery/cli/__init__.py`:

```python
```

Create `src/mbquery/cli/app.py`:

```python
"""Root CLI application."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

# Register command groups
app.command(name="query")(query_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

Create `src/mbquery/cli/query.py`:

```python
"""mbquery query — execute SQL queries."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import execute_sql
from mbquery.formatters import format_result
from mbquery.formatters.redact import redact_pii
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)


def query_cmd(
    sql: Optional[str] = typer.Argument(None, help="SQL query to execute"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read SQL from file"),
    format: Optional[str] = typer.Option(None, "--format", help="Output format: table, csv, json, jsonl, markdown"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
    db: Optional[int] = typer.Option(None, "--db", help="Database ID"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Row limit"),
    no_redact: bool = typer.Option(False, "--no-redact", help="Disable PII redaction"),
    fields: Optional[str] = typer.Option(None, "--fields", help="Comma-separated column names to include"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show HTTP requests"),
) -> None:
    """Execute a SQL query against Metabase."""
    if not sql and not file:
        err_console.print("[red]Error:[/] Provide SQL as argument or use --file")
        raise typer.Exit(1)

    if file:
        if not file.exists():
            err_console.print(f"[red]Error:[/] File not found: {file}")
            raise typer.Exit(1)
        sql = file.read_text().strip()

    assert sql is not None

    store = ConfigStore()
    try:
        active_profile = store.resolve_profile(profile)
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

    database_id = db or active_profile.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified. Use --db or set default_db in profile.")
        raise typer.Exit(1)

    config = store.load()
    row_limit = limit or config.defaults.limit
    should_redact = config.defaults.redact_pii and not no_redact
    output_format = format or auto_format()

    client = MetabaseClient(active_profile, verbose=verbose)
    try:
        result = execute_sql(client, sql, database_id=database_id, limit=row_limit)
    except Exception as e:
        err_console.print(f"[red]Error executing query:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

    if should_redact:
        result = redact_pii(result)

    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        result = result.filter_fields(field_list)

    output = format_result(result, output_format)
    typer.echo(output)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_query.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/cli/ tests/test_cli_query.py
git commit -m "feat: mbquery query command with all output formats and PII redaction"
```

---

## Task 7: Schema Discovery + Cache

**Files:**
- Create: `src/mbquery/core/database.py`
- Create: `src/mbquery/core/schema_cache.py`
- Test: `tests/test_schema_cache.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_schema_cache.py`:

```python
import json
import time
import respx
from pathlib import Path
from mbquery.core.schema_cache import SchemaCache
from mbquery.core.client import MetabaseClient
from mbquery.config.models import Profile, AuthConfig


@pytest.fixture
def client():
    return MetabaseClient(Profile(
        name="test", url="https://metabase.test.com",
        auth=AuthConfig(method="api-key", api_key="mb_testkey"), default_db=2,
    ))


@pytest.fixture
def cache_dir(tmp_path):
    d = tmp_path / "schema_cache"
    d.mkdir()
    return d


import pytest

MOCK_METADATA = {
    "id": 2,
    "name": "Production",
    "tables": [
        {
            "id": 10,
            "name": "users",
            "schema": "public",
            "fields": [
                {"id": 100, "name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"id": 101, "name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
                {"id": 102, "name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
            ],
        },
        {
            "id": 11,
            "name": "orders",
            "schema": "public",
            "fields": [
                {"id": 200, "name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"id": 201, "name": "amount", "base_type": "type/Float", "semantic_type": None},
            ],
        },
    ],
}


@respx.mock
def test_schema_cache_fetch_and_cache(client, cache_dir):
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    cache = SchemaCache(cache_dir)
    schema = cache.get_schema(client, database_id=2, profile_name="test")
    assert len(schema["tables"]) == 2
    assert schema["tables"][0]["name"] == "users"
    # Verify it was cached to disk
    cache_file = cache_dir / "test_2.json"
    assert cache_file.exists()


@respx.mock
def test_schema_cache_uses_disk_cache(client, cache_dir):
    # Pre-populate cache
    cache_file = cache_dir / "test_2.json"
    cached = {"database_id": 2, "tables": [{"name": "cached_table", "fields": []}], "cached_at": time.time()}
    cache_file.write_text(json.dumps(cached))

    cache = SchemaCache(cache_dir)
    schema = cache.get_schema(client, database_id=2, profile_name="test")
    # Should use cache, NOT make HTTP call
    assert len(respx.calls) == 0
    assert schema["tables"][0]["name"] == "cached_table"


@respx.mock
def test_schema_cache_refresh_bypasses_cache(client, cache_dir):
    # Pre-populate stale cache
    cache_file = cache_dir / "test_2.json"
    cached = {"database_id": 2, "tables": [{"name": "stale"}], "cached_at": time.time()}
    cache_file.write_text(json.dumps(cached))

    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)

    cache = SchemaCache(cache_dir)
    schema = cache.get_schema(client, database_id=2, profile_name="test", force_refresh=True)
    assert schema["tables"][0]["name"] == "users"
    assert len(respx.calls) == 1


@respx.mock
def test_schema_cache_expired_ttl(client, cache_dir):
    # Cache with old timestamp
    cache_file = cache_dir / "test_2.json"
    cached = {"database_id": 2, "tables": [{"name": "old"}], "cached_at": time.time() - 100000}
    cache_file.write_text(json.dumps(cached))

    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)

    cache = SchemaCache(cache_dir, ttl_seconds=3600)
    schema = cache.get_schema(client, database_id=2, profile_name="test")
    assert schema["tables"][0]["name"] == "users"  # fetched fresh


def test_schema_to_prompt_context(cache_dir):
    cache = SchemaCache(cache_dir)
    schema = {
        "database_id": 2,
        "tables": [
            {
                "name": "users",
                "fields": [
                    {"name": "id", "base_type": "type/Integer"},
                    {"name": "email", "base_type": "type/Text"},
                ],
            },
        ],
    }
    prompt = cache.schema_to_prompt_context(schema)
    assert "users" in prompt
    assert "id" in prompt
    assert "email" in prompt
    assert "type/Integer" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_schema_cache.py -v`
Expected: FAIL

- [ ] **Step 3: Implement schema cache**

Create `src/mbquery/core/database.py`:

```python
"""Database, table, and field operations."""

from __future__ import annotations

from mbquery.core.client import MetabaseClient


def list_databases(client: MetabaseClient) -> list[dict]:
    """List all databases."""
    resp = client.get("/api/database")
    return resp.get("data", resp) if isinstance(resp, dict) else resp


def get_database_metadata(client: MetabaseClient, database_id: int) -> dict:
    """Get full metadata for a database (tables + fields)."""
    return client.get(f"/api/database/{database_id}", params={"include": "tables.fields"})


def list_tables(client: MetabaseClient, database_id: int) -> list[dict]:
    """List tables in a database."""
    metadata = get_database_metadata(client, database_id)
    return metadata.get("tables", [])


def get_table_fields(client: MetabaseClient, table_id: int) -> list[dict]:
    """Get fields for a table."""
    metadata = client.get(f"/api/table/{table_id}/query_metadata")
    return metadata.get("fields", [])
```

Create `src/mbquery/core/schema_cache.py`:

```python
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

    def get_schema(
        self,
        client: MetabaseClient,
        database_id: int,
        profile_name: str,
        force_refresh: bool = False,
    ) -> dict:
        """Get schema for a database. Uses cache unless expired or force_refresh."""
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
                        {
                            "name": f["name"],
                            "base_type": f.get("base_type"),
                            "semantic_type": f.get("semantic_type"),
                        }
                        for f in t.get("fields", [])
                    ],
                }
                for t in raw.get("tables", [])
            ],
        }
        self._write_cache(profile_name, database_id, schema)
        return schema

    def schema_to_prompt_context(self, schema: dict) -> str:
        """Convert schema dict to a text context for NL→SQL prompts."""
        lines = ["Database schema:"]
        for table in schema.get("tables", []):
            fields_str = ", ".join(
                f"{f['name']} ({f.get('base_type', 'unknown')})"
                for f in table.get("fields", [])
            )
            lines.append(f"  Table: {table['name']} — columns: {fields_str}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_schema_cache.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/core/database.py src/mbquery/core/schema_cache.py tests/test_schema_cache.py
git commit -m "feat: schema auto-discovery with disk cache and TTL"
```

---

## Task 8: AI Layer — LLM Provider Interface + Gemini + OpenAI-Compatible

**Files:**
- Create: `src/mbquery/ai/__init__.py`
- Create: `src/mbquery/ai/base.py`
- Create: `src/mbquery/ai/prompt.py`
- Create: `src/mbquery/ai/openai_compat.py`
- Create: `src/mbquery/ai/gemini.py`
- Test: `tests/test_ai.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ai.py`:

```python
import json
import pytest
import respx
import httpx
from mbquery.ai.base import LLMProvider
from mbquery.ai.prompt import build_nl_to_sql_prompt
from mbquery.ai.openai_compat import OpenAICompatProvider
from mbquery.ai.gemini import GeminiProvider


def test_build_prompt_basic():
    schema_context = "Table: users — columns: id (type/Integer), name (type/Text)"
    prompt = build_nl_to_sql_prompt("count all users", schema_context)
    assert "count all users" in prompt
    assert "users" in prompt
    assert "SELECT" in prompt  # instruction to return SQL


def test_build_prompt_with_hints():
    schema_context = "Table: orders — columns: id, status"
    hints = "status values are 'pending', 'completed', 'refunded'"
    prompt = build_nl_to_sql_prompt("count completed orders", schema_context, hints=hints)
    assert "pending" in prompt
    assert "completed" in prompt


@respx.mock
def test_openai_compat_generate_sql():
    respx.post("https://api.openai.com/v1/chat/completions").respond(json={
        "choices": [{"message": {"content": "SELECT COUNT(*) FROM users"}}]
    })
    provider = OpenAICompatProvider(
        api_key="sk-test",
        model="gpt-4o",
        base_url="https://api.openai.com/v1",
    )
    sql = provider.generate_sql("count all users in the users table")
    assert "SELECT" in sql
    assert "users" in sql


@respx.mock
def test_openai_compat_strips_markdown():
    respx.post("https://api.openai.com/v1/chat/completions").respond(json={
        "choices": [{"message": {"content": "```sql\nSELECT COUNT(*) FROM users\n```"}}]
    })
    provider = OpenAICompatProvider(api_key="sk-test", model="gpt-4o", base_url="https://api.openai.com/v1")
    sql = provider.generate_sql("count users")
    assert sql.strip() == "SELECT COUNT(*) FROM users"
    assert "```" not in sql


@respx.mock
def test_gemini_generate_sql():
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={
        "candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) FROM orders"}]}}]
    })
    provider = GeminiProvider(api_key="AIza_test", model="gemini-2.0-flash")
    sql = provider.generate_sql("count all orders")
    assert "SELECT" in sql
    assert "orders" in sql


@respx.mock
def test_gemini_strips_markdown():
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={
        "candidates": [{"content": {"parts": [{"text": "```sql\nSELECT 1\n```"}]}}]
    })
    provider = GeminiProvider(api_key="AIza_test", model="gemini-2.0-flash")
    sql = provider.generate_sql("select one")
    assert sql.strip() == "SELECT 1"


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_ai.py -v`
Expected: FAIL

- [ ] **Step 3: Implement AI layer**

Create `src/mbquery/ai/__init__.py`:

```python
from mbquery.ai.base import LLMProvider
from mbquery.ai.openai_compat import OpenAICompatProvider
from mbquery.ai.gemini import GeminiProvider
from mbquery.ai.prompt import build_nl_to_sql_prompt

__all__ = ["LLMProvider", "OpenAICompatProvider", "GeminiProvider", "build_nl_to_sql_prompt"]
```

Create `src/mbquery/ai/base.py`:

```python
"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_sql(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the generated SQL string."""
        ...
```

Create `src/mbquery/ai/prompt.py`:

```python
"""NL→SQL prompt builder."""

from __future__ import annotations


def build_nl_to_sql_prompt(
    question: str,
    schema_context: str,
    hints: str | None = None,
) -> str:
    """Build a prompt that asks the LLM to convert natural language to SQL."""
    parts = [
        "You are a PostgreSQL expert. Convert the following natural language query to SQL.",
        "",
        schema_context,
    ]

    if hints:
        parts.append("")
        parts.append(f"Additional context:\n{hints}")

    parts.extend([
        "",
        f"User query: {question}",
        "",
        "CRITICAL: Return ONLY the raw SQL query. No explanations, no markdown code blocks,",
        "no comments. Start directly with SELECT, INSERT, UPDATE, DELETE, WITH, or other SQL keyword.",
    ])

    return "\n".join(parts)
```

Create `src/mbquery/ai/openai_compat.py`:

```python
"""OpenAI-compatible LLM provider (covers OpenAI, Ollama, vLLM, Anthropic, etc.)."""

from __future__ import annotations

import re

import httpx

from mbquery.ai.base import LLMProvider


def _strip_markdown_sql(text: str) -> str:
    """Remove markdown code block wrappers from SQL."""
    text = text.strip()
    match = re.match(r"^```(?:sql)?\s*\n?(.*?)```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class OpenAICompatProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=60.0)

    def generate_sql(self, prompt: str) -> str:
        resp = self._http.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a SQL expert. Return only valid SQL."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _strip_markdown_sql(content)
```

Create `src/mbquery/ai/gemini.py`:

```python
"""Google Gemini LLM provider."""

from __future__ import annotations

import re

import httpx

from mbquery.ai.base import LLMProvider


def _strip_markdown_sql(text: str) -> str:
    """Remove markdown code block wrappers from SQL."""
    text = text.strip()
    match = re.match(r"^```(?:sql)?\s*\n?(.*?)```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._http = httpx.Client(timeout=60.0)

    def generate_sql(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        resp = self._http.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _strip_markdown_sql(text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_ai.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/ai/ tests/test_ai.py
git commit -m "feat: pluggable LLM layer — OpenAI-compatible and Gemini providers"
```

---

## Task 9: `mbquery ask` Command (NL→SQL)

**Files:**
- Create: `src/mbquery/cli/ask.py`
- Modify: `src/mbquery/cli/app.py` (register ask command)
- Test: `tests/test_cli_ask.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_ask.py`:

```python
import json
import pytest
import yaml
import respx
from typer.testing import CliRunner
from mbquery.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    schema_cache_dir = config_dir / "schema_cache"
    schema_cache_dir.mkdir()
    # Write a cached schema
    import json as _json, time
    schema = {
        "database_id": 2,
        "tables": [{"name": "users", "fields": [
            {"name": "id", "base_type": "type/Integer"},
            {"name": "email", "base_type": "type/Text"},
        ]}],
        "cached_at": time.time(),
    }
    (schema_cache_dir / "test_2.json").write_text(_json.dumps(schema))
    config = {
        "active_profile": "test",
        "profiles": {
            "test": {
                "url": "https://metabase.test.com",
                "auth": {"method": "api-key", "api_key": "mb_testkey"},
                "default_db": 2,
            }
        },
        "llm": {"provider": "gemini", "model": "gemini-2.0-flash", "api_key": "AIza_test", "base_url": None},
        "defaults": {"format": "table", "limit": 100, "redact_pii": False},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


@respx.mock
def test_ask_generates_and_executes():
    # Mock Gemini to return SQL
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={
        "candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) FROM users"}]}}]
    })
    # Mock Metabase to return result
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[42]],
            "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["ask", "--format", "json", "how many users are there"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["count"] == 42


@respx.mock
def test_ask_show_sql_flag():
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={
        "candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) FROM users"}]}}]
    })
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {"rows": [[42]], "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]},
        "row_count": 1,
    })
    result = runner.invoke(app, ["ask", "--show-sql", "--format", "json", "count users"])
    assert result.exit_code == 0
    # --show-sql prints to stderr, check it doesn't break output
    data = json.loads(result.output)
    assert data[0]["count"] == 42


def test_ask_no_llm_configured(tmp_path, monkeypatch):
    config_dir = tmp_path / "mbquery2"
    config_dir.mkdir()
    (config_dir / "schema_cache").mkdir()
    config = {
        "active_profile": "test",
        "profiles": {"test": {
            "url": "https://metabase.test.com",
            "auth": {"method": "api-key", "api_key": "mb_testkey"},
            "default_db": 2,
        }},
        "defaults": {"format": "table", "limit": 100, "redact_pii": False},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ""))
    # Point to the no-LLM config
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir.parent))
    # Need a new config dir name that matches
    result = runner.invoke(app, ["ask", "count users"])
    assert result.exit_code == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_ask.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ask command**

Create `src/mbquery/cli/ask.py`:

```python
"""mbquery ask — natural language to SQL queries."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.ai.gemini import GeminiProvider
from mbquery.ai.openai_compat import OpenAICompatProvider
from mbquery.ai.prompt import build_nl_to_sql_prompt
from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import execute_sql
from mbquery.core.schema_cache import SchemaCache
from mbquery.formatters import format_result
from mbquery.formatters.redact import redact_pii
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)


def _create_llm_provider(llm_config):
    """Create the appropriate LLM provider from config."""
    if llm_config.provider == "gemini":
        return GeminiProvider(api_key=llm_config.api_key, model=llm_config.model)
    else:
        return OpenAICompatProvider(
            api_key=llm_config.api_key or "",
            model=llm_config.model,
            base_url=llm_config.base_url or "https://api.openai.com/v1",
        )


def ask_cmd(
    question: str = typer.Argument(..., help="Natural language question"),
    show_sql: bool = typer.Option(False, "--show-sql", help="Print the generated SQL before executing"),
    format: Optional[str] = typer.Option(None, "--format", help="Output format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
    db: Optional[int] = typer.Option(None, "--db", help="Database ID"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Row limit"),
    no_redact: bool = typer.Option(False, "--no-redact", help="Disable PII redaction"),
    fields: Optional[str] = typer.Option(None, "--fields", help="Comma-separated column names"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show HTTP requests"),
) -> None:
    """Ask a natural language question and get results from Metabase."""
    store = ConfigStore()
    config = store.load()

    if not config.llm:
        err_console.print("[red]Error:[/] No LLM configured. Run: mbquery config set-llm")
        raise typer.Exit(1)

    try:
        active_profile = store.resolve_profile(profile)
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

    database_id = db or active_profile.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified. Use --db or set default_db in profile.")
        raise typer.Exit(1)

    # Get schema context
    cache = SchemaCache(store.config_dir / "schema_cache")
    client = MetabaseClient(active_profile, verbose=verbose)

    try:
        schema = cache.get_schema(client, database_id=database_id, profile_name=active_profile.name)
        schema_text = cache.schema_to_prompt_context(schema)

        # Load hints if available
        hints_file = store.config_dir / "hints.yaml"
        hints = None
        if hints_file.exists():
            import yaml
            with open(hints_file) as f:
                hints_data = yaml.safe_load(f)
            if hints_data:
                hints = "\n".join(f"- {k}: {v}" for k, v in hints_data.items())

        # Build prompt and call LLM
        prompt = build_nl_to_sql_prompt(question, schema_text, hints=hints)
        provider = _create_llm_provider(config.llm)

        err_console.print("[dim]Generating SQL...[/]")
        sql = provider.generate_sql(prompt)

        if show_sql:
            err_console.print(f"\n[bold cyan]Generated SQL:[/]\n  {sql}\n")

        # Execute the generated SQL
        row_limit = limit or config.defaults.limit
        should_redact = config.defaults.redact_pii and not no_redact
        output_format = format or auto_format()

        result = execute_sql(client, sql, database_id=database_id, limit=row_limit)

        if should_redact:
            result = redact_pii(result)

        if fields:
            field_list = [f.strip() for f in fields.split(",")]
            result = result.filter_fields(field_list)

        output = format_result(result, output_format)
        typer.echo(output)

    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        err_console.print("[dim]Tip: Use 'mbquery query' with raw SQL as a fallback.[/]")
        raise typer.Exit(1)
    finally:
        client.close()
```

Update `src/mbquery/cli/app.py` — add ask command registration:

```python
"""Root CLI application."""

from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd
from mbquery.cli.ask import ask_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_ask.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/cli/ask.py src/mbquery/cli/app.py tests/test_cli_ask.py
git commit -m "feat: mbquery ask — natural language to SQL queries"
```

---

## Task 10: `mbquery schema` Command

**Files:**
- Create: `src/mbquery/cli/schema.py`
- Modify: `src/mbquery/cli/app.py` (register schema group)
- Test: `tests/test_cli_schema.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_schema.py`:

```python
import json
import time
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
    config = {
        "active_profile": "test",
        "profiles": {"test": {
            "url": "https://metabase.test.com",
            "auth": {"method": "api-key", "api_key": "mb_testkey"},
            "default_db": 2,
        }},
        "defaults": {"format": "table", "limit": 100, "redact_pii": False},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


MOCK_DB_LIST = {"data": [
    {"id": 1, "name": "Staging", "engine": "postgres"},
    {"id": 2, "name": "Production", "engine": "postgres"},
]}

MOCK_METADATA = {
    "id": 2,
    "name": "Production",
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
    assert data[0]["name"] == "users"


@respx.mock
def test_schema_fields():
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    result = runner.invoke(app, ["schema", "fields", "users", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["name"] == "id"


@respx.mock
def test_schema_refresh():
    respx.get("https://metabase.test.com/api/database/2").respond(json=MOCK_METADATA)
    result = runner.invoke(app, ["schema", "refresh"])
    assert result.exit_code == 0
    assert "Refreshed" in result.output or "refreshed" in result.output.lower() or "cached" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_schema.py -v`
Expected: FAIL

- [ ] **Step 3: Implement schema command**

Create `src/mbquery/cli/schema.py`:

```python
"""mbquery schema — browse database schema."""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console

from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.database import list_databases
from mbquery.core.queries import QueryResult
from mbquery.core.schema_cache import SchemaCache
from mbquery.formatters import format_result
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)

schema_app = typer.Typer(name="schema", help="Browse database schema.", no_args_is_help=True)


def _get_client_and_profile(profile_name: str | None = None):
    store = ConfigStore()
    active = store.resolve_profile(profile_name)
    return MetabaseClient(active), active, store


@schema_app.command()
def databases(
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """List all databases."""
    client, active, store = _get_client_and_profile(profile)
    try:
        dbs = list_databases(client)
        if isinstance(dbs, dict):
            dbs = dbs.get("data", [dbs])
        result = QueryResult(
            columns=[
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
                {"name": "engine", "base_type": "type/Text", "semantic_type": None},
            ],
            rows=[[db["id"], db["name"], db.get("engine", "")] for db in dbs],
            row_count=len(dbs),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()


@schema_app.command()
def tables(
    db: Optional[int] = typer.Option(None, "--db"),
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """List tables in a database."""
    client, active, store = _get_client_and_profile(profile)
    database_id = db or active.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    try:
        cache = SchemaCache(store.config_dir / "schema_cache")
        schema = cache.get_schema(client, database_id=database_id, profile_name=active.name)
        tbl_list = schema.get("tables", [])
        result = QueryResult(
            columns=[
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
                {"name": "schema", "base_type": "type/Text", "semantic_type": None},
                {"name": "fields", "base_type": "type/Integer", "semantic_type": None},
            ],
            rows=[[t["name"], t.get("schema", ""), len(t.get("fields", []))] for t in tbl_list],
            row_count=len(tbl_list),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()


@schema_app.command()
def fields(
    table_name: str = typer.Argument(..., help="Table name"),
    db: Optional[int] = typer.Option(None, "--db"),
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """List fields in a table."""
    client, active, store = _get_client_and_profile(profile)
    database_id = db or active.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    try:
        cache = SchemaCache(store.config_dir / "schema_cache")
        schema = cache.get_schema(client, database_id=database_id, profile_name=active.name)
        table = next((t for t in schema.get("tables", []) if t["name"] == table_name), None)
        if not table:
            err_console.print(f"[red]Error:[/] Table '{table_name}' not found.")
            raise typer.Exit(1)
        flds = table.get("fields", [])
        result = QueryResult(
            columns=[
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
                {"name": "base_type", "base_type": "type/Text", "semantic_type": None},
                {"name": "semantic_type", "base_type": "type/Text", "semantic_type": None},
            ],
            rows=[[f["name"], f.get("base_type", ""), f.get("semantic_type", "") or ""] for f in flds],
            row_count=len(flds),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()


@schema_app.command()
def refresh(
    db: Optional[int] = typer.Option(None, "--db"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """Refresh cached schema from Metabase API."""
    client, active, store = _get_client_and_profile(profile)
    database_id = db or active.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    try:
        cache = SchemaCache(store.config_dir / "schema_cache")
        schema = cache.get_schema(
            client, database_id=database_id, profile_name=active.name, force_refresh=True
        )
        table_count = len(schema.get("tables", []))
        field_count = sum(len(t.get("fields", [])) for t in schema.get("tables", []))
        typer.echo(f"Schema cached: {table_count} tables, {field_count} fields.")
    finally:
        client.close()
```

Update `src/mbquery/cli/app.py`:

```python
"""Root CLI application."""

from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd
from mbquery.cli.ask import ask_cmd
from mbquery.cli.schema import schema_app

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)
app.add_typer(schema_app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_schema.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/cli/schema.py src/mbquery/cli/app.py tests/test_cli_schema.py
git commit -m "feat: mbquery schema — browse databases, tables, fields with cache"
```

---

## Task 11: `mbquery card` + `mbquery dashboard` + `mbquery search` Commands

**Files:**
- Create: `src/mbquery/core/cards.py`
- Create: `src/mbquery/core/dashboards.py`
- Create: `src/mbquery/core/search.py`
- Create: `src/mbquery/utils/resolve.py`
- Create: `src/mbquery/cli/card.py`
- Create: `src/mbquery/cli/dashboard.py`
- Create: `src/mbquery/cli/search.py`
- Modify: `src/mbquery/cli/app.py`
- Test: `tests/test_cli_card_dash_search.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_card_dash_search.py`:

```python
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
    config = {
        "active_profile": "test",
        "profiles": {"test": {
            "url": "https://metabase.test.com",
            "auth": {"method": "api-key", "api_key": "mb_testkey"},
            "default_db": 2,
        }},
        "defaults": {"format": "table", "limit": 100, "redact_pii": False},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


# --- Card tests ---

@respx.mock
def test_card_list():
    respx.get("https://metabase.test.com/api/card").respond(json=[
        {"id": 1, "name": "Monthly Revenue", "collection_id": 5, "display": "table"},
        {"id": 2, "name": "User Count", "collection_id": 5, "display": "scalar"},
    ])
    result = runner.invoke(app, ["card", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@respx.mock
def test_card_run():
    respx.post("https://metabase.test.com/api/card/1/query").respond(json={
        "data": {
            "rows": [[50000]],
            "cols": [{"name": "revenue", "base_type": "type/Float", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["card", "run", "1", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["revenue"] == 50000


@respx.mock
def test_card_run_by_name():
    respx.get("https://metabase.test.com/api/card").respond(json=[
        {"id": 1, "name": "Monthly Revenue", "collection_id": 5, "display": "table"},
    ])
    respx.post("https://metabase.test.com/api/card/1/query").respond(json={
        "data": {
            "rows": [[50000]],
            "cols": [{"name": "revenue", "base_type": "type/Float", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["card", "run", "Monthly Revenue", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["revenue"] == 50000


# --- Dashboard tests ---

@respx.mock
def test_dashboard_list():
    respx.get("https://metabase.test.com/api/dashboard").respond(json=[
        {"id": 10, "name": "Sales Dashboard", "collection_id": 3},
        {"id": 11, "name": "Ops Dashboard", "collection_id": 3},
    ])
    result = runner.invoke(app, ["dashboard", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@respx.mock
def test_dashboard_show():
    respx.get("https://metabase.test.com/api/dashboard/10").respond(json={
        "id": 10,
        "name": "Sales Dashboard",
        "dashcards": [
            {"id": 100, "card": {"id": 1, "name": "Revenue"}, "size_x": 6, "size_y": 4},
            {"id": 101, "card": {"id": 2, "name": "Users"}, "size_x": 6, "size_y": 4},
        ],
    })
    result = runner.invoke(app, ["dashboard", "show", "10", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


# --- Search tests ---

@respx.mock
def test_search():
    respx.get("https://metabase.test.com/api/search").respond(json={
        "data": [
            {"id": 1, "name": "Revenue Card", "model": "card"},
            {"id": 10, "name": "Revenue Dashboard", "model": "dashboard"},
        ],
    })
    result = runner.invoke(app, ["search", "revenue", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@respx.mock
def test_search_with_type_filter():
    respx.get("https://metabase.test.com/api/search").respond(json={
        "data": [
            {"id": 1, "name": "Revenue Card", "model": "card"},
        ],
    })
    result = runner.invoke(app, ["search", "revenue", "--type", "card", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_card_dash_search.py -v`
Expected: FAIL

- [ ] **Step 3: Implement core modules**

Create `src/mbquery/utils/resolve.py`:

```python
"""Name-or-ID resolution for Metabase entities."""

from __future__ import annotations


def resolve_card_id(client, id_or_name: str) -> int:
    """Resolve a card ID from either a numeric ID or a name."""
    if id_or_name.isdigit():
        return int(id_or_name)

    cards = client.get("/api/card")
    matches = [c for c in cards if c["name"].lower() == id_or_name.lower()]
    if not matches:
        matches = [c for c in cards if id_or_name.lower() in c["name"].lower()]
    if len(matches) == 0:
        raise ValueError(f"No card found matching '{id_or_name}'")
    if len(matches) > 1:
        names = [f"  {m['id']}: {m['name']}" for m in matches[:5]]
        raise ValueError(f"Multiple cards match '{id_or_name}':\n" + "\n".join(names))
    return matches[0]["id"]
```

Create `src/mbquery/core/cards.py`:

```python
"""Card (saved question) operations."""

from __future__ import annotations

from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult


def list_cards(client: MetabaseClient) -> list[dict]:
    """List all saved questions/cards."""
    return client.get("/api/card")


def run_card(client: MetabaseClient, card_id: int, parameters: dict | None = None) -> QueryResult:
    """Execute a saved card and return results."""
    payload = {}
    if parameters:
        payload["parameters"] = [
            {"type": "category", "target": ["variable", ["template-tag", k]], "value": v}
            for k, v in parameters.items()
        ]
    resp = client.post(f"/api/card/{card_id}/query", json=payload)
    data = resp.get("data", {})
    cols = data.get("cols", [])
    columns = [
        {"name": c.get("name", f"col_{i}"), "base_type": c.get("base_type"), "semantic_type": c.get("semantic_type")}
        for i, c in enumerate(cols)
    ]
    return QueryResult(
        columns=columns,
        rows=data.get("rows", []),
        row_count=resp.get("row_count", len(data.get("rows", []))),
    )
```

Create `src/mbquery/core/dashboards.py`:

```python
"""Dashboard operations."""

from __future__ import annotations

from mbquery.core.client import MetabaseClient


def list_dashboards(client: MetabaseClient) -> list[dict]:
    """List all dashboards."""
    return client.get("/api/dashboard")


def get_dashboard(client: MetabaseClient, dashboard_id: int) -> dict:
    """Get dashboard details with cards."""
    return client.get(f"/api/dashboard/{dashboard_id}")
```

Create `src/mbquery/core/search.py`:

```python
"""Search operations."""

from __future__ import annotations

from mbquery.core.client import MetabaseClient


def search(client: MetabaseClient, query: str, model_type: str | None = None) -> list[dict]:
    """Search across Metabase content."""
    params: dict = {"q": query}
    if model_type:
        params["models"] = model_type
    resp = client.get("/api/search", params=params)
    if isinstance(resp, dict):
        return resp.get("data", [])
    return resp
```

- [ ] **Step 4: Implement CLI commands**

Create `src/mbquery/cli/card.py`:

```python
"""mbquery card — saved question operations."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.config.store import ConfigStore
from mbquery.core.cards import list_cards, run_card
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult
from mbquery.formatters import format_result
from mbquery.formatters.redact import redact_pii
from mbquery.utils.resolve import resolve_card_id
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)

card_app = typer.Typer(name="card", help="Saved question operations.", no_args_is_help=True)


@card_app.command(name="list")
def card_list(
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """List all saved questions."""
    store = ConfigStore()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        cards = list_cards(client)
        result = QueryResult(
            columns=[
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
                {"name": "collection_id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "display", "base_type": "type/Text", "semantic_type": None},
            ],
            rows=[[c["id"], c["name"], c.get("collection_id", ""), c.get("display", "")] for c in cards],
            row_count=len(cards),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()


@card_app.command(name="run")
def card_run(
    id_or_name: str = typer.Argument(..., help="Card ID or name"),
    param: Optional[list[str]] = typer.Option(None, "--param", help="Parameter as key=value"),
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
    no_redact: bool = typer.Option(False, "--no-redact"),
    fields: Optional[str] = typer.Option(None, "--fields"),
) -> None:
    """Execute a saved question by ID or name."""
    store = ConfigStore()
    config = store.load()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        card_id = resolve_card_id(client, id_or_name)
        parameters = {}
        if param:
            for p in param:
                key, _, value = p.partition("=")
                parameters[key] = value

        result = run_card(client, card_id, parameters=parameters or None)

        should_redact = config.defaults.redact_pii and not no_redact
        if should_redact:
            result = redact_pii(result)
        if fields:
            result = result.filter_fields([f.strip() for f in fields.split(",")])

        typer.echo(format_result(result, format or auto_format()))
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()
```

Create `src/mbquery/cli/dashboard.py`:

```python
"""mbquery dashboard — dashboard operations."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.dashboards import list_dashboards, get_dashboard
from mbquery.core.queries import QueryResult
from mbquery.formatters import format_result
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)

dashboard_app = typer.Typer(name="dashboard", help="Dashboard operations.", no_args_is_help=True)


@dashboard_app.command(name="list")
def dash_list(
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """List all dashboards."""
    store = ConfigStore()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        dashboards = list_dashboards(client)
        result = QueryResult(
            columns=[
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
                {"name": "collection_id", "base_type": "type/Integer", "semantic_type": None},
            ],
            rows=[[d["id"], d["name"], d.get("collection_id", "")] for d in dashboards],
            row_count=len(dashboards),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()


@dashboard_app.command()
def show(
    dashboard_id: int = typer.Argument(..., help="Dashboard ID"),
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """Show dashboard structure (cards and layout)."""
    store = ConfigStore()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        dash = get_dashboard(client, dashboard_id)
        dashcards = dash.get("dashcards", dash.get("ordered_cards", []))
        result = QueryResult(
            columns=[
                {"name": "card_id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "card_name", "base_type": "type/Text", "semantic_type": None},
                {"name": "size", "base_type": "type/Text", "semantic_type": None},
            ],
            rows=[
                [
                    dc.get("card", {}).get("id", ""),
                    dc.get("card", {}).get("name", ""),
                    f"{dc.get('size_x', '')}x{dc.get('size_y', '')}",
                ]
                for dc in dashcards
                if dc.get("card")
            ],
            row_count=len(dashcards),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()
```

Create `src/mbquery/cli/search.py`:

```python
"""mbquery search — search across Metabase."""

from __future__ import annotations

from typing import Optional

import typer

from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult
from mbquery.core.search import search
from mbquery.formatters import format_result
from mbquery.utils.tty import auto_format


search_cmd_func = None  # defined below


def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type: card, dashboard, table, collection"),
    format: Optional[str] = typer.Option(None, "--format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p"),
) -> None:
    """Search across all Metabase content."""
    store = ConfigStore()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        results = search(client, query, model_type=type)
        qr = QueryResult(
            columns=[
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
                {"name": "model", "base_type": "type/Text", "semantic_type": None},
            ],
            rows=[[r["id"], r["name"], r.get("model", "")] for r in results],
            row_count=len(results),
        )
        typer.echo(format_result(qr, format or auto_format()))
    finally:
        client.close()
```

Update `src/mbquery/cli/app.py`:

```python
"""Root CLI application."""

from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd
from mbquery.cli.ask import ask_cmd
from mbquery.cli.schema import schema_app
from mbquery.cli.card import card_app
from mbquery.cli.dashboard import dashboard_app
from mbquery.cli.search import search_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)
app.add_typer(schema_app)
app.add_typer(card_app)
app.add_typer(dashboard_app)
app.command(name="search")(search_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_card_dash_search.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/core/cards.py src/mbquery/core/dashboards.py src/mbquery/core/search.py src/mbquery/utils/resolve.py src/mbquery/cli/card.py src/mbquery/cli/dashboard.py src/mbquery/cli/search.py src/mbquery/cli/app.py tests/test_cli_card_dash_search.py
git commit -m "feat: card, dashboard, and search commands with name-or-ID resolution"
```

---

## Task 12: `mbquery config` Command (Interactive Setup Wizard)

**Files:**
- Create: `src/mbquery/cli/config_cmd.py`
- Modify: `src/mbquery/cli/app.py`
- Test: `tests/test_cli_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli_config.py`:

```python
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


def test_config_list_empty(setup_config):
    result = runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    assert "No profiles" in result.output


def test_config_add_and_list(setup_config):
    result = runner.invoke(app, [
        "config", "add", "prod",
        "--url", "https://metabase.example.com",
        "--api-key", "mb_test123",
    ])
    assert result.exit_code == 0

    result = runner.invoke(app, ["config", "list"])
    assert result.exit_code == 0
    assert "prod" in result.output


def test_config_switch(setup_config):
    runner.invoke(app, ["config", "add", "prod", "--url", "https://prod.mb.com", "--api-key", "mb_1"])
    runner.invoke(app, ["config", "add", "dev", "--url", "https://dev.mb.com", "--api-key", "mb_2"])
    result = runner.invoke(app, ["config", "switch", "dev"])
    assert result.exit_code == 0
    assert "dev" in result.output


def test_config_switch_nonexistent(setup_config):
    result = runner.invoke(app, ["config", "switch", "nope"])
    assert result.exit_code == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_config.py -v`
Expected: FAIL

- [ ] **Step 3: Implement config command**

Create `src/mbquery/cli/config_cmd.py`:

```python
"""mbquery config — profile and setup management."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mbquery.config.store import ConfigStore

err_console = Console(stderr=True)
out_console = Console()

config_app = typer.Typer(name="config", help="Manage profiles and settings.", no_args_is_help=True)


@config_app.command(name="list")
def config_list() -> None:
    """List all configured profiles."""
    store = ConfigStore()
    config = store.load()

    if not config.profiles:
        typer.echo("No profiles configured. Run: mbquery config add <name> --url <url> --api-key <key>")
        return

    table = Table(title="Profiles")
    table.add_column("Name", style="bold")
    table.add_column("URL")
    table.add_column("Auth")
    table.add_column("Default DB")
    table.add_column("Active", justify="center")

    for name, profile in config.profiles.items():
        is_active = "✓" if name == config.active_profile else ""
        table.add_row(
            name,
            profile.url,
            profile.auth.method,
            str(profile.default_db or ""),
            is_active,
        )

    out_console.print(table)


@config_app.command()
def add(
    name: str = typer.Argument(..., help="Profile name"),
    url: str = typer.Option(..., "--url", help="Metabase URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key"),
    email: Optional[str] = typer.Option(None, "--email", help="Email for session auth"),
    password: Optional[str] = typer.Option(None, "--password", help="Password for session auth"),
    db: Optional[int] = typer.Option(None, "--db", help="Default database ID"),
) -> None:
    """Add a new Metabase profile."""
    if api_key:
        auth_method = "api-key"
    elif email:
        auth_method = "session"
    else:
        err_console.print("[red]Error:[/] Provide --api-key or --email + --password")
        raise typer.Exit(1)

    store = ConfigStore()
    store.add_profile(
        name=name,
        url=url,
        auth_method=auth_method,
        api_key=api_key,
        email=email,
        password=password,
        default_db=db,
    )
    typer.echo(f"Profile '{name}' added.")


@config_app.command()
def switch(
    name: str = typer.Argument(..., help="Profile to switch to"),
) -> None:
    """Switch active profile."""
    store = ConfigStore()
    try:
        store.switch_profile(name)
        typer.echo(f"Switched to profile '{name}'.")
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@config_app.command(name="set-llm")
def set_llm_cmd(
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="LLM API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Custom API base URL"),
) -> None:
    """Configure LLM for natural language queries (interactive if no flags)."""
    if not provider:
        # Interactive mode
        typer.echo("\n  Choose your LLM provider:")
        typer.echo("    1. OpenAI (GPT-4o, GPT-4o-mini)")
        typer.echo("    2. Google Gemini (Gemini 2.0 Flash — free tier available)")
        typer.echo("    3. Anthropic Claude (via OpenAI-compatible)")
        typer.echo("    4. Ollama (local, free, no API key needed)")
        typer.echo("    5. Other OpenAI-compatible endpoint")
        typer.echo("    6. Skip for now")
        choice = typer.prompt("\n  Choice", type=int)

        if choice == 6:
            typer.echo("Skipped LLM setup.")
            return

        provider_map = {1: "openai", 2: "gemini", 3: "openai", 4: "openai", 5: "openai"}
        provider = provider_map.get(choice, "openai")

        model_menus = {
            1: [("gpt-4o", "recommended"), ("gpt-4o-mini", "fast, cheap"), ("custom", None)],
            2: [("gemini-2.0-flash", "recommended — fast, cheap"), ("gemini-2.5-pro", "best quality"), ("custom", None)],
            3: [("claude-sonnet-4-20250514", "recommended"), ("claude-haiku-4-5-20251001", "fast"), ("custom", None)],
            4: [("llama3", "recommended"), ("mistral", "fast"), ("custom", None)],
            5: [("custom", None)],
        }
        models = model_menus.get(choice, [("custom", None)])

        typer.echo("\n  Choose model:")
        for i, (m, desc) in enumerate(models, 1):
            label = f"{m} ({desc})" if desc else m
            typer.echo(f"    {i}. {label}")
        model_choice = typer.prompt("\n  Choice", type=int, default=1)

        if model_choice <= len(models):
            model = models[model_choice - 1][0]
        else:
            model = models[0][0]

        if model == "custom":
            model = typer.prompt("  Model name")

        base_url_map = {
            3: "https://api.anthropic.com/v1",
            4: "http://localhost:11434/v1",
        }
        base_url = base_url_map.get(choice)
        if choice == 5:
            base_url = typer.prompt("  Base URL")

        if choice != 4:
            api_key = typer.prompt("  API Key", hide_input=True)
        else:
            api_key = "ollama"  # Ollama doesn't need a key

    store = ConfigStore()
    store.set_llm(provider=provider, model=model or "gpt-4o", api_key=api_key, base_url=base_url)
    typer.echo(f"LLM configured: {provider}/{model}")


@config_app.command(name="set-hints")
def set_hints(
    table: str = typer.Argument(..., help="Table name"),
    hint: str = typer.Argument(..., help="Hint text"),
) -> None:
    """Add a schema hint for better NL→SQL generation."""
    import yaml
    store = ConfigStore()
    hints_file = store.config_dir / "hints.yaml"

    hints = {}
    if hints_file.exists():
        with open(hints_file) as f:
            hints = yaml.safe_load(f) or {}

    hints[table] = hint

    with open(hints_file, "w") as f:
        yaml.dump(hints, f, default_flow_style=False)

    typer.echo(f"Hint saved for table '{table}'.")


@config_app.command()
def init() -> None:
    """Interactive setup wizard."""
    typer.echo("\n  Welcome to mbquery! Let's set up your first profile.\n")

    url = typer.prompt("  Metabase URL")

    typer.echo("  Auth method:")
    typer.echo("    1. API Key (recommended)")
    typer.echo("    2. Email + Password")
    auth_choice = typer.prompt("  Choice", type=int, default=1)

    api_key = None
    email = None
    password = None

    if auth_choice == 1:
        api_key = typer.prompt("  API Key", hide_input=True)
        auth_method = "api-key"
    else:
        email = typer.prompt("  Email")
        password = typer.prompt("  Password", hide_input=True)
        auth_method = "session"

    db_str = typer.prompt("  Default database ID (optional, press Enter to skip)", default="")
    default_db = int(db_str) if db_str else None
    name = typer.prompt("  Profile name", default="default")

    store = ConfigStore()
    store.add_profile(
        name=name,
        url=url,
        auth_method=auth_method,
        api_key=api_key,
        email=email,
        password=password,
        default_db=default_db,
    )
    typer.echo(f"\n  ✅ Profile '{name}' saved.")

    setup_llm = typer.confirm("  Set up AI-powered natural language queries?", default=True)
    if setup_llm:
        set_llm_cmd()

    typer.echo("\n  You're ready! Try:")
    typer.echo("    mbquery query \"SELECT 1\"")
    typer.echo("    mbquery ask \"how many users signed up last week\"")
    typer.echo()
```

Update `src/mbquery/cli/app.py`:

```python
"""Root CLI application."""

from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd
from mbquery.cli.ask import ask_cmd
from mbquery.cli.schema import schema_app
from mbquery.cli.card import card_app
from mbquery.cli.dashboard import dashboard_app
from mbquery.cli.search import search_cmd
from mbquery.cli.config_cmd import config_app

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)
app.add_typer(schema_app)
app.add_typer(card_app)
app.add_typer(dashboard_app)
app.command(name="search")(search_cmd)
app.add_typer(config_app)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_cli_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/cli/config_cmd.py src/mbquery/cli/app.py tests/test_cli_config.py
git commit -m "feat: config command — add, list, switch profiles, LLM wizard, hints"
```

---

## Task 13: MCP Server Mode

**Files:**
- Create: `src/mbquery/mcp/__init__.py`
- Create: `src/mbquery/mcp/server.py`
- Create: `src/mbquery/cli/serve.py`
- Modify: `src/mbquery/cli/app.py`
- Test: `tests/test_mcp_server.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp_server.py`:

```python
import pytest

pytest.importorskip("mcp", reason="mcp package not installed")

import json
import respx
from mbquery.mcp.server import create_mcp_server
from mbquery.config.models import Profile, AuthConfig


@pytest.fixture
def profile():
    return Profile(
        name="test",
        url="https://metabase.test.com",
        auth=AuthConfig(method="api-key", api_key="mb_testkey"),
        default_db=2,
    )


def test_create_mcp_server(profile, tmp_path):
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    assert server is not None
    # Check tools are registered
    assert len(server._tools) >= 8


@respx.mock
def test_mcp_query_tool_blocks_writes(profile, tmp_path):
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    query_tool = server._tools.get("query")
    assert query_tool is not None
    # The tool function should exist
    assert callable(query_tool["handler"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Dev/mbquery && pip install -e ".[mcp,dev]" && pytest tests/test_mcp_server.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement MCP server**

Create `src/mbquery/mcp/__init__.py`:

```python
```

Create `src/mbquery/mcp/server.py`:

```python
"""MCP server for mbquery — exposes Metabase tools to AI agents."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from mbquery.config.models import Profile
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import execute_sql, is_write_query, QueryResult
from mbquery.core.database import list_databases as _list_databases
from mbquery.core.cards import list_cards as _list_cards, run_card as _run_card
from mbquery.core.dashboards import list_dashboards as _list_dashboards, get_dashboard
from mbquery.core.search import search as _search
from mbquery.core.schema_cache import SchemaCache


def _result_to_text(result: QueryResult, max_rows: int = 100) -> str:
    """Convert QueryResult to compact text for AI consumption."""
    lines = [" | ".join(result.column_names)]
    for row in result.rows[:max_rows]:
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
    if result.row_count > max_rows:
        lines.append(f"... ({result.row_count - max_rows} more rows)")
    return "\n".join(lines)


def _optimize_list(items: list[dict], keys: list[str]) -> list[dict]:
    """Strip response to only essential keys for token efficiency."""
    return [{k: item.get(k) for k in keys if k in item} for item in items]


class MbqueryMCPServer:
    def __init__(self, profile: Profile, cache_dir: Path):
        self.profile = profile
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = MetabaseClient(profile)
        self._schema_cache = SchemaCache(cache_dir)
        self._tools: dict = {}
        self._register_tools()

    def _register_tools(self) -> None:
        self._tools = {
            "query": {
                "description": "Execute a SQL query against Metabase. Write queries (INSERT/UPDATE/DELETE/DROP) are blocked.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"},
                        "database_id": {"type": "integer", "description": "Database ID (optional, uses default)"},
                    },
                    "required": ["sql"],
                },
                "handler": self._handle_query,
            },
            "list_databases": {
                "description": "List all databases configured in Metabase.",
                "schema": {"type": "object", "properties": {}},
                "handler": self._handle_list_databases,
            },
            "list_tables": {
                "description": "List tables in a database.",
                "schema": {
                    "type": "object",
                    "properties": {"database_id": {"type": "integer"}},
                },
                "handler": self._handle_list_tables,
            },
            "get_table_schema": {
                "description": "Get columns and types for a specific table.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string"},
                        "database_id": {"type": "integer"},
                    },
                    "required": ["table_name"],
                },
                "handler": self._handle_get_table_schema,
            },
            "list_cards": {
                "description": "List all saved questions/cards in Metabase.",
                "schema": {"type": "object", "properties": {}},
                "handler": self._handle_list_cards,
            },
            "run_card": {
                "description": "Execute a saved question/card by ID.",
                "schema": {
                    "type": "object",
                    "properties": {"card_id": {"type": "integer"}},
                    "required": ["card_id"],
                },
                "handler": self._handle_run_card,
            },
            "list_dashboards": {
                "description": "List all dashboards in Metabase.",
                "schema": {"type": "object", "properties": {}},
                "handler": self._handle_list_dashboards,
            },
            "search": {
                "description": "Search across all Metabase content.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "type": {"type": "string", "enum": ["card", "dashboard", "table", "collection"]},
                    },
                    "required": ["query"],
                },
                "handler": self._handle_search,
            },
            "get_schema_context": {
                "description": "Get full database schema context for NL→SQL. Returns table names, columns, and types.",
                "schema": {
                    "type": "object",
                    "properties": {"database_id": {"type": "integer"}},
                },
                "handler": self._handle_get_schema_context,
            },
        }

    def _db_id(self, args: dict) -> int:
        return args.get("database_id") or self.profile.default_db or 1

    def _handle_query(self, args: dict) -> str:
        sql = args["sql"]
        if is_write_query(sql):
            return "Error: Write queries are blocked in MCP mode for safety."
        result = execute_sql(self._client, sql, database_id=self._db_id(args))
        return _result_to_text(result)

    def _handle_list_databases(self, args: dict) -> str:
        dbs = _list_databases(self._client)
        if isinstance(dbs, dict):
            dbs = dbs.get("data", [])
        optimized = _optimize_list(dbs, ["id", "name", "engine"])
        return json.dumps(optimized, indent=2)

    def _handle_list_tables(self, args: dict) -> str:
        schema = self._schema_cache.get_schema(
            self._client, database_id=self._db_id(args), profile_name=self.profile.name
        )
        tables = [{"name": t["name"], "fields": len(t.get("fields", []))} for t in schema.get("tables", [])]
        return json.dumps(tables, indent=2)

    def _handle_get_table_schema(self, args: dict) -> str:
        schema = self._schema_cache.get_schema(
            self._client, database_id=self._db_id(args), profile_name=self.profile.name
        )
        table = next((t for t in schema.get("tables", []) if t["name"] == args["table_name"]), None)
        if not table:
            return f"Error: Table '{args['table_name']}' not found."
        return json.dumps(table, indent=2)

    def _handle_list_cards(self, args: dict) -> str:
        cards = _list_cards(self._client)
        optimized = _optimize_list(cards, ["id", "name", "display", "collection_id"])
        return json.dumps(optimized, indent=2)

    def _handle_run_card(self, args: dict) -> str:
        result = _run_card(self._client, args["card_id"])
        return _result_to_text(result)

    def _handle_list_dashboards(self, args: dict) -> str:
        dashboards = _list_dashboards(self._client)
        optimized = _optimize_list(dashboards, ["id", "name", "collection_id"])
        return json.dumps(optimized, indent=2)

    def _handle_search(self, args: dict) -> str:
        results = _search(self._client, args["query"], model_type=args.get("type"))
        optimized = _optimize_list(results, ["id", "name", "model"])
        return json.dumps(optimized, indent=2)

    def _handle_get_schema_context(self, args: dict) -> str:
        schema = self._schema_cache.get_schema(
            self._client, database_id=self._db_id(args), profile_name=self.profile.name
        )
        return self._schema_cache.schema_to_prompt_context(schema)

    def get_tools(self) -> list[dict]:
        """Return MCP tool definitions."""
        return [
            {"name": name, "description": tool["description"], "inputSchema": tool["schema"]}
            for name, tool in self._tools.items()
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool by name with arguments."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        return tool["handler"](arguments)


def create_mcp_server(profile: Profile, cache_dir: Path) -> MbqueryMCPServer:
    """Create an MCP server instance."""
    return MbqueryMCPServer(profile, cache_dir)
```

Create `src/mbquery/cli/serve.py`:

```python
"""mbquery serve — start MCP server."""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console

err_console = Console(stderr=True)


def serve_cmd(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Start MCP server (stdio transport)."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        err_console.print("[red]Error:[/] MCP not installed. Run: pip install mbquery[mcp]")
        raise typer.Exit(1)

    from mbquery.config.store import ConfigStore
    from mbquery.mcp.server import create_mcp_server

    store = ConfigStore()
    try:
        active = store.resolve_profile(profile)
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

    cache_dir = store.config_dir / "schema_cache"
    mbq = create_mcp_server(active, cache_dir)

    server = Server("mbquery")

    @server.list_tools()
    async def list_tools():
        tools = mbq.get_tools()
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in tools
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result_text = mbq.call_tool(name, arguments)
        return [TextContent(type="text", text=result_text)]

    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    err_console.print("[dim]mbquery MCP server starting...[/]")
    asyncio.run(run())
```

Update `src/mbquery/cli/app.py` — add serve command:

```python
"""Root CLI application."""

from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd
from mbquery.cli.ask import ask_cmd
from mbquery.cli.schema import schema_app
from mbquery.cli.card import card_app
from mbquery.cli.dashboard import dashboard_app
from mbquery.cli.search import search_cmd
from mbquery.cli.config_cmd import config_app
from mbquery.cli.serve import serve_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)
app.add_typer(schema_app)
app.add_typer(card_app)
app.add_typer(dashboard_app)
app.command(name="search")(search_cmd)
app.add_typer(config_app)
app.command(name="serve")(serve_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/Dev/mbquery && pytest tests/test_mcp_server.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/Dev/mbquery && git add src/mbquery/mcp/ src/mbquery/cli/serve.py src/mbquery/cli/app.py tests/test_mcp_server.py
git commit -m "feat: MCP server mode with 9 tools and response optimization"
```

---

## Task 14: README + Final Integration Test

**Files:**
- Create: `README.md`
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
"""Integration test — verify full CLI works end-to-end."""

import json
import yaml
import pytest
import respx
from typer.testing import CliRunner
from mbquery.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def full_config(tmp_path, monkeypatch):
    import time
    config_dir = tmp_path / "mbquery"
    config_dir.mkdir()
    schema_dir = config_dir / "schema_cache"
    schema_dir.mkdir()

    # Write config
    config = {
        "active_profile": "test",
        "profiles": {"test": {
            "url": "https://metabase.test.com",
            "auth": {"method": "api-key", "api_key": "mb_testkey"},
            "default_db": 2,
        }},
        "llm": {"provider": "gemini", "model": "gemini-2.0-flash", "api_key": "AIza_test", "base_url": None},
        "defaults": {"format": "table", "limit": 100, "redact_pii": True},
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)

    # Write cached schema
    schema = {
        "database_id": 2,
        "tables": [{"name": "users", "fields": [
            {"name": "id", "base_type": "type/Integer"},
            {"name": "email", "base_type": "type/Text"},
        ]}],
        "cached_at": time.time(),
    }
    (schema_dir / "test_2.json").write_text(json.dumps(schema))

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


@respx.mock
def test_full_sql_workflow():
    """Test: query → format → redact → output."""
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1, "alice@test.com", "Alice"], [2, "bob@test.com", "Bob"]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
                {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
            ],
        },
        "row_count": 2,
    })
    result = runner.invoke(app, ["query", "--format", "json", "SELECT * FROM users"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["id"] == 1
    assert data[0]["email"] == "[REDACTED]"
    assert data[0]["name"] == "[REDACTED]"


@respx.mock
def test_full_nl_workflow():
    """Test: ask NL → LLM → SQL → Metabase → format → output."""
    respx.post("https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent").respond(json={
        "candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) AS total FROM users"}]}}]
    })
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[42]],
            "cols": [{"name": "total", "base_type": "type/Integer", "semantic_type": None}],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["ask", "--format", "json", "how many users are there"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data[0]["total"] == 42


def test_all_commands_registered():
    """Verify all expected commands exist."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["query", "ask", "schema", "card", "dashboard", "search", "config", "serve"]:
        assert cmd in result.output, f"Command '{cmd}' not found in help output"


@respx.mock
def test_format_csv_output():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1, 100]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "amount", "base_type": "type/Float", "semantic_type": None},
            ],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "csv", "SELECT 1"])
    assert result.exit_code == 0
    assert "id,amount" in result.output
    assert "1,100" in result.output


@respx.mock
def test_format_markdown_output():
    respx.post("https://metabase.test.com/api/dataset").respond(json={
        "data": {
            "rows": [[1, "test"]],
            "cols": [
                {"name": "id", "base_type": "type/Integer", "semantic_type": None},
                {"name": "name", "base_type": "type/Text", "semantic_type": None},
            ],
        },
        "row_count": 1,
    })
    result = runner.invoke(app, ["query", "--format", "markdown", "SELECT 1"])
    assert result.exit_code == 0
    assert "| id | name |" in result.output
    assert "| 1 | test |" in result.output
```

- [ ] **Step 2: Run integration tests**

Run: `cd ~/Dev/mbquery && pytest tests/test_integration.py -v`
Expected: All 5 tests PASS

- [ ] **Step 3: Run full test suite**

Run: `cd ~/Dev/mbquery && pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Write README.md**

Create `README.md`:

```markdown
# mbquery

The ultimate Metabase CLI — SQL queries, natural language queries, and MCP server in one tool.

## Install

```bash
pip install mbquery
```

For MCP server support:

```bash
pip install mbquery[mcp]
```

## Quick Start

```bash
# Set up your first profile
mbquery config init

# Run SQL queries
mbquery query "SELECT COUNT(*) FROM users"

# Ask in natural language
mbquery ask "how many users signed up last week"

# Browse schema
mbquery schema tables
mbquery schema fields users

# Run saved questions
mbquery card list
mbquery card run 42

# Search
mbquery search "revenue"
```

## Features

- **SQL queries** — Run any SQL query against Metabase from your terminal
- **Natural language** — Ask questions in plain English, get SQL + results
- **Pluggable AI** — OpenAI, Gemini, Ollama, or any OpenAI-compatible endpoint
- **Schema discovery** — Auto-pulls your database schema for accurate NL→SQL
- **6 output formats** — Table, CSV, JSON, JSONL, Markdown
- **PII redaction** — Automatically masks sensitive columns (on by default)
- **Multi-profile** — Switch between prod, staging, dev instances
- **MCP server** — Let AI agents query your Metabase
- **Python library** — `from mbquery import MetabaseClient`

## Output Formats

```bash
mbquery query "SELECT * FROM users LIMIT 5" --format table    # Rich table (default)
mbquery query "SELECT * FROM users LIMIT 5" --format csv      # CSV
mbquery query "SELECT * FROM users LIMIT 5" --format json     # JSON array
mbquery query "SELECT * FROM users LIMIT 5" --format jsonl    # JSON Lines
mbquery query "SELECT * FROM users LIMIT 5" --format markdown # Markdown table
```

## Natural Language Queries

```bash
# Set up AI provider
mbquery config set-llm

# Ask anything
mbquery ask "top 10 customers by revenue"
mbquery ask "how many orders were placed last month" --show-sql
```

Supports: OpenAI, Google Gemini, Anthropic Claude, Ollama (local), and any OpenAI-compatible API.

## Multi-Profile

```bash
mbquery config add prod --url https://metabase.example.com --api-key mb_xxx
mbquery config add staging --url https://staging.metabase.com --api-key mb_yyy
mbquery config switch staging
mbquery config list
```

## MCP Server

```bash
mbquery serve
```

Add to Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mbquery": {
      "command": "mbquery",
      "args": ["serve"]
    }
  }
}
```

## Schema Hints

Improve NL→SQL accuracy with business context:

```bash
mbquery config set-hints users "plan_type values are 'free', 'pro', 'enterprise'"
mbquery config set-hints orders "status values are 'pending', 'completed', 'refunded'"
```

## Environment Variables

All config can be overridden with env vars (useful for CI/CD):

```bash
MBQUERY_URL=https://metabase.example.com
MBQUERY_API_KEY=mb_xxx
MBQUERY_DEFAULT_DB=2
MBQUERY_LLM_PROVIDER=openai
MBQUERY_LLM_API_KEY=sk-xxx
MBQUERY_LLM_MODEL=gpt-4o
MBQUERY_FORMAT=json
MBQUERY_REDACT_PII=false
```

## License

MIT
```

- [ ] **Step 5: Lint and commit**

```bash
cd ~/Dev/mbquery && ruff check src/ tests/ --fix && ruff format src/ tests/
git add README.md tests/test_integration.py
git commit -m "feat: README and integration tests"
```

---

## Task 15: GitHub Repo + CI + PyPI Prep

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `.github/workflows/publish.yml`
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.ruff_cache/
.pytest_cache/
.mypy_cache/
.venv/
venv/
*.so
.coverage
htmlcov/
```

- [ ] **Step 2: Create test CI workflow**

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e ".[dev,mcp]"
      - name: Lint
        run: ruff check src/ tests/
      - name: Test
        run: pytest tests/ -v --tb=short
```

- [ ] **Step 3: Create publish workflow**

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install build tools
        run: pip install build
      - name: Build
        run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 4: Create GitHub repo and push**

```bash
cd ~/Dev/mbquery
git add .gitignore .github/
git commit -m "ci: GitHub Actions for tests and PyPI publishing"
```

Then ask user to create the GitHub repo and push:

```bash
# Switch to personal GitHub account
gh auth switch --user shubhamattri
gh repo create mbquery --public --description "The ultimate Metabase CLI — SQL, natural language queries, and MCP server" --source . --push
```

- [ ] **Step 5: Verify CI runs**

Run: `gh run list --repo shubhamattri/mbquery`
Expected: Test workflow triggered and passing
