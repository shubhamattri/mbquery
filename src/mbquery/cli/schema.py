"""mbquery schema — browse database schema."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.database import list_databases
from mbquery.core.queries import QueryResult
from mbquery.core.schema_cache import SchemaCache
from mbquery.formatters import format_result
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)
schema_app = typer.Typer(name="schema", help="Browse database schema.", no_args_is_help=True)

def _get_client_and_profile(profile_name: str | None = None):
    from mbquery.cli.config_cmd import require_profile
    store = ConfigStore()
    active = require_profile(store, profile_name)
    return MetabaseClient(active), active, store

@schema_app.command()
def databases(format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """List all databases."""
    client, active, store = _get_client_and_profile(profile)
    try:
        dbs = list_databases(client)
        if isinstance(dbs, dict):
            dbs = dbs.get("data", [dbs])
        result = QueryResult(
            columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "name", "base_type": "type/Text", "semantic_type": None}, {"name": "engine", "base_type": "type/Text", "semantic_type": None}],
            rows=[[db["id"], db["name"], db.get("engine", "")] for db in dbs],
            row_count=len(dbs),
        )
        typer.echo(format_result(result, format or auto_format()))
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

@schema_app.command()
def tables(db: Optional[int] = typer.Option(None, "--db"), format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """List tables in a database."""
    client, active, store = _get_client_and_profile(profile)
    database_id = db or active.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    try:
        cache = SchemaCache(store.config_dir / "schema_cache")
        schema = cache.get_schema(client, database_id=database_id, profile_name=active.name)
        tbl_list = schema.get("tables", [])
        result = QueryResult(
            columns=[{"name": "name", "base_type": "type/Text", "semantic_type": None}, {"name": "schema", "base_type": "type/Text", "semantic_type": None}, {"name": "fields", "base_type": "type/Integer", "semantic_type": None}],
            rows=[[t["name"], t.get("schema", ""), len(t.get("fields", []))] for t in tbl_list],
            row_count=len(tbl_list),
        )
        typer.echo(format_result(result, format or auto_format()))
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

@schema_app.command()
def fields(table_name: str = typer.Argument(..., help="Table name"), db: Optional[int] = typer.Option(None, "--db"), format: Optional[str] = typer.Option(None, "--format"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """List fields in a table."""
    client, active, store = _get_client_and_profile(profile)
    database_id = db or active.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    try:
        cache = SchemaCache(store.config_dir / "schema_cache")
        schema = cache.get_schema(client, database_id=database_id, profile_name=active.name)
        table = next((t for t in schema.get("tables", []) if t["name"] == table_name), None)
        if not table:
            err_console.print(f"[red]Error:[/] Table '{table_name}' not found.")
            raise typer.Exit(1)
        flds = table.get("fields", [])
        result = QueryResult(
            columns=[{"name": "name", "base_type": "type/Text", "semantic_type": None}, {"name": "base_type", "base_type": "type/Text", "semantic_type": None}, {"name": "semantic_type", "base_type": "type/Text", "semantic_type": None}],
            rows=[[f["name"], f.get("base_type", ""), f.get("semantic_type", "") or ""] for f in flds],
            row_count=len(flds),
        )
        typer.echo(format_result(result, format or auto_format()))
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

@schema_app.command()
def refresh(db: Optional[int] = typer.Option(None, "--db"), profile: Optional[str] = typer.Option(None, "--profile", "-p")) -> None:
    """Refresh cached schema from Metabase API."""
    client, active, store = _get_client_and_profile(profile)
    database_id = db or active.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    try:
        cache = SchemaCache(store.config_dir / "schema_cache")
        schema = cache.get_schema(client, database_id=database_id, profile_name=active.name, force_refresh=True)
        table_count = len(schema.get("tables", []))
        field_count = sum(len(t.get("fields", [])) for t in schema.get("tables", []))
        typer.echo(f"Schema cached: {table_count} tables, {field_count} fields.")
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()
