import pytest
import respx

from mbquery.ai.base import LLMProvider
from mbquery.ai.gemini import GeminiProvider
from mbquery.ai.openai_compat import OpenAICompatProvider
from mbquery.ai.prompt import build_nl_to_sql_prompt


def test_build_prompt_basic():
    schema_context = "Table: users — columns: id (type/Integer), name (type/Text)"
    prompt = build_nl_to_sql_prompt("count all users", schema_context)
    assert "count all users" in prompt
    assert "users" in prompt
    assert "SELECT" in prompt


def test_build_prompt_with_hints():
    schema_context = "Table: orders — columns: id, status"
    hints = "status values are 'pending', 'completed', 'refunded'"
    prompt = build_nl_to_sql_prompt("count completed orders", schema_context, hints=hints)
    assert "pending" in prompt
    assert "completed" in prompt


@respx.mock
def test_openai_compat_generate_sql():
    respx.post("https://api.openai.com/v1/chat/completions").respond(json={"choices": [{"message": {"content": "SELECT COUNT(*) FROM users"}}]})
    provider = OpenAICompatProvider(api_key="sk-test", model="gpt-4o", base_url="https://api.openai.com/v1")
    sql = provider.generate_sql("count all users")
    assert "SELECT" in sql
    assert "users" in sql


@respx.mock
def test_openai_compat_strips_markdown():
    respx.post("https://api.openai.com/v1/chat/completions").respond(json={"choices": [{"message": {"content": "```sql\nSELECT COUNT(*) FROM users\n```"}}]})
    provider = OpenAICompatProvider(api_key="sk-test", model="gpt-4o", base_url="https://api.openai.com/v1")
    sql = provider.generate_sql("count users")
    assert sql.strip() == "SELECT COUNT(*) FROM users"
    assert "```" not in sql


@respx.mock
def test_gemini_generate_sql():
    respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent").respond(json={"candidates": [{"content": {"parts": [{"text": "SELECT COUNT(*) FROM orders"}]}}]})
    provider = GeminiProvider(api_key="AIza_test", model="gemini-2.0-flash")
    sql = provider.generate_sql("count all orders")
    assert "SELECT" in sql


@respx.mock
def test_gemini_strips_markdown():
    respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent").respond(json={"candidates": [{"content": {"parts": [{"text": "```sql\nSELECT 1\n```"}]}}]})
    provider = GeminiProvider(api_key="AIza_test", model="gemini-2.0-flash")
    sql = provider.generate_sql("select one")
    assert sql.strip() == "SELECT 1"


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


# Fix 7: Gemini uses v1beta endpoint
@respx.mock
def test_gemini_uses_v1beta_endpoint():
    route = respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent").respond(
        json={"candidates": [{"content": {"parts": [{"text": "SELECT 1"}]}}]}
    )
    provider = GeminiProvider(api_key="AIza_test", model="gemini-2.0-flash")
    provider.generate_sql("select one")
    assert route.called


# Fix 8: Gemini safety filter — no candidates raises descriptive error
@respx.mock
def test_gemini_safety_filter_raises():
    respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent").respond(
        json={"promptFeedback": {"blockReason": "SAFETY"}}
    )
    provider = GeminiProvider(api_key="AIza_test", model="gemini-2.0-flash")
    with pytest.raises(ValueError, match="LLM blocked the request.*SAFETY"):
        provider.generate_sql("dangerous prompt")
