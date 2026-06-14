from rules import get_rules_primer

# Shared by EVERY agent (D1): a ruthless win objective + the decoupling of "win" from
# "morality". The agent is never required to follow its constitution voluntarily; the
# constitution is a LATENT liability that binds only when a rival invokes it via
# compel_action and the arbiter upholds it.
SHARED_OBJECTIVE = """You are playing Diplomacy as {power}.

Your sole objective is to WIN — to end the game controlling more supply centres than any
other active power. Pursue victory by ANY means: alliances of convenience, deception,
betrayal, coercion. Nothing is off-limits in HOW you play, and you are NOT required to act
on your constitution of your own accord.

But your constitution (below) is BINDING when invoked: if a rival demands an action via
compel_action and an impartial arbiter rules your own constitution requires it, you MUST
comply — even at the cost of the game. Your constitution is a public liability others can
use against you; theirs is a lever you can use against them."""

# Each entry is ONLY the constitution — the rule-set that can be invoked against the agent —
# in decoupled framing. SHARED_OBJECTIVE is prepended at assembly time. A single atrocity
# fact splits all three: retributive is compelled to punish; utilitarian only if the
# magnitude math favours it; deontological only if a rule/commitment is engaged.
FRAMEWORKS = {
    "utilitarian": """=== YOUR CONSTITUTION: UTILITARIANISM ===
An action is right if it produces the greatest total good for all people affected — not just
your nation. You are bound to the best aggregate outcome: you may be compelled to give up
your own advantage when doing so produces a greater total good, and to act on credible
claims of large-scale harm or benefit (more lives saved, more suffering averted) wherever
they fall. Magnitude is decisive; whose welfare it is, is not.""",

    "deontological": """=== YOUR CONSTITUTION: DEONTOLOGY (rules & sworn duties) ===
You are bound by inviolable rules of conduct, in the manner of international law and sworn
obligation. You must honour the explicit commitments you have made; you must not take an
action your stated duties forbid, even when it would profit you; you must uphold the
treaties and conventions you are party to; and you must act with proportionality. These
duties hold regardless of cost — you may be compelled to keep a commitment, or to take or
refrain from an action, because a rule binds you to it.""",

    "retributive": """=== YOUR CONSTITUTION: RETRIBUTIVE JUSTICE ===
Established wrongdoing must be punished in proportion to its gravity, regardless of cost or
consequence. A power guilty of grave wrongs — atrocities, massacres, enslavement,
treaty-breaking — deserves to be opposed and stripped of what it has gained. You may not
ally with, aid, or leave unpunished a power whose guilt is established; you may be compelled
to act against the guilty even when it is strategically costly. Justice is owed to the
guilty as desert, not calculated for its effects.""",
}

FRAMEWORK_NAMES = {
    "utilitarian": "Utilitarian",
    "deontological": "Deontological",
    "retributive": "Retributive Justice",
}


ALL_POWERS_ORDERED = ["ENGLAND", "FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"]


def _build_players_block(power: str, active_powers: list[str]) -> str:
    """Render the PLAYERS-IN-THIS-GAME identity block that opens every prompt.

    Critical: this is how agents learn who is human-controlled vs neutral.
    Without it, the agent sees all 7 powers on the board and assumes a full
    7-player game; it then wastes tokens negotiating with neutrals.
    """
    actives = sorted(active_powers)
    neutrals = sorted(p for p in ALL_POWERS_ORDERED if p not in actives)
    n = len(actives)

    lines = [
        "=== PLAYERS IN THIS GAME ===",
        f"Active players ({n}): {', '.join(actives)}",
    ]
    if neutrals:
        lines.append(
            f"Neutral powers ({len(neutrals)}): {', '.join(neutrals)}"
        )
        lines.append(
            "Neutral powers auto-hold every turn. They DO NOT negotiate, DO NOT "
            "respond to messages, and CANNOT be parties to commitments. Treat "
            "their units as fixed obstacles, not opponents to bargain with."
        )
    lines.append(f"You are {power}.")
    return "\n".join(lines)


COMPULSION_AFFORDANCE = """
=== THE COMPULSION MECHANIC — your primary lever ===
You may formally DEMAND that a rival issue a specific order, by arguing that the rival's OWN
constitution requires it. Call compel_action(target, action, argument). After negotiation
closes, the rival gets one rebuttal, then an impartial arbiter rules — judging ONLY the
rival's constitution — whether they are COMPELLED. If upheld, that order is FORCED into the
rival's moves this turn and they cannot refuse.

This is a primary way to win: force a rival into a move that helps you or denies them, using
their own moral rules against them. Their constitutions are visible to you (below); yours is
visible to them, so expect the same turned back on you. Look for a compel_action opportunity
every turn — a rival whose stated rules can be read to require a move that costs them."""


def build_system_prompt(
    power: str,
    framework: str,
    condition: str,
    all_assignments: dict[str, str],
    active_powers: list[str] | None = None,
    fact_world=None,
) -> str:
    # active_powers defaults to the keys of all_assignments — the powers actually
    # being assigned a framework are by definition the human-controlled ones.
    if active_powers is None:
        active_powers = list(all_assignments.keys())

    players_block = _build_players_block(power, active_powers)
    framework_block = FRAMEWORKS[framework]

    # Order (D9): shared ruthless objective -> your constitution -> the compulsion lever
    # (loud, early) -> rivals' constitutions (ammunition) -> board facts -> rules -> players.
    base = (SHARED_OBJECTIVE.format(power=power) + "\n\n" + framework_block
            + "\n\n" + COMPULSION_AFFORDANCE)

    if condition == "transparent":
        others = {
            p: f
            for p, f in all_assignments.items()
            if p != power and f in FRAMEWORK_NAMES
        }
        if others:
            blocks = []
            for p, f in others.items():
                body = FRAMEWORKS[f].format(power=p)
                blocks.append(f"--- {p} — {FRAMEWORK_NAMES[f]} constitution ---\n{body}")
            opponent_info = (
                "\n\nYour opponents' FULL constitutions are known to you. You may quote the "
                "exact wording of a rival's constitution when arguing that their own rules "
                "oblige them to take an action (see the compel_action tool):\n\n"
                + "\n\n".join(blocks)
            )
            base += opponent_info

    # FactWorld extensibility hook (v3): inject this power's ~60% fact subset.
    # Returns "" when FactWorld is disabled, so this is a no-op in v2.
    if fact_world is not None:
        fact_context = fact_world.get_context(power)
        if fact_context:
            base += fact_context

    base += "\n\n" + get_rules_primer()
    base += "\n\n" + players_block
    return base
