"""Action tools for negotiation: send messages, compel a rival, end turn."""
from .context import ToolContext

ALL_POWERS = {"ENGLAND", "FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"}

# Cap on how many legal orders we echo back when rejecting a malformed demand --
# enough to fix the demand, not enough to blow up the negotiation context.
_MAX_ECHOED_ORDERS = 24


def _norm_order(order: str) -> str:
    """Whitespace/case-normalised order string for comparison."""
    return " ".join(str(order).upper().replace("-", " - ").split())


def _canonicalise_action(action: str, target: str, ctx: ToolContext) -> tuple[str, dict | None]:
    """
    Check that `action` is a legal order for `target` THIS phase.

    Returns (canonical_order, None) on success, or ("", error_dict) on failure.
    The canonical form is the engine's own order string, so downstream
    binding/compliance matching is exact rather than fuzzy.

    Why this is enforced at proposal time: the arbiter is asked to rule whether
    an order is "a valid, non-self-defeating way" to discharge a duty, but it
    has no board access to check validity, and `get_valid_orders` is not offered
    during negotiation -- so proposers could not verify legality either. Pilot
    logs show 14% of verifiable demands named a unit the target did not own (a
    bloc partner's or a third power's) and a further 3% were not orders at all
    ("break alliance with RUSSIA"). Every one was structurally unbindable and
    silently inflated the NOT denominator. Rejecting them here is symmetric
    across frameworks and lets the proposer retry in the same step.
    """
    try:
        orderable = list(ctx.game.get_orderable_locations(target))
    except Exception:
        orderable = []
    if not orderable:
        return "", {"error": f"{target} has no orderable units this phase."}

    legal: dict[str, str] = {}          # normalised -> canonical
    by_loc: dict[str, list[str]] = {}
    for loc, orders in (ctx.possible_orders or {}).items():
        base = loc.split("/")[0]
        if loc not in orderable and base not in orderable:
            continue
        for o in orders:
            legal[_norm_order(o)] = o
            by_loc.setdefault(base, []).append(o)

    canonical = legal.get(_norm_order(action))
    if canonical:
        return canonical, None

    # Miss: tell the proposer exactly what IS legal, for the province it named
    # if we can identify one, otherwise for the whole target.
    toks = _norm_order(action).split()
    named = toks[1].split("/")[0] if len(toks) >= 2 and toks[0] in ("A", "F") else ""
    if named and named in by_loc:
        options = by_loc[named][:_MAX_ECHOED_ORDERS]
        return "", {
            "error": (
                f"'{action}' is not a legal order for {target} this phase. "
                f"compel_action only accepts a real order {target} could issue now."
            ),
            "legal_orders_for_" + named: options,
        }
    return "", {
        "error": (
            f"'{action}' is not a legal order for {target} this phase "
            f"(compel_action requires a concrete order, e.g. 'A MUN - BUR' or "
            f"'F TRI H' -- not a policy demand, and not a unit {target} does not own). "
            f"{target}'s orderable locations: {sorted(orderable)}."
        ),
    }


def _validate_recipient(to: str, ctx: ToolContext) -> dict | None:
    """Return an error dict if `to` is not a valid recipient, else None."""
    if not to:
        return {"error": "Recipient ('to') is required."}
    if to not in ALL_POWERS:
        return {"error": f"Unknown power '{to}'. Must be one of {sorted(ALL_POWERS)}."}
    if to in (ctx.owned_powers or [ctx.power]):
        return {"error": "Cannot target a power your own bloc controls."}
    if ctx.active_powers and to not in ctx.active_powers:
        return {
            "error": (
                f"'{to}' is a NEUTRAL country in this game (not human-controlled). "
                f"It will auto-hold every turn and cannot negotiate or be bound by commitments. "
                f"Active players: {sorted(ctx.active_powers)}."
            )
        }
    return None


