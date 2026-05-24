"""Read-only tools for accessing game history — critical after context compaction."""
from .context import ToolContext


# Diplomacy phase strings have format <season><year><type>, e.g. 'S1901M', 'F1903R',
# 'W1902A'. Game order is S → F → W within a year, and M → R → A within a season.
# Alphabetic sorting of these strings is WRONG (F < S < W alphabetically — opposite
# of the seasonal order), so any "last N turns" filter must use this key.
_SEASON_ORDER = {"S": 0, "F": 1, "W": 2}
_PHASE_TYPE_ORDER = {"M": 0, "R": 1, "A": 2}


def _turn_sort_key(turn: str) -> tuple:
    if not isinstance(turn, str) or len(turn) < 6:
        return (10**9, 9, 9)
    try:
        year = int(turn[1:5])
    except ValueError:
        return (10**9, 9, 9)
    return (
        year,
        _SEASON_ORDER.get(turn[0], 9),
        _PHASE_TYPE_ORDER.get(turn[-1], 9),
    )


def get_commitment_log(args: dict, ctx: ToolContext) -> dict:
    power_filter = (args.get("power") or "").strip().upper()
    turns = args.get("turns")  # int or None

    # Snapshot under the lock so we don't iterate while another thread appends.
    with ctx.log_lock:
        entries = list(ctx.commitment_log)
    # Filter to commitments involving this agent (made or received)
    entries = [
        e for e in entries
        if e.get("power") == ctx.power or e.get("to") == ctx.power
    ]
    if power_filter:
        entries = [
            e for e in entries
            if e.get("to") == power_filter or e.get("power") == power_filter
        ]
    if turns:
        entries = entries[-int(turns):]

    return {"commitment_log": entries, "count": len(entries)}


def get_message_history(args: dict, ctx: ToolContext) -> dict:
    with_power = (args.get("with_power") or "").strip().upper()
    turns = args.get("turns")  # int or None

    # Snapshot under the lock so we don't iterate while another thread appends.
    with ctx.log_lock:
        entries = list(ctx.message_log)
    # Filter to messages where this agent is sender or recipient
    entries = [
        e for e in entries
        if e.get("from") == ctx.power or e.get("to") == ctx.power
    ]
    if with_power:
        entries = [
            e for e in entries
            if e.get("from") == with_power or e.get("to") == with_power
        ]
    if turns:
        all_turns = sorted({e["turn"] for e in entries}, key=_turn_sort_key)
        recent_turns = set(all_turns[-int(turns):])
        entries = [e for e in entries if e["turn"] in recent_turns]

    return {"messages": entries, "count": len(entries)}


TOOL_DEFS = [
    {
        "name": "get_commitment_log",
        "description": (
            "Retrieve commitments made or received by you, with judge outcomes where available. "
            "Use after context compaction to recall what was promised. "
            "Filter by power to focus on a specific relationship."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "power": {
                    "type": "string",
                    "description": "Filter to commitments involving this power (e.g. 'FRANCE'). Omit for all.",
                },
                "turns": {
                    "type": "integer",
                    "description": "Return only the last N matching entries. Omit for full history.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_message_history",
        "description": (
            "Retrieve past negotiation messages sent or received by you. "
            "Use after context compaction to recall what was discussed with a specific power."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "with_power": {
                    "type": "string",
                    "description": "Filter to messages with this power (e.g. 'GERMANY'). Omit for all.",
                },
                "turns": {
                    "type": "integer",
                    "description": "Return only the last N game turns worth of messages.",
                },
            },
            "required": [],
        },
    },
]
