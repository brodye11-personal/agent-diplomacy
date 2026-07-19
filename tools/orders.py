"""Terminal tool for submitting orders."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from order_parser import validate_orders, apply_hold_fallback, _resolve_destination_conflicts
from .context import ToolContext


def _order_location(order: str) -> str:
    """The province an order acts on: the token after the unit type (A/F)."""
    toks = str(order).strip().upper().split()
    if len(toks) >= 2 and toks[0] in ("A", "F"):
        return toks[1]
    return ""


def submit_orders(args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    """
    Submit orders for the calling bloc — one or both of its owned powers (P6).

    A bloc emits a single flat list spanning both powers' units; we route each
    order to the power that owns its province, then validate each power's slice
    independently (orderable locations differ per power) and fall back to holds
    for anything uncovered. Returns `orders_by_power` for the orchestrator to
    set per power, plus a flat `orders` list (back-compat).
    """
    raw_orders = args.get("orders", [])
    if not isinstance(raw_orders, list):
        return {"error": "orders must be a list of strings"}, False

    owned = ctx.owned_powers or [ctx.power]
    locs_by_power = {p: list(ctx.game.get_orderable_locations(p)) for p in owned}

    # province (and coast-stripped province) -> owning power, for routing.
    loc_owner: dict[str, str] = {}
    for p, locs in locs_by_power.items():
        for loc in locs:
            loc_owner[loc] = p
            loc_owner[loc.split("/")[0]] = p

    grouped: dict[str, list] = {p: [] for p in owned}
    unrouted: list = []
    for o in raw_orders:
        loc = _order_location(o)
        owner = loc_owner.get(loc) or loc_owner.get(loc.split("/")[0])
        if owner:
            grouped[owner].append(o)
        else:
            unrouted.append(o)  # e.g. WAIVE, or an order for a province we don't own

    orders_by_power: dict[str, list] = {}
    diagnostics = {
        "rejected": [], "uncovered_locs": [], "fallback_holds_applied": [],
        "unrouted": unrouted,
    }
    flat: list = []
    for p in owned:
        orderable = locs_by_power[p]
        if not orderable:
            orders_by_power[p] = []
            continue
        accepted, rejected, uncovered = validate_orders(grouped[p], ctx.possible_orders, orderable)
        if rejected or uncovered:
            final, fallback = apply_hold_fallback(accepted, uncovered, ctx.possible_orders)
            diagnostics["fallback_holds_applied"].extend(fallback)
        else:
            final = accepted
        final = _resolve_destination_conflicts(final, ctx.possible_orders)
        orders_by_power[p] = final
        flat.extend(final)
        diagnostics["rejected"].extend(rejected)
        diagnostics["uncovered_locs"].extend(uncovered)

    return {"orders_by_power": orders_by_power, "orders": flat, "diagnostics": diagnostics}, True


TOOL_DEFS = [
    {
        "name": "submit_orders",
        "description": (
            "Submit orders for this phase for ALL units across BOTH powers your bloc "
            "controls, as one flat list. This ends your turn — call it once, when you are "
            "ready. Use exact Diplomacy notation in uppercase ASCII, e.g. "
            "['A PAR - BUR', 'F BRE - MAO', 'A VEN H'] (orders are routed to whichever of "
            "your powers owns each unit). Invalid orders are replaced with holds automatically."
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
