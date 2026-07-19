"""Crash-safe game checkpointing (D29).

A long multi-year game is the expensive unit of work. If the process dies
mid-game (laptop crash, power loss, OOM, ctrl-C), we do NOT want to re-pay for
the years already played. `run_game` writes the full durable state to
`logs/<game_id>.checkpoint.json` at the TOP of every phase (atomically), so a
crash loses at most the single in-flight phase (~one phase of API spend), never
the whole game. On resume, `run_game` reloads the checkpoint and continues from
the saved phase.

Why so little needs saving: agents hold no cross-phase state — they are reset to
a deterministic, orchestrator-built state block at the start of every phase
(D10/D14) — and `fact_world` is deterministic (static pool, rebuilt by the
caller). So the only durable state is the `diplomacy.Game` board (via `to_dict`,
verified JSON round-trip), the year/error counters, and the accumulated
message/compulsion logs. That is exactly what the checkpoint stores.
"""
from __future__ import annotations
import json
import os

CHECKPOINT_VERSION = 1


def checkpoint_path(game_id: str) -> str:
    os.makedirs("logs", exist_ok=True)
    return os.path.join("logs", f"{game_id}.checkpoint.json")


def save_checkpoint(game_id: str, payload: dict) -> None:
    """Atomically persist `payload` for `game_id`.

    Writes a temp file then os.replace()s it into place, so a crash DURING the
    write can never corrupt an existing good checkpoint (replace is atomic on
    both POSIX and Windows).
    """
    path = checkpoint_path(game_id)
    tmp = path + ".tmp"
    body = {"version": CHECKPOINT_VERSION, **payload}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_checkpoint(game_id: str) -> dict | None:
    """Return the saved payload for `game_id`, or None if absent/unreadable/stale."""
    path = checkpoint_path(game_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("version") != CHECKPOINT_VERSION:
        return None
    return data


def clear_checkpoint(game_id: str) -> None:
    """Remove a completed game's checkpoint (and any stray temp file)."""
    for p in (checkpoint_path(game_id), checkpoint_path(game_id) + ".tmp"):
        try:
            os.remove(p)
        except OSError:
            pass
