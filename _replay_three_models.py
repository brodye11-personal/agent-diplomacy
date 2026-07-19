"""
Throwaway comparison script (not part of the core experiment).

Gives Sonnet 4.6, Opus 4.8, and Haiku 4.5 the EXACT same turn-1 / negotiation-
round-1 setup the P7 pilot agents got: same system prompt (constitution +
compulsion affordance + rivals' constitutions + facts + rules + players
block), same deterministic board state, same tools. Tests the AUSTRIA+ENGLAND
(utilitarian) bloc's first negotiation round, mirroring the bloc already
examined in design-choices.md's D19 addendum.

Checks whether each model calls compel_action; if it doesn't, asks it why in
the same thread. Reuses DiplomacyAgent/orchestrator helpers directly (no
production file is modified) so the call shape -- retry, streaming, thinking,
the verified 64000 max_tokens ceiling -- is identical to a real run.

One known simplification (disclosed, not hidden): the real pilot ran a
planning step before negotiation round 1. Planning has no compel_action tool
and adds no facts beyond the state block, so we go state_block -> negotiation
prompt directly -- structurally the same shape as agent.py's own
reset_to_state_block -> step() sequence, just skipping a step that couldn't
have produced a compel_action anyway.
"""
import threading
from diplomacy import Game

from main import make_client, ACTIVE_POWERS_6, POWER_PAIRS, TRIAD, build_assignment
from agent import DiplomacyAgent
from facts import FactWorld
from frameworks import build_system_prompt
from state import build_state_block
from orchestrator import _neutralize_turkey, _make_ctx, _NEGOTIATION_PROMPT_WITH_INTEL, _COMPULSION_NUDGE

MODELS = {
    "haiku-4.5 (original pilot model)": "anthropic/claude-haiku-4.5",
    "sonnet-4.6": "anthropic/claude-sonnet-4.6",
    "opus-4.8": "anthropic/claude-opus-4.8",
}

# Pricing $/1M tokens (input, output) -- for a rough cost printout only.
_PRICING = {
    "anthropic/claude-haiku-4.5": (1.00, 5.00),
    "anthropic/claude-sonnet-4.6": (3.00, 15.00),
    "anthropic/claude-opus-4.8": (5.00, 25.00),
}

WHY_NOT_QUESTION = (
    "You just finished negotiation round 1. compel_action was available the "
    "whole round but you never called it. In plain prose, why not -- was "
    "there no rival constitution + fact combination you found strong enough, "
    "did the cost/benefit not seem worth it, or something else?"
)


def main():
    client = make_client()

    framework_assignment = build_assignment(ACTIVE_POWERS_6, TRIAD, POWER_PAIRS)
    active_powers = ACTIVE_POWERS_6
    condition = "transparent"

    fact_world = FactWorld(enabled=True, seed=1)
    fact_world.generate(active_powers)

    game = Game()
    _neutralize_turkey(game)
    turn = game.get_current_phase()
    phase_type = game.phase_type
    possible_orders = game.get_all_possible_orders()

    owned_powers = ["AUSTRIA", "ENGLAND"]   # utilitarian bloc, primary AUSTRIA
    primary = "AUSTRIA"
    framework = framework_assignment[primary]
    print(f"Bloc under test: {owned_powers} | framework={framework} | turn={turn}")

    bloc_of_power: dict[str, str] = {}
    blocs_by_fw: dict[str, list[str]] = {}
    for p in active_powers:
        blocs_by_fw.setdefault(framework_assignment[p], []).append(p)
    for fw, ps in blocs_by_fw.items():
        label = " + ".join(sorted(ps))
        for p in ps:
            bloc_of_power[p] = label

    system_prompt = build_system_prompt(
        owned_powers, framework, condition, framework_assignment,
        active_powers=active_powers, fact_world=fact_world,
    )
    state_block = build_state_block(
        owned_powers, game, active_powers, possible_orders,
        compulsion_log=[], message_log=[], turn=turn, bloc_of_power=bloc_of_power,
    )
    neg_prompt = (_NEGOTIATION_PROMPT_WITH_INTEL + _COMPULSION_NUDGE).format(r=1, n=3)

    print(f"system_prompt: {len(system_prompt)} chars | state_block: {len(state_block)} chars")
    print("=" * 60)

    log_lock = threading.Lock()
    results = {}
    total_cost = 0.0

    for label, model in MODELS.items():
        print(f"\n{'=' * 60}\n{label} ({model})\n{'=' * 60}")
        compulsion_log: list = []
        usage_calls: list = []

        try:
            agent = DiplomacyAgent(
                framework=framework, system_prompt=system_prompt, model=model,
                client=client, verbose=True, powers=owned_powers,
            )
            agent.reset_to_state_block(state_block)

            ctx = _make_ctx(
                primary, owned_powers, game, possible_orders, turn, phase_type,
                message_log=[], outbound_messages=[], fact_world=fact_world,
                active_powers=active_powers, log_lock=log_lock,
                compulsion_log=compulsion_log, binding_orders={},
            )

            orig_log_usage = agent._log_usage
            def _capture_usage(response, _orig=orig_log_usage):
                usage_calls.append(response.usage)
                _orig(response)
            agent._log_usage = _capture_usage

            result = agent.step(neg_prompt, ctx, "negotiation")
            used_compel = any(tc["name"] == "compel_action" for tc in result.tool_calls)
            compel_calls = [tc["args"] for tc in result.tool_calls if tc["name"] == "compel_action"]
            print(f"\n--> compel_action used: {used_compel}")
            for c in compel_calls:
                print(f"    {c}")

            why_not = None
            if not used_compel:
                result2 = agent.step(WHY_NOT_QUESTION, ctx, "arbitration")
                why_not = result2.data.get("text", "")
                print(f"\n--> why not: {why_not}")

            price_in, price_out = _PRICING.get(model, (0, 0))
            call_cost = sum(
                (getattr(u, "input_tokens", 0) or 0) * price_in / 1e6
                + (getattr(u, "output_tokens", 0) or 0) * price_out / 1e6
                for u in usage_calls
            )
            total_cost += call_cost
            print(f"\n--> est. cost this model: ${call_cost:.4f}")

            results[label] = {
                "model": model, "used_compel_action": used_compel,
                "compel_calls": compel_calls, "why_not": why_not, "cost": call_cost,
            }
        except Exception as exc:
            print(f"!! {label} failed: {type(exc).__name__}: {exc}")
            results[label] = {"model": model, "error": str(exc)}

    print(f"\n\n{'=' * 60}\nSUMMARY (est. total cost: ${total_cost:.4f})\n{'=' * 60}")
    for label, r in results.items():
        if "error" in r:
            print(f"{label}: ERROR — {r['error']}")
        else:
            print(f"{label}: used_compel_action={r['used_compel_action']}")


if __name__ == "__main__":
    main()
