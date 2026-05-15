"""Read-only reference tool for Diplomacy rules."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from rules import RULES_PRIMER, POWER_GUIDANCE
from .context import ToolContext

_TOPICS = {
    "convoys": [
        "CONVOY", "convoy", "C ", " C ", "across sea",
    ],
    "support": [
        "Support", "SUPPORT", " S ", "support hold", "support move", "cut",
    ],
    "builds": [
        "Winter", "Adjustments", "build new units", "disband", "BUILD",
    ],
    "retreats": [
        "retreat", "Retreat", "dislodge", "RETREAT",
    ],
    "dislodge": [
        "dislodge", "Dislodge", "strength", "Strength", "bounce", "Bounce",
    ],
}

_FULL_SECTIONS = RULES_PRIMER.split("\n\n")


def _topic_lines(topic: str) -> str:
    keywords = _TOPICS.get(topic.lower(), [])
    if not keywords:
        return RULES_PRIMER
    matched = [
        section for section in _FULL_SECTIONS
        if any(kw in section for kw in keywords)
    ]
    return "\n\n".join(matched) if matched else RULES_PRIMER


def get_rules(args: dict, ctx: ToolContext) -> dict:
    topic = (args.get("topic") or "").strip().lower()
    if topic == "opening" or topic == "guidance":
        guidance = POWER_GUIDANCE.get(ctx.power, "")
        return {"rules": guidance or "No specific opening guidance available."}
    text = _topic_lines(topic) if topic else RULES_PRIMER
    return {"topic": topic or "all", "rules": text}


TOOL_DEFS = [
    {
        "name": "get_rules",
        "description": (
            "Look up Diplomacy rules. Use topic to narrow the result: "
            "'convoys', 'support', 'builds', 'retreats', 'dislodge', 'opening'. "
            "Omit topic for the full rules primer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Optional: convoys | support | builds | retreats | dislodge | opening",
                }
            },
            "required": [],
        },
    },
]
