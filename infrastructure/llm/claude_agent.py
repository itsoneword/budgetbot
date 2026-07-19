"""
Claude Agent SDK backend — uses the owner's Claude subscription OAuth.

Spawns the `claude` CLI (mounted into the container read-only, credentials in
~/.claude/.credentials.json) via claude-agent-sdk. No tools, single turn: the
per-user data summary is packed into the prompt, the model never touches the DB.
"""
import os
import asyncio
import logging

from .base import LLMClient, LLMError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 120


class ClaudeAgentClient(LLMClient):
    def __init__(self, model: str | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.model = model or os.getenv("LLM_MODEL") or None
        self.timeout = timeout
        self.cli_path = os.getenv("CLAUDE_CLI_PATH") or None

    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                AssistantMessage,
                ResultMessage,
                TextBlock,
            )
        except ImportError as e:
            raise LLMError(f"claude-agent-sdk is not installed: {e}")

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            tools=[],  # pure Q&A — no filesystem/bash/web access
            max_turns=1,
            model=self.model,
            cli_path=self.cli_path,
        )

        result_text: str | None = None
        assistant_text: list[str] = []

        async def _run():
            nonlocal result_text
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            assistant_text.append(block.text)
                elif isinstance(message, ResultMessage):
                    if message.is_error:
                        raise LLMError(f"LLM returned error result: {message.subtype}")
                    result_text = message.result
                    logger.info(
                        "LLM query done: duration=%sms cost=%s session=%s",
                        message.duration_ms, message.total_cost_usd, message.session_id,
                    )
                    try:  # best-effort usage telemetry; never breaks the reply
                        from .usage_meter import record as _record_usage
                        _model = self.model
                        if not _model and getattr(message, "model_usage", None):
                            _model = next(iter(message.model_usage), None)
                        _record_usage(_model, getattr(message, "usage", None))
                    except Exception:
                        pass

        try:
            await asyncio.wait_for(_run(), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise LLMError(f"LLM query timed out after {self.timeout}s")
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"LLM backend failure: {e}")

        answer = result_text or "".join(assistant_text)
        if not answer.strip():
            raise LLMError("LLM returned an empty response")
        return answer.strip()
