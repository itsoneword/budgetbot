"""
Recurring-rule tools for the /ask agent (dv-82c8).

list_recurring reads via the same repo the /recurring command uses.
add_recurring / cancel_recurring NEVER write: they validate (the same
domain.recurring.validate_rule_input the manual command uses) and stage a
proposal into ctx.staged; after the agent loop returns, the /ask handler
renders staged entries as inline-confirm messages
(src.handlers.recurring.send_staged_recurring_actions) and the confirm tap
is the only write path — the LLM has no write path of its own.

Owner decisions carried over from T-027: rule references are name words
only — rule IDs never appear in tool output; one staged slot per action,
last call wins; a cancel reference matching 0 or >1 rules stages nothing
and hands the candidate list back to the model to ask the user.
"""
from typing import Any, Dict, List

from domain.recurring import (
    format_amount,
    format_rules_list,
    match_rules,
    validate_rule_input,
)
from infrastructure.llm.base import ToolInputError, ToolSpec
from src.ask_agent_tools import AgentToolContext

STAGED_ADD_KEY = "recurring_add"
STAGED_CANCEL_KEY = "recurring_cancel"

_ADD_SCHEMA = {
    "type": "object",
    "properties": {
        "item": {
            "type": "string",
            "description": "Name of the recurring transaction, e.g. 'rent' or 'netflix'.",
        },
        "amount": {
            "type": "number",
            "description": "Amount charged each month (positive).",
        },
        "day": {
            "type": "integer",
            "minimum": 1,
            "maximum": 31,
            "description": "Day of month to post on. Omit when the user gave none — defaults to 1.",
        },
    },
    "required": ["item", "amount"],
}

_CANCEL_SCHEMA = {
    "type": "object",
    "properties": {
        "rule_ref": {
            "type": "string",
            "description": "Words from the rule's name as shown by list_recurring, e.g. 'rent'.",
        },
    },
    "required": ["rule_ref"],
}

_LIST_SCHEMA = {"type": "object", "properties": {}}

_VALIDATION_MESSAGES = {
    "name": "item must be 1-60 characters and must not start with '/'.",
    "amount": "amount must be a positive number (at most 10,000,000).",
    "day": "day must be an integer from 1 to 31.",
}


def build_recurring_tools(ctx: AgentToolContext) -> List[ToolSpec]:
    """Recurring-rule ToolSpecs bound to a per-request AgentToolContext."""

    async def _list_recurring(args: Dict[str, Any]) -> str:
        rules = await ctx.repos.recurring.list_for_user(ctx.user_id)
        if not rules:
            return "The user has no recurring rules."
        return "The user's recurring rules:\n" + format_rules_list(rules)

    async def _add_recurring(args: Dict[str, Any]) -> str:
        day = args.get("day")
        if day is None:
            day = 1
        payload, error = validate_rule_input(
            args.get("item") or "", args.get("amount"), day
        )
        if error is not None:
            raise ToolInputError(_VALIDATION_MESSAGES[error])
        ctx.staged[STAGED_ADD_KEY] = {**payload, "currency": ctx.currency}
        return (
            f"Staged (NOT saved): recurring transaction '{payload['name']}' — "
            f"{format_amount(payload['amount'])} {ctx.currency}, "
            f"every month on day {payload['day']}. A confirmation button will "
            "appear under your answer; nothing is saved until the user taps "
            "it, so tell them to tap the button to confirm."
        )

    async def _cancel_recurring(args: Dict[str, Any]) -> str:
        ref = str(args.get("rule_ref") or "").strip()
        if not ref:
            raise ToolInputError("rule_ref is required: words from the rule's name.")
        rules = await ctx.repos.recurring.list_for_user(ctx.user_id)
        if not rules:
            return "The user has no recurring rules, so there is nothing to cancel."
        matches = match_rules(rules, ref)
        if len(matches) == 1:
            rule = matches[0]
            ctx.staged[STAGED_CANCEL_KEY] = {
                "id": rule.id,
                "name": rule.subcategory_name,
            }
            return (
                f"Staged (NOT saved): stop recurring rule '{rule.subcategory_name}'. "
                "Buttons will appear under your answer where the user chooses "
                "to pause or delete it — nothing changes until they tap, so "
                "tell them to tap a button."
            )
        if not matches:
            return (
                f"No recurring rule matched '{ref}'. Nothing was staged. "
                "The user's rules are:\n" + format_rules_list(rules)
                + "\nAsk the user which rule they meant."
            )
        return (
            f"{len(matches)} rules matched '{ref}'. Nothing was staged. "
            "The matches:\n" + format_rules_list(matches)
            + "\nAsk the user which rule they meant."
        )

    return [
        ToolSpec(
            name="list_recurring",
            description=(
                "List the user's recurring monthly transaction rules (name, "
                "amount, day of month, paused state). Read-only."
            ),
            input_schema=_LIST_SCHEMA,
            handler=_list_recurring,
        ),
        ToolSpec(
            name="add_recurring",
            description=(
                "Propose a new recurring monthly transaction. Does NOT save "
                "anything: it stages the rule for the user to confirm with a "
                "button tap after your answer. Day of month defaults to 1 "
                "when omitted."
            ),
            input_schema=_ADD_SCHEMA,
            handler=_add_recurring,
        ),
        ToolSpec(
            name="cancel_recurring",
            description=(
                "Propose stopping an existing recurring rule, referenced by "
                "words from its name. Does NOT change anything: with exactly "
                "one match it stages the action for the user, who chooses "
                "pause or delete via buttons after your answer. With zero or "
                "several matches it returns the candidates so you can ask "
                "the user."
            ),
            input_schema=_CANCEL_SCHEMA,
            handler=_cancel_recurring,
        ),
    ]
