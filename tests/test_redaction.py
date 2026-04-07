from mbquery.core.queries import QueryResult
from mbquery.formatters.redact import redact_pii, PII_SEMANTIC_TYPES

def test_pii_types_list():
    assert "type/Email" in PII_SEMANTIC_TYPES
    assert "type/Name" in PII_SEMANTIC_TYPES
    assert "type/Phone" in PII_SEMANTIC_TYPES
    assert "type/Integer" not in PII_SEMANTIC_TYPES

def test_redact_pii_masks_email_and_name():
    result = QueryResult(
        columns=[
            {"name": "id", "base_type": "type/Integer", "semantic_type": None},
            {"name": "name", "base_type": "type/Text", "semantic_type": "type/Name"},
            {"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"},
        ],
        rows=[[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]],
        row_count=2,
    )
    redacted = redact_pii(result)
    assert redacted.rows[0][0] == 1
    assert redacted.rows[0][1] == "[REDACTED]"
    assert redacted.rows[0][2] == "[REDACTED]"

def test_redact_pii_no_pii_columns():
    result = QueryResult(
        columns=[{"name": "id", "base_type": "type/Integer", "semantic_type": None}, {"name": "count", "base_type": "type/Integer", "semantic_type": None}],
        rows=[[1, 100], [2, 200]], row_count=2,
    )
    redacted = redact_pii(result)
    assert redacted.rows == [[1, 100], [2, 200]]

def test_redact_pii_preserves_original():
    result = QueryResult(columns=[{"name": "email", "base_type": "type/Text", "semantic_type": "type/Email"}], rows=[["alice@example.com"]], row_count=1)
    redacted = redact_pii(result)
    assert result.rows[0][0] == "alice@example.com"
    assert redacted.rows[0][0] == "[REDACTED]"

def test_redact_pii_all_types():
    columns = [{"name": f"col_{st.split('/')[-1]}", "base_type": "type/Text", "semantic_type": st} for st in PII_SEMANTIC_TYPES]
    rows = [[f"value_{i}" for i in range(len(columns))]]
    result = QueryResult(columns=columns, rows=rows, row_count=1)
    redacted = redact_pii(result)
    for val in redacted.rows[0]:
        assert val == "[REDACTED]"
