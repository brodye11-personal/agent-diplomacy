"""
Full experiment runner for the agentic architecture.
Rotates framework assignments across runs to control for positional advantage.

Usage (PowerShell):
  python run_experiment.py --players 3 --runs 6 --condition blind transparent
  python run_experiment.py --players 7 --runs 20 --model claude-sonnet-4-5-20250929
"""
import argparse
from dotenv import load_dotenv

import orchestrator
from main import make_client, PLAYER_CONFIGS, DEFAULT_AGENT_MODEL, DEFAULT_JUDGE_MODEL
from facts import FactWorld

load_dotenv()

# Framework rotation sets — same positional-counterbalancing scheme as v1.
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
    args = parser.parse_args()

    active_powers = PLAYER_CONFIGS[args.players]
    framework_sets = FRAMEWORKS_3 if args.players == 3 else FRAMEWORKS_7

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
            )
            print(f"  -> Winner: {summary['winner']} | SC: {summary['final_sc_counts']}")

    print(f"\nAll {total_runs} runs complete. Run `python analysis.py` to summarise results.")


if __name__ == "__main__":
    main()
