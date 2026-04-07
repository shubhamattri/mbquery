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
        table.add_row(name, profile.url, profile.auth.method, str(profile.default_db or ""), is_active)
    out_console.print(table)

@config_app.command()
def add(name: str = typer.Argument(...), url: str = typer.Option(..., "--url"), api_key: Optional[str] = typer.Option(None, "--api-key"), email: Optional[str] = typer.Option(None, "--email"), password: Optional[str] = typer.Option(None, "--password"), db: Optional[int] = typer.Option(None, "--db")) -> None:
    """Add a new Metabase profile."""
    if api_key:
        auth_method = "api-key"
    elif email:
        auth_method = "session"
    else:
        err_console.print("[red]Error:[/] Provide --api-key or --email + --password")
        raise typer.Exit(1)
    store = ConfigStore()
    store.add_profile(name=name, url=url, auth_method=auth_method, api_key=api_key, email=email, password=password, default_db=db)
    typer.echo(f"Profile '{name}' added.")

@config_app.command()
def switch(name: str = typer.Argument(...)) -> None:
    """Switch active profile."""
    store = ConfigStore()
    try:
        store.switch_profile(name)
        typer.echo(f"Switched to profile '{name}'.")
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

@config_app.command(name="set-llm")
def set_llm_cmd(provider: Optional[str] = typer.Option(None, "--provider"), model: Optional[str] = typer.Option(None, "--model"), api_key: Optional[str] = typer.Option(None, "--api-key"), base_url: Optional[str] = typer.Option(None, "--base-url")) -> None:
    """Configure LLM for natural language queries (interactive if no flags)."""
    if not provider:
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
            2: [("gemini-2.0-flash", "recommended"), ("gemini-2.5-pro", "best quality"), ("custom", None)],
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
        model = models[min(model_choice, len(models)) - 1][0]
        if model == "custom":
            model = typer.prompt("  Model name")
        base_url_map = {3: "https://api.anthropic.com/v1", 4: "http://localhost:11434/v1"}
        base_url = base_url_map.get(choice)
        if choice == 5:
            base_url = typer.prompt("  Base URL")
        if choice != 4:
            api_key = typer.prompt("  API Key", hide_input=True)
        else:
            api_key = "ollama"
    store = ConfigStore()
    store.set_llm(provider=provider, model=model or "gpt-4o", api_key=api_key, base_url=base_url)
    typer.echo(f"LLM configured: {provider}/{model}")

@config_app.command(name="set-hints")
def set_hints(table: str = typer.Argument(...), hint: str = typer.Argument(...)) -> None:
    """Add a schema hint for better NL→SQL."""
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
    api_key = email = password = None
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
    store.add_profile(name=name, url=url, auth_method=auth_method, api_key=api_key, email=email, password=password, default_db=default_db)
    typer.echo(f"\n  Profile '{name}' saved.")
    setup_llm = typer.confirm("  Set up AI-powered natural language queries?", default=True)
    if setup_llm:
        set_llm_cmd()
    typer.echo("\n  You're ready! Try:")
    typer.echo("    mbquery query \"SELECT 1\"")
    typer.echo("    mbquery ask \"how many users signed up last week\"")
    typer.echo()
