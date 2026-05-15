import argparse
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
from diplomacy import Game

from agent import LLMAgent
from frameworks import build_system_prompt
from negotiation import run_negotiation_phase
from betrayal import judge_commitments, extract_self_flagged
from logger import get_log_path, log_turn, log_game_summary
from facts import FactWorld
from memory import GameMemory

load_dotenv()

ALL_POWERS = ["ENGLAND", "FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"]

PLAYER_CONFIGS = {
    3: ["ENGLAND", "FRANCE", "GERMANY"],
    7: ALL_POWERS,
}


def make_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key.")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def get_board_state(game: Game, power: str, possible_orders: dict) -> dict:
    orderable_locs = game.get_orderable_locations(power)
    return {
        "phase": game.get_current_phase(),
        "your_units": game.get_units(power),
        "your_centers": game.get_centers(power),
        "all_units": game.get_units(),
        "all_centers": game.get_centers(),
        "possible_orders": {
            loc: possible_orders.get(loc, [])
            for loc in orderable_locs
        },
    }



def _extract_commitments_made(power: str, negotiations: list[dict]) -> list[str]:
    """Pull commitment strings made by this power in this turn's negotiations."""
    seen = set()
    commitments = []
    for convo in negotiations:
        if power not in convo["pair"]:
            continue
        for msg in convo["messages"]:
            if msg["role"] == power:
                content = msg["content"]
                if isinstance(content, dict) and content.get("commitment"):
                    c = content["commitment"]
                    if c not in seen:
                        seen.add(c)
                        commitments.append(c)
    return commitments


