"""mbquery card — saved question operations."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.cli.config_cmd import require_profile
from mbquery.config.store import ConfigStore
from mbquery.core.cards import list_cards, run_card
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult
from mbquery.formatters import format_result
from mbquery.formatters.redact import redact_pii
from mbquery.utils.resolve import resolve_card_id
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)
card_app = typer.Typer(name="card", help="Saved question operations.", no_args_is_help=True)

@card_app.command(name="list")
def card_list(format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """List all saved questions."""
    store = ConfigStore()
    active = require_profile(store, profile)
    client = MetabaseClient(active)
    try:
        cards = list_cards(client)
        result = QueryResult(
            columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "name", "base_type": "type/Text", "semantic_type": None}, {"name": "collection_id", "base_type": "type/Integer", "semantic_type": None}, {"name": "display", "base_type": "type/Text", "semantic_type": None}],
            rows=[[c["id"], c["name"], c.get("collection_id", ""), c.get("display", "")] for c in cards],
            row_count=len(cards),
        )
        typer.echo(format_result(result, format or auto_format()))
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

@card_app.command(name="run")
def card_run(id_or_name: str = typer.Argument(..., help="Card ID or name"), param: Optional[list[str]] = typer.Option(None, "--param"), format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p"), no_redact: bool = typer.Option(False, "--no-redact"), fields: Optional[str] = typer.Option(None, "--fields")) -> None:
    """Execute a saved question by ID or name."""
    store = ConfigStore()
    config = store.load()
    active = require_profile(store, profile)
    client = MetabaseClient(active)
    try:
        card_id = resolve_card_id(client, id_or_name)
        parameters = {}
        if param:
            for p in param:
                key, _, value = p.partition("=")
                parameters[key] = value
        result = run_card(client, card_id, parameters=parameters or None)
        if config.defaults.redact_pii and not no_redact:
            result = redact_pii(result)
        if fields:
            result = result.filter_fields([f.strip() for f in fields.split(",")])
        typer.echo(format_result(result, format or auto_format()))
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()
