"""Rich table formatter."""
from io import StringIO

from rich.console import Console
from rich.table import Table

from mbquery.core.queries import QueryResult


def format_table(result: QueryResult) -> str:
    table = Table(show_header=True, header_style="bold cyan")
    for col in result.columns:
        table.add_column(col["name"])
    for row in result.rows:
        table.add_row(*[str(v) if v is not None else "NULL" for v in row])
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    console.print(table)
    return buf.getvalue()
