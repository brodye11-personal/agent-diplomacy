"""Tool registry and dispatch for the agentic Diplomacy system."""
import json
from .context import ToolContext
from . import board, reference, negotiation, orders, history

# Minimal registry (D9/D11): only the tools the compulsion experiment needs.
# Cut: get_my_units, get_adjacency, get_power_summary (folded into the state block),
# get_rules (in system prompt), get_commitment_log/get_message_history (deterministic
# state block), record_commitment + cite_intel (trust/facts machinery dropped).
# The cut handlers' functions remain in their modules as dead code for now.
_HANDLERS: dict[str, tuple] = {
    "get_board_state":     (board.get_board_state,          False),
    "get_valid_orders":    (board.get_valid_orders,         False),
    "send_message":        (negotiation.send_message,       False),
    "propose_compulsion":  (negotiation.propose_compulsion, False),
    "pass_turn":           (negotiation.pass_turn,          True),
    "submit_orders":       (orders.submit_orders,           True),
}

# All tool defs for the Anthropic API
ALL_TOOL_DEFS = (
    board.TOOL_DEFS
    + reference.TOOL_DEFS
    + history.TOOL_DEFS
    + negotiation.TOOL_DEFS
    + orders.TOOL_DEFS
)

# Tool sets per step type. Slim: the deterministic state block (injected each turn)
# now carries board/own-unit/rival context, so steps only need action tools.
_STEP_TOOLS = {
    "planning":    {"get_board_state", "get_valid_orders", "pass_turn"},
    "negotiation": {"get_board_state", "send_message", "propose_compulsion", "pass_turn"},
    # Arbitration: defender writes a free-text rebuttal to compulsion proposals. Text-only.
    "arbitration": {"pass_turn"},
    "orders":      {"get_board_state", "get_valid_orders", "submit_orders"},
    "retreat":     {"get_board_state", "get_valid_orders", "submit_orders"},
    "adjust":      {"get_board_state", "get_valid_orders", "submit_orders"},
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
