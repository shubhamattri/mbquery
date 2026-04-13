"""mbquery login — authenticate via Google SSO."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

err_console = Console(stderr=True)


def login_cmd(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
) -> None:
    """Authenticate via Google SSO (opens browser)."""
    from mbquery.config.store import ConfigStore
    from mbquery.auth.google_sso import google_sso_login, fetch_google_client_id

    store = ConfigStore()
    if not store.is_configured():
        err_console.print("[red]Error:[/] No profile configured. Run: mbquery config init")
        raise typer.Exit(1)

    config = store.load()
    profile_name = profile or config.active_profile
    if not profile_name or profile_name not in config.profiles:
        err_console.print("[red]Error:[/] No active profile.")
        raise typer.Exit(1)

    prof = config.profiles[profile_name]

    if prof.auth.method != "google-sso":
        err_console.print(f"[yellow]Profile '{profile_name}' uses {prof.auth.method} auth, not Google SSO.[/]")
        err_console.print("Login is only needed for Google SSO profiles.")
        raise typer.Exit(1)

    if not prof.auth.google_client_id:
        err_console.print("  Fetching Google client ID from Metabase...")
        client_id = fetch_google_client_id(prof.url)
        if not client_id:
            client_id = typer.prompt("  Google OAuth Client ID (from Google Cloud Console)")
        prof.auth.google_client_id = client_id
        store.save(config)

    try:
        session_token = google_sso_login(
            metabase_url=prof.url,
            google_client_id=prof.auth.google_client_id,
            google_client_secret=prof.auth.google_client_secret,
        )
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

    # Store the session token
    prof.auth.session_token = session_token
    store.save(config)

    # Verify it works
    from mbquery.core.client import MetabaseClient
    client = MetabaseClient(prof)
    try:
        user = client.test_connection()
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        email = user.get("email", "")
        err_console.print(f"\n  [green]Logged in as: {name} ({email})[/]")
    except Exception as e:
        err_console.print(f"  [yellow]Warning:[/] Session saved but verification failed: {e}")
    finally:
        client.close()
