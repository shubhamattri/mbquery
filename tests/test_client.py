import httpx
import pytest
import respx
from mbquery.core.client import MetabaseClient
from mbquery.config.models import Profile, AuthConfig


@pytest.fixture
def api_key_profile() -> Profile:
    return Profile(name="test", url="https://metabase.test.com", auth=AuthConfig(method="api-key", api_key="mb_testkey"), default_db=2)


@respx.mock
def test_client_get_with_api_key(api_key_profile):
    route = respx.get("https://metabase.test.com/api/user/current").respond(json={"id": 1, "email": "test@test.com", "first_name": "Test", "last_name": "User"})
    client = MetabaseClient(api_key_profile)
    result = client.get("/api/user/current")
    assert result["email"] == "test@test.com"
    assert route.called
    assert route.calls[0].request.headers["x-api-key"] == "mb_testkey"


@respx.mock
def test_client_post(api_key_profile):
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[42]], "cols": [{"name": "count"}]}})
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
    profile = Profile(name="test", url="https://metabase.test.com", auth=AuthConfig(method="session", email="a@b.com", password="pass"))
    respx.post("https://metabase.test.com/api/session").respond(json={"id": "sess_token_123"})
    respx.get("https://metabase.test.com/api/user/current").respond(json={"id": 1, "email": "a@b.com", "first_name": "A", "last_name": "B"})
    client = MetabaseClient(profile)
    result = client.get("/api/user/current")
    assert result["email"] == "a@b.com"
    req = respx.calls[-1].request
    assert req.headers["x-metabase-session"] == "sess_token_123"
