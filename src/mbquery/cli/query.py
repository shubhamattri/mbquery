"""mbquery query — execute SQL queries."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from mbquery.cli.config_cmd import require_profile
from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import execute_sql
from mbquery.formatters import format_result
from mbquery.formatters.redact import redact_pii
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)


def query_cmd(
    sql: Optional[str] = typer.Argument(None, help="SQL query to execute"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read SQL from file"),
    format: Optional[str] = typer.Option(None, "--format", help="Output format: table, csv, json, jsonl, markdown"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
    db: Optional[int] = typer.Option(None, "--db", help="Database ID"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Row limit"),
    no_redact: bool = typer.Option(False, "--no-redact", help="Disable PII redaction"),
    fields: Optional[str] = typer.Option(None, "--fields", help="Comma-separated column names to include"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show HTTP requests"),
) -> None:
    """Execute a SQL query against Metabase."""
    if not sql and not file:
        err_console.print("[red]Error:[/] Provide SQL as argument or use --file")
        raise typer.Exit(1)

    if file:
        if not file.exists():
            err_console.print(f"[red]Error:[/] File not found: {file}")
            raise typer.Exit(1)
        sql = file.read_text().strip()

    assert sql is not None

    store = ConfigStore()
    try:
        active_profile = require_profile(store, profile)
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)

    database_id = db or active_profile.default_db
    if not database_id:
        err_console.print(
            "[red]Error:[/] No database specified. Use --db <id> or set a default:\n"
            "  mbquery config add <profile> --url <url> --api-key <key> --db <id>"
        )
        raise typer.Exit(1)

    config = store.load()
    row_limit = limit or config.defaults.limit
    should_redact = config.defaults.redact_pii and not no_redact
    output_format = format or auto_format()

    client = MetabaseClient(active_profile, verbose=verbose)
    try:
        result = execute_sql(client, sql, database_id=database_id, limit=row_limit)
    except Exception as e:
        err_console.print(f"[red]Error executing query:[/] {e}")
        raise typer.Exit(1)
    finally:
        client.close()

    if should_redact:
        result = redact_pii(result)

    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        result = result.filter_fields(field_list)

    output = format_result(result, output_format)
    typer.echo(output)
