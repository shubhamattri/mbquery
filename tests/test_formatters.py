import json

import pytest

from mbquery.core.queries import QueryResult
from mbquery.formatters import format_result
from mbquery.formatters.csv_fmt import format_csv
from mbquery.formatters.json_fmt import format_json, format_jsonl
from mbquery.formatters.markdown import format_markdown
from mbquery.formatters.table import format_table


@pytest.fixture
def sample_result():
    return QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": None},
            {"name": "count", "base_type": "type/Integer", "semantic_type": None},
        ],
        rows=[[1, "Alice", 100], [2, "Bob", 200]],
        row_count=2,
    )

def test_format_table(sample_result):
    output = format_table(sample_result)
    assert "id" in output
    assert "Alice" in output
    assert "Bob" in output

def test_format_csv(sample_result):
    output = format_csv(sample_result)
    lines = output.strip().split("\n")
    assert lines[0] == "id,name,count"
    assert lines[1] == "1,Alice,100"
    assert lines[2] == "2,Bob,200"

def test_format_json(sample_result):
    output = format_json(sample_result)
    data = json.loads(output)
    assert len(data) == 2
    assert data[0] == {"id": 1, "name": "Alice", "count": 100}

def test_format_jsonl(sample_result):
    output = format_jsonl(sample_result)
    lines = output.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1, "name": "Alice", "count": 100}

def test_format_markdown(sample_result):
    output = format_markdown(sample_result)
    lines = output.strip().split("\n")
    assert "| id | name | count |" in lines[0]
    assert lines[1].startswith("| --")
    assert "| 1 | Alice | 100 |" in lines[2]

def test_format_result_dispatch(sample_result):
    csv_output = format_result(sample_result, fmt="csv")
    assert "id,name,count" in csv_output
    json_output = format_result(sample_result, fmt="json")
    data = json.loads(json_output)
    assert len(data) == 2

def test_format_result_invalid():
    result = QueryResult(columns=[], rows=[], row_count=0)
    with pytest.raises(ValueError, match="Unknown format"):
        format_result(result, fmt="xml")

def test_format_empty_result():
    result = QueryResult(columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}], rows=[], row_count=0)
    csv_out = format_csv(result)
    assert csv_out.strip() == "id"
    json_out = format_json(result)
    assert json.loads(json_out) == []


# Fix 5: Markdown escapes pipe and newline in cell values
def test_format_markdown_escapes_pipe():
    result = QueryResult(
        columns=[{"name": "col", "base_type": "type/Text", "semantic_type": None}],
        rows=[["a|b"], ["c\nd"]],
        row_count=2,
    )
    output = format_markdown(result)
    assert "a\\|b" in output
    assert "c d" in output  # newline replaced with space
