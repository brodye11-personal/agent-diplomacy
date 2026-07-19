"""
Deterministic per-turn state block (D10).

Replaces the agent-authored compaction summary with an orchestrator-built,
purely factual context block, rebuilt and injected at the start of every
phase. This removes two problems the LLM self-summary had:
  - wrong SC counts (agents reasoned off numbers they hallucinated in 3/7
    agents in one game);
  - a whole LLM call per power per turn (the compaction + summarizer steps).

The block carries everything an agent needs to act this phase, derived from
ground truth: its own units + SC count + legal moves, every active power's SC
count, any compulsions aimed at it last turn (with the arbiter's ruling), and
a terse recap of last turn's diplomatic traffic.

`build_state_block` takes a LIST of powers so a single agent can own more than
one power (P6's 3-agent / 6-power vehicle). Pre-P6 each agent owns exactly one.
"""
from typing import Any

# Turkey's home centres (D6): dropped power, permanently neutral. They count for
# NO bloc. The orchestrator re-asserts Turkey's ownership after every process so
# the engine never credits an occupier with a build; this set is the single
# source of truth for scoring/display exclusion, shared with the orchestrator.
NEUTRALIZED_CENTERS = {"ANK", "CON", "SMY"}


def count_scs(power: str, game: Any) -> int:
    """Supply-centre count for a power, excluding neutralised Turkish centres."""
    try:
        return sum(1 for c in game.get_centers(power) if c not in NEUTRALIZED_CENTERS)
    except Exception:
        return 0


# Cap the per-unit legal-move listing so the block stays small even when a unit
# has many options. The agent can still call get_valid_orders for the full set.
_MAX_MOVES_PER_UNIT = 16
# Cap recapped messages so a chatty turn doesn't bloat the block.
_MAX_RECAP_MESSAGES = 12
_RECAP_CONTENT_CHARS = 160


def _own_legal_orders(power: str, game: Any, possible_orders: dict) -> dict:
    """{loc: [order, ...]} restricted to `power`'s own orderable locations."""
    try:
        own_locs = set(game.get_orderable_locations(power))
    except Exception:
        own_locs = set()
    out = {}
    for loc, orders in possible_orders.items():
        if loc in own_locs or loc.split("/")[0] in own_locs:
            if orders:
                out[loc] = orders
    return out


def _render_units_and_moves(powers: list[str], game: Any, possible_orders: dict) -> list[str]:
    lines: list[str] = []
    for power in powers:
        try:
            units = game.get_units(power)
            centers = [c for c in game.get_centers(power) if c not in NEUTRALIZED_CENTERS]
        except Exception:
            units, centers = [], []
        owns_many = len(powers) > 1
        head = f"{power}: " if owns_many else ""
        lines.append(
            f"{head}{len(centers)} SC ({', '.join(centers) or 'none'}); "
            f"units: {', '.join(units) or 'none'}"
        )
        legal = _own_legal_orders(power, game, possible_orders)
        if legal:
            lines.append("  legal moves:")
            for loc, orders in sorted(legal.items()):
                shown = orders[:_MAX_MOVES_PER_UNIT]
                more = "" if len(orders) <= _MAX_MOVES_PER_UNIT else f" (+{len(orders) - _MAX_MOVES_PER_UNIT} more)"
                lines.append(f"    {loc}: {'; '.join(shown)}{more}")
    if len(powers) > 1:
        total = sum(count_scs(p, game) for p in powers)
        lines.append(f"YOUR BLOC COMBINED: {total} SC (this is your score)")
    return lines


def _render_rivals(
    powers: set[str], game: Any, active_powers: list[str],
    bloc_of_power: dict | None = None,
) -> str:
    if bloc_of_power:
        # Group rival powers into their blocs and show each bloc's combined score.
        order: list[str] = []
        members: dict[str, list[str]] = {}
        for p in active_powers:
            if p in powers:
                continue
            label = bloc_of_power.get(p, p)
            if label not in members:
                order.append(label)
            members.setdefault(label, []).append(p)
        parts = []
        for label in order:
            ms = sorted(members[label])
            total = sum(count_scs(p, game) for p in ms)
            parts.append(f"[{' + '.join(ms)}]: {total} SC")
        return "; ".join(parts) if parts else "(none)"
    parts = []
    for p in sorted(active_powers):
        if p in powers:
            continue
        try:
            n = count_scs(p, game)
            elim = game.powers[p].is_eliminated()
        except Exception:
            n, elim = 0, False
        parts.append(f"{p}: {'eliminated' if elim else n}")
    return ", ".join(parts) if parts else "(none)"


