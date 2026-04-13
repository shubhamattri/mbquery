import pytest
import respx
from mbquery.auth.google_sso import fetch_google_client_id


@respx.mock
def test_fetch_google_client_id():
    respx.get("https://metabase.test.com/api/session/properties").respond(json={
        "google-auth-client-id": "test-client-id.apps.googleusercontent.com",
        "google-auth-enabled": True,
    })
    client_id = fetch_google_client_id("https://metabase.test.com")
    assert client_id == "test-client-id.apps.googleusercontent.com"


@respx.mock
def test_fetch_google_client_id_not_configured():
    respx.get("https://metabase.test.com/api/session/properties").respond(json={
        "google-auth-enabled": False,
    })
    client_id = fetch_google_client_id("https://metabase.test.com")
    assert client_id is None


@respx.mock
def test_fetch_google_client_id_server_error():
    respx.get("https://metabase.test.com/api/session/properties").respond(status_code=500)
    client_id = fetch_google_client_id("https://metabase.test.com")
    assert client_id is None
