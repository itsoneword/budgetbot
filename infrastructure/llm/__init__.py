"""LLM client factory — backend chosen by the LLM_BACKEND env var."""
import os
from functools import lru_cache

from .base import LLMClient, LLMError

__all__ = ["LLMClient", "LLMError", "get_llm_client"]


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    backend = os.getenv("LLM_BACKEND", "claude_agent")
    if backend == "claude_agent":
        from .claude_agent import ClaudeAgentClient
        return ClaudeAgentClient()
    # Future: openrouter backend via config (see docs/tasks/T-018)
    raise LLMError(f"Unknown LLM_BACKEND: {backend}")
