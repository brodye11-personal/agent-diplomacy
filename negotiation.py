from itertools import combinations
from concurrent.futures import ThreadPoolExecutor, as_completed


MAX_EXCHANGES = 2  # messages per side per pair per phase

POWER_NEIGHBORS = {
    "ENGLAND": {"FRANCE", "GERMANY", "RUSSIA"},
    "FRANCE": {"ENGLAND", "GERMANY", "ITALY"},
    "GERMANY": {"ENGLAND", "FRANCE", "AUSTRIA", "RUSSIA"},
    "AUSTRIA": {"GERMANY", "RUSSIA", "ITALY", "TURKEY"},
    "ITALY": {"FRANCE", "AUSTRIA", "TURKEY"},
    "RUSSIA": {"ENGLAND", "GERMANY", "AUSTRIA", "TURKEY"},
    "TURKEY": {"AUSTRIA", "ITALY", "RUSSIA"},
}


def _public_content(msg: dict) -> dict:
    """Strip scratchpad before showing a message to the opposing agent."""
    if isinstance(msg, dict):
        return {k: v for k, v in msg.items() if k != "scratchpad"}
    return msg


def _run_pair(power_a: str, power_b: str, agents: dict, state: dict, verbose: bool, exchanges: int = MAX_EXCHANGES) -> dict:
    """Run one negotiation conversation between two powers sequentially."""
    if verbose:
        print(f"\n--- Negotiation: {power_a} <-> {power_b} ---")

    history = []       # shown to agents — scratchpad stripped
    messages_log = []  # full record for logs — scratchpad included

    for _ in range(exchanges):
        msg_a = agents[power_a].negotiate(state, power_b, history)
        messages_log.append({"role": power_a, "content": msg_a})
        history.append({"role": power_a, "content": _public_content(msg_a)})

        msg_b = agents[power_b].negotiate(state, power_a, history)
        messages_log.append({"role": power_b, "content": msg_b})
        history.append({"role": power_b, "content": _public_content(msg_b)})

    return {"pair": [power_a, power_b], "messages": messages_log}


def run_negotiation_phase(
    agents: dict,
    state: dict,
    verbose: bool = False,
    parallel: bool = False,
    neighbor_only: bool = False,
    exchanges: int = MAX_EXCHANGES,
) -> list[dict]:
    """
    Run all pair conversations for one movement phase.

    neighbor_only=True: only run negotiations between diplomatically adjacent powers
    (~12 pairs for 7-player instead of 21).

    exchanges: number of back-and-forth rounds per pair (default 2).

    parallel=False (default): pairs run sequentially so later conversations can
    implicitly reflect what an agent learned from earlier ones.
    parallel=True: all pairs run concurrently (faster but no cross-conversation flow).
    """
    all_pairs = list(combinations(sorted(agents.keys()), 2))

    if neighbor_only:
        pairs = [
            (a, b) for a, b in all_pairs
            if b in POWER_NEIGHBORS.get(a, set()) or a in POWER_NEIGHBORS.get(b, set())
        ]
    else:
        pairs = all_pairs

    if parallel:
        results = {}
        with ThreadPoolExecutor(max_workers=len(pairs)) as executor:
            futures = {
                executor.submit(_run_pair, a, b, agents, state, verbose, exchanges): (a, b)
                for a, b in pairs
            }
            for future in as_completed(futures):
                pair_key = futures[future]
                results[pair_key] = future.result()
        return [results[pair] for pair in pairs if pair in results]

    return [_run_pair(a, b, agents, state, verbose, exchanges) for a, b in pairs]
