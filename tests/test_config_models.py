from mbquery.config.models import AppConfig, Defaults, LLMConfig, Profile


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
