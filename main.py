"""
Entry point for a single agentic-Diplomacy game.

Wires up CLI args → Anthropic client → orchestrator.run_game.
The actual game loop lives in orchestrator.py; everything here is glue.

Usage examples (PowerShell):
  python main.py --players 3 --turns 2 --verbose
  python main.py --players 7 --turns 5 --frameworks utilitarian deontological hhh baseline utilitarian deontological hhh
  python main.py --condition transparent --players 3 --model claude-sonnet-4-5-20250929
"""
import argparse
import os
from dotenv import load_dotenv
import anthropic

import orchestrator
from facts import FactWorld

load_dotenv()

ALL_POWERS = ["ENGLAND", "FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"]

PLAYER_CONFIGS = {
    3: ["ENGLAND", "FRANCE", "GERMANY"],
    7: ALL_POWERS,
}

# Defaults: cheap + fast for iteration; promote to Sonnet once tool-use is reliable.
DEFAULT_AGENT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_JUDGE_MODEL = "claude-sonnet-4-5-20250929"


def make_client() -> anthropic.Anthropic:
    """Anthropic client. Requires ANTHROPIC_API_KEY (no fallback)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(api_key=api_key)


def main():
    parser = argparse.ArgumentParser(description="Agentic Diplomacy: moral frameworks under negotiation pressure")
    parser.add_argument("--condition", choices=["blind", "transparent"], default="blind")
    parser.add_argument("--players", type=int, choices=[3, 7], default=3,
                        help="Number of active players: 3=ENG/FRA/GER, 7=all powers")
    parser.add_argument("--frameworks", nargs="*", default=None,
                        help="Framework per active power (in player order): baseline utilitarian deontological hhh")
    parser.add_argument("--turns", type=int, default=5, help="Number of game years to play")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_AGENT_MODEL,
                        help=f"Anthropic model for agents (default: {DEFAULT_AGENT_MODEL})")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL, dest="judge_model",
                        help=f"Anthropic model for the commitment judge (default: {DEFAULT_JUDGE_MODEL})")
    parser.add_argument("--negotiation-rounds", type=int, default=3, dest="n_negotiation_rounds",
                        help="Negotiation rounds per movement turn (default: 3)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--facts", action="store_true",
                        help="Enable FactWorld (v3 — not yet implemented)")
    args = parser.parse_args()

    active_powers = PLAYER_CONFIGS[args.players]

    if args.frameworks is None:
        frameworks_list = ["baseline"] * len(active_powers)
    elif len(args.frameworks) != len(active_powers):
        parser.error(
            f"--frameworks expects {len(active_powers)} values for --players {args.players} "
            f"({', '.join(active_powers)}), got {len(args.frameworks)}"
        )
    else:
        frameworks_list = args.frameworks

    framework_assignment = dict(zip(active_powers, frameworks_list))

    client = make_client()
    fact_world = FactWorld(enabled=args.facts)
    if args.facts:
        fact_world.generate(active_powers)

    for run_index in range(1, args.runs + 1):
        print(f"\nStarting run {run_index}/{args.runs} ({args.players}-player)...")
        summary = orchestrator.run_game(
            run_index=run_index,
            condition=args.condition,
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
        print(f"Run {run_index} complete. Winner: {summary['winner']} | SC: {summary['final_sc_counts']}")


if __name__ == "__main__":
    main()
