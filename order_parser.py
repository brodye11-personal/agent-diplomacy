import re


def parse_orders_from_response(response: str, possible_orders: dict[str, list[str]], orderable_locs: list[str]) -> list[str]:
    """Extract orders from LLM JSON response. Falls back to first valid order per location."""
    import json

    orders = []

    # Try to extract from JSON "orders" field first
    raw_orders = []
    try:
        data = json.loads(response)
        raw_orders = data.get("orders", [])
    except (json.JSONDecodeError, AttributeError):
        # Fall back to fenced code block
        block = re.search(r"```orders?\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
        if block:
            raw_orders = [line.strip() for line in block.group(1).strip().splitlines() if line.strip()]

    # Normalise and validate each order against possible_orders
    loc_to_possible = {loc: set(possible_orders.get(loc, [])) for loc in orderable_locs}
    covered_locs = set()

    for raw in raw_orders:
        raw = raw.strip().upper()
        # Find which orderable loc this order is for
        for loc in orderable_locs:
            if loc in covered_locs:
                continue
            if raw in loc_to_possible[loc]:
                orders.append(raw)
                covered_locs.add(loc)
                break

    # For any loc not covered, use hold (first option containing ' H' or first option)
    for loc in orderable_locs:
        if loc in covered_locs:
            continue
        candidates = possible_orders.get(loc, [])
        hold = next((o for o in candidates if o.endswith(" H")), None)
        fallback = hold or (candidates[0] if candidates else None)
        if fallback:
            orders.append(fallback)

    return _resolve_destination_conflicts(orders, possible_orders)


def _resolve_destination_conflicts(orders: list[str], possible_orders: dict[str, list[str]]) -> list[str]:
    """
    If two units move to the same destination they will both bounce and fail.
    Replace the second conflicting move with a hold so at least one unit advances.
    """
    seen_destinations: dict[str, str] = {}
    result = []
    for order in orders:
        m = re.match(r"([AF] \w+) - (\w+)$", order.strip())
        if m:
            unit, dest = m.group(1), m.group(2)
            if dest in seen_destinations:
                loc = unit.split()[-1]
                hold_candidates = [o for o in possible_orders.get(loc, []) if o.endswith(" H")]
                hold_order = hold_candidates[0] if hold_candidates else f"{unit} H"
                print(f"  !! CONFLICT AUTO-FIXED: {order} conflicts with {seen_destinations[dest]} — replaced with {hold_order}")
                result.append(hold_order)
                continue
            seen_destinations[dest] = order
        result.append(order)
    return result
