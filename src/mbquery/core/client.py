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
        self._authenticated = False

    def _ensure_auth(self) -> None:
        """Lazily authenticate on first request for session auth."""
        if self.profile.auth.method == "session" and not self._authenticated:
            resp = self._http.post(
                f"{self._base_url}/api/session",
                json={"username": self.profile.auth.email, "password": self.profile.auth.password},
            )
            resp.raise_for_status()
            self._session_token = resp.json()["id"]
            self._authenticated = True

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.profile.auth.method == "api-key":
            headers["x-api-key"] = self.profile.auth.api_key or ""
        elif self._session_token:
            headers["x-metabase-session"] = self._session_token
        return headers

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        self._ensure_auth()
        url = f"{self._base_url}{endpoint}"
        if self.verbose:
            import sys
            print(f"GET {url}", file=sys.stderr)
        resp = self._http.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, endpoint: str, json: dict | None = None) -> dict:
        self._ensure_auth()
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
        return self.get("/api/user/current")
