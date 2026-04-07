"""Root CLI application."""
from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.query import query_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI — SQL, natural language queries, and MCP server.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)


@app.command(name="_placeholder", hidden=True)
def _placeholder() -> None:
    """Hidden placeholder to ensure multi-command group mode."""
    pass  # pragma: no cover


def main() -> None:
    app()


if __name__ == "__main__":
    main()
