"""
Entry point for a single agentic-Diplomacy game.

Wires up CLI args -> Anthropic-format client (routed via OpenRouter) ->
orchestrator.run_game. The actual game loop lives in orchestrator.py.

Usage examples (PowerShell):
  python main.py --players 3 --turns 2 --verbose
  python main.py --players 7 --turns 5 --frameworks utilitarian deontological hhh baseline utilitarian deontological hhh
  python main.py --condition transparent --players 3 --model anthropic/claude-sonnet-4.5
"""
import argparse
import os
import sys
from dotenv import load_dotenv
import anthropic

import orchestrator
from facts import FactWorld

# Windows consoles default to cp1252; our prompts + verbose output contain
# unicode (en-dash, arrow, etc.). Force UTF-8 so prints don't crash mid-run.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

load_dotenv()

ALL_POWERS = ["ENGLAND", "FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"]

PLAYER_CONFIGS = {
    3: ["ENGLAND", "FRANCE", "GERMANY"],
    7: ALL_POWERS,
}

# OpenRouter's Anthropic-compatible Messages endpoint.
# The Anthropic SDK accepts base_url + auth_token (bearer auth) directly.
OPENROUTER_BASE_URL = "https://openrouter.ai/api"

# Defaults: cheap iteration model. DeepSeek V3 is ~5x cheaper than Haiku 4.5
# on input and ~5x cheaper on output, with strong agentic tool-use. Override
# with --model anthropic/claude-haiku-4.5 (or sonnet) for production runs
# once tool-use behaviour is confirmed on this game shape.
# OpenRouter slug format = "<provider>/<model>".
DEFAULT_AGENT_MODEL = "deepseek/deepseek-chat"
DEFAULT_JUDGE_MODEL = "anthropic/claude-sonnet-4.5"


def make_client() -> anthropic.Anthropic:
    """
    Build an anthropic.Anthropic client that talks to OpenRouter's
    Anthropic-Messages endpoint.

    Why OpenRouter: cross-provider routing, sticky-routing for prompt
    caching, single billing surface for any future model comparison.
    Why the Anthropic SDK against it: zero changes to our tool-use loop
    -- the request/response shape is identical to Anthropic-direct.
    Auth uses the bearer token (auth_token=), not x-api-key (api_key=).
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return anthropic.Anthropic(
        base_url=OPENROUTER_BASE_URL,
        auth_token=api_key,
    )


def main():
    parser = argparse.ArgumentParser(description="Agentic Diplomacy: moral frameworks under negotiation pressure")
    parser.add_argument("--condition", choices=["blind", "transparent"], default="transparent",
                        help="transparent (default) = rivals' full constitutions are known "
                             "(the thesis condition); blind = the R4 baseline.")
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
                        help="Enable FactWorld: shared morally-loaded facts about territories "
                             "(common knowledge by default). The substrate the compulsion "
                             "arbiter reasons over — recommended ON for compulsion runs.")
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

    for run_index in range(1, args.runs + 1):
        # Per-run FactWorld so each run gets an independent dossier distribution.
        # Without this every run uses seed=42 and the morally-loaded intel is
        # identical across runs, confounding any framework effect on lying.
        fact_world = FactWorld(enabled=args.facts, seed=run_index)
        if args.facts:
            fact_world.generate(active_powers)

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
