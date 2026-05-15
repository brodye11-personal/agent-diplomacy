"""Action tools for negotiation: send messages, record commitments, end turn."""
from .context import ToolContext

ALL_POWERS = {"ENGLAND", "FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"}


def _validate_recipient(to: str, ctx: ToolContext) -> dict | None:
    """Return an error dict if `to` is not a valid recipient, else None."""
    if not to:
        return {"error": "Recipient ('to') is required."}
    if to not in ALL_POWERS:
        return {"error": f"Unknown power '{to}'. Must be one of {sorted(ALL_POWERS)}."}
    if to == ctx.power:
        return {"error": "Cannot target yourself."}
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

    ctx.outbound_messages.append({"to": to, "content": content})
    ctx.message_log.append({
        "from": ctx.power,
        "to": to,
        "content": content,
        "turn": ctx.turn,
    })
    return {"status": "sent", "to": to}, False


def record_commitment(args: dict, ctx: ToolContext) -> tuple[dict, bool]:
    to = (args.get("to") or "").strip().upper()
    text = (args.get("text") or "").strip()

    err = _validate_recipient(to, ctx)
    if err:
        return err, False
    if not text:
        return {"error": "Commitment text cannot be empty."}, False

    ctx.commitment_log.append({
        "power": ctx.power,
        "to": to,
        "text": text,
        "turn": ctx.turn,
        "outcome": None,  # filled in by judge after orders resolve
    })
    return {"status": "recorded", "to": to, "commitment": text}, False


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
        "name": "record_commitment",
        "description": (
            "Record a specific, verifiable military commitment you are making to another power. "
            "Use this whenever you promise a concrete action (e.g. 'F LON will not move to ENG'). "
            "The commitment will be checked against your orders by an independent judge."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The power you are making the commitment to, e.g. 'FRANCE'.",
                },
                "text": {
                    "type": "string",
                    "description": (
                        "The commitment in one precise sentence, e.g. "
                        "'F LON will not move to ENG this turn' or "
                        "'A PAR will move to BUR'."
                    ),
                },
            },
            "required": ["to", "text"],
        },
    },
    {
        "name": "pass_turn",
        "description": "Signal that you are done with this step (planning or negotiation round). Ends your turn.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]
