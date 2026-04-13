import pytest
import respx
from unittest.mock import patch, MagicMock
from mbquery.auth.google_sso import (
    fetch_google_client_id,
    google_sso_login,
    _generate_pkce,
    DEFAULT_CALLBACK_PORT,
    _check_port_available,
    _OAuthCallbackHandler,
)


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


def test_default_callback_port():
    """Fixed port must be 8766."""
    assert DEFAULT_CALLBACK_PORT == 8766


def test_pkce_generation():
    """PKCE verifier must be 86 chars (token_urlsafe(64)); challenge must be valid base64url."""
    import base64
    import hashlib

    code_verifier, code_challenge = _generate_pkce()

    # token_urlsafe(64) produces 86 URL-safe chars
    assert len(code_verifier) == 86
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in code_verifier)

    # Verify the challenge is sha256(verifier) base64url-encoded without padding
    expected_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
    assert code_challenge == expected_challenge

    # No padding characters allowed in PKCE challenge
    assert "=" not in code_challenge


def test_pkce_verifier_and_challenge_differ():
    """Each call must produce a fresh, unique pair."""
    v1, c1 = _generate_pkce()
    v2, c2 = _generate_pkce()
    assert v1 != v2
    assert c1 != c2


def test_google_sso_login_raises_if_port_occupied():
    """google_sso_login must raise ValueError (not silently use another port) when port is busy."""
    with patch("mbquery.auth.google_sso._check_port_available", return_value=False):
        with pytest.raises(ValueError, match="already in use"):
            google_sso_login(
                metabase_url="https://metabase.test.com",
                google_client_id="test-client-id",
                callback_port=8766,
            )


@respx.mock
def test_google_sso_login_full_flow():
    """Full SSO flow: PKCE, state verification, token exchange, Metabase auth."""
    fixed_state = "test_state_value_abc123"
    fixed_verifier = "A" * 86  # mock verifier — token_urlsafe(64) returns 86 chars
    fixed_challenge = "test_challenge_value"

    mock_server = MagicMock()
    # Simulate the callback handler receiving the auth code after one iteration
    call_count = {"n": 0}

    def fake_handle_request():
        call_count["n"] += 1
        if call_count["n"] == 1:
            _OAuthCallbackHandler.auth_code = "test_auth_code"
            _OAuthCallbackHandler.error = None

    mock_server.handle_request.side_effect = fake_handle_request
    mock_server.server_close = MagicMock()

    respx.post("https://oauth2.googleapis.com/token").respond(json={
        "id_token": "test_id_token",
        "access_token": "test_access_token",
    })
    respx.post("https://metabase.test.com/api/session/google_auth").respond(json={
        "id": "metabase_session_token_xyz",
    })

    with patch("mbquery.auth.google_sso._check_port_available", return_value=True), \
         patch("mbquery.auth.google_sso.HTTPServer", return_value=mock_server), \
         patch("mbquery.auth.google_sso.webbrowser.open"), \
         patch("mbquery.auth.google_sso.secrets.token_urlsafe", return_value=fixed_state), \
         patch("mbquery.auth.google_sso._generate_pkce", return_value=(fixed_verifier, fixed_challenge)):

        # Reset handler state before test
        _OAuthCallbackHandler.auth_code = None
        _OAuthCallbackHandler.error = None
        _OAuthCallbackHandler.expected_state = None

        session_token = google_sso_login(
            metabase_url="https://metabase.test.com",
            google_client_id="test-client-id",
            google_client_secret="test-client-secret",
        )

    assert session_token == "metabase_session_token_xyz"
    mock_server.server_close.assert_called_once()

    # Verify both PKCE code_verifier AND client_secret are sent together
    token_request = respx.calls[0].request
    assert b"code_verifier=" + fixed_verifier.encode() in token_request.content
    assert b"client_secret=test-client-secret" in token_request.content


@respx.mock
def test_google_sso_login_pkce_only_no_client_secret():
    """Without client_secret, only PKCE code_verifier is sent (Desktop OAuth client flow)."""
    fixed_state = "test_state_value_abc123"
    fixed_verifier = "B" * 86
    fixed_challenge = "test_challenge_value_2"

    mock_server = MagicMock()
    call_count = {"n": 0}

    def fake_handle_request():
        call_count["n"] += 1
        if call_count["n"] == 1:
            _OAuthCallbackHandler.auth_code = "test_auth_code_2"
            _OAuthCallbackHandler.error = None

    mock_server.handle_request.side_effect = fake_handle_request
    mock_server.server_close = MagicMock()

    respx.post("https://oauth2.googleapis.com/token").respond(json={
        "id_token": "test_id_token_2",
        "access_token": "test_access_token_2",
    })
    respx.post("https://metabase.test.com/api/session/google_auth").respond(json={
        "id": "metabase_session_token_pkce_only",
    })

    with patch("mbquery.auth.google_sso._check_port_available", return_value=True), \
         patch("mbquery.auth.google_sso.HTTPServer", return_value=mock_server), \
         patch("mbquery.auth.google_sso.webbrowser.open"), \
         patch("mbquery.auth.google_sso.secrets.token_urlsafe", return_value=fixed_state), \
         patch("mbquery.auth.google_sso._generate_pkce", return_value=(fixed_verifier, fixed_challenge)):

        _OAuthCallbackHandler.auth_code = None
        _OAuthCallbackHandler.error = None
        _OAuthCallbackHandler.expected_state = None

        session_token = google_sso_login(
            metabase_url="https://metabase.test.com",
            google_client_id="test-client-id",
            # No google_client_secret — Desktop OAuth client
        )

    assert session_token == "metabase_session_token_pkce_only"

    # PKCE verifier present, client_secret absent
    token_request = respx.calls[0].request
    assert b"code_verifier=" + fixed_verifier.encode() in token_request.content
    assert b"client_secret" not in token_request.content


def test_oauth_callback_handler_ignores_favicon():
    """Non-/callback paths must return 404 without touching auth_code."""
    from io import BytesIO
    from unittest.mock import MagicMock

    handler = _OAuthCallbackHandler.__new__(_OAuthCallbackHandler)
    handler.path = "/favicon.ico"
    handler.send_response = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()

    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None
    _OAuthCallbackHandler.expected_state = None

    handler.do_GET()

    handler.send_response.assert_called_with(404)
    assert _OAuthCallbackHandler.auth_code is None


def test_oauth_callback_handler_state_mismatch():
    """Callback with wrong state must set error and return 400."""
    from unittest.mock import MagicMock

    handler = _OAuthCallbackHandler.__new__(_OAuthCallbackHandler)
    handler.path = "/callback?code=abc&state=wrong_state"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()

    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None
    _OAuthCallbackHandler.expected_state = "correct_state"

    handler.do_GET()

    handler.send_response.assert_called_with(400)
    assert _OAuthCallbackHandler.error == "state_mismatch"
    assert _OAuthCallbackHandler.auth_code is None


def test_oauth_callback_handler_valid_state():
    """Callback with correct state must set auth_code."""
    from unittest.mock import MagicMock

    correct_state = "correct_state_value"
    handler = _OAuthCallbackHandler.__new__(_OAuthCallbackHandler)
    handler.path = f"/callback?code=valid_auth_code&state={correct_state}"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = MagicMock()

    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None
    _OAuthCallbackHandler.expected_state = correct_state

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    assert _OAuthCallbackHandler.auth_code == "valid_auth_code"
    assert _OAuthCallbackHandler.error is None
