import pytest
import respx

from mbquery.config.models import AuthConfig, Profile
from mbquery.mcp.server import MbqueryMCPServer, create_mcp_server


@pytest.fixture
def profile():
    return Profile(name="test", url="https://metabase.test.com", auth=AuthConfig(method="api-key", api_key="mb_testkey"), default_db=2)

def test_create_mcp_server(profile, tmp_path):
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    assert server is not None
    assert isinstance(server, MbqueryMCPServer)

def test_mcp_tools_registered(profile, tmp_path):
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    tools = server.get_tools()
    tool_names = {t["name"] for t in tools}
    assert "query" in tool_names
    assert "list_databases" in tool_names
    assert "list_tables" in tool_names
    assert "get_table_schema" in tool_names
    assert "list_cards" in tool_names
    assert "run_card" in tool_names
    assert "list_dashboards" in tool_names
    assert "search" in tool_names
    assert "get_schema_context" in tool_names
    assert len(tools) == 9

def test_mcp_query_blocks_writes(profile, tmp_path):
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    result = server.call_tool("query", {"sql": "DELETE FROM users"})
    assert "blocked" in result.lower() or "error" in result.lower()

def test_mcp_unknown_tool(profile, tmp_path):
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    result = server.call_tool("nonexistent", {})
    assert "Unknown tool" in result

@respx.mock
def test_mcp_query_executes(profile, tmp_path):
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[42]], "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]}, "row_count": 1})
    server = create_mcp_server(profile, cache_dir=tmp_path / "cache")
    result = server.call_tool("query", {"sql": "SELECT COUNT(*) FROM users"})
    assert "42" in result
