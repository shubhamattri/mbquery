"""mbquery config — profile and setup management."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mbquery.config.store import ConfigStore

err_console = Console(stderr=True)
out_console = Console()
config_app = typer.Typer(name="config", help="Manage profiles and settings.", no_args_is_help=True)


def require_profile(store: ConfigStore, profile_name: str | None = None) -> "Profile":
    """Resolve profile, auto-launching setup wizard if unconfigured.

    This is the single entry point all commands should use instead of
    store.resolve_profile() directly. It provides a friendly first-run
    experience instead of a cryptic error.
    """
    from mbquery.config.models import Profile  # noqa: F811

    if not profile_name and not store.is_configured():
        # Check env vars first
        import os

        if os.environ.get("MBQUERY_URL") and os.environ.get("MBQUERY_API_KEY"):
            return store.resolve_profile()

        err_console.print()
        err_console.print(
            Panel(
                "[bold]Welcome to mbquery![/]\n\n"
                "No profile configured yet. Let's set one up — takes 30 seconds.",
                title="First Run",
                border_style="cyan",
            )
        )
        err_console.print()
        _run_init_wizard(store)

    return store.resolve_profile(profile_name)


def _test_connection(store: ConfigStore, profile_name: str) -> bool:
    """Test Metabase connection and print result."""
    from mbquery.core.client import MetabaseClient

    profile = store.resolve_profile(profile_name)
    client = MetabaseClient(profile)
    try:
        user = client.test_connection()
        first = user.get("first_name", "")
        last = user.get("last_name", "")
        email = user.get("email", "")
        err_console.print(f"  [green]Connected as: {first} {last} ({email})[/]")
        return True
    except Exception as e:
        err_console.print(f"  [red]Connection failed:[/] {e}")
        err_console.print("  Check your URL and credentials and try again.")
        return False
    finally:
        client.close()


def _run_init_wizard(store: ConfigStore) -> None:
    """Interactive setup wizard. Called by `config init` or auto on first run."""
    # Step 1: Metabase URL
    while True:
        url = typer.prompt("  Metabase URL (e.g. https://metabase.yourcompany.com)")
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            err_console.print("  [yellow]URL must start with http:// or https://[/]")
            continue
        break

    # Step 2: Auth method
    err_console.print()
    err_console.print("  How do you authenticate?")
    err_console.print("    [bold]1.[/] API Key [dim](recommended — get one from Admin > Settings > Authentication)[/]")
    err_console.print("    [bold]2.[/] Email + Password")
    err_console.print("    [bold]3.[/] Google SSO [dim](opens browser for Google sign-in)[/]")
    auth_choice = typer.prompt("  Choice", type=int, default=1)

    api_key = email = password = None
    google_client_id = None
    google_client_secret = None
    if auth_choice == 1:
        api_key = typer.prompt("  API Key", hide_input=True)
        auth_method = "api-key"
    elif auth_choice == 3:
        auth_method = "google-sso"
        from mbquery.auth.google_sso import fetch_google_client_id
        err_console.print("  Fetching Google client ID from Metabase...")
        google_client_id = fetch_google_client_id(url)
        if not google_client_id:
            google_client_id = typer.prompt("  Google OAuth Client ID (from Google Cloud Console)")
        err_console.print()
        err_console.print("  [bold]Google Client Secret[/] (one-time admin setup):")
        err_console.print("    Get it from Google Cloud Console → OAuth 2.0 Client → Client Secret")
        err_console.print("    This is only needed once — all team members share the same config.")
        secret_input = typer.prompt("  Client Secret (press Enter to skip)", default="", hide_input=True)
        google_client_secret = secret_input if secret_input else None
    else:
        email = typer.prompt("  Email")
        password = typer.prompt("  Password", hide_input=True)
        auth_method = "session"

    # Step 3: Profile name
    name = typer.prompt("  Profile name", default="default")

    # Step 4: Save and test connection
    err_console.print()
    store.add_profile(
        name=name, url=url, auth_method=auth_method,
        api_key=api_key, email=email, password=password,
    )

    # For Google SSO, store client_id/secret and run initial login
    if auth_method == "google-sso":
        config = store.load()
        profile = config.profiles[name]
        profile.auth.google_client_id = google_client_id
        profile.auth.google_client_secret = google_client_secret
        store.save(config)

        err_console.print("  Running Google SSO login...")
        from mbquery.auth.google_sso import google_sso_login
        try:
            session_token = google_sso_login(
                metabase_url=url,
                google_client_id=google_client_id,
                google_client_secret=google_client_secret,
            )
            config = store.load()
            config.profiles[name].auth.session_token = session_token
            store.save(config)
        except Exception as e:
            err_console.print(f"  [yellow]Warning:[/] SSO login failed: {e}")
            err_console.print("  Run [bold]mbquery login[/] to authenticate later.")

    err_console.print("  Testing connection...")
    if not _test_connection(store, name):
        err_console.print()
        err_console.print("  [yellow]Profile saved but connection failed.[/]")
        err_console.print("  You can fix it later: [bold]mbquery config add <name> --url <url> --api-key <key>[/]")
        err_console.print()
        return

    # Step 5: Database ID (only ask after successful connection)
    err_console.print()
    err_console.print("  [dim]Tip: Find your database ID in Metabase Admin > Databases[/]")
    db_str = typer.prompt("  Default database ID (press Enter to skip)", default="")
    if db_str:
        config = store.load()
        profile = config.profiles[name]
        profile.default_db = int(db_str)
        store.save(config)

    # Step 6: LLM setup (optional)
    err_console.print()
    setup_llm = typer.confirm("  Enable natural language queries (AI-powered)?", default=True)
    if setup_llm:
        err_console.print()
        _run_llm_wizard(store)

    # Done!
    err_console.print()

    # Warn if no default_db was configured
    config_check = store.load()
    profile_check = config_check.profiles.get(name)
    if profile_check and not profile_check.default_db:
        err_console.print(Panel(
            "[yellow]⚠️  No default database set.[/] You'll need to pass [bold]--db <id>[/] with every command.\n\n"
            "To set a default later:\n"
            "  [bold]mbquery config add <name> --url <url> --api-key <key> --db <id>[/]\n\n"
            "Find your database ID in [bold]Metabase Admin > Databases[/].",
            title="Warning",
            border_style="yellow",
        ))
        err_console.print()

    err_console.print(Panel(
        "[bold green]Setup complete![/]\n\n"
        "Try these commands:\n"
        "  [bold]mbquery query \"SELECT 1\"[/]           — run SQL\n"
        "  [bold]mbquery ask \"count all users\"[/]      — natural language\n"
        "  [bold]mbquery schema tables[/]               — browse schema\n"
        "  [bold]mbquery card list[/]                   — saved questions\n"
        "  [bold]mbquery --help[/]                      — all commands",
        title="Ready",
        border_style="green",
    ))


def _run_llm_wizard(store: ConfigStore) -> None:
    """Interactive LLM provider setup."""
    err_console.print("  Choose your LLM provider:")
    err_console.print("    [bold]1.[/] OpenAI [dim](GPT-4o, GPT-4o-mini)[/]")
    err_console.print("    [bold]2.[/] Google Gemini [dim](free tier available)[/]")
    err_console.print("    [bold]3.[/] Anthropic Claude [dim](via OpenAI-compatible API)[/]")
    err_console.print("    [bold]4.[/] Ollama [dim](local, free, no API key)[/]")
    err_console.print("    [bold]5.[/] Other OpenAI-compatible endpoint")
    err_console.print("    [bold]6.[/] Skip for now")
    choice = typer.prompt("\n  Choice", type=int)

    if choice == 6:
        err_console.print("  Skipped. You can set it up later: [bold]mbquery config set-llm[/]")
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

    err_console.print()
    err_console.print("  Choose model:")
    for i, (m, desc) in enumerate(models, 1):
        label = f"{m} [dim]({desc})[/]" if desc else m
        err_console.print(f"    [bold]{i}.[/] {label}")
    model_choice = typer.prompt("\n  Choice", type=int, default=1)
    model = models[min(model_choice, len(models)) - 1][0]

    if model == "custom":
        model = typer.prompt("  Model name")

    base_url = None
    base_url_map = {3: "https://api.anthropic.com/v1", 4: "http://localhost:11434/v1"}
    base_url = base_url_map.get(choice)

    if choice == 5:
        base_url = typer.prompt("  Base URL")

    api_key = None
    if choice == 4:
        api_key = "ollama"
    else:
        api_key = typer.prompt("  API Key", hide_input=True)

    store.set_llm(provider=provider, model=model, api_key=api_key, base_url=base_url)
    err_console.print(f"  [green]LLM configured:[/] {provider}/{model}")


# --- CLI Commands ---


@config_app.command()
def init() -> None:
    """Interactive setup wizard."""
    store = ConfigStore()
    if store.is_configured():
        err_console.print("  Already configured. Profiles:")
        for name in store.list_profiles():
            err_console.print(f"    - {name}")
        if not typer.confirm("\n  Run setup again? (will add a new profile)", default=False):
            return
    _run_init_wizard(store)


@config_app.command(name="list")
def config_list() -> None:
    """List all configured profiles."""
    store = ConfigStore()
    config = store.load()
    if not config.profiles:
        err_console.print("No profiles configured yet.")
        err_console.print("Run: [bold]mbquery config init[/]")
        return
    table = Table(title="Profiles")
    table.add_column("Name", style="bold")
    table.add_column("URL")
    table.add_column("Auth")
    table.add_column("Default DB")
    table.add_column("Active", justify="center")
    for name, profile in config.profiles.items():
        is_active = "✓" if name == config.active_profile else ""
        table.add_row(name, profile.url, profile.auth.method, str(profile.default_db or "-"), is_active)
    out_console.print(table)

    if config.llm:
        err_console.print(f"\nLLM: {config.llm.provider}/{config.llm.model}")
    else:
        err_console.print("\nLLM: [yellow]not configured[/] (run: mbquery config set-llm)")


@config_app.command()
def add(
    name: str = typer.Argument(..., help="Profile name"),
    url: str = typer.Option(..., "--url", help="Metabase URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key"),
    email: Optional[str] = typer.Option(None, "--email", help="Email for session auth"),
    password: Optional[str] = typer.Option(None, "--password", help="Password"),
    db: Optional[int] = typer.Option(None, "--db", help="Default database ID"),
    google_sso: bool = typer.Option(False, "--google-sso", help="Use Google SSO authentication"),
    google_client_id: Optional[str] = typer.Option(None, "--google-client-id", help="Google OAuth client ID"),
    google_client_secret: Optional[str] = typer.Option(None, "--google-client-secret", help="Google OAuth client secret (Web app clients)"),
) -> None:
    """Add a new Metabase profile."""
    if api_key:
        auth_method = "api-key"
    elif email:
        auth_method = "session"
    elif google_sso:
        auth_method = "google-sso"
    else:
        err_console.print("[red]Error:[/] Provide --api-key, --email + --password, or --google-sso")
        raise typer.Exit(1)

    store = ConfigStore()
    store.add_profile(
        name=name, url=url, auth_method=auth_method,
        api_key=api_key, email=email, password=password, default_db=db,
    )

    if auth_method == "google-sso":
        config = store.load()
        profile = config.profiles[name]
        if not google_client_id:
            from mbquery.auth.google_sso import fetch_google_client_id
            google_client_id = fetch_google_client_id(url)
            if not google_client_id:
                err_console.print("[red]Error:[/] Could not fetch Google client ID from Metabase. Provide --google-client-id")
                store.remove_profile(name)
                raise typer.Exit(1)
        profile.auth.google_client_id = google_client_id
        profile.auth.google_client_secret = google_client_secret
        store.save(config)
        err_console.print(f"Profile '{name}' added with Google SSO auth.")
        err_console.print("Run [bold]mbquery login[/] to authenticate.")
        return

    err_console.print(f"Profile '{name}' added.")

    # Test connection
    err_console.print("Testing connection...")
    _test_connection(store, name)


@config_app.command()
def switch(name: str = typer.Argument(..., help="Profile to switch to")) -> None:
    """Switch active profile."""
    store = ConfigStore()
    try:
        store.switch_profile(name)
        err_console.print(f"Switched to profile '[bold]{name}[/]'.")
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)


@config_app.command(name="set-llm")
def set_llm_cmd(
    provider: Optional[str] = typer.Option(None, "--provider"),
    model: Optional[str] = typer.Option(None, "--model"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
) -> None:
    """Configure LLM for natural language queries."""
    store = ConfigStore()
    if not provider:
        # Interactive mode
        _run_llm_wizard(store)
        return

    store.set_llm(provider=provider, model=model or "gpt-4o", api_key=api_key, base_url=base_url)
    err_console.print(f"LLM configured: {provider}/{model}")


@config_app.command(name="set-hints")
def set_hints(
    table: str = typer.Argument(..., help="Table name"),
    hint: str = typer.Argument(..., help="Hint text"),
) -> None:
    """Add a schema hint for better NL→SQL."""
    import yaml

    store = ConfigStore()
    hints_file = store.config_dir / "hints.yaml"
    hints = {}
    if hints_file.exists():
        with open(hints_file, encoding="utf-8") as f:
            hints = yaml.safe_load(f) or {}
    hints[table] = hint
    with open(hints_file, "w", encoding="utf-8") as f:
        yaml.dump(hints, f, default_flow_style=False)
    err_console.print(f"Hint saved for table '[bold]{table}[/]'.")


@config_app.command()
def test() -> None:
    """Test connection to active Metabase profile."""
    store = ConfigStore()
    if not store.is_configured():
        err_console.print("No profiles configured. Run: [bold]mbquery config init[/]")
        raise typer.Exit(1)
    config = store.load()
    err_console.print(f"Testing profile '[bold]{config.active_profile}[/]'...")
    if not _test_connection(store, config.active_profile):
        raise typer.Exit(1)
