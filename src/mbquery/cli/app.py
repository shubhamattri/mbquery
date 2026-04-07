"""Root CLI application."""
from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.ask import ask_cmd
from mbquery.cli.card import card_app
from mbquery.cli.config_cmd import config_app
from mbquery.cli.dashboard import dashboard_app
from mbquery.cli.query import query_cmd
from mbquery.cli.schema import schema_app
from mbquery.cli.search import search_cmd
from mbquery.cli.serve import serve_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console(stderr=True)

app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)
app.add_typer(schema_app)
app.add_typer(card_app)
app.add_typer(dashboard_app)
app.command(name="search")(search_cmd)
app.add_typer(config_app)
app.command(name="serve")(serve_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
