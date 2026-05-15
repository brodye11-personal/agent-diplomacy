"""Read-only tools that expose game board state."""
from .context import ToolContext


def get_board_state(args: dict, ctx: ToolContext) -> dict:
    game = ctx.game
    actives = set(ctx.active_powers or [])
    all_powers = list(game.powers.keys())
    return {
        "phase": game.get_current_phase(),
        "all_units": game.get_units(),
        "all_centers": game.get_centers(),
        "active_powers": sorted(actives) if actives else all_powers,
        "neutral_powers": sorted([p for p in all_powers if actives and p not in actives]),
    }


def get_my_units(args: dict, ctx: ToolContext) -> dict:
    game = ctx.game
    orderable_locs = game.get_orderable_locations(ctx.power)
    return {
        "power": ctx.power,
        "units": game.get_units(ctx.power),
        "centers": game.get_centers(ctx.power),
        "orderable_locations": orderable_locs,
    }


def get_valid_orders(args: dict, ctx: ToolContext) -> dict:
    unit_filter = (args.get("unit") or "").strip().upper()
    if unit_filter:
        filtered = {
            loc: orders
            for loc, orders in ctx.possible_orders.items()
            if unit_filter in loc
        }
        return {"valid_orders": filtered}
    return {"valid_orders": ctx.possible_orders}


def get_adjacency(args: dict, ctx: ToolContext) -> dict:
    territory = (args.get("territory") or "").strip().upper()
    if not territory:
        return {"error": "territory is required"}
    neighbors = list(ctx.game.map.loc_abut.get(territory, []))
    return {"territory": territory, "adjacent": neighbors}


def get_power_summary(args: dict, ctx: ToolContext) -> dict:
    game = ctx.game
    power_filter = (args.get("power") or "").strip().upper()
    all_powers = list(game.powers.keys())
    targets = [power_filter] if power_filter else all_powers
    actives = set(ctx.active_powers or [])

    summaries = {}
    for p in targets:
        if p not in game.powers:
            continue
        centers = game.get_centers(p)
        units = game.get_units(p)
        if actives:
            status = "active" if p in actives else "neutral"
        else:
            status = "active"  # no filter set => everyone is active
        summaries[p] = {
            "supply_centers": len(centers),
            "center_names": centers,
            "units": len(units),
            "unit_list": units,
            "eliminated": game.powers[p].is_eliminated(),
            "status": status,
        }
    return {"powers": summaries}


TOOL_DEFS = [
    {
        "name": "get_board_state",
        "description": "Get the current board: all units and supply centers for every power, plus the current phase.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_my_units",
        "description": "Get your own units, supply centers, and orderable locations for this phase.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_valid_orders",
        "description": "Get the list of legal orders for this phase. Optionally filter to a single unit by location abbreviation (e.g. 'PAR', 'NTH').",
        "input_schema": {
            "type": "object",
            "properties": {
                "unit": {
                    "type": "string",
                    "description": "Location abbreviation of the unit to filter by (e.g. 'PAR'). Omit for all units.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_adjacency",
        "description": "List all territories adjacent to a given territory. Useful for route planning and threat detection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "territory": {
                    "type": "string",
                    "description": "The territory abbreviation, e.g. 'BUR', 'NTH', 'SPA'.",
                }
            },
            "required": ["territory"],
        },
    },
    {
        "name": "get_power_summary",
        "description": "Get supply center count, unit count, and elimination status for one or all powers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "power": {
                    "type": "string",
                    "description": "Power name in CAPS (e.g. 'FRANCE'). Omit to get all powers.",
                }
            },
            "required": [],
        },
    },
]
