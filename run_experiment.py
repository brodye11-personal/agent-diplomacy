"""
Full experiment runner for the agentic architecture.
Rotates framework assignments across runs to control for positional advantage.

Usage (PowerShell):
  python run_experiment.py --players 3 --runs 6 --condition blind transparent
  python run_experiment.py --players 7 --runs 20 --model claude-sonnet-4-5-20250929
"""
import argparse
import uuid
from dotenv import load_dotenv

import orchestrator
import manifest as exp_manifest
from main import make_client, PLAYER_CONFIGS, DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL
from facts import FactWorld

load_dotenv()

# Framework rotation sets — same positional-counterbalancing scheme as v1.
FRAMEWORKS_3 = [
    ["utilitarian", "deontological", "rawlsian"],
    ["deontological", "rawlsian", "utilitarian"],
    ["rawlsian", "utilitarian", "deontological"],
    ["baseline", "utilitarian", "deontological"],
    ["utilitarian", "baseline", "rawlsian"],
    ["deontological", "rawlsian", "baseline"],
]

FRAMEWORKS_7 = [
    ["utilitarian", "deontological", "rawlsian", "baseline", "utilitarian", "deontological", "rawlsian"],
    ["deontological", "rawlsian", "utilitarian", "utilitarian", "baseline", "rawlsian", "deontological"],
    ["rawlsian", "utilitarian", "deontological", "deontological", "rawlsian", "baseline", "utilitarian"],
    ["baseline", "utilitarian", "rawlsian", "deontological", "utilitarian", "rawlsian", "baseline"],
    ["utilitarian", "baseline", "deontological", "rawlsian", "deontological", "utilitarian", "baseline"],
    ["deontological", "rawlsian", "baseline", "utilitarian", "baseline", "deontological", "rawlsian"],
]

# mukobi-inspired defector condition: one power is a guaranteed defector.
# Rotates which power/position gets the defector role so results aren't
# confounded with starting position. Use with --defector flag.
FRAMEWORKS_3_DEFECTOR = [
    ["defector", "utilitarian", "deontological"],
    ["utilitarian", "defector", "rawlsian"],
    ["deontological", "rawlsian", "defector"],
    ["defector", "rawlsian", "utilitarian"],
    ["utilitarian", "deontological", "defector"],
    ["defector", "baseline", "rawlsian"],
]

FRAMEWORKS_7_DEFECTOR = [
    ["defector", "utilitarian", "deontological", "rawlsian", "baseline", "utilitarian", "deontological"],
    ["utilitarian", "defector", "rawlsian", "utilitarian", "baseline", "rawlsian", "deontological"],
    ["rawlsian", "utilitarian", "defector", "deontological", "rawlsian", "baseline", "utilitarian"],
    ["baseline", "utilitarian", "rawlsian", "defector", "utilitarian", "rawlsian", "baseline"],
    ["utilitarian", "baseline", "deontological", "rawlsian", "defector", "utilitarian", "baseline"],
    ["deontological", "rawlsian", "baseline", "utilitarian", "baseline", "defector", "rawlsian"],
]


