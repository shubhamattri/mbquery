"""mbquery ask — natural language to SQL queries."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from mbquery.ai.gemini import GeminiProvider
from mbquery.ai.openai_compat import OpenAICompatProvider
from mbquery.ai.prompt import build_nl_to_sql_prompt
from mbquery.config.store import ConfigStore
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import execute_sql
from mbquery.core.schema_cache import SchemaCache
from mbquery.formatters import format_result
from mbquery.formatters.redact import redact_pii
from mbquery.utils.tty import auto_format

err_console = Console(stderr=True)


def _create_llm_provider(llm_config):
    if llm_config.provider == "gemini":
        return GeminiProvider(api_key=llm_config.api_key, model=llm_config.model)
    else:
        return OpenAICompatProvider(
            api_key=llm_config.api_key or "",
            model=llm_config.model,
            base_url=llm_config.base_url or "https://api.openai.com/v1",
        )


def ask_cmd(
    question: str = typer.Argument(..., help="Natural language question"),
    show_sql: bool = typer.Option(False, "--show-sql", help="Print the generated SQL before executing"),
    format: Optional[str] = typer.Option(None, "--format", help="Output format"),
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to use"),
    db: Optional[int] = typer.Option(None, "--db", help="Database ID"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Row limit"),
    no_redact: bool = typer.Option(False, "--no-redact", help="Disable PII redaction"),
    fields: Optional[str] = typer.Option(None, "--fields", help="Comma-separated column names"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show HTTP requests"),
) -> None:
    """Ask a natural language question and get results from Metabase."""
    store = ConfigStore()
    config = store.load()
    if not config.llm:
        err_console.print("[red]Error:[/] No LLM configured. Run: mbquery config set-llm")
        raise typer.Exit(1)
    try:
        active_profile = store.resolve_profile(profile)
    except ValueError as e:
        err_console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    database_id = db or active_profile.default_db
    if not database_id:
        err_console.print("[red]Error:[/] No database specified.")
        raise typer.Exit(1)
    cache = SchemaCache(store.config_dir / "schema_cache")
    client = MetabaseClient(active_profile, verbose=verbose)
    try:
        schema = cache.get_schema(client, database_id=database_id, profile_name=active_profile.name)
        schema_text = cache.schema_to_prompt_context(schema)
        hints = None
        hints_file = store.config_dir / "hints.yaml"
        if hints_file.exists():
            import yaml
            with open(hints_file) as f:
                hints_data = yaml.safe_load(f)
            if hints_data:
                hints = "\n".join(f"- {k}: {v}" for k, v in hints_data.items())
        prompt = build_nl_to_sql_prompt(question, schema_text, hints=hints)
        provider = _create_llm_provider(config.llm)
        err_console.print("[dim]Generating SQL...[/]")
        sql = provider.generate_sql(prompt)
        if show_sql:
            err_console.print(f"\n[bold cyan]Generated SQL:[/]\n  {sql}\n")
        row_limit = limit or config.defaults.limit
        should_redact = config.defaults.redact_pii and not no_redact
        output_format = format or auto_format()
        result = execute_sql(client, sql, database_id=database_id, limit=row_limit)
        if should_redact:
            result = redact_pii(result)
        if fields:
            result = result.filter_fields([f.strip() for f in fields.split(",")])
        output = format_result(result, output_format)
        typer.echo(output)
    except Exception as e:
        err_console.print(f"[red]Error:[/] {e}")
        err_console.print("[dim]Tip: Use 'mbquery query' with raw SQL as a fallback.[/]")
        raise typer.Exit(1)
    finally:
        client.close()
