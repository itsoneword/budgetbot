"""
Tests for the tool-calling seam in infrastructure/llm (no CLI, no SDK spawn).
"""
import pytest

from infrastructure.llm.base import LLMClient, LLMError, ToolInputError, ToolSpec
from infrastructure.llm.claude_agent import ClaudeAgentClient


class _NoToolsBackend(LLMClient):
    async def complete(self, prompt, system_prompt=None):
        return "plain answer"


async def test_default_complete_with_tools_raises_llm_error():
    client = _NoToolsBackend()
    with pytest.raises(LLMError, match="does not support tool calling"):
        await client.complete_with_tools("q", tools=[])


async def test_claude_agent_without_tools_delegates_to_complete(monkeypatch):
    client = ClaudeAgentClient()
    calls = []

    async def fake_complete(prompt, system_prompt=None):
        calls.append((prompt, system_prompt))
        return "answer"

    monkeypatch.setattr(client, "complete", fake_complete)
    assert await client.complete_with_tools("q", "sys", tools=None) == "answer"
    assert await client.complete_with_tools("q2", "sys", tools=[]) == "answer"
    assert calls == [("q", "sys"), ("q2", "sys")]


def test_toolspec_holds_async_handler():
    async def handler(args):
        return "ok"

    spec = ToolSpec(name="t", description="d", input_schema={"type": "object"}, handler=handler)
    assert spec.name == "t"
    assert isinstance(ToolInputError("bad"), Exception)
