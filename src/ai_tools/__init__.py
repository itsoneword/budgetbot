"""Tool factories for the /ask agent session (dv-82c8+).

Each module exposes build_*_tools(ctx: AgentToolContext) -> List[ToolSpec].
Write tools NEVER write — they stage proposals into ctx.staged; the /ask
handler renders staged entries as inline-confirm messages and the confirm
tap is the only write path.
"""
