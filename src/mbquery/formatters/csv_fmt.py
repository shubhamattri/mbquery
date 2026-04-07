"""CSV formatter."""
import csv
from io import StringIO
from mbquery.core.queries import QueryResult

def format_csv(result: QueryResult) -> str:
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(result.column_names)
    for row in result.rows:
        writer.writerow(row)
    return buf.getvalue()
