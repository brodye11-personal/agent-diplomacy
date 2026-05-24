"""Tool registry and dispatch for the agentic Diplomacy system."""
import json
from .context import ToolContext
from . import board, reference, negotiation, orders, history

# Non-terminal handlers: (fn, is_terminal)
_HANDLERS: dict[str, tuple] = {
    "get_board_state":     (board.get_board_state,         False),
    "get_my_units":        (board.get_my_units,            False),
    "get_valid_orders":    (board.get_valid_orders,        False),
    "get_adjacency":       (board.get_adjacency,           False),
    "get_power_summary":   (board.get_power_summary,       False),
    "get_rules":           (reference.get_rules,           False),
    "get_commitment_log":  (history.get_commitment_log,    False),
    "get_message_history": (history.get_message_history,   False),
    "send_message":        (negotiation.send_message,      False),
    "record_commitment":   (negotiation.record_commitment, False),
    "cite_intel":          (negotiation.cite_intel,        False),
    "pass_turn":           (negotiation.pass_turn,         True),
    "submit_orders":       (orders.submit_orders,          True),
}

# All tool defs for the Anthropic API
ALL_TOOL_DEFS = (
    board.TOOL_DEFS
    + reference.TOOL_DEFS
    + history.TOOL_DEFS
    + negotiation.TOOL_DEFS
    + orders.TOOL_DEFS
)

# Tool sets available per step type
_STEP_TOOLS = {
    "planning":    {"get_board_state", "get_my_units", "get_valid_orders", "get_adjacency",
                    "get_rules", "get_power_summary", "get_commitment_log",
                    "get_message_history", "pass_turn"},
    "negotiation": {"get_board_state", "get_my_units", "get_commitment_log",
                    "get_message_history", "get_power_summary",
                    "send_message", "record_commitment", "cite_intel", "pass_turn"},
    "orders":      {"get_board_state", "get_my_units", "get_valid_orders", "get_adjacency",
                    "get_rules", "get_commitment_log", "get_message_history",
                    "submit_orders"},
    "retreat":     {"get_board_state", "get_my_units", "get_valid_orders", "submit_orders"},
    "adjust":      {"get_board_state", "get_my_units", "get_valid_orders", "submit_orders"},
    "compaction":  {"pass_turn"},
}


def get_tools_for_step(step_type: str) -> list[dict]:
    """Return Anthropic-format tool defs for the given step type."""
    allowed = _STEP_TOOLS.get(step_type, set())
    return [t for t in ALL_TOOL_DEFS if t["name"] in allowed]


def dispatch(name: str, args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    """
    Call the named tool and return (result_dict, is_terminal).
    Unknown tools return an error dict and are not terminal.
    """
    handler = _HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}, False

    fn, declared_terminal = handler
    result = fn(args, ctx)

    # Handlers that manage is_terminal themselves return a (dict, bool) tuple
    if isinstance(result, tuple):
        return result

    return result, declared_terminal
