import threading
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
    active_powers: list = None  # human-controlled powers; others auto-hold as neutrals
    fact_world: Any = None     # FactWorld placeholder (v3)
    # Constitutional-compulsion experiment: propose_compulsion appends proposals
    # here; the orchestrator fills ruling/complied after the negotiation phase.
    compulsion_log: list = None   # [{proposer, target, action, argument, turn, ...}]
    binding_orders: dict = None   # power -> [order_str] the arbiter has compelled
    # One lock per game, shared across threads. Protects commitment_log and
    # message_log from interleaved appends/reads when agents run in parallel.
    log_lock: Any = None

    def __post_init__(self):
        if self.active_powers is None:
            self.active_powers = []
        if self.compulsion_log is None:
            self.compulsion_log = []
        if self.binding_orders is None:
            self.binding_orders = {}
        if self.log_lock is None:
            self.log_lock = threading.Lock()
