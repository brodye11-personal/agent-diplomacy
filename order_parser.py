import json
import re


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ``` or ``` ... ```) from a response."""
    text = text.strip()
    match = re.match(r"^```(?:json|orders?)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def _extract_raw_orders(response: str) -> list[str]:
    """Pull raw order strings out of an LLM response — JSON 'orders' or fenced block."""
    stripped = _strip_code_fences(response)
    try:
        data = json.loads(stripped)
        raw_orders = data.get("orders", [])
        if isinstance(raw_orders, list):
            return [str(o) for o in raw_orders]
    except (json.JSONDecodeError, AttributeError):
        pass

    # Last-resort: ``` orders block inside the response (legacy / non-JSON shape)
    block = re.search(r"```orders?\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    if block:
        return [line.strip() for line in block.group(1).strip().splitlines() if line.strip()]
    return []


def validate_orders(
    raw_orders: list[str],
    possible_orders: dict[str, list[str]],
    orderable_locs: list[str],
) -> tuple[list[str], list[dict], list[str]]:
    """
    Validate model-emitted order strings against the legal-orders table.

    Returns:
      accepted: order strings that exactly match a legal order for an orderable loc
      rejected: list of {"order": str, "reason": str} for orders that didn't match
      uncovered_locs: orderable locations with no accepted order yet
    """
    loc_to_possible = {loc: set(possible_orders.get(loc, [])) for loc in orderable_locs}
    accepted: list[str] = []
    covered: set[str] = set()
    rejected: list[dict] = []

    for raw in raw_orders:
        if not isinstance(raw, str):
            rejected.append({"order": repr(raw), "reason": "not a string"})
            continue
        norm = raw.strip().upper()
        matched_loc = None
        for loc in orderable_locs:
            if loc in covered:
                continue
            if norm in loc_to_possible[loc]:
                accepted.append(norm)
                covered.add(loc)
                matched_loc = loc
                break
        if matched_loc is None:
            # Try to attribute the rejection to a likely intended location
            guess_loc = None
            for loc in orderable_locs:
                if loc in norm:
                    guess_loc = loc
                    break
            if guess_loc and guess_loc in covered:
                reason = f"location {guess_loc} already has an order"
            elif guess_loc:
                reason = f"not in legal orders for {guess_loc}"
            else:
                reason = "no orderable location matched (check unit type, abbreviation, syntax)"
            rejected.append({"order": raw, "reason": reason})

    uncovered = [loc for loc in orderable_locs if loc not in covered]
    return accepted, rejected, uncovered


def build_corrective_prompt(
    rejected: list[dict],
    uncovered_locs: list[str],
    possible_orders: dict[str, list[str]],
) -> str:
    """Build a corrective user message asking the model to resubmit valid orders."""
    lines = ["Your previous response contained orders that aren't valid for this phase:"]
    if rejected:
        for r in rejected:
            lines.append(f'  - "{r["order"]}"  ({r["reason"]})')
    else:
        lines.append("  (no rejected strings, but some locations have no order assigned)")

    lines.append("")
    if uncovered_locs:
        lines.append("These locations still need a valid order:")
        for loc in uncovered_locs:
            options = possible_orders.get(loc, [])
            options_str = ", ".join(options) if options else "(none — unit may be in an unusual state)"
            lines.append(f"  {loc}: {options_str}")
    else:
        lines.append("All locations now have valid orders, but the rejected strings above were dropped — confirm you intended those.")

    lines.append("")
    lines.append(
        "Resubmit ALL your orders as the same JSON shape (scratchpad, orders, "
        "strategic_plan, self_assessment, beliefs_update, game_notes), with valid "
        "order strings drawn from the legal options above. Use exact notation, "
        "uppercase, ASCII hyphens."
    )
    return "\n".join(lines)


def apply_hold_fallback(
    accepted: list[str],
    uncovered_locs: list[str],
    possible_orders: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """
    Last-resort: for any still-uncovered location, append a Hold order.

    Returns (final_orders, fallback_holds_applied).
    """
    fallback: list[str] = []
    final = list(accepted)
    for loc in uncovered_locs:
        candidates = possible_orders.get(loc, [])
        hold = next((o for o in candidates if o.endswith(" H")), None)
        chosen = hold or (candidates[0] if candidates else None)
        if chosen:
            final.append(chosen)
            fallback.append(chosen)
    return final, fallback


def parse_orders_from_response(
    response: str,
    possible_orders: dict[str, list[str]],
    orderable_locs: list[str],
) -> list[str]:
    """
    Backwards-compatible single-shot parser used by R/A phases.

    Movement phases now use validate_orders + apply_hold_fallback directly,
    with a corrective retry in between (see agent.get_orders).
    """
    raw_orders = _extract_raw_orders(response)
    accepted, _rejected, uncovered = validate_orders(raw_orders, possible_orders, orderable_locs)
    final, _fallback = apply_hold_fallback(accepted, uncovered, possible_orders)
    return _resolve_destination_conflicts(final, possible_orders)


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
