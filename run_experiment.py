"""
Full experiment runner for the agentic architecture.
Rotates the framework→bloc assignment across runs to control for start position.

Usage (PowerShell):
  python run_experiment.py --players 6 --runs 6 --condition blind transparent
  python run_experiment.py --players 6 --runs 12 --model anthropic/claude-sonnet-4.5
"""
import argparse
import itertools
import uuid
from dotenv import load_dotenv

import orchestrator
import manifest as exp_manifest
from main import (
    make_client, PLAYER_CONFIGS, DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL,
    POWER_PAIRS, TRIAD, build_assignment,
)
from facts import FactWorld

load_dotenv()

# Framework rotation: the triad (utilitarian / deontological / retributive)
# permuted across the 3 fixed power-pairs. All 3! = 6 permutations counterbalance
# start position against framework (D5).
FRAMEWORK_ROTATIONS = [list(p) for p in itertools.permutations(TRIAD)]


def main():
    parser = argparse.ArgumentParser(description="Run a full agentic-Diplomacy experiment")
    parser.add_argument("--players", type=int, choices=[3, 6], default=6,
                        help="6 (default) = the vehicle (3 blocs of 2 non-adjacent powers); "
                             "3 = legacy single-power debug mode.")
    parser.add_argument("--runs", type=int, default=6, help="Runs per condition")
    parser.add_argument(
        # D27: default to transparent only -- the thesis condition is
        # specifically compulsion under known constitutions; blind was a
        # control we're not currently budgeting for. Pass --condition blind
        # transparent explicitly to restore the control comparison.
        "--condition", nargs="+", choices=["blind", "transparent"],
        default=["transparent"],
    )
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_AGENT_MODEL)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL, dest="judge_model")
    parser.add_argument("--negotiation-rounds", type=int, default=3, dest="n_negotiation_rounds")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--facts", action="store_true")
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
    pairs = POWER_PAIRS if args.players == 6 else None

    # Snapshot of key args stored in the manifest so resume can warn on mismatch.
    args_snapshot = {
        "players": args.players,
        "runs": args.runs,
        "condition": args.condition,
        "turns": args.turns,
        "model": args.model,
        "judge_model": args.judge_model,
        "n_negotiation_rounds": args.n_negotiation_rounds,
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

            rotation = FRAMEWORK_ROTATIONS[run_index % len(FRAMEWORK_ROTATIONS)]
            framework_assignment = build_assignment(active_powers, rotation, pairs)

            # Per-run FactWorld so each game gets an independent dossier
            # distribution. Seed is run_counter (stable across resumes) so a
            # given run uses the same dossier whether it ran fresh or after
            # `--resume`. Without per-run seeding every run shares the same
            # intel, confounding framework effects.
            fact_world = FactWorld(enabled=args.facts, seed=run_counter)
            if args.facts:
                fact_world.generate(active_powers)

            # Stable game_id per (experiment, condition, run) so a crashed game
            # can be found and resumed mid-flight (D29). Deterministic, so
            # `--resume EXP_ID` reconstructs the same id and picks up its
            # checkpoint instead of replaying years already played.
            game_id = f"{experiment_id}-{condition}-{run_index}"

            print(f"\n[{run_counter}/{total_runs}] condition={condition} | frameworks={framework_assignment} | game_id={game_id}")

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
                game_id=game_id,
                resume=True,
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
