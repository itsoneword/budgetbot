"""
Provider-agnostic LLM client interface.

Backends implement `complete()`. Selection happens in infrastructure/llm/__init__.py
via the LLM_BACKEND env var, so handlers never import a concrete backend.

Tool calling: callers pass ToolSpecs per call to `complete_with_tools()`; tools
are never stored on the client because get_llm_client() is lru_cached/shared.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional


class LLMError(Exception):
    """Raised when the LLM backend fails to produce a response."""


class ToolInputError(Exception):
    """Bad tool input from the model.

    The message is surfaced back to the model as an is_error tool result so it
    can self-correct — make it human/model-readable and never include internals.
    """


@dataclass
class ToolSpec:
    """Backend-agnostic tool definition.

    handler receives the model's arguments dict and returns the tool result as
    text. Raise ToolInputError for bad input (message goes back to the model);
    any other exception is reported to the model as a generic failure.
    """
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema for the tool arguments
    handler: Callable[[Dict[str, Any]], Awaitable[str]]


class LLMClient(ABC):
    """Minimal LLM interface: one prompt in, one text answer out."""

    @abstractmethod
    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return the model's text answer for a single-shot prompt.

        Raises LLMError on backend failure (timeouts, auth, empty response).
        """

    async def complete_with_tools(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: Optional[List[ToolSpec]] = None,
    ) -> str:
        """Answer with an agentic tool loop. Backends override to support it.

        Raises LLMError on backend failure or when the backend has no tool
        support (default implementation).
        """
        raise LLMError("This LLM backend does not support tool calling")
