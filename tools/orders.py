"""Terminal tool for submitting orders."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from order_parser import validate_orders, apply_hold_fallback, _resolve_destination_conflicts
from .context import ToolContext


def submit_orders(args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    raw_orders = args.get("orders", [])
    if not isinstance(raw_orders, list):
        return {"error": "orders must be a list of strings"}, False

    orderable_locs = ctx.game.get_orderable_locations(ctx.power)

    if not orderable_locs:
        return {"orders": [], "diagnostics": {"note": "no orderable locations"}}, True

    accepted, rejected, uncovered = validate_orders(raw_orders, ctx.possible_orders, orderable_locs)
    diagnostics = {
        "rejected": rejected,
        "uncovered_locs": uncovered,
        "retry_attempted": False,
        "fallback_holds_applied": [],
    }

    if rejected or uncovered:
        final, fallback = apply_hold_fallback(accepted, uncovered, ctx.possible_orders)
        diagnostics["fallback_holds_applied"] = fallback
    else:
        final = accepted

    final = _resolve_destination_conflicts(final, ctx.possible_orders)
    return {"orders": final, "diagnostics": diagnostics}, True


TOOL_DEFS = [
    {
        "name": "submit_orders",
        "description": (
            "Submit your orders for this phase. This ends your turn — call it once, "
            "when you are ready. Use exact Diplomacy notation in uppercase ASCII, "
            "e.g. ['A PAR - BUR', 'F BRE - MAO', 'A MAR S A PAR - BUR']. "
            "Invalid orders will be replaced with holds automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of order strings in standard Diplomacy notation.",
                }
            },
            "required": ["orders"],
        },
    },
]