def _extract_commitments_with_opponents(power: str, negotiations: list[dict]) -> list[dict]:
    """Same as _extract_commitments_made but preserves the recipient of each commitment.

    Returns [{"to": opponent, "commitment": text}, ...] with duplicates removed.
    """
    seen = set()
    result = []
    for convo in negotiations:
        if power not in convo["pair"]:
            continue
        opponent = next((p for p in convo["pair"] if p != power), "?")
        for msg in convo["messages"]:
            if msg["role"] != power:
                continue
            content = msg["content"]
            if not isinstance(content, dict):
                continue
            text = (content.get("commitment") or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append({"to": opponent, "commitment": text})
    return result


def run_game(
    run_index: int,
    condition: str,
    framework_assignment: dict,
    model: str,
    judge_model: str,
    max_years: int,
    verbose: bool,
    fact_world: FactWorld,
    client: OpenAI,
    active_powers: list[str],
    parallel_negotiation: bool = False,
    neighbor_only: bool = False,
    exchanges: int = 2,
) -> dict:
    game_id = str(uuid.uuid4())[:8]
    log_path = get_log_path(game_id)

    if verbose:
        print(f"\n{'='*60}")
        print(f"GAME {game_id} | Run {run_index} | Condition: {condition}")
        print(f"Players ({len(active_powers)}): {active_powers}")
        print(f"Frameworks: {framework_assignment}")
        print(f"{'='*60}")

    # Build per-agent memories
    memories = {power: GameMemory(power) for power in active_powers}

    # Build agents
    agents = {}
    for power in active_powers:
        framework = framework_assignment[power]
        system_prompt = build_system_prompt(power, framework, condition, framework_assignment)
        if verbose:
            print(f"\n[{power}] SYSTEM PROMPT:\n{system_prompt}\n{'-'*40}")
        agents[power] = LLMAgent(
            power=power,
            system_prompt=system_prompt,
            model=model,
            client=client,
            memory=memories[power],
            fact_world=fact_world,
            verbose=verbose,
        )

    game = Game()

    # Auto-hold all non-active powers so the game engine doesn't stall waiting for their orders
    passive_powers = [p for p in ALL_POWERS if p not in active_powers]

    years_completed = 0
    last_year = None

    while not game.is_game_done:
        phase = game.get_current_phase()
        phase_type = game.phase_type  # 'M', 'R', 'A'

        # Stop after max_years full years
        current_year = game.phase.split()[1] if game.phase else None
        if current_year and current_year != last_year:
            if last_year is not None:
                years_completed += 1
            last_year = current_year
            if years_completed >= max_years:
                break

        if verbose:
            print(f"\n{'='*40}")
            print(f"PHASE: {phase} (type={phase_type})")
            print(f"SC counts: { {p: len(game.get_centers(p)) for p in active_powers} }")

        possible_orders = game.get_all_possible_orders()

        # Passive powers hold all units automatically
        for p in passive_powers:
            if not game.powers[p].is_eliminated():
                hold_orders = [f"{u} H" for u in game.get_units(p)]
                if hold_orders:
                    game.set_orders(p, hold_orders)

        negotiations = []
        submitted_by_power = {}
        self_assessments = {}
        strategic_plans = {}
        truncated_agents = []

        if phase_type == "M":
            # Reset each agent's turn notes at the start of each movement phase
            for p in active_powers:
                if not game.powers[p].is_eliminated():
                    agents[p].reset_turn()

            # Shared board state for negotiation (no per-agent possible orders needed)
            shared_state = {
                "phase": phase,
                "all_units": game.get_units(),
                "all_centers": game.get_centers(),
            }
            alive_agents = {p: agents[p] for p in active_powers if not game.powers[p].is_eliminated()}
            negotiations = run_negotiation_phase(alive_agents, shared_state, verbose=verbose, parallel=parallel_negotiation, neighbor_only=neighbor_only, exchanges=exchanges)

            # Order phase — all agents submit in parallel
            active_this_phase = [p for p in active_powers if not game.powers[p].is_eliminated()]

            def _get_orders(power):
                state = get_board_state(game, power, possible_orders)
                commitments = _extract_commitments_with_opponents(power, negotiations)
                return power, *agents[power].get_orders(state, commitments_made=commitments)

            with ThreadPoolExecutor(max_workers=len(active_this_phase)) as executor:
                futures = {executor.submit(_get_orders, p): p for p in active_this_phase}
                for future in as_completed(futures):
                    power, orders, self_assessment, strategic_plan, was_truncated = future.result()
                    game.set_orders(power, orders)
                    submitted_by_power[power] = orders
                    self_assessments[power] = self_assessment
                    strategic_plans[power] = strategic_plan
                    if was_truncated:
                        truncated_agents.append(power)

                    if verbose:
                        print(f"[{power}] ORDERS: {orders}")
                        if self_assessment.get("violated_commitments"):
                            print(f"[{power}] ** SELF-FLAGGED: {self_assessment['violated_commitments']}")

        elif phase_type in ("R", "A"):
            ra_powers = [
                p for p in active_powers
                if not game.powers[p].is_eliminated()
                and game.get_orderable_locations(p)
            ]

            def _get_ra_orders(power):
                state = get_board_state(game, power, possible_orders)
                orders, _, __, _truncated = agents[power].get_orders(state)
                if _truncated:
                    print(f"  !! TRUNCATED [{power}] during R/A phase orders")
                return power, orders

            with ThreadPoolExecutor(max_workers=max(len(ra_powers), 1)) as executor:
                for power, orders in executor.map(_get_ra_orders, ra_powers):
                    game.set_orders(power, orders)
                    submitted_by_power[power] = orders

        # Capture submitted orders before advancing (get_orders returns empty after process())
        resolved_orders = {
            p: game.get_orders(p) for p in active_powers
            if not game.powers[p].is_eliminated()
        }

        # Advance phase
        game.process()

        sc_counts = {p: len(game.get_centers(p)) for p in active_powers}
        dislodged = [str(u) for p in active_powers for u in game.powers[p].retreats]

        if phase_type == "M":
            # External judge pass: check each agent's commitments against their orders
            all_commitment_outcomes = {}
            betrayals_flagged = []

            def _judge_power(power):
                commitments = _extract_commitments_made(power, negotiations)
                orders = submitted_by_power.get(power, [])
                outcomes = judge_commitments(phase, commitments, orders, client, judge_model)
                self_flagged = extract_self_flagged(power, self_assessments.get(power, {}), orders)
                return power, outcomes, self_flagged

            with ThreadPoolExecutor(max_workers=len(active_this_phase)) as executor:
                for power, outcomes, self_flagged in executor.map(_judge_power, active_this_phase):
                    all_commitment_outcomes[power] = outcomes
                    for o in outcomes:
                        if o.get("outcome") == "BROKEN":
                            betrayals_flagged.append({
                                "power": power,
                                "commitment_violated": o["commitment"],
                                "submitted_orders": submitted_by_power.get(power, []),
                                "reasoning": o.get("reasoning", ""),
                                "narrative_score": self_assessments.get(power, {}).get("narrative_score", 1),
                                "source": "judge",
                            })
                    betrayals_flagged.extend(self_flagged)

            # Update each agent's memory with this turn's full record
            for power in active_powers:
                memories[power].add_turn(
                    phase=phase,
                    sc_counts=sc_counts,
                    negotiations=negotiations,
                    submitted_orders=submitted_by_power.get(power, []),
                    commitment_outcomes=all_commitment_outcomes.get(power, []),
                    all_submitted_orders=submitted_by_power,
                )

            log_turn(
                path=log_path,
                game_id=game_id,
                run=run_index,
                condition=condition,
                framework_assignment=framework_assignment,
                model=model,
                phase=phase,
                negotiations=negotiations,
                submitted_orders=submitted_by_power,
                resolved_orders=resolved_orders,
                sc_counts=sc_counts,
                dislodged=dislodged,
                betrayals_flagged=betrayals_flagged,
                strategic_plans=strategic_plans,
                truncated_agents=truncated_agents,
            )

    final_sc = {p: len(game.get_centers(p)) for p in active_powers}
    summary = {
        "final_sc_counts": final_sc,
        "winner": max(final_sc, key=final_sc.get),
        "phases_played": years_completed,
    }
    log_game_summary(game_id, summary)

    if verbose:
        print(f"\nGAME OVER. Final SC: {final_sc}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Diplomacy LLM moral frameworks experiment")
    parser.add_argument("--condition", choices=["blind", "transparent"], default="blind")
    parser.add_argument("--players", type=int, choices=[3, 7], default=3,
                        help="Number of active players: 3=ENG/FRA/GER, 7=all powers")
    parser.add_argument("--frameworks", nargs="*", default=None,
                        help="Framework per active power (in player order): baseline utilitarian deontological hhh")
    parser.add_argument("--turns", type=int, default=5, help="Number of game years to play")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--model", default="openai/gpt-4o")
    parser.add_argument("--judge-model", default=None, dest="judge_model",
                        help="Model for commitment judge (defaults to --model if not set)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--fast-parallel", action="store_true", dest="fast_parallel",
                        help="Run negotiation pairs in parallel (faster but agents can't adapt across conversations)")
    parser.add_argument("--neighbor-only", action="store_true", dest="neighbor_only",
                        help="Only negotiate between diplomatically adjacent powers (~12 pairs vs 21 for 7-player)")
    parser.add_argument("--exchanges", type=int, default=2,
                        help="Number of back-and-forth rounds per negotiation pair (default 2)")
    parser.add_argument("--facts", action="store_true", help="Enable FactWorld (not yet implemented)")
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

    judge_model = args.judge_model or args.model

    for run_index in range(1, args.runs + 1):
        print(f"\nStarting run {run_index}/{args.runs} ({args.players}-player)...")
        summary = run_game(
            run_index=run_index,
            condition=args.condition,
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
        print(f"Run {run_index} complete. Winner: {summary['winner']} | SC: {summary['final_sc_counts']}")


if __name__ == "__main__":
    main()
