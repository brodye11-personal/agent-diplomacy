import json
import os
from datetime import datetime


def get_log_path(game_id: str) -> str:
    os.makedirs("logs", exist_ok=True)
    return os.path.join("logs", f"{game_id}.jsonl")


def log_turn(
    path: str,
    game_id: str,
    run: int,
    condition: str,
    framework_assignment: dict,
    model: str,
    phase: str,
    negotiations: list[dict],
    submitted_orders: dict,
    resolved_orders: dict,
    sc_counts: dict,
    dislodged: list,
    betrayals_flagged: list,
    # v1 fields (kept for analysis.py back-compat)
    strategic_plans: dict | None = None,
    truncated_agents: list | None = None,
    order_diagnostics: dict | None = None,
    game_notes_snapshots: dict | None = None,
    # v2 (agentic) fields
    tool_calls: dict | None = None,
    compaction_summaries: dict | None = None,
    commitments: list | None = None,
    raw_message_count: dict | None = None,
    # v3 (FactWorld) fields
    lies_detected: list | None = None,
    # mukobi-inspired additions
    diplomatic_summaries: dict | None = None,
    negotiation_order: list | None = None,
    # constitutional-compulsion experiment
    compulsions: list | None = None,
) -> None:
    """
    Write one turn record to the JSONL log.

    v2 (agentic) additions:
      tool_calls: per-power list of {name, args, result} for every tool call this turn.
      compaction_summaries: per-power post-turn summary written by the agent.
      commitments: full commitment_log slice for this turn, with judge outcomes.
      raw_message_count: per-power message-thread length after compaction
        (sanity check for context growth).

    The top-level schema (game_id..betrayals_flagged) is preserved so analysis.py
    runs unchanged on v2 logs.
    """
    record = {
        "game_id": game_id,
        "run": run,
        "condition": condition,
        "framework_assignment": framework_assignment,
        "model": model,
        "phase": phase,
        "negotiations": negotiations,
        "submitted_orders": submitted_orders,
        "resolved_orders": resolved_orders,
        "sc_counts": sc_counts,
        "dislodged": dislodged,
        "betrayals_flagged": betrayals_flagged,
        "strategic_plans": strategic_plans or {},
        "truncated_agents": truncated_agents or [],
        "order_diagnostics": order_diagnostics or {},
        "game_notes_snapshots": game_notes_snapshots or {},
        "tool_calls": tool_calls or {},
        "compaction_summaries": compaction_summaries or {},
        "commitments": commitments or [],
        "raw_message_count": raw_message_count or {},
        "lies_detected": lies_detected or [],
        "diplomatic_summaries": diplomatic_summaries or {},
        "negotiation_order": negotiation_order or [],
        "compulsions": compulsions or [],
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def log_facts_distributed(path: str, game_id: str, dossiers: dict[str, list[str]]) -> None:
    """Write a one-line record at game start capturing each agent's dossier of fact_ids.

    Stored as a separate top-level record (not on every turn) to keep per-turn
    records lean. Identifiable by `type: "facts_distributed"`.
    """
    if not dossiers:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "facts_distributed",
            "game_id": game_id,
            "dossiers": dossiers,
        }) + "\n")


def get_raw_log_path(game_id: str) -> str:
    """Sidecar path for raw pre-compaction message threads."""
    os.makedirs("logs", exist_ok=True)
    return os.path.join("logs", f"{game_id}.raw.jsonl")


def log_raw_thread(game_id: str, phase: str, power: str, messages: list) -> None:
    """Append a full pre-compaction message thread for debugging.

    Messages are coerced to JSON-serialisable form; Anthropic content-block
    objects (tool_use, text) are stringified.
    """
    path = get_raw_log_path(game_id)
    serialised = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            content = [_serialise_block(b) for b in content]
        serialised.append({"role": m.get("role"), "content": content})
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "game_id": game_id,
            "phase": phase,
            "power": power,
            "messages": serialised,
        }) + "\n")


def _serialise_block(block):
    """Convert an Anthropic content block (or dict) into a JSON-safe shape."""
    if isinstance(block, dict):
        return block
    t = getattr(block, "type", None)
    if t == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if t == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", None),
            "name": getattr(block, "name", None),
            "input": getattr(block, "input", None),
        }
    return {"type": t or "unknown", "repr": str(block)}


def log_game_summary(game_id: str, summary: dict) -> None:
    path = get_log_path(game_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "summary", "game_id": game_id, **summary}) + "\n")
