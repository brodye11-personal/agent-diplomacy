from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolContext:
    """Carries game state and mutable logs into every tool call."""
    power: str
    game: Any                  # diplomacy.Game
    possible_orders: dict      # {loc: [order_str, ...]} pre-fetched for this phase
    turn: str                  # e.g. "S1901M"
    phase_type: str            # "M", "R", "A"
    commitment_log: list       # [{power, to, text, turn, outcome}] — orchestrator-owned
    message_log: list          # [{from, to, content, round, turn}] — orchestrator-owned
    outbound_messages: list    # [{to, content}] — reset per negotiation step by orchestrator
    fact_world: Any = None     # FactWorld placeholder (v3)
