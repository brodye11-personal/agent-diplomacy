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
    strategic_plans: dict | None = None,
    truncated_agents: list | None = None,
) -> None:
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
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def log_game_summary(game_id: str, summary: dict) -> None:
    path = get_log_path(game_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "summary", "game_id": game_id, **summary}) + "\n")
