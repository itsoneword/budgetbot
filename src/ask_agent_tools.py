"""
Glue between the /ask agent session and domain tool logic.

build_ask_toolspecs(session) wraps the pure functions in domain/ask_tools.py
as backend-agnostic ToolSpecs: argument coercion (Decimal conversion, limit
clamp) and ValueError -> ToolInputError translation live here; all filtering/
formatting logic stays in domain/. No I/O — the session already holds the
full transaction history (T-049), so the model never touches the DB.

AgentToolContext is the agreed context shape for tool factories that need
more than the session (write tools, dv-82c8): tools STAGE proposed actions
into `staged`; after the agent loop returns, the /ask handler renders staged
entries as inline-confirm messages. Read tools never touch it.
"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from domain.ask_tools import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    QUERY_TRANSACTIONS_SCHEMA,
    format_no_match,
    format_query_result,
    query_transactions,
)
from domain.models.user_session import UserSession
from infrastructure.llm.base import ToolInputError, ToolSpec


@dataclass
class AgentToolContext:
    """Per-request context handed to tool factories (interface for dv-82c8)."""
    repos: Any
    user_id: int
    currency: str
    language: str
    staged: Dict[str, Any] = field(default_factory=dict)


def _to_decimal(value, name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ToolInputError(f"{name} must be a number, got {value!r}.")


def build_ask_toolspecs(session: UserSession) -> List[ToolSpec]:
    """Read tools for the /ask agent, bound to an already-loaded session."""

    async def _query_transactions(args: Dict[str, Any]) -> str:
        kwargs: Dict[str, Any] = {}
        for key in ("period", "category", "subcategory", "transaction_type"):
            value = args.get(key)
            if value is not None:
                kwargs[key] = str(value)
        for key in ("min_amount", "max_amount"):
            if args.get(key) is not None:
                kwargs[key] = _to_decimal(args[key], key)
        limit = args.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                raise ToolInputError(f"limit must be an integer, got {limit!r}.")
            kwargs["limit"] = max(1, min(limit, MAX_LIMIT))
        else:
            kwargs["limit"] = DEFAULT_LIMIT

        try:
            result = query_transactions(session.transactions, **kwargs)
        except ValueError as e:
            raise ToolInputError(str(e))

        if result.total_matches == 0:
            known = {t.category for t in session.transactions} | set(session.categories)
            return format_no_match(sorted(known))
        return format_query_result(result, session.currency)

    return [
        ToolSpec(
            name="query_transactions",
            description=(
                "Search the user's raw transaction rows with filters: period, "
                "category, subcategory, transaction type, amount range. Rows "
                "come back newest first (default 20, max 200); the match count "
                "and totals always cover ALL matches, so sums are correct even "
                "when rows are truncated. All filters are optional."
            ),
            input_schema=QUERY_TRANSACTIONS_SCHEMA,
            handler=_query_transactions,
        )
    ]
