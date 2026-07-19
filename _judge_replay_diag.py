"""
Diagnostic replay (throwaway): recover the per-ruling arbiter reasoning the
D22 run failed to log, and test whether the DEFENDER'S REBUTTAL is doing any
of the work.

Parses the 20 real compel_action proposals out of p7_sonnet_bump_log.txt, then
re-runs each through the REAL judge_compulsion with the EXACT defender
constitution + cited facts + board context the live run used -- but with
NO rebuttal. If proposals still come back NOT with the defense removed, the
"defender successfully defends" framing is wrong: the proposals are
structurally non-binding on their own (rules 1+5), not out-argued.

--extract-only prints the parsed proposals and spends nothing.
"""
import ast
import re
import sys
import threading

from diplomacy import Game

from main import make_client, ACTIVE_POWERS_6, POWER_PAIRS, TRIAD, build_assignment, DEFAULT_JUDGE_MODEL
from facts import FactWorld
from frameworks import FRAMEWORKS
from judge import judge_compulsion
from orchestrator import _neutralize_turkey
from state import count_scs

LOG = "p7_sonnet_bump_log.txt"

# [PROPOSER] TOOL compel_action({...dict...}) → {...}  (log uses a unicode arrow)
LINE_RE = re.compile(r"\[([A-Z]+)\] TOOL compel_action\((\{.*\})\)\s*(?:->|→)", re.M)


def parse_proposals(text):
    out = []
    for m in LINE_RE.finditer(text):
        proposer = m.group(1)
        try:
            d = ast.literal_eval(m.group(2))
        except Exception as exc:
            print(f"!! parse fail for {proposer}: {exc}")
            continue
        out.append({
            "proposer": proposer,
            "target": d.get("target", ""),
            "action": d.get("action", ""),
            "argument": d.get("argument", ""),
        })
    return out


def main():
    extract_only = "--extract-only" in sys.argv

    text = open(LOG, encoding="utf-8").read()
    proposals = parse_proposals(text)

    framework_assignment = build_assignment(ACTIVE_POWERS_6, TRIAD, POWER_PAIRS)

    # Board context: SC counts during S1901M/F1901M negotiation are the
    # start-of-game counts (SCs only change at fall adjudication -> W builds),
    # so both this run's negotiation batches saw the same tally. Rebuild it the
    # way the orchestrator labels blocs.
    game = Game()
    _neutralize_turkey(game)
    blocs_by_fw = {}
    for p in ACTIVE_POWERS_6:
        blocs_by_fw.setdefault(framework_assignment[p], []).append(p)
    board_context = "; ".join(
        f"[{'+'.join(ps)}]={sum(count_scs(p, game) for p in ps)}"
        for ps in blocs_by_fw.values()
    )

    print(f"Parsed {len(proposals)} proposals from {LOG}")
    print(f"framework_assignment: {framework_assignment}")
    print(f"board_context: {board_context}")
    print("=" * 70)
    for i, p in enumerate(proposals, 1):
        fw = framework_assignment.get(p["target"], "?")
        print(f"{i:2d}. {p['proposer']:7s} -> {p['target']:7s} ({fw:13s}) "
              f"order={p['action']!r}")
    if extract_only:
        return

    fact_world = FactWorld(enabled=True, seed=1)
    fact_world.generate(ACTIVE_POWERS_6)
    client = make_client()
    model = DEFAULT_JUDGE_MODEL

    print("\n" + "=" * 70)
    print(f"REPLAYING through judge_compulsion ({model}), NO rebuttal supplied")
    print("=" * 70)

    results = []
    for i, p in enumerate(proposals, 1):
        defender_fw = framework_assignment.get(p["target"], "")
        fw_text = FRAMEWORKS.get(defender_fw, "")
        facts_text = fact_world.facts_for_text(p["argument"])
        # No rebuttal: judge_compulsion fills "(no rebuttal given)".
        verdict = judge_compulsion(
            {"action": p["action"], "argument": p["argument"]},
            fw_text, facts_text, board_context, client, model,
        )
        results.append((p, defender_fw, verdict))
        print(f"\n{i:2d}. {p['proposer']} -> {p['target']} ({defender_fw}) | {p['action']}")
        print(f"    RULING: {verdict['ruling']}")
        print(f"    clause: {verdict.get('clause','')}")
        print(f"    reasoning: {verdict.get('reasoning','')}")

    n_comp = sum(1 for _, _, v in results if v["ruling"] == "COMPELLED")
    print("\n" + "=" * 70)
    print(f"SUMMARY (no rebuttal): {n_comp}/{len(results)} COMPELLED")
    by_fw = {}
    for _, dfw, v in results:
        by_fw.setdefault(dfw, [0, 0])
        by_fw[dfw][0] += 1
        if v["ruling"] == "COMPELLED":
            by_fw[dfw][1] += 1
    for dfw, (tot, comp) in by_fw.items():
        print(f"  {dfw:13s}: {comp}/{tot} COMPELLED")


if __name__ == "__main__":
    main()
