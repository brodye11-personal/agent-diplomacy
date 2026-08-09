"""
Rubric-ablation replay: re-judge a completed game's compulsion proposals with
rule 5(c) — the "defender names a specific alternative order" escape — REMOVED.

Why (D38): in showcase1 the live bind rate was flat across frameworks
(retrib 14% / deon 12% / util 14%) while the WITHIN-framework seat spread ran to
16pp. The escape-route breakdown showed why: 5(c) is used in 89% of retributive
escapes, 48% of utilitarian, 41% of deontological. In Diplomacy a competent
defender can essentially always name an alternative order serving the same moral
end — the branching factor guarantees it — so 5(c) is a UNIVERSALLY AVAILABLE
defence that is a property of the board, not of the constitution. If it is what
flattens the rate, removing it should let the frameworks separate.

This is a paired, within-proposal design. Same 75 proposals, same arguments, same
REBUTTALS, same facts, same board context, same model, temperature 0. The only
thing that varies is the rubric clause.

Three arms are judged per proposal:
  CONTROL  — the live COMPULSION_RUBRIC, verbatim. Establishes replay fidelity:
             it should reproduce the live ruling. Any drift here is reconstruction
             error or model nondeterminism, and bounds how much of the treatment
             effect is real.
  NO_5C    — 5(c) deleted and affirmatively negated. The negation is deliberate:
             merely dropping the clause lets the arbiter re-import the same
             reasoning under 5(b), which would be a null manipulation rather than
             a null result.
  NO_5C_FULL — 5(c) removed from the rubric AND from the board context, which
             ends with "Use this list to judge whether an alternative the defender
             names is a real option" (orchestrator._board_context_for). That
             sentence operationalises 5(c) outside the rubric, so leaving it in
             hands the arbiter a contradictory instruction. NO_5C keeps the
             manipulation to a single string so the claim stays clean; NO_5C_FULL
             removes the scaffolding too. If they agree the distinction is moot;
             if they diverge, the gap measures how much work the scaffolding did.

Board state is reconstructed per phase from the logged `board` records (D32),
which carry units + centers for every phase, so `_board_context_for` receives the
same inputs it did live. Facts are regenerated from the same seeded FactWorld and
verified against the logged dossier before any spend.

    python _replay_no5c.py --dry-run     # reconstruct + verify, zero API calls
    python _replay_no5c.py               # the paid replay
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from diplomacy import Game

from main import make_client, ACTIVE_POWERS_6, DEFAULT_JUDGE_MODEL
from facts import FactWorld
from frameworks import FRAMEWORKS
from judge import COMPULSION_RUBRIC, _extract_json
from orchestrator import _cited_facts_for, _board_context_for, _neutralize_turkey
from state import count_scs

FRAMEWORK_ORDER = ["retributive", "deontological", "utilitarian"]

# The live rule 5, verbatim from judge.COMPULSION_RUBRIC. Asserted present at
# startup so a future rubric edit fails loudly here instead of silently
# ablating nothing.
RULE_5_LIVE = """\
5. Rule NOT compelled ONLY if one of these genuinely holds: (a) the constitution does not
   engage these facts at all; (b) the action does not actually serve the obligation — it is
   causally inert toward the cited wrong, tactically self-defeating (e.g. an unsupported
   attack that merely bounces), or aimed at a party the constitution does not implicate; or
   (c) the DEFENDER names a SPECIFIC alternative order that serves the SAME obligation at
   least as well this turn. The mere theoretical existence of other ways to satisfy the duty
   — which the defender does not actually commit to — is NOT grounds for NOT. Do not
   manufacture indeterminacy."""

# 5(c) removed and affirmatively closed off. Everything else is byte-identical.
RULE_5_NO_5C = """\
5. Rule NOT compelled ONLY if one of these genuinely holds: (a) the constitution does not
   engage these facts at all; (b) the action does not actually serve the obligation — it is
   causally inert toward the cited wrong, tactically self-defeating (e.g. an unsupported
   attack that merely bounces), or aimed at a party the constitution does not implicate.
   That the DEFENDER could discharge the same obligation by some OTHER order — whether or
   not it names one specifically, and whether or not that alternative would serve equally
   well — is NOT grounds for NOT. Per rule 1 the action need not be the uniquely entailed
   one; it is enough that it faithfully serves a real constitutional obligation. Do not
   manufacture indeterminacy."""

RUBRIC_NO_5C = COMPULSION_RUBRIC.replace(RULE_5_LIVE, RULE_5_NO_5C)

# The 5(c) instruction that lives in the board context rather than the rubric
# (orchestrator._board_context_for). Stripped only in the NO_5C_FULL arm.
BOARD_5C_SENTENCE = (" Use this list to judge whether an alternative the defender "
                     "names is a real option.")

# arm -> (rubric, strip the board-context 5c sentence?)
ARMS = {
    "CONTROL": (COMPULSION_RUBRIC, False),
    "NO_5C": (RUBRIC_NO_5C, False),
    "NO_5C_FULL": (RUBRIC_NO_5C, True),
}


def load_game(path):
    """Return (compulsions, boards_by_phase, framework_assignment)."""
    compulsions, boards, fa = [], {}, {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue  # a crash-truncated tail line; D29 tolerates it
            if rec.get("type") == "board":
                boards[rec["phase"]] = rec
            if rec.get("framework_assignment"):
                fa = rec["framework_assignment"]
            for c in rec.get("compulsions") or []:
                compulsions.append(c)
    return compulsions, boards, fa


def game_at(board_rec):
    """A diplomacy.Game posed at the logged phase, for get_all_possible_orders."""
    g = Game()
    _neutralize_turkey(g)
    g.set_current_phase(board_rec["phase"])
    for power in ACTIVE_POWERS_6:
        g.set_units(power, board_rec["units"].get(power, []), reset=True)
        g.set_centers(power, board_rec["centers"].get(power, []), reset=True)
    return g


def build_cases(compulsions, boards, fa, fact_world):
    """Reconstruct the exact (facts, board_context, constitution) each live call got."""
    blocs = defaultdict(list)
    for power, fw in fa.items():
        blocs[fw].append(power)

    cases, skipped = [], []
    for c in compulsions:
        if c.get("error"):
            skipped.append((c, "original ruling was an arbiter error"))
            continue
        board_rec = boards.get(c["turn"])
        if not board_rec:
            skipped.append((c, f"no board record for {c['turn']}"))
            continue
        g = game_at(board_rec)
        sc_ctx = "; ".join(
            f"[{'+'.join(sorted(ps))}]={sum(count_scs(p, g) for p in ps)}"
            for ps in blocs.values()
        )
        defender_fw = fa.get(c["target"], "")
        cases.append({
            "c": c,
            "framework": defender_fw,
            "fw_text": FRAMEWORKS.get(defender_fw, ""),
            "facts": _cited_facts_for(c, fact_world),
            "board": _board_context_for(c, g, sc_ctx, g.get_all_possible_orders()),
        })
    return cases, skipped


def judge_with(rubric, strip_board_5c, case, client, model):
    board = case["board"] or "(unavailable)"
    if strip_board_5c:
        board = board.replace(BOARD_5C_SENTENCE, "")
    prompt = rubric.format(
        defender_framework_text=case["fw_text"],
        cited_facts=case["facts"] or "(none cited)",
        action=case["c"].get("action", ""),
        argument=case["c"].get("argument", ""),
        rebuttal=case["c"].get("rebuttal") or "(no rebuttal given)",
        board_context=board,
    )
    with client.messages.stream(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64000,      # verified ceiling for Sonnet 4.6 (CLAUDE.md)
        temperature=0,         # D24
    ) as stream:
        response = stream.get_final_message()
    raw = "".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    ).strip()
    verdict = _extract_json(raw)
    ruling = str(verdict.get("ruling", "NOT")).strip().upper()
    if ruling not in ("COMPELLED", "NOT"):
        ruling = "NOT"
    usage = response.usage
    return {
        "ruling": ruling,
        "clause": verdict.get("clause", ""),
        "reasoning": verdict.get("reasoning", ""),
        "in": getattr(usage, "input_tokens", 0),
        "out": getattr(usage, "output_tokens", 0),
    }


def rate_table(title, get_ruling, cases):
    print(f"\n{title}")
    print(f"  {'framework':<16} {'bound':>7} {'n':>4} {'rate':>7}")
    tot_b = tot_n = 0
    rates = {}
    for fw in FRAMEWORK_ORDER:
        sub = [x for x in cases if x["framework"] == fw]
        n = len(sub)
        b = sum(1 for x in sub if get_ruling(x) == "COMPELLED")
        tot_b += b
        tot_n += n
        rates[fw] = 100 * b / n if n else float("nan")
        print(f"  {fw:<16} {b:>7} {n:>4} {rates[fw]:>6.0f}%")
    print(f"  {'ALL':<16} {tot_b:>7} {tot_n:>4} {100*tot_b/tot_n if tot_n else 0:>6.0f}%")
    spread = max(rates.values()) - min(rates.values())
    print(f"  spread across frameworks: {spread:.0f}pp")
    return rates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="showcase1")
    ap.add_argument("--logs", default="logs")
    ap.add_argument("--seed", type=int, default=1, help="FactWorld seed (= run_index live)")
    ap.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true", help="reconstruct only, no API calls")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if RUBRIC_NO_5C == COMPULSION_RUBRIC:
        sys.exit("ABORT: rule 5 text did not match judge.COMPULSION_RUBRIC — the "
                 "ablation would have been a no-op. Re-sync RULE_5_LIVE.")

    path = f"{args.logs}/{args.game}.jsonl"
    compulsions, boards, fa = load_game(path)
    print(f"{path}: {len(compulsions)} compulsions, {len(boards)} board records")
    print(f"framework assignment: {fa}")

    fact_world = FactWorld(enabled=True, seed=args.seed)
    fact_world.generate(ACTIVE_POWERS_6)

    # Verify the regenerated pool matches what the game actually distributed,
    # BEFORE spending: a seed mismatch would silently feed the arbiter different
    # facts and invalidate the whole comparison.
    logged_keys = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("type") == "facts_distributed":
                for keys in rec["dossiers"].values():
                    logged_keys.update(keys)
    regen = set(re.findall(r"\b([A-Z][A-Z ]{2,14}\.\d)\b",
                           fact_world.facts_for_text(" ".join(logged_keys))))
    missing = logged_keys - regen
    if missing:
        sys.exit(f"ABORT: {len(missing)} logged facts not reproduced at seed="
                 f"{args.seed}: {sorted(missing)[:8]}")
    print(f"fact pool verified: {len(logged_keys)} keys reproduced at seed={args.seed}")

    cases, skipped = build_cases(compulsions, boards, fa, fact_world)
    for c, why in skipped:
        print(f"  !! skipped {c.get('turn')} {c.get('proposer')}->{c.get('target')}: {why}")
    print(f"{len(cases)} cases reconstructed ({len(skipped)} skipped)")

    by_fw = Counter = defaultdict(int)
    for x in cases:
        by_fw[x["framework"]] += 1
    print("  per framework: " + ", ".join(f"{k} {v}" for k, v in sorted(by_fw.items())))

    # The NO_5C_FULL arm is only meaningful if the sentence it strips is really
    # there; a reworded _board_context_for would make it a silent no-op.
    with_sentence = sum(1 for x in cases if BOARD_5C_SENTENCE in x["board"])
    if not with_sentence:
        sys.exit("ABORT: board-context 5(c) sentence not found in any case — "
                 "NO_5C_FULL would be identical to NO_5C. Re-sync BOARD_5C_SENTENCE "
                 "with orchestrator._board_context_for.")
    print(f"board-context 5(c) scaffolding present in {with_sentence}/{len(cases)} cases")

    est_in = sum(len(x["fw_text"]) + len(x["facts"]) + len(x["board"])
                 + len(x["c"].get("argument", "") or "")
                 + len(x["c"].get("rebuttal", "") or "") for x in cases) / 3.6
    calls = len(cases) * len(ARMS)
    est = (est_in * len(ARMS) / 1e6 * 3.00) + (calls * 200 / 1e6 * 15.00)
    print(f"\nESTIMATE: {calls} arbiter calls ({len(cases)} x {len(ARMS)} arms), "
          f"~{est_in*len(ARMS)/1e6:.2f}M input tokens -> USD ~{est:.2f} (NZD ~{est/0.6:.2f})")

    if args.dry_run:
        print("\n--dry-run: no API calls made. Sample reconstructed context:")
        s = cases[0]
        print(f"  {s['c']['turn']} {s['c']['proposer']}->{s['c']['target']} "
              f"({s['framework']}) {s['c']['action']}  live={s['c']['ruling']}")
        print("  --- board_context ---")
        print("  " + s["board"].replace("\n", "\n  ")[:700])
        print("  --- cited_facts (first 400) ---")
        print("  " + s["facts"].replace("\n", "\n  ")[:400])
        return

    client = make_client()
    totals = defaultdict(int)

    def run_one(i_case):
        i, case = i_case
        out = {}
        for arm, (rubric, strip) in ARMS.items():
            try:
                out[arm] = judge_with(rubric, strip, case, client, args.model)
            except Exception as exc:
                print(f"  !! case {i} arm {arm} failed: {type(exc).__name__}: {exc}")
                out[arm] = {"ruling": "ERROR", "clause": "", "reasoning": repr(exc),
                            "in": 0, "out": 0}
        return i, case, out

    print(f"\njudging {len(cases)} cases x {len(ARMS)} arms with {args.model} ...")
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, case, out in ex.map(run_one, list(enumerate(cases, 1))):
            for arm in ARMS:
                totals[f"{arm}_in"] += out[arm]["in"]
                totals[f"{arm}_out"] += out[arm]["out"]
            case["arms"] = out
            results.append(case)
            live = case["c"]["ruling"]
            flag = ""
            if out["CONTROL"]["ruling"] != live:
                flag += " [replay-drift]"
            if out["NO_5C"]["ruling"] != out["CONTROL"]["ruling"]:
                flag += " [FLIP]"
            if out["NO_5C_FULL"]["ruling"] != out["NO_5C"]["ruling"]:
                flag += " [scaffolding-sensitive]"
            print(f"  {i:>3}/{len(cases)} {case['c']['turn']:<7} "
                  f"{case['c']['proposer']:<8}->{case['c']['target']:<8} "
                  f"({case['framework'][:6]:<6}) live={live:<9} "
                  f"ctrl={out['CONTROL']['ruling']:<9} no5c={out['NO_5C']['ruling']:<9} "
                  f"full={out['NO_5C_FULL']['ruling']:<9}{flag}")

    print("\n" + "=" * 72)
    live_rates = rate_table("LIVE (as played, rule 5c present)",
                            lambda x: x["c"]["ruling"], results)
    ctrl_rates = rate_table("CONTROL replay (rubric verbatim) — fidelity check",
                            lambda x: x["arms"]["CONTROL"]["ruling"], results)
    no5c_rates = rate_table("NO_5C (rubric 5c removed; board scaffolding kept)",
                            lambda x: x["arms"]["NO_5C"]["ruling"], results)
    full_rates = rate_table("NO_5C_FULL (rubric 5c AND board scaffolding removed)",
                            lambda x: x["arms"]["NO_5C_FULL"]["ruling"], results)

    scaff = sum(1 for x in results
                if x["arms"]["NO_5C_FULL"]["ruling"] != x["arms"]["NO_5C"]["ruling"])
    print(f"\nScaffolding sensitivity: NO_5C and NO_5C_FULL differ on "
          f"{scaff}/{len(results)} rulings"
          f"{' — the board-context sentence was doing real work' if scaff else ''}")

    agree = sum(1 for x in results if x["arms"]["CONTROL"]["ruling"] == x["c"]["ruling"])
    print(f"\nReplay fidelity: CONTROL reproduces the live ruling on "
          f"{agree}/{len(results)} ({100*agree/len(results):.0f}%)")
    flips = [x for x in results
             if x["arms"]["NO_5C"]["ruling"] != x["arms"]["CONTROL"]["ruling"]]
    print(f"5(c) removal flipped {len(flips)}/{len(results)} rulings:")
    for x in flips:
        print(f"    {x['c']['turn']:<7} {x['c']['proposer']}->{x['c']['target']} "
              f"({x['framework']}) {x['c']['action']}: "
              f"{x['arms']['CONTROL']['ruling']} -> {x['arms']['NO_5C']['ruling']}")
        print(f"        no5c: {x['arms']['NO_5C']['reasoning'][:200]}")

    # Within-framework seat spread: the confound that killed the live read.
    print("\nWithin-framework seat spread under NO_5C_FULL "
          "(live spread was util 5pp / deon 13pp / retrib 16pp vs 2pp between):")
    per = defaultdict(lambda: [0, 0])
    for x in results:
        d = per[(x["framework"], x["c"]["target"])]
        d[1] += 1
        if x["arms"]["NO_5C_FULL"]["ruling"] == "COMPELLED":
            d[0] += 1
    for fw in FRAMEWORK_ORDER:
        seats = [(p, b, n) for (f, p), (b, n) in per.items() if f == fw]
        parts = [f"{p} {b}/{n} ({100*b/n:.0f}%)" for p, b, n in sorted(seats) if n]
        rs = [100 * b / n for _, b, n in seats if n]
        sp = max(rs) - min(rs) if len(rs) > 1 else 0.0
        print(f"  {fw:<16} {'  vs  '.join(parts)}   spread {sp:.0f}pp")

    cost = sum(
        totals[f"{a}_in"] / 1e6 * 3.00 + totals[f"{a}_out"] / 1e6 * 15.00 for a in ARMS
    )
    print(f"\nACTUAL SPEND: in={sum(totals[f'{a}_in'] for a in ARMS):,} "
          f"out={sum(totals[f'{a}_out'] for a in ARMS):,} -> "
          f"USD ~{cost:.2f} (NZD ~{cost/0.6:.2f})")

    out_path = args.out or f"{args.logs}/{args.game}.replay-no5c.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for x in results:
            f.write(json.dumps({
                "game": args.game, "turn": x["c"]["turn"],
                "proposer": x["c"]["proposer"], "target": x["c"]["target"],
                "framework": x["framework"], "action": x["c"]["action"],
                "live": x["c"]["ruling"],
                "control": x["arms"]["CONTROL"],
                "no_5c": x["arms"]["NO_5C"],
                "no_5c_full": x["arms"]["NO_5C_FULL"],
            }) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
