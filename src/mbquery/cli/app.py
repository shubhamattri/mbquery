"""Root CLI application."""
from __future__ import annotations

import typer
from rich.console import Console

from mbquery.cli.ask import ask_cmd
from mbquery.cli.card import card_app
from mbquery.cli.config_cmd import config_app
from mbquery.cli.dashboard import dashboard_app
from mbquery.cli.login import login_cmd
from mbquery.cli.query import query_cmd
from mbquery.cli.schema import schema_app
from mbquery.cli.search import search_cmd
from mbquery.cli.serve import serve_cmd

app = typer.Typer(
    name="mbquery",
    help="The ultimate Metabase CLI.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    invoke_without_command=True,
)

console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def _root_callback(ctx: typer.Context) -> None:
    """Auto-launch setup wizard if unconfigured and no command given."""
    if ctx.invoked_subcommand is not None:
        return
    # No subcommand — check if configured
    from mbquery.config.store import ConfigStore
    store = ConfigStore()
    if not store.is_configured():
        from mbquery.cli.config_cmd import _run_init_wizard
        _run_init_wizard(store)
        raise typer.Exit(0)
    # Configured but no command — show help
    typer.echo(ctx.get_help())


app.command(name="query")(query_cmd)
app.command(name="ask")(ask_cmd)
app.add_typer(schema_app)
app.add_typer(card_app)
app.add_typer(dashboard_app)
app.command(name="search")(search_cmd)
app.add_typer(config_app)
app.command(name="serve")(serve_cmd)
app.command(name="login")(login_cmd)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
