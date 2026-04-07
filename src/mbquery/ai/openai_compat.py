"""OpenAI-compatible LLM provider."""
from __future__ import annotations
import re
import httpx
from mbquery.ai.base import LLMProvider


def _strip_markdown_sql(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:sql)?\s*\n?(.*?)```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class OpenAICompatProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=60.0)

    def generate_sql(self, prompt: str) -> str:
        resp = self._http.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a SQL expert. Return only valid SQL."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _strip_markdown_sql(content)