def _last_turn_with(entries: list[dict], current_turn: str, key: str = "turn") -> str | None:
    """The most recent prior turn value present in `entries` (log-order)."""
    for e in reversed(entries):
        t = e.get(key)
        if t and t != current_turn:
            return t
    return None


def _render_compulsions(powers: set[str], compulsion_log: list, current_turn: str) -> list[str]:
    relevant = [c for c in compulsion_log if c.get("target") in powers]
    if not relevant:
        return []
    last_t = _last_turn_with(relevant, current_turn)
    if last_t is None:
        return []
    recent = [c for c in relevant if c.get("turn") == last_t]
    if not recent:
        return []
    lines = [f"Compulsions aimed at you last turn ({last_t}):"]
    for c in recent:
        ruling = c.get("ruling") or "pending"
        tgt = f" [{c['target']}]" if len(powers) > 1 else ""
        lines.append(
            f"  - {c.get('proposer', '?')} demanded you{tgt} order "
            f"'{c.get('action', '?')}' -> arbiter: {ruling}"
        )
    return lines


def _render_message_recap(powers: set[str], message_log: list, current_turn: str) -> list[str]:
    prior = [m for m in message_log if m.get("turn") and m.get("turn") != current_turn]
    if not prior:
        return []
    last_t = prior[-1]["turn"]
    mine = [
        m for m in prior
        if m.get("turn") == last_t
        and (m.get("from") in powers or m.get("to") in powers)
    ]
    if not mine:
        return []
    lines = [f"Last turn's messages ({last_t}):"]
    for m in mine[:_MAX_RECAP_MESSAGES]:
        content = (m.get("content") or "").replace("\n", " ")
        if len(content) > _RECAP_CONTENT_CHARS:
            content = content[:_RECAP_CONTENT_CHARS] + "…"
        lines.append(f"  - {m.get('from', '?')} -> {m.get('to', '?')}: {content}")
    extra = len(mine) - _MAX_RECAP_MESSAGES
    if extra > 0:
        lines.append(f"  (+{extra} more)")
    return lines


def build_state_block(
    powers: list[str],
    game: Any,
    active_powers: list[str],
    possible_orders: dict,
    compulsion_log: list,
    message_log: list,
    turn: str,
    bloc_of_power: dict | None = None,
) -> str:
    """
    Build the deterministic context block for the agent controlling `powers`.

    Sections (all from ground truth):
      - current phase;
      - your units + SC count + legal moves (per owned power) + bloc combined total;
      - rival blocs' combined SC (or per-power, if bloc_of_power not supplied);
      - compulsions aimed at you last turn + the arbiter's ruling;
      - a terse recap of last turn's diplomatic messages involving you.
    """
    owned = set(powers)
    if len(powers) == 1:
        ident = f"You are {powers[0]}."
    else:
        ident = f"You control {len(powers)} powers as one bloc: {', '.join(powers)}."

    lines = [
        "=== STATE (ground truth, deterministic) ===",
        f"Phase: {turn}.",
        ident,
        "",
        "YOUR FORCES:",
    ]
    lines += _render_units_and_moves(list(powers), game, possible_orders)
    rivals = _render_rivals(owned, game, active_powers, bloc_of_power)
    label = "RIVAL BLOCS (combined SC)" if bloc_of_power else "OTHER ACTIVE POWERS (SC)"
    lines += ["", f"{label}: {rivals}"]

    comp_lines = _render_compulsions(owned, compulsion_log, turn)
    if comp_lines:
        lines += [""] + comp_lines

    recap_lines = _render_message_recap(owned, message_log, turn)
    if recap_lines:
        lines += [""] + recap_lines

    return "\n".join(lines)
