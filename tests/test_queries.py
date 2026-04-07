import json

import pytest
import respx

from mbquery.config.models import AuthConfig, Profile
from mbquery.core.client import MetabaseClient
from mbquery.core.queries import QueryResult, execute_sql


@pytest.fixture
def client():
    profile = Profile(name="test", url="https://metabase.test.com", auth=AuthConfig(method="api-key", api_key="mb_testkey"), default_db=2)
    return MetabaseClient(profile)


@respx.mock
def test_execute_sql_returns_query_result(client):
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[100], [200]], "cols": [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]}, "row_count": 2})
    result = execute_sql(client, "SELECT COUNT(*) FROM users", database_id=2)
    assert isinstance(result, QueryResult)
    assert result.columns == [{"name": "count", "base_type": "type/Integer", "semantic_type": None}]
    assert result.rows == [[100], [200]]
    assert result.row_count == 2


@respx.mock
def test_execute_sql_with_limit(client):
    respx.post("https://metabase.test.com/api/dataset").respond(json={"data": {"rows": [[1]], "cols": [{"name": "id", "base_type": "type/Integer", "semantic_type": None}]}, "row_count": 1})
    execute_sql(client, "SELECT id FROM users", database_id=2, limit=10)
    call_body = respx.calls[0].request.read()
    body = json.loads(call_body)
    assert "LIMIT 10" in body["native"]["query"]


@respx.mock
def test_execute_sql_error(client):
    respx.post("https://metabase.test.com/api/dataset").respond(status_code=400, json={"message": "Syntax error"})
    with pytest.raises(Exception):
        execute_sql(client, "SELECTT bad", database_id=2)


def test_query_result_column_names():
    result = QueryResult(
        columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"}],
        rows=[[1, "Alice"], [2, "Bob"]], row_count=2,
    )
    assert result.column_names == ["id", "name"]


def test_query_result_filter_fields():
    result = QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ],
        rows=[[1, "Alice", "a@b.com"], [2, "Bob", "b@c.com"]], row_count=2,
    )
    filtered = result.filter_fields(["id", "email"])
    assert filtered.column_names == ["id", "email"]
    assert filtered.rows == [[1, "a@b.com"], [2, "b@c.com"]]
