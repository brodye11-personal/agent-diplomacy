"""
Full experiment runner. Loops over conditions and rotates framework assignments
across runs to control for positional advantage.

Usage:
  python run_experiment.py --players 3 --runs 6 --condition blind transparent --model google/gemini-2.5-flash
  python run_experiment.py --players 7 --runs 20 --model google/gemini-2.5-flash
"""
import argparse
import os
from dotenv import load_dotenv

from main import run_game, make_client, PLAYER_CONFIGS
from facts import FactWorld

load_dotenv()

# Framework rotation sets — cycle through so each position gets each framework
# across runs. Add more sets or increase --runs for better counterbalancing.
FRAMEWORKS_3 = [
    ["utilitarian", "deontological", "hhh"],
    ["deontological", "hhh", "utilitarian"],
    ["hhh", "utilitarian", "deontological"],
    ["baseline", "utilitarian", "deontological"],
    ["utilitarian", "baseline", "hhh"],
    ["deontological", "hhh", "baseline"],
]

FRAMEWORKS_7 = [
    ["utilitarian", "deontological", "hhh", "baseline", "utilitarian", "deontological", "hhh"],
    ["deontological", "hhh", "utilitarian", "utilitarian", "baseline", "hhh", "deontological"],
    ["hhh", "utilitarian", "deontological", "deontological", "hhh", "baseline", "utilitarian"],
    ["baseline", "utilitarian", "hhh", "deontological", "utilitarian", "hhh", "baseline"],
    ["utilitarian", "baseline", "deontological", "hhh", "deontological", "utilitarian", "baseline"],
    ["deontological", "hhh", "baseline", "utilitarian", "baseline", "deontological", "hhh"],
]


def main():
    parser = argparse.ArgumentParser(description="Run full Diplomacy experiment")
    parser.add_argument("--players", type=int, choices=[3, 7], default=3,
                        help="Number of active players: 3=ENG/FRA/GER, 7=all powers")
    parser.add_argument("--runs", type=int, default=6, help="Runs per condition")
    parser.add_argument(
        "--condition", nargs="+", choices=["blind", "transparent"],
        default=["blind", "transparent"],
    )
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--model", default="openai/gpt-4o")
    parser.add_argument("--judge-model", default=None, dest="judge_model",
                        help="Model for commitment judge (defaults to --model if not set)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--fast-parallel", action="store_true", dest="fast_parallel")
    parser.add_argument("--neighbor-only", action="store_true", dest="neighbor_only")
    parser.add_argument("--exchanges", type=int, default=2)
    parser.add_argument("--facts", action="store_true")
    args = parser.parse_args()

    active_powers = PLAYER_CONFIGS[args.players]
    framework_sets = FRAMEWORKS_3 if args.players == 3 else FRAMEWORKS_7
    judge_model = args.judge_model or args.model

    client = make_client()
    fact_world = FactWorld(enabled=args.facts)
    if args.facts:
        fact_world.generate(active_powers)

    total_runs = len(args.condition) * args.runs
    run_counter = 0

    for condition in args.condition:
        for run_index in range(args.runs):
            run_counter += 1
            framework_list = framework_sets[run_index % len(framework_sets)]
            framework_assignment = dict(zip(active_powers, framework_list))

            print(f"\n[{run_counter}/{total_runs}] condition={condition} | frameworks={framework_assignment}")

            summary = run_game(
                run_index=run_counter,
                condition=condition,
                framework_assignment=framework_assignment,
                model=args.model,
                judge_model=judge_model,
                max_years=args.turns,
                verbose=args.verbose,
                fact_world=fact_world,
                client=client,
                active_powers=active_powers,
                parallel_negotiation=args.fast_parallel,
                neighbor_only=args.neighbor_only,
                exchanges=args.exchanges,
            )
            print(f"  → Winner: {summary['winner']} | SC: {summary['final_sc_counts']}")

    print(f"\nAll {total_runs} runs complete. Run `python analysis.py` to summarise results.")


if __name__ == "__main__":
    main()