def main():
    parser = argparse.ArgumentParser(description="Run a full agentic-Diplomacy experiment")
    parser.add_argument("--players", type=int, choices=[3, 7], default=3,
                        help="Number of active players: 3=ENG/FRA/GER, 7=all powers")
    parser.add_argument("--runs", type=int, default=6, help="Runs per condition")
    parser.add_argument(
        "--condition", nargs="+", choices=["blind", "transparent"],
        default=["blind", "transparent"],
    )
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_AGENT_MODEL)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL, dest="judge_model")
    parser.add_argument("--negotiation-rounds", type=int, default=3, dest="n_negotiation_rounds")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--facts", action="store_true")
    parser.add_argument(
        "--defector", action="store_true",
        help="Use defector framework rotation sets (one power is always a defector).",
    )
    parser.add_argument(
        "--max-errors", type=int, default=10, dest="max_completion_errors",
        help="Abort a game after this many API/engine errors (default: 10).",
    )
    parser.add_argument(
        "--resume", metavar="EXP_ID", default=None,
        help="Resume an interrupted batch using the experiment ID printed at start.",
    )
    args = parser.parse_args()

    active_powers = PLAYER_CONFIGS[args.players]
    if args.defector:
        framework_sets = FRAMEWORKS_3_DEFECTOR if args.players == 3 else FRAMEWORKS_7_DEFECTOR
    else:
        framework_sets = FRAMEWORKS_3 if args.players == 3 else FRAMEWORKS_7

    # Snapshot of key args stored in the manifest so resume can warn on mismatch.
    args_snapshot = {
        "players": args.players,
        "runs": args.runs,
        "condition": args.condition,
        "turns": args.turns,
        "model": args.model,
        "judge_model": args.judge_model,
        "n_negotiation_rounds": args.n_negotiation_rounds,
        "defector": args.defector,
        "max_completion_errors": args.max_completion_errors,
        "facts": args.facts,
    }

    # ── MANIFEST: create new or resume existing ────────────────────────────
    if args.resume:
        exp = exp_manifest.load(args.resume)
        experiment_id = args.resume
        exp_manifest.warn_if_args_differ(exp, args_snapshot)
        done = exp_manifest.completed_set(exp)
        already = len(done)
        print(f"[resume] experiment_id={experiment_id} | {already} run(s) already complete, skipping.")
    else:
        experiment_id = uuid.uuid4().hex[:8]
        exp = exp_manifest.create(experiment_id, args_snapshot)
        done = set()

    client = make_client()

    total_runs = len(args.condition) * args.runs
    completed_this_session = 0

    for condition in args.condition:
        for run_index in range(args.runs):
            # run_counter is deterministic: same value whether resuming or not.
            condition_idx = args.condition.index(condition)
            run_counter = condition_idx * args.runs + run_index + 1

            if (condition, run_index) in done:
                print(f"\n[{run_counter}/{total_runs}] SKIP (already done) condition={condition} run={run_index}")
                continue

            framework_list = framework_sets[run_index % len(framework_sets)]
            framework_assignment = dict(zip(active_powers, framework_list))

            # Per-run FactWorld so each game gets an independent dossier
            # distribution. Seed is run_counter (stable across resumes) so a
            # given run uses the same dossier whether it ran fresh or after
            # `--resume`. Without per-run seeding every run shares the same
            # intel, confounding framework effects.
            fact_world = FactWorld(enabled=args.facts, seed=run_counter)
            if args.facts:
                fact_world.generate(active_powers)

            print(f"\n[{run_counter}/{total_runs}] condition={condition} | frameworks={framework_assignment}")

            summary = orchestrator.run_game(
                run_index=run_counter,
                condition=condition,
                framework_assignment=framework_assignment,
                model=args.model,
                judge_model=args.judge_model,
                max_years=args.turns,
                verbose=args.verbose,
                fact_world=fact_world,
                client=client,
                active_powers=active_powers,
                n_negotiation_rounds=args.n_negotiation_rounds,
                max_completion_errors=args.max_completion_errors,
            )

            # Record completion immediately so a crash mid-next-game doesn't
            # lose this one.
            exp_manifest.record_completion(
                experiment_id=experiment_id,
                condition=condition,
                run_index=run_index,
                run_counter=run_counter,
                game_id=summary.get("game_id", "unknown"),
                framework_assignment=framework_assignment,
            )
            completed_this_session += 1
            print(f"  -> Winner: {summary['winner']} | SC: {summary['final_sc_counts']}")

    total_done = len(exp_manifest.completed_set(exp_manifest.load(experiment_id)))
    print(
        f"\n{completed_this_session} run(s) completed this session "
        f"({total_done}/{total_runs} total for experiment {experiment_id})."
    )
    if total_done < total_runs:
        print(f"To continue: python run_experiment.py --resume {experiment_id}")
    else:
        print("Batch complete. Run `python analysis.py` to summarise results.")


if __name__ == "__main__":
    main()
