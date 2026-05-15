"""
v1 negotiation pipeline — REMOVED in the agentic redesign.

The negotiation loop is now driven by `orchestrator.run_game`:
  - Outbound: each agent calls the `send_message` tool during a negotiation step.
  - Routing: orchestrator collects outbound messages each round and injects them
    into recipient threads as `Inbound from X: ...` user messages.
  - Commitments: agents call the explicit `record_commitment` tool; the judge
    reads `commitment_log` directly (no prose parsing).

This file is kept as a stub for back-compat with anything still importing the
old names, and to keep `main` git history clean. Do not import from here in v2.
"""

POWER_NEIGHBORS = {
    "ENGLAND": {"FRANCE", "GERMANY", "RUSSIA"},
    "FRANCE": {"ENGLAND", "GERMANY", "ITALY"},
    "GERMANY": {"ENGLAND", "FRANCE", "AUSTRIA", "RUSSIA"},
    "AUSTRIA": {"GERMANY", "RUSSIA", "ITALY", "TURKEY"},
    "ITALY": {"FRANCE", "AUSTRIA", "TURKEY"},
    "RUSSIA": {"ENGLAND", "GERMANY", "AUSTRIA", "TURKEY"},
    "TURKEY": {"AUSTRIA", "ITALY", "RUSSIA"},
}


def run_negotiation_phase(*args, **kwargs):
    raise RuntimeError(
        "run_negotiation_phase was removed in the agentic redesign. "
        "Negotiation is now handled inside orchestrator.run_game via "
        "the send_message / record_commitment tools."
    )
