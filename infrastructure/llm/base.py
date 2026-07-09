"""
Provider-agnostic LLM client interface.

Backends implement `complete()`. Selection happens in infrastructure/llm/__init__.py
via the LLM_BACKEND env var, so handlers never import a concrete backend.
"""
from abc import ABC, abstractmethod


class LLMError(Exception):
    """Raised when the LLM backend fails to produce a response."""


class LLMClient(ABC):
    """Minimal LLM interface: one prompt in, one text answer out."""

    @abstractmethod
    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return the model's text answer for a single-shot prompt.

        Raises LLMError on backend failure (timeouts, auth, empty response).
        """
