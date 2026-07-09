"""LLM client factory — backend chosen by the LLM_BACKEND env var."""
import os
from functools import lru_cache

from .base import LLMClient, LLMError

__all__ = ["LLMClient", "LLMError", "get_llm_client"]


@lru_cache(maxsize=4)
def get_llm_client(model: str | None = None) -> LLMClient:
    """model=None uses the backend default (LLM_MODEL env). Pass an explicit
    model for cheaper side-tasks, e.g. intent classification on haiku."""
    backend = os.getenv("LLM_BACKEND", "claude_agent")
    if backend == "claude_agent":
        from .claude_agent import ClaudeAgentClient
        return ClaudeAgentClient(model=model)
    # Future: openrouter backend via config (see docs/tasks/T-018)
    raise LLMError(f"Unknown LLM_BACKEND: {backend}")