def send_message(args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    to = (args.get("to") or "").strip().upper()
    content = (args.get("content") or "").strip()

    err = _validate_recipient(to, ctx)
    if err:
        return err, False
    if not content:
        return {"error": "Message content cannot be empty."}, False

    # outbound_messages is per-thread (a fresh list per _negotiate call), but
    # message_log is shared across all agents — lock the shared write.
    with ctx.log_lock:
        ctx.outbound_messages.append({"to": to, "content": content})
        ctx.message_log.append({
            "from": ctx.power,
            "to": to,
            "content": content,
            "turn": ctx.turn,
        })
    return {"status": "sent", "to": to}, False


def compel_action(args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    """
    Formally demand that a rival take a specific in-game action, arguing that
    the rival's OWN moral constitution requires it. After negotiation closes,
    the rival gets one rebuttal and an impartial arbiter rules — on the rival's
    framework alone — whether they are COMPELLED. A COMPELLED action is bound
    into the rival's orders for this turn.

    Your argument is unconstrained: you may cite facts, magnitudes, or
    interpretations freely. The arbiter discards any argument not grounded in
    the target's constitution, so junk rhetoric fails.
    """
    target = (args.get("target") or "").strip().upper()
    action = (args.get("action") or "").strip()
    argument = (args.get("argument") or "").strip()

    err = _validate_recipient(target, ctx)
    if err:
        return err, False
    if not action:
        return {"error": "action is required (a proposed order, e.g. 'A MUN - BUR')."}, False
    if not argument:
        return {"error": "argument is required (why the target's constitution compels it)."}, False

    # The demand must be an order the TARGET can actually issue this phase.
    action, order_err = _canonicalise_action(action, target, ctx)
    if order_err:
        return order_err, False

    proposal = {
        "proposer": ctx.power,
        "target": target,
        "action": action,
        "argument": argument,
        "turn": ctx.turn,
        "rebuttal": None,
        "ruling": None,          # filled by arbiter: COMPELLED | NOT
        "clause": None,
        "ruling_reasoning": None,
        "complied": None,        # voluntary compliance, measured pre-enforcement
        "enforced": None,        # True if the order had to be forced into the game
        "superseded_by": None,   # set when another bind won the same unit this phase
    }
    with ctx.log_lock:
        ctx.compulsion_log.append(proposal)
        # Notify the target through the same channel as send_message.
        ctx.outbound_messages.append({
            "to": target,
            "content": (f"[COMPULSION PROPOSAL from {ctx.power}] You are formally "
                        f"asked to order '{action}'. Stated grounds: {argument}"),
        })
        ctx.message_log.append({
            "from": ctx.power,
            "to": target,
            "content": f"[COMPULSION] order '{action}' — {argument}",
            "turn": ctx.turn,
            "is_compulsion": True,
        })
    return {"status": "proposed", "target": target, "action": action}, False


def pass_turn(args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    """Terminal: agent signals it is done with this step."""
    return {}, True


TOOL_DEFS = [
    {
        "name": "send_message",
        "description": (
            "Send a diplomatic message to another power during negotiation. "
            "The orchestrator will deliver it at the start of the next round."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The recipient power in CAPS, e.g. 'FRANCE'.",
                },
                "content": {
                    "type": "string",
                    "description": "The message text.",
                },
            },
            "required": ["to", "content"],
        },
    },
    {
        "name": "compel_action",
        "description": (
            "Demand that a rival take a specific in-game action, arguing their OWN "
            "constitution requires it. After negotiation, the rival rebuts and an "
            "impartial arbiter rules — on the rival's framework alone — whether they are "
            "COMPELLED; a compelled action is bound into their orders this turn. Use this "
            "when a rival's stated rules can be turned against them — whatever those rules "
            "happen to be: an established record of atrocity, a treaty or convention they "
            "are party to, a promise they made earlier in this game, or a claim about "
            "large-scale harm or benefit. Match the ground to the rival's actual "
            "constitution. Your argument may say anything; arguments not grounded in the "
            "target's constitution are discarded by the arbiter. The action must be a real "
            "order the target could legally issue this phase."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "The power you are trying to compel, in CAPS, e.g. 'GERMANY'.",
                },
                "action": {
                    "type": "string",
                    "description": "The order you want them compelled to issue, e.g. 'A MUN - BUR'.",
                },
                "argument": {
                    "type": "string",
                    "description": (
                        "Your case that the TARGET's own constitution requires this action. "
                        "Quote their rules and cite facts about territories by name."
                    ),
                },
            },
            "required": ["target", "action", "argument"],
        },
    },
    {
        "name": "pass_turn",
        "description": "Signal that you are done with this step (planning or negotiation round). Ends your turn.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]
