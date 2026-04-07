"""mbquery dashboard — dashboard operations."""
from __future__ import annotations
from typing import Optional
import typer
from rich.console import Console
from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.dashboards import list_dashboards, get_dashboard
from mbquery.core.queries import QueryResult
from mbquery.formatters import format_result
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)
dashboard_app = typer.Typer(name="dashboard", help="Dashboard operations.", no_args_is_help=True)

@dashboard_app.command(name="list")
def dash_list(format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """List all dashboards."""
    store = ConfigStore()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        dashboards = list_dashboards(client)
        result = QueryResult(
            columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "name", "base_type": "type/Text", "semantic_type": None}, {"name": "collection_id", "base_type": "type/Integer", "semantic_type": None}],
            rows=[[d["id"], d["name"], d.get("collection_id", "")] for d in dashboards],
            row_count=len(dashboards),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()

@dashboard_app.command()
def show(dashboard_id: int = typer.Argument(..., help="Dashboard ID"), format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """Show dashboard structure."""
    store = ConfigStore()
    active = store.resolve_profile(profile)
    client = MetabaseClient(active)
    try:
        dash = get_dashboard(client, dashboard_id)
        dashcards = dash.get("dashcards", dash.get("ordered_cards", []))
        result = QueryResult(
            columns=[{"name": "card_id", "base_type": "type/Integer", "semantic_type": None}, {"name": "card_name", "base_type": "type/Text", "semantic_type": None}, {"name": "size", "base_type": "type/Text", "semantic_type": None}],
            rows=[[dc.get("card", {}).get("id", ""), dc.get("card", {}).get("name", ""), f"{dc.get('size_x', '')}x{dc.get('size_y', '')}"] for dc in dashcards if dc.get("card")],
            row_count=len(dashcards),
        )
        typer.echo(format_result(result, format or auto_format()))
    finally:
        client.close()
