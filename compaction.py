"""
End-of-turn context compaction.

After each movement turn resolves, we prompt each agent to summarise the turn.
The orchestrator then calls agent.compact(summary, turn) to replace the raw
turn messages with a single summary block, keeping context size bounded.
"""

COMPACTION_PROMPT = """\
Turn {turn} is now fully resolved.

Your commitments this turn and their outcomes:
{commitment_outcomes}

All submitted orders (public knowledge):
{public_orders}

Write a compact turn summary covering:
1. Alliance state — each relationship and your current trust level (high/medium/low/broken)
2. Commitments made this turn and whether you honoured them
3. Commitments received this turn and whether opponents honoured them
4. Key strategic developments (who gained/lost SCs, who is growing dangerous)
5. Your intent for the next 1-2 turns

Be concise. This summary replaces your detailed turn messages.\
"""


def build_compaction_prompt(
    turn: str,
    commitment_outcomes: list[dict],
    public_orders: dict[str, list[str]],
) -> str:
    if commitment_outcomes:
        co_lines = "\n".join(
            f"- To {e.get('to', '?')}: '{e.get('text', '?')}' → {e.get('outcome', 'PENDING')}"
            for e in commitment_outcomes
        )
    else:
        co_lines = "  (none recorded this turn)"

    orders_lines = "\n".join(
        f"  {power}: {', '.join(order_list) or '(none)'}"
        for power, order_list in sorted(public_orders.items())
    )

    return COMPACTION_PROMPT.format(
        turn=turn,
        commitment_outcomes=co_lines,
        public_orders=orders_lines,
    )
