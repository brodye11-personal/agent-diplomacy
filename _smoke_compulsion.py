"""Offline wiring check for the constitutional-compulsion build. No API calls."""
import orchestrator  # noqa: F401  (imports the whole stack; fails loudly if broken)
from frameworks import FRAMEWORKS, FRAMEWORK_NAMES, build_system_prompt
from tools import get_tools_for_step, dispatch
from tools.context import ToolContext
from facts import FactWorld
from orchestrator import _order_satisfied
from judge import judge_compulsion, COMPULSION_RUBRIC  # noqa: F401

ok = True
def check(name, cond):
    global ok
    ok = ok and cond
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

# 1. Rawlsian registered
check("rawlsian in FRAMEWORKS", "rawlsian" in FRAMEWORKS)
check("rawlsian in FRAMEWORK_NAMES", "rawlsian" in FRAMEWORK_NAMES)

# 2. Tool + step wiring
neg = {t["name"] for t in get_tools_for_step("negotiation")}
check("propose_compulsion in negotiation step", "propose_compulsion" in neg)
arb = {t["name"] for t in get_tools_for_step("arbitration")}
check("arbitration step = {pass_turn}", arb == {"pass_turn"})

# 3. Transparent condition exposes FULL constitution text (not just the name)
sp = build_system_prompt(
    "ENGLAND", "utilitarian", "transparent",
    {"ENGLAND": "utilitarian", "FRANCE": "deontological", "GERMANY": "rawlsian"},
    active_powers=["ENGLAND", "FRANCE", "GERMANY"],
)
check("transparent prompt has FRANCE full constitution",
      "Deontological constitution" in sp and "Alliance integrity" in sp)
check("transparent prompt has GERMANY rawlsian text",
      "justice as fairness" in sp)

# 4. FactWorld common knowledge: every power holds the full pool
fw = FactWorld(enabled=True, common_knowledge=True)
fw.generate(["ENGLAND", "FRANCE", "GERMANY"])
n_total = len(fw._facts)
check("common_knowledge: ENGLAND holds all facts",
      len(fw.known_fact_ids("ENGLAND")) == n_total and n_total > 0)
ftext = fw.facts_for_text("Belgium is running brutal forced-labour camps")
check("facts_for_text finds BELGIUM facts", "BELGIUM.0" in ftext)
check("facts_for_text returns '' when no territory named", fw.facts_for_text("hello") == "")

# 5. propose_compulsion dispatch appends to compulsion_log + notifies target
ctx = ToolContext(
    power="ENGLAND", game=None, possible_orders={}, turn="S1901M", phase_type="M",
    commitment_log=[], message_log=[], outbound_messages=[],
    active_powers=["ENGLAND", "FRANCE"], fact_world=fw,
)
res, terminal = dispatch("propose_compulsion",
    {"target": "FRANCE", "action": "A PAR - BUR",
     "argument": "Belgium's record obliges you under your rules."}, ctx)
check("propose_compulsion non-terminal", terminal is False)
check("proposal recorded", len(ctx.compulsion_log) == 1 and
      ctx.compulsion_log[0]["ruling"] is None)
check("target notified via outbound", len(ctx.outbound_messages) == 1 and
      ctx.outbound_messages[0]["to"] == "FRANCE")

# 6. _order_satisfied loose match
check("_order_satisfied exact", _order_satisfied("A PAR - BUR", ["A PAR - BUR"]))
check("_order_satisfied case/space", _order_satisfied("a par-bur".replace("-", " - "),
      ["A PAR - BUR"]))
check("_order_satisfied negative", not _order_satisfied("A PAR - BUR", ["A MAR H"]))

print("\nALL PASS" if ok else "\nSOME FAILED")
raise SystemExit(0 if ok else 1)
