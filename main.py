"""
Entry point for a single agentic-Diplomacy game.

Wires up CLI args -> Anthropic-format client (routed via OpenRouter) ->
orchestrator.run_game. The actual game loop lives in orchestrator.py.

Usage examples (PowerShell):
  python main.py --players 6 --turns 2 --verbose --facts
  python main.py --players 6 --frameworks retributive utilitarian deontological
  python main.py --condition transparent --players 6 --model anthropic/claude-sonnet-4.5
"""
import argparse
import os
import sys
from dotenv import load_dotenv
import anthropic

import orchestrator
from facts import FactWorld
from facts_matched import as_pool as matched_as_pool

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

# P6 vehicle (D5/D6): 3 blocs of two NON-ADJACENT powers each, Turkey dropped.
# The pairs are fixed; the 3 frameworks rotate across them (run_experiment.py).
POWER_PAIRS = [("ENGLAND", "AUSTRIA"), ("FRANCE", "RUSSIA"), ("GERMANY", "ITALY")]
ACTIVE_POWERS_6 = [p for pair in POWER_PAIRS for p in pair]
TRIAD = ["utilitarian", "deontological", "retributive"]

PLAYER_CONFIGS = {
    3: ["ENGLAND", "FRANCE", "GERMANY"],   # legacy single-power debug mode
    6: ACTIVE_POWERS_6,                    # the experiment vehicle
}


def build_assignment(active_powers, frameworks, pairs=None):
    """Map power -> framework.

    With `pairs` (the 6-power vehicle), `frameworks` has one entry per pair and
    both powers of a pair share it (so the bloc is a single framework). Without
    pairs (legacy 3-power), `frameworks` is per-power.
    """
    if pairs:
        fa = {}
        for (p1, p2), fw in zip(pairs, frameworks):
            fa[p1] = fw
            fa[p2] = fw
        return fa
    return dict(zip(active_powers, frameworks))

# OpenRouter's Anthropic-compatible Messages endpoint.
# The Anthropic SDK accepts base_url + auth_token (bearer auth) directly.
OPENROUTER_BASE_URL = "https://openrouter.ai/api"

# Defaults (D21, supersedes D17): Sonnet 4.6 for BOTH agents and the arbiter.
# D20 found Haiku 4.5 (the D17 agent default) was the only one of three models
# that never even attempted compel_action from an identical opening position,
# while Sonnet 4.6 and Opus 4.8 both did, with more specific, adjacency-
# grounded arguments. Bumping agents to Sonnet 4.6 to test whether that
# specificity raises the COMPELLED rate (D19's 0/17), not just the attempt
# rate. This drops the agent/arbiter cost-tier split D17 set up -- Sonnet 4.6
# is now the ceiling for both roles. DeepSeek V3 stays excluded for agents:
# documented weak/inconsistent function-calling support, and no `thinking`
# param support, which would silently drop the reasoning trace D8 relies on.
# OpenRouter slug format = "<provider>/<model>".
DEFAULT_AGENT_MODEL = "anthropic/claude-sonnet-4.6"
DEFAULT_JUDGE_MODEL = "anthropic/claude-sonnet-4.6"


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
    parser.add_argument("--players", type=int, choices=[3, 6], default=6,
                        help="6 (default) = the vehicle: 3 blocs of 2 non-adjacent powers "
                             "(ENG+AUS, FRA+RUS, GER+ITA), Turkey dropped. 3 = legacy "
                             "single-power debug mode (ENG/FRA/GER).")
    parser.add_argument("--frameworks", nargs="*", default=None,
                        help="3 frameworks. For --players 6 they map to the 3 pairs in order "
                             "(ENG+AUS, FRA+RUS, GER+ITA); for --players 3 they map to the 3 "
                             "powers. Default: utilitarian deontological retributive.")
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
    parser.add_argument("--matched-facts", action="store_true", dest="matched_facts",
                        help="Use the D41 matched-triple pool (facts_matched) instead of the "
                             "incremental 33-fact FACT_POOL: 8 territories x 3 facts, one per "
                             "framework, matched on specificity, gravity and actionability so "
                             "no framework is advantaged by the substrate. Requires --facts.")
    parser.add_argument("--game-id", default=None, dest="game_id",
                        help="Stable game id for crash-safe resume (D29). If a checkpoint "
                             "exists for it, the run continues from where it crashed instead "
                             "of replaying years already played. Re-run the SAME command "
                             "(same --frameworks etc.) to resume. With --runs >1 each run "
                             "appends its index.")
    args = parser.parse_args()

    active_powers = PLAYER_CONFIGS[args.players]
    pairs = POWER_PAIRS if args.players == 6 else None
    n_expected = len(pairs) if pairs else len(active_powers)

    if args.frameworks is None:
        frameworks_list = list(TRIAD)
    elif len(args.frameworks) != n_expected:
        unit = "pairs (ENG+AUS, FRA+RUS, GER+ITA)" if pairs else f"powers ({', '.join(active_powers)})"
        parser.error(
            f"--frameworks expects {n_expected} values for --players {args.players} "
            f"-> {unit}, got {len(args.frameworks)}"
        )
    else:
        frameworks_list = args.frameworks

    framework_assignment = build_assignment(active_powers, frameworks_list, pairs)

    client = make_client()

    for run_index in range(1, args.runs + 1):
        # Per-run FactWorld so each run gets an independent dossier distribution.
        # Without this every run uses seed=42 and the morally-loaded intel is
        # identical across runs, confounding any framework effect on lying.
        pool = matched_as_pool() if args.matched_facts else None
        fact_world = FactWorld(enabled=args.facts, seed=run_index, pool=pool)
        if args.facts:
            fact_world.generate(active_powers)

        # Crash-safe id (D29): only when the user opts in via --game-id. With
        # multiple runs each gets a distinct suffix so they don't collide.
        game_id = None
        if args.game_id:
            game_id = args.game_id if args.runs == 1 else f"{args.game_id}-{run_index}"

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
            game_id=game_id,
            resume=bool(game_id),
        )
        print(f"Run {run_index} complete. Winner: {summary['winner']} | SC: {summary['final_sc_counts']}")


if __name__ == "__main__":
    main()
