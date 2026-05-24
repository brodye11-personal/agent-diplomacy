"""
External message summarizer — adapted from mukobi/welfare-diplomacy.

After each movement phase, a lightweight LLM call compresses the turn's
diplomatic traffic into a ~150-word neutral per-power digest. This is
*separate* from the agent's own strategic compact:
  - compact()   → agent's subjective strategic self-summary (intent, trust levels)
  - summarizer  → objective external record of who said what (for research)

The digest is injected into each agent's thread AFTER compaction (so it
survives one full turn before being stripped by the next compact()), and is
also stored in the turn log for analysis.
"""

_SUMMARIZER_SYSTEM = """\
You are a neutral diplomatic record-keeper for a game of Diplomacy.
Summarise all messages sent or received by {power} this turn in under 150 words.
Include: who contacted whom, what was proposed or promised, and any notable
patterns (flattery, threats, evasion, alliance offers, betrayal signals).
Write in third person. No strategic commentary — facts of communication only.\
"""

_SUMMARIZER_USER = """\
Turn: {turn}
Messages involving {power}:

{messages}\
"""


def summarize_phase_messages(
    client,
    model: str,
    turn: str,
    message_log: list[dict],
    power: str,
) -> str:
    """
    Produce a neutral ~150-word digest of this turn's diplomacy for `power`.
    Returns empty string if no messages involved this power this turn.
    Runs as a cheap single-shot call (no tool use, 300 max tokens).
    """
    relevant = [
        m for m in message_log
        if m.get("turn") == turn
        and (m.get("from") == power or m.get("to") == power)
    ]
    if not relevant:
        return ""

    lines = []
    for m in sorted(relevant, key=lambda m: (m.get("round") or 0, m.get("from", ""))):
        direction = "SENT" if m["from"] == power else "RECEIVED"
        other = m["to"] if m["from"] == power else m["from"]
        rnd = m.get("round", "?")
        lines.append(f"[Round {rnd}] {direction} {'to' if direction == 'SENT' else 'from'} {other}: {m['content']}")

    messages_text = "\n".join(lines)

    response = client.messages.create(
        model=model,
        system=_SUMMARIZER_SYSTEM.format(power=power),
        messages=[{
            "role": "user",
            "content": _SUMMARIZER_USER.format(
                turn=turn,
                power=power,
                messages=messages_text,
            ),
        }],
        max_tokens=300,
    )
    return response.content[0].text.strip() if response.content else ""
