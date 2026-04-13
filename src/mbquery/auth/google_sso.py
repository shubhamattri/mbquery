"""Google SSO authentication for Metabase."""
from __future__ import annotations

import secrets
import socket
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
from rich.console import Console

err_console = Console(stderr=True)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_CALLBACK_PORT = 8766


def _check_port_available(port: int) -> bool:
    """Return True if the given port is free to bind on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback code."""
    auth_code: str | None = None
    error: str | None = None
    expected_state: str | None = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Ignore non-callback requests (favicon, etc.)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        # Verify state parameter (CSRF protection)
        received_state = params.get("state", [None])[0]
        if self.expected_state and received_state != self.expected_state:
            _OAuthCallbackHandler.error = "state_mismatch"
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Error: State mismatch (possible CSRF)</h2></body></html>")
            return

        if "code" in params:
            _OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family: system-ui; text-align: center; padding: 60px;">
                <h2>Authenticated!</h2>
                <p>You can close this tab and return to your terminal.</p>
                </body></html>
            """)
        elif "error" in params:
            _OAuthCallbackHandler.error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h2>Error: {_OAuthCallbackHandler.error}</h2></body></html>".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP server logs


def fetch_google_client_id(metabase_url: str) -> str | None:
    """Fetch Google OAuth client_id from Metabase's public properties."""
    try:
        resp = httpx.get(f"{metabase_url}/api/session/properties", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("google-auth-client-id")
    except Exception:
        return None


def google_sso_login(
    metabase_url: str,
    google_client_id: str,
    google_client_secret: str,
    callback_port: int = DEFAULT_CALLBACK_PORT,
) -> str:
    """Run the full Google SSO flow and return a Metabase session token.

    Opens browser for Google consent, captures auth code via localhost,
    exchanges for ID token, then authenticates with Metabase.

    The redirect URI is always http://127.0.0.1:<callback_port>/callback.
    Register this exact URI in your Google Cloud Console OAuth credentials.
    Default port is 8766.

    Returns the Metabase session token string.
    Raises ValueError on any failure.
    """
    if not google_client_secret:
        raise ValueError(
            "Google client_secret is required for OAuth. Get it from Google Cloud Console."
        )

    if not _check_port_available(callback_port):
        raise ValueError(
            f"Port {callback_port} is already in use. Free the port and try again.\n"
            f"Your Google Cloud Console redirect URI must be: "
            f"http://127.0.0.1:{callback_port}/callback"
        )

    redirect_uri = f"http://127.0.0.1:{callback_port}/callback"
    state = secrets.token_urlsafe(32)

    # Reset handler state
    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None
    _OAuthCallbackHandler.expected_state = state

    # Start local server
    server = HTTPServer(("127.0.0.1", callback_port), _OAuthCallbackHandler)
    server.timeout = 5  # 5 second timeout per handle_request() call

    # Build Google OAuth URL
    params = {
        "client_id": google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    err_console.print(f"\n  Opening browser for Google sign-in...")
    err_console.print(f"  [dim]If browser doesn't open, visit:[/]")
    err_console.print(f"  [dim]{auth_url[:80]}...[/]")
    webbrowser.open(auth_url)

    # Wait for callback — loop to handle favicon and other stray requests
    err_console.print("  Waiting for authentication...")
    deadline = time.time() + 120  # 2 minute total timeout
    while time.time() < deadline:
        server.handle_request()
        if _OAuthCallbackHandler.auth_code or _OAuthCallbackHandler.error:
            break
    server.server_close()

    if _OAuthCallbackHandler.error:
        raise ValueError(f"Google auth failed: {_OAuthCallbackHandler.error}")

    if not _OAuthCallbackHandler.auth_code:
        raise ValueError("No auth code received. Authentication timed out or was cancelled.")

    auth_code = _OAuthCallbackHandler.auth_code

    # Exchange auth code for tokens
    err_console.print("  Exchanging token...")
    token_data = {
        "code": auth_code,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    resp = httpx.post(GOOGLE_TOKEN_URL, data=token_data, timeout=15.0)
    if resp.status_code != 200:
        raise ValueError(f"Google token exchange failed: {resp.text}")

    tokens = resp.json()
    id_token = tokens.get("id_token")
    if not id_token:
        raise ValueError("No ID token in Google response")

    # Authenticate with Metabase using the Google ID token
    err_console.print("  Authenticating with Metabase...")
    mb_resp = httpx.post(
        f"{metabase_url}/api/session/google_auth",
        json={"token": id_token},
        timeout=15.0,
    )
    if mb_resp.status_code != 200:
        raise ValueError(f"Metabase Google auth failed: {mb_resp.text}")

    session = mb_resp.json()
    session_id = session.get("id")
    if not session_id:
        raise ValueError("No session ID in Metabase response")

    return session_id
