"""Google Gemini LLM provider."""
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


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self._http = httpx.Client(timeout=60.0)

    def generate_sql(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent?key={self.api_key}"
        resp = self._http.post(url, headers={"Content-Type": "application/json"}, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0},
        })
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _strip_markdown_sql(text)
