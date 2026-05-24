"""
Experiment manifest — tracks which games in a batch have completed.

Each run_experiment.py invocation creates a manifest file:
  logs/experiment_{id}.json

The file records the experiment args and every completed (condition, run_index)
pair with its game_id. On resume, run_experiment.py reads the manifest, skips
completed pairs, and continues numbering from where it left off.

Only between-game resume is supported — mid-game state is not checkpointed.
"""

import json
import os
from datetime import datetime, timezone

_DIR = "logs"


def _path(experiment_id: str) -> str:
    os.makedirs(_DIR, exist_ok=True)
    return os.path.join(_DIR, f"experiment_{experiment_id}.json")


def create(experiment_id: str, args_snapshot: dict) -> dict:
    """
    Create a fresh manifest for a new experiment batch and persist it.
    Returns the manifest dict (also written to disk immediately so --resume
    works even if the first game crashes before completing).
    """
    manifest = {
        "experiment_id": experiment_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "args": args_snapshot,
        "completed": [],
    }
    _save(_path(experiment_id), manifest)
    print(f"[manifest] experiment_id={experiment_id}  (use --resume {experiment_id} to continue if interrupted)")
    return manifest


def load(experiment_id: str) -> dict:
    """
    Load an existing manifest. Raises FileNotFoundError with a helpful message
    if the experiment_id doesn't match any saved file.
    """
    path = _path(experiment_id)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No experiment manifest found for id '{experiment_id}'.\n"
            f"Expected file: {path}\n"
            f"Run `python run_experiment.py` (without --resume) to start a new batch."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def record_completion(
    experiment_id: str,
    condition: str,
    run_index: int,
    run_counter: int,
    game_id: str,
    framework_assignment: dict,
) -> None:
    """
    Append one completed-game entry to the manifest and flush to disk.
    Called immediately after orchestrator.run_game() returns so the record
    lands even if the next game crashes.
    """
    manifest = load(experiment_id)
    manifest["completed"].append({
        "condition": condition,
        "run_index": run_index,
        "run_counter": run_counter,
        "game_id": game_id,
        "framework_assignment": framework_assignment,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    _save(_path(experiment_id), manifest)


def completed_set(manifest: dict) -> set[tuple[str, int]]:
    """
    Return the set of (condition, run_index) pairs already recorded as done.
    Used by run_experiment.py to skip games on resume.
    """
    return {
        (entry["condition"], entry["run_index"])
        for entry in manifest.get("completed", [])
    }


def warn_if_args_differ(manifest: dict, current_args: dict) -> None:
    """
    Print a warning for any key experiment parameter that differs between
    the saved manifest and the current invocation. Doesn't block — the user
    may legitimately want to resume with a different model or turn count.
    """
    saved = manifest.get("args", {})
    important = ["players", "runs", "condition", "turns", "defector", "n_negotiation_rounds"]
    diffs = [
        f"  {k}: saved={saved.get(k)!r}  now={current_args.get(k)!r}"
        for k in important
        if saved.get(k) != current_args.get(k)
    ]
    if diffs:
        print("[manifest] WARNING: current args differ from saved experiment:")
        print("\n".join(diffs))
        print("[manifest] Continuing anyway — results may be inconsistent across runs.")


def _save(path: str, manifest: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
