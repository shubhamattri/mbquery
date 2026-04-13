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


def test_profile_google_sso_auth_without_secret():
    """google_client_secret is optional — omitting it keeps it out of to_dict output."""
    profile = Profile.from_dict("sso", {
        "url": "https://metabase.test.com",
        "auth": {
            "method": "google-sso",
            "google_client_id": "test.apps.googleusercontent.com",
            "session_token": "sess_abc",
        },
    })
    assert profile.auth.method == "google-sso"
    assert profile.auth.google_client_id == "test.apps.googleusercontent.com"
    assert profile.auth.google_client_secret is None
    assert profile.auth.session_token == "sess_abc"

    d = profile.to_dict()
    assert d["auth"]["method"] == "google-sso"
    assert d["auth"]["google_client_id"] == "test.apps.googleusercontent.com"
    assert "google_client_secret" not in d["auth"]
    assert d["auth"]["session_token"] == "sess_abc"


def test_profile_google_sso_auth_with_secret():
    """google_client_secret roundtrip: stored and serialised when provided."""
    profile = Profile.from_dict("sso-web", {
        "url": "https://metabase.test.com",
        "auth": {
            "method": "google-sso",
            "google_client_id": "test.apps.googleusercontent.com",
            "google_client_secret": "GOCSPX-supersecret",
            "session_token": "sess_xyz",
        },
    })
    assert profile.auth.google_client_secret == "GOCSPX-supersecret"

    d = profile.to_dict()
    assert d["auth"]["google_client_secret"] == "GOCSPX-supersecret"
    assert d["auth"]["google_client_id"] == "test.apps.googleusercontent.com"
    assert d["auth"]["session_token"] == "sess_xyz"


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
