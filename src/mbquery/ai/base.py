"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_sql(self, prompt: str) -> str:
        ...
