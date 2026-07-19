"""Append per-call LLM token usage to a JSONL that the host reads for reporting.

Best-effort telemetry: every failure is swallowed so it can never break a reply.
Writes to $LLM_USAGE_LOG (default /app/user_data/llm-usage.jsonl, which is bind-
mounted to the host at budgetbot/user_data/).
"""
import os
import json
import logging
import datetime

logger = logging.getLogger(__name__)

_PATH = os.getenv("LLM_USAGE_LOG", "/app/user_data/llm-usage.jsonl")


def record(model, usage, service: str = "budgetbot") -> None:
    try:
        u = usage or {}
        get = u.get if isinstance(u, dict) else (lambda k, d=0: getattr(u, k, d))
        row = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "service": service,
            "model": model or "default",
            "input_tokens": get("input_tokens", 0) or 0,
            "output_tokens": get("output_tokens", 0) or 0,
            "cache_read_input_tokens": get("cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": get("cache_creation_input_tokens", 0) or 0,
        }
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception as exc:  # telemetry must never break the bot
        logger.warning("usage_meter record failed: %s", exc)
