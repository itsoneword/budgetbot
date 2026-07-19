"""
Claude Agent SDK backend — uses the owner's Claude subscription OAuth.

Spawns the `claude` CLI (mounted into the container read-only, credentials in
~/.claude/.credentials.json) via claude-agent-sdk.

Two modes share one message-loop runner:
- complete(): no tools, single turn — the per-user data summary is packed into
  the prompt, the model never touches the DB (T-018).
- complete_with_tools(): agentic loop over caller-supplied ToolSpecs exposed as
  an in-process SDK MCP server ("finance"). Built-in tools stay disabled
  (tools=[]); only mcp__finance__* is allowed, so the model still has no
  filesystem/bash/web access. Tool rounds are capped by max_turns and the
  whole call by a wall-clock timeout.

Usage telemetry: one usage_meter row per assistant turn (AssistantMessage
.usage/.model); the ResultMessage cumulative usage is recorded only as a
fallback when no per-turn rows were written — never both (no double counting).
"""
import os
import asyncio
import logging
from typing import List, Optional

from .base import LLMClient, LLMError, ToolInputError, ToolSpec

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = int(os.getenv("ASK_TIMEOUT_SECONDS", "120"))
DEFAULT_MAX_TOOL_TURNS = int(os.getenv("ASK_MAX_TOOL_TURNS", "8"))


def _record_usage(model, usage) -> None:
    """Best-effort usage telemetry; never breaks the reply."""
    try:
        from .usage_meter import record
        record(model, usage)
    except Exception:
        pass


class ClaudeAgentClient(LLMClient):
    def __init__(self, model: str | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.model = model or os.getenv("LLM_MODEL") or None
        self.timeout = timeout
        self.cli_path = os.getenv("CLAUDE_CLI_PATH") or None

    async def _run(self, prompt: str, options) -> tuple[Optional[str], str, Optional[str]]:
        """Drive one query() to completion.

        Returns (result_text, accumulated_assistant_text, error_subtype).
        error_subtype is None on success. Records per-turn usage; falls back to
        the ResultMessage cumulative usage only if no per-turn rows landed.
        """
        from claude_agent_sdk import (
            query,
            AssistantMessage,
            ResultMessage,
            TextBlock,
        )

        result_text: Optional[str] = None
        error_subtype: Optional[str] = None
        assistant_text: list[str] = []
        per_turn_usage_recorded = False

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        assistant_text.append(block.text)
                usage = getattr(message, "usage", None)
                if usage:
                    _record_usage(getattr(message, "model", None) or self.model, usage)
                    per_turn_usage_recorded = True
            elif isinstance(message, ResultMessage):
                if message.is_error:
                    error_subtype = message.subtype or "error"
                else:
                    result_text = message.result
                logger.info(
                    "LLM query done: subtype=%s turns=%s duration=%sms cost=%s session=%s",
                    message.subtype, message.num_turns, message.duration_ms,
                    message.total_cost_usd, message.session_id,
                )
                if not per_turn_usage_recorded:
                    _model = self.model
                    if not _model and getattr(message, "model_usage", None):
                        _model = next(iter(message.model_usage), None)
                    _record_usage(_model, getattr(message, "usage", None))

        return result_text, "".join(assistant_text), error_subtype

    async def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            from claude_agent_sdk import ClaudeAgentOptions
        except ImportError as e:
            raise LLMError(f"claude-agent-sdk is not installed: {e}")

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            tools=[],  # pure Q&A — no filesystem/bash/web access
            max_turns=1,
            model=self.model,
            cli_path=self.cli_path,
        )

        try:
            result_text, assistant_text, error_subtype = await asyncio.wait_for(
                self._run(prompt, options), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise LLMError(f"LLM query timed out after {self.timeout}s")
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"LLM backend failure: {e}")

        if error_subtype:
            raise LLMError(f"LLM returned error result: {error_subtype}")
        answer = result_text or assistant_text
        if not answer.strip():
            raise LLMError("LLM returned an empty response")
        return answer.strip()

    async def complete_with_tools(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: Optional[List[ToolSpec]] = None,
    ) -> str:
        if not tools:
            return await self.complete(prompt, system_prompt)

        try:
            from claude_agent_sdk import (
                ClaudeAgentOptions,
                create_sdk_mcp_server,
                tool as sdk_tool,
            )
        except ImportError as e:
            raise LLMError(f"claude-agent-sdk is not installed: {e}")

        def _wrap(spec: ToolSpec):
            @sdk_tool(spec.name, spec.description, spec.input_schema)
            async def _handler(args, _spec=spec):
                try:
                    text = await _spec.handler(args or {})
                    return {"content": [{"type": "text", "text": text}]}
                except ToolInputError as e:
                    # Model-readable input problem: let the model self-correct.
                    return {"content": [{"type": "text", "text": str(e)}], "is_error": True}
                except Exception:
                    # Never leak internals to the model.
                    logger.exception("tool %s failed", _spec.name)
                    return {
                        "content": [{"type": "text", "text": f"Tool {_spec.name} failed."}],
                        "is_error": True,
                    }
            return _handler

        server = create_sdk_mcp_server("finance", tools=[_wrap(s) for s in tools])
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            tools=[],  # built-ins stay off — no filesystem/bash/web access
            mcp_servers={"finance": server},
            allowed_tools=[f"mcp__finance__{s.name}" for s in tools],
            permission_mode="dontAsk",
            max_turns=DEFAULT_MAX_TOOL_TURNS,
            model=self.model,
            cli_path=self.cli_path,
        )

        try:
            result_text, assistant_text, error_subtype = await asyncio.wait_for(
                self._run(prompt, options), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise LLMError(f"LLM query timed out after {self.timeout}s")
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"LLM backend failure: {e}")

        # Turn-cap/budget exhaustion with usable text: return what we have
        # instead of erroring — a partial answer beats ASK_ERROR in chat.
        answer = (result_text or assistant_text).strip()
        if error_subtype and not answer:
            raise LLMError(f"LLM returned error result: {error_subtype}")
        if error_subtype:
            logger.warning(
                "LLM tool loop ended with %s; returning accumulated text (%d chars)",
                error_subtype, len(answer),
            )
        if not answer:
            raise LLMError("LLM returned an empty response")
        return answer
