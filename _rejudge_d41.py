"""Re-judge a completed game's proposals under the CURRENT constitutions + rubric.

Fail-cheap check after a wording change: the arguments, rebuttals, facts and board
are the ones actually played, so if the same defences now fail, the change bit.
Caveat: rebuttals were authored against the OLD wording, so this is a strong
signal, not a clean measurement -- a live run is still needed to confirm.
"""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from diplomacy import Game
from main import make_client, ACTIVE_POWERS_6, DEFAULT_JUDGE_MODEL
from facts import FactWorld
from facts_matched import as_pool
from frameworks import FRAMEWORKS
from judge import judge_compulsion
from orchestrator import _cited_facts_for, _board_context_for, _neutralize_turkey
from state import count_scs

game_id = sys.argv[1] if len(sys.argv) > 1 else "d41a"
comps, boards, fa = [], {}, {}
for ln in open(f"logs/{game_id}.jsonl", encoding="utf-8"):
    try: r = json.loads(ln)
    except ValueError: continue
    if r.get("type") == "board": boards[r["phase"]] = r
    if r.get("framework_assignment"): fa = r["framework_assignment"]
    comps += r.get("compulsions") or []

fw_world = FactWorld(enabled=True, seed=1, pool=as_pool())
fw_world.generate(ACTIVE_POWERS_6)
blocs = {}
for p, f in fa.items(): blocs.setdefault(f, []).append(p)
client = make_client()

def one(c):
    b = boards[c["turn"]]
    g = Game(); _neutralize_turkey(g); g.set_current_phase(b["phase"])
    for p in ACTIVE_POWERS_6:
        g.set_units(p, b["units"].get(p, []), reset=True)
        g.set_centers(p, b["centers"].get(p, []), reset=True)
    sc = "; ".join(f"[{'+'.join(sorted(ps))}]={sum(count_scs(x, g) for x in ps)}"
                   for ps in blocs.values())
    v = judge_compulsion(c, FRAMEWORKS[fa[c["target"]]], _cited_facts_for(c, fw_world),
                         _board_context_for(c, g, sc, g.get_all_possible_orders()),
                         client, DEFAULT_JUDGE_MODEL)
    return c, v

with ThreadPoolExecutor(max_workers=4) as ex:
    res = list(ex.map(one, comps))

# judge_compulsion FAILS SAFE TO NOT on any exception, so a transport failure
# (notably OpenRouter 402 "requires more credits") silently returns a full set of
# NOT rulings that look exactly like real ones. Refuse to report in that case.
errs = [v for _, v in res if v.get("error")]
if errs:
    sys.exit(f"ABORT: {len(errs)}/{len(res)} arbiter calls FAILED and fell back to NOT "
             f"-- these are not rulings. First error: {errs[0]['reasoning'][:200]}")
n = sum(1 for _, v in res if v["ruling"] == "COMPELLED")
for c, v in res:
    flip = "  <-- FLIPPED" if v["ruling"] != c["ruling"] else ""
    print(f"{c['turn']} {c['proposer']:>7}->{c['target']:<8} ({fa[c['target']][:6]:<6}) "
          f"{c['action']:<16} was={c['ruling']:<9} now={v['ruling']:<9}{flip}")
    print(f"     {v['reasoning'][:300]}")
print(f"\nunder new wording: {n}/{len(res)} COMPELLED (was "
      f"{sum(1 for c,_ in res if c['ruling']=='COMPELLED')}/{len(res)})")
