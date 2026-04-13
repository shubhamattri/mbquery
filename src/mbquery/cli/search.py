"""mbquery search — search across Metabase."""
from __future__ import annotations

from typing import Optional

import typer

from mbquery.cli.config_cmd import require_profile
from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult
from mbquery.core.search import search
from mbquery.formatters import format_result
from mbquery.utils.tty import auto_format


def search_cmd(query: str = typer.Argument(..., help="Search query"), type: Optional[str] = typer.Option(None, "--type", "-t"), format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """Search across all Metabase content."""
    from rich.console import Console
    err_console = Console(stderr=True)
    store = ConfigStore()
    active = require_profile(store, profile)
    client = MetabaseClient(active)
    try:
        results = search(client, query, model_type=type)
        qr = QueryResult(
            columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "name", "base_type": "type/Text", "semantic_type": None}, {"name": "model", "base_type": "type/Text", "semantic_type": None}],
            rows=[[r["id"], r["name"], r.get("model", "")] for r in results],
            row_count=len(results),
        )
        typer.echo(format_result(qr, format or auto_format()))
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()
