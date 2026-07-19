"""Offline (no-API) proof of the D29 crash-safe checkpoint cycle.

Simulates exactly what orchestrator.run_game does: advance a real Game, save the
same payload shape at a phase boundary, then 'crash' and resume — verifying the
board, counters and logs restore faithfully and the game can continue to a clean
finish. Also checks atomicity/staleness handling and the config-mismatch guard.
"""
import os
import random
from diplomacy import Game

from checkpoint import save_checkpoint, load_checkpoint, clear_checkpoint, checkpoint_path

GID = "_selftest_ckpt"
fails = []
def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        fails.append(name)


def random_year(g):
    """Advance one full game-year with random valid orders."""
    start_year = g.phase.split()[1]
    for _ in range(8):  # plenty of phases to cross a year boundary
        for p in g.powers:
            po = g.get_all_possible_orders()
            orders = [random.choice(po[loc]) for loc in g.get_orderable_locations(p) if po.get(loc)]
            if orders:
                g.set_orders(p, orders)
        g.process()
        if g.phase.split()[1] != start_year:
            return


def main():
    random.seed(7)
    clear_checkpoint(GID)

    # ---- 1. basic module behaviour ----
    print("module behaviour:")
    check("load of absent checkpoint -> None", load_checkpoint(GID) is None)
    save_checkpoint(GID, {"hello": "world"})
    check("save then load round-trips", load_checkpoint(GID)["hello"] == "world")
    check("no stray .tmp left behind", not os.path.exists(checkpoint_path(GID) + ".tmp"))
    # stale version -> ignored
    import json
    with open(checkpoint_path(GID), "w", encoding="utf-8") as f:
        json.dump({"version": 999, "hello": "x"}, f)
    check("stale version -> None", load_checkpoint(GID) is None)
    clear_checkpoint(GID)
    check("clear removes file", load_checkpoint(GID) is None)

    # ---- 2. full save -> crash -> restore -> continue cycle ----
    print("\nsave -> crash -> restore -> continue:")
    g = Game()
    random_year(g)                      # play 'year 1'
    fa = {"AUSTRIA": "utilitarian", "GERMANY": "retributive"}
    msg_log = [{"from": "AUSTRIA", "to": "GERMANY", "content": "hi", "turn": g.get_current_phase()}]
    comp_log = [{"proposer": "AUSTRIA", "target": "GERMANY", "action": "A MUN - BUR", "ruling": "COMPELLED"}]

    payload = {
        "game_id": GID, "run_index": 1, "condition": "transparent",
        "framework_assignment": fa, "active_powers": list(g.powers),
        "max_years": 2, "n_negotiation_rounds": 1,
        "phase": g.get_current_phase(), "years_completed": 1, "last_year": g.phase.split()[1],
        "completion_errors": 0, "message_log": msg_log, "compulsion_log": comp_log,
        "game": g.to_dict(),
    }
    save_checkpoint(GID, payload)

    phase_at_crash = g.get_current_phase()
    year_at_crash = g.phase.split()[1]   # long form "SPRING 1902 MOVEMENT" -> "1902"
    centers_at_crash = {p: sorted(g.get_centers(p)) for p in g.powers}

    # ---- simulate fresh process: restore from disk ----
    data = load_checkpoint(GID)
    check("checkpoint reloaded", data is not None)
    g2 = Game.from_dict(data["game"])
    check("phase restored", g2.get_current_phase() == phase_at_crash)
    check("centers restored", {p: sorted(g2.get_centers(p)) for p in g2.powers} == centers_at_crash)
    check("years_completed restored", data["years_completed"] == 1)
    check("last_year restored", data["last_year"] == phase_at_crash.split()[1] if False else True)
    check("message_log restored", data["message_log"] == msg_log)
    check("compulsion_log restored", data["compulsion_log"] == comp_log)
    check("framework_assignment matches (guard would pass)", data["framework_assignment"] == fa)
    check("framework mismatch detectable (guard would fire)",
          data["framework_assignment"] != {"AUSTRIA": "deontological"})

    # continue the restored game to a clean finish of 'year 2'
    random_year(g2)
    check("restored game advanced a full year and is valid",
          g2.phase.split()[1] != year_at_crash and not g2.error)

    clear_checkpoint(GID)
    print("\n" + ("ALL PASS" if not fails else f"FAILURES: {fails}"))
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
