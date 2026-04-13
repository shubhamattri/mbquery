"""MCP server for mbquery."""
from __future__ import annotations

import json
from pathlib import Path

from mbquery.config.models import Profile
from mbquery.core.cards import list_cards as _list_cards
from mbquery.core.cards import run_card as _run_card
from mbquery.core.client import MetabaseClient
from mbquery.core.dashboards import list_dashboards as _list_dashboards
from mbquery.core.database import list_databases as _list_databases
from mbquery.core.queries import QueryResult, execute_sql, is_write_query
from mbquery.core.schema_cache import SchemaCache
from mbquery.core.search import search as _search


def _result_to_text(result: QueryResult, max_rows: int = 100) -> str:
    lines = [" | ".join(result.column_names)]
    for row in result.rows[:max_rows]:
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))
    if result.row_count > max_rows:
        lines.append(f"... ({result.row_count - max_rows} more rows)")
    return "\n".join(lines)


def _optimize_list(items: list[dict], keys: list[str]) -> list[dict]:
    return [{k: item.get(k) for k in keys if k in item} for item in items]


# NOTE: Handlers use sync httpx.Client. For v0.2, migrate to httpx.AsyncClient
# when async support is added to core/client.py
class MbqueryMCPServer:
    def __init__(self, profile: Profile, cache_dir: Path):
        self.profile = profile
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = MetabaseClient(profile)
        self._schema_cache = SchemaCache(cache_dir)
        self._tools: dict = {}
        self._register_tools()

    def _register_tools(self) -> None:
        self._tools = {
            "query": {"description": "Execute a SQL query against Metabase. Write queries blocked.", "schema": {"type": "object", "properties": {"sql": {"type": "string"}, "database_id": {"type": "integer"}}, "required": ["sql"]}, "handler": self._handle_query},
            "list_databases": {"description": "List all databases.", "schema": {"type": "object", "properties": {}}, "handler": self._handle_list_databases},
            "list_tables": {"description": "List tables in a database.", "schema": {"type": "object", "properties": {"database_id": {"type": "integer"}}}, "handler": self._handle_list_tables},
            "get_table_schema": {"description": "Get columns/types for a table.", "schema": {"type": "object", "properties": {"table_name": {"type": "string"}, "database_id": {"type": "integer"}}, "required": ["table_name"]}, "handler": self._handle_get_table_schema},
            "list_cards": {"description": "List saved questions.", "schema": {"type": "object", "properties": {}}, "handler": self._handle_list_cards},
            "run_card": {"description": "Execute a saved question by ID.", "schema": {"type": "object", "properties": {"card_id": {"type": "integer"}}, "required": ["card_id"]}, "handler": self._handle_run_card},
            "list_dashboards": {"description": "List dashboards.", "schema": {"type": "object", "properties": {}}, "handler": self._handle_list_dashboards},
            "search": {"description": "Search across Metabase.", "schema": {"type": "object", "properties": {"query": {"type": "string"}, "type": {"type": "string"}}, "required": ["query"]}, "handler": self._handle_search},
            "get_schema_context": {"description": "Get full schema for NL→SQL.", "schema": {"type": "object", "properties": {"database_id": {"type": "integer"}}}, "handler": self._handle_get_schema_context},
        }

    def _db_id(self, args: dict) -> int:
        db = args.get("database_id") or self.profile.default_db
        if not db:
            raise ValueError("No database_id provided and no default database configured.")
        return db

    def _handle_query(self, args: dict) -> str:
        sql = args["sql"]
        if is_write_query(sql):
            return "Error: Write queries are blocked in MCP mode."
        result = execute_sql(self._client, sql, database_id=self._db_id(args))
        return _result_to_text(result)

    def _handle_list_databases(self, args: dict) -> str:
        dbs = _list_databases(self._client)
        if isinstance(dbs, dict):
            dbs = dbs.get("data", [])
        return json.dumps(_optimize_list(dbs, ["id", "name", "engine"]), indent=2)

    def _handle_list_tables(self, args: dict) -> str:
        schema = self._schema_cache.get_schema(self._client, database_id=self._db_id(args), profile_name=self.profile.name)
        tables = [{"name": t["name"], "fields": len(t.get("fields", []))} for t in schema.get("tables", [])]
        return json.dumps(tables, indent=2)

    def _handle_get_table_schema(self, args: dict) -> str:
        schema = self._schema_cache.get_schema(self._client, database_id=self._db_id(args), profile_name=self.profile.name)
        table = next((t for t in schema.get("tables", []) if t["name"] == args["table_name"]), None)
        if not table:
            return f"Error: Table '{args['table_name']}' not found."
        return json.dumps(table, indent=2)

    def _handle_list_cards(self, args: dict) -> str:
        cards = _list_cards(self._client)
        return json.dumps(_optimize_list(cards, ["id", "name", "display", "collection_id"]), indent=2)

    def _handle_run_card(self, args: dict) -> str:
        result = _run_card(self._client, args["card_id"])
        return _result_to_text(result)

    def _handle_list_dashboards(self, args: dict) -> str:
        dashboards = _list_dashboards(self._client)
        return json.dumps(_optimize_list(dashboards, ["id", "name", "collection_id"]), indent=2)

    def _handle_search(self, args: dict) -> str:
        results = _search(self._client, args["query"], model_type=args.get("type"))
        return json.dumps(_optimize_list(results, ["id", "name", "model"]), indent=2)

    def _handle_get_schema_context(self, args: dict) -> str:
        schema = self._schema_cache.get_schema(self._client, database_id=self._db_id(args), profile_name=self.profile.name)
        return self._schema_cache.schema_to_prompt_context(schema)

    def get_tools(self) -> list[dict]:
        return [{"name": name, "description": tool["description"], "inputSchema": tool["schema"]} for name, tool in self._tools.items()]

    def call_tool(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        return tool["handler"](arguments)


def create_mcp_server(profile: Profile, cache_dir: Path) -> MbqueryMCPServer:
    return MbqueryMCPServer(profile, cache_dir)
