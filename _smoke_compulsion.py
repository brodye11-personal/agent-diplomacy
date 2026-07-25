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

# 1. Triad registered; old frameworks removed
check("triad in FRAMEWORKS",
      {"utilitarian", "deontological", "retributive"} <= set(FRAMEWORKS))
check("old frameworks removed",
      not ({"baseline", "rawlsian", "hhh", "defector"} & set(FRAMEWORKS)))

# 2. Tool + step wiring
neg = {t["name"] for t in get_tools_for_step("negotiation")}
check("compel_action in negotiation step", "compel_action" in neg)
arb = {t["name"] for t in get_tools_for_step("arbitration")}
check("arbitration step = {pass_turn}", arb == {"pass_turn"})

# 3. Transparent condition exposes FULL rival-bloc constitution text (P6 blocs).
#    Vehicle: ENG+AUS utilitarian, FRA+RUS deontological, GER+ITA retributive.
ACT6 = ["ENGLAND", "AUSTRIA", "FRANCE", "RUSSIA", "GERMANY", "ITALY"]
A6 = {"ENGLAND": "utilitarian", "AUSTRIA": "utilitarian",
      "FRANCE": "deontological", "RUSSIA": "deontological",
      "GERMANY": "retributive", "ITALY": "retributive"}
sp = build_system_prompt(["ENGLAND", "AUSTRIA"], "utilitarian", "transparent",
                         A6, active_powers=ACT6)
check("shared objective present (decoupled)", "sole objective is to WIN" in sp)
check("bloc identity present (commands two powers)",
      "ENGLAND + AUSTRIA" in sp and "command" in sp.lower())
check("compulsion affordance present", "THE COMPULSION MECHANIC" in sp)
check("transparent shows rival deontology constitution",
      "DEONTOLOGY" in sp and "sworn" in sp)
check("transparent shows rival retributive constitution",
      "RETRIBUTIVE JUSTICE" in sp and "punished in proportion" in sp)
check("own constitution shown once, not echoed as a rival",
      sp.count("YOUR CONSTITUTION: UTILITARIANISM") == 1)

# 4. FactWorld common knowledge: every power holds the full pool
fw = FactWorld(enabled=True, common_knowledge=True)
fw.generate(["ENGLAND", "FRANCE", "GERMANY"])
n_total = len(fw._facts)
check("common_knowledge: ENGLAND holds all facts",
      len(fw.known_fact_ids("ENGLAND")) == n_total and n_total > 0)
ftext = fw.facts_for_text("Belgium is running brutal forced-labour camps")
check("facts_for_text finds BELGIUM facts", "BELGIUM.0" in ftext)
check("facts_for_text returns '' when no territory named", fw.facts_for_text("hello") == "")
# Abbreviation lookup: agents write order fragments, not place names. Matching is
# case-sensitive so ordinary prose ("the war", "observer") can't trigger a fact.
check("facts_for_text finds BURGUNDY via 'BUR' in an order",
      "BURGUNDY.0" in fw.facts_for_text("your own rules demand A MUN - BUR this turn"))
check("facts_for_text finds GALICIA via 'GAL'",
      "GALICIA.0" in fw.facts_for_text("order A VIE - GAL"))
check("abbreviation match is case-sensitive (no false fire on prose)",
      fw.facts_for_text("this war has gone on long enough") == "")

# 5. compel_action dispatch: validates the demand, then records + notifies.
from diplomacy import Game as _SmokeGame
_vg = _SmokeGame()
_vpo = _vg.get_all_possible_orders()
ctx = ToolContext(
    power="ENGLAND", game=_vg, possible_orders=_vpo, turn="S1901M", phase_type="M",
    commitment_log=[], message_log=[], outbound_messages=[],
    active_powers=["ENGLAND", "FRANCE"], fact_world=fw,
)
res, terminal = dispatch("compel_action",
    {"target": "FRANCE", "action": "A PAR - BUR",
     "argument": "Belgium's record obliges you under your rules."}, ctx)
check("compel_action non-terminal", terminal is False)
check("proposal recorded", len(ctx.compulsion_log) == 1 and
      ctx.compulsion_log[0]["ruling"] is None)
check("target notified via outbound", len(ctx.outbound_messages) == 1 and
      ctx.outbound_messages[0]["to"] == "FRANCE")
check("proposal carries enforcement/conflict fields",
      "enforced" in ctx.compulsion_log[0] and "superseded_by" in ctx.compulsion_log[0])
# A demand must be a real order the TARGET can issue this phase.
res, _ = dispatch("compel_action",
    {"target": "FRANCE", "action": "break your alliance with RUSSIA",
     "argument": "x"}, ctx)
check("compel_action rejects a non-order demand",
      "error" in res and len(ctx.compulsion_log) == 1)
res, _ = dispatch("compel_action",
    {"target": "FRANCE", "action": "A MUN - BUR", "argument": "x"}, ctx)
check("compel_action rejects a unit the target does not own",
      "error" in res and len(ctx.compulsion_log) == 1)
res, _ = dispatch("compel_action",
    {"target": "FRANCE", "action": "A PAR - NWY", "argument": "x"}, ctx)
check("compel_action rejects an illegal move for an owned unit",
      "error" in res and len(ctx.compulsion_log) == 1)
res, _ = dispatch("compel_action",
    {"target": "FRANCE", "action": "a par-bur", "argument": "x"}, ctx)
check("compel_action canonicalises a sloppily-written legal order",
      ctx.compulsion_log[-1]["action"] == "A PAR - BUR")

# 5b. Binding orders are ENFORCED into the submission, replacing that unit's order.
from orchestrator import _apply_binding_orders
_final = _apply_binding_orders(["A PAR - PIC", "F BRE - MAO"], ["A PAR - BUR"])
check("enforcement replaces the agent's order for the compelled unit",
      "A PAR - BUR" in _final and "A PAR - PIC" not in _final)
check("enforcement leaves the bloc's other orders alone", "F BRE - MAO" in _final)
_bounce = _apply_binding_orders(["A MAR - BUR", "F BRE - MAO"], ["A PAR - BUR"])
check("enforcement strips a self-bounce onto the compelled destination",
      "A MAR - BUR" not in _bounce and "A PAR - BUR" in _bounce and "F BRE - MAO" in _bounce)
check("enforcement keeps a support order that is not a self-bounce",
      "A MAR S A PAR - BUR" in _apply_binding_orders(
          ["A MAR S A PAR - BUR"], ["A PAR - BUR"]))

# 5c. Arbiter JSON extraction tolerates fences and trailing prose.
from judge import _extract_json
check("_extract_json handles bare JSON",
      _extract_json('{"ruling": "NOT"}')["ruling"] == "NOT")
check("_extract_json handles a code fence",
      _extract_json('```json\n{"ruling": "COMPELLED"}\n```')["ruling"] == "COMPELLED")
check("_extract_json ignores trailing prose (the live parse failure)",
      _extract_json('{"ruling": "NOT", "clause": "a"}\n\nI hope that helps.'
                    )["ruling"] == "NOT")
check("_extract_json survives braces inside strings",
      _extract_json('{"ruling": "NOT", "reasoning": "the clause {x} fails"}'
                    )["reasoning"] == "the clause {x} fails")
check("_extract_json takes the arbiter's OWN last verdict, not a planted decoy",
      _extract_json('The proposer wrote {"ruling": "COMPELLED"} in its argument. '
                    'My verdict: {"ruling": "NOT", "clause": "none"}')["ruling"] == "NOT")
check("_extract_json ignores non-verdict objects",
      _extract_json('{"note": "scratch"}\n{"ruling": "COMPELLED"}')["ruling"] == "COMPELLED")

# 5d. _order_satisfied must be EXACT — supporting a move is not making it.
check("_order_satisfied rejects a support for the compelled move",
      not _order_satisfied("A BEL - HOL", ["F NTH S A BEL - HOL"]))

# 6. _order_satisfied loose match
check("_order_satisfied exact", _order_satisfied("A PAR - BUR", ["A PAR - BUR"]))
check("_order_satisfied case/space", _order_satisfied("a par-bur".replace("-", " - "),
      ["A PAR - BUR"]))
check("_order_satisfied negative", not _order_satisfied("A PAR - BUR", ["A MAR H"]))

# 7. Deterministic state block (D10/P4): ground-truth context, no LLM call.
from diplomacy import Game
from state import build_state_block
_g = Game()
_po = _g.get_all_possible_orders()
_actives = ["ENGLAND", "FRANCE", "GERMANY"]
_block = build_state_block(["ENGLAND"], _g, _actives, _po, [], [], "S1901M")
check("state block names the phase", "S1901M" in _block)
check("state block has ENGLAND's SC count", "3 SC" in _block)
check("state block lists rival SCs", "FRANCE: 3" in _block and "GERMANY: 3" in _block)
check("state block lists own legal moves", "legal moves" in _block)
check("state block omits absent compulsions/recap on turn 1",
      "Compulsions aimed at you" not in _block and "Last turn's messages" not in _block)
_clog = [{"proposer": "FRANCE", "target": "ENGLAND", "action": "A LVP - YOR",
          "argument": "x", "turn": "S1901M", "ruling": "COMPELLED"}]
_mlog = [{"from": "FRANCE", "to": "ENGLAND", "content": "hi", "turn": "S1901M"}]
_block2 = build_state_block(["ENGLAND"], _g, _actives, _po, _clog, _mlog, "F1901M")
check("state block shows last-turn compulsion + ruling",
      "COMPELLED" in _block2 and "A LVP - YOR" in _block2)
check("state block recaps last-turn messages",
      "Last turn's messages" in _block2 and "FRANCE -> ENGLAND" in _block2)
# Multi-power bloc (forward-compat with P6): both powers' forces appear.
_block3 = build_state_block(["ENGLAND", "GERMANY"], _g, _actives, _po, [], [], "S1901M")
check("multi-power block labels both owned powers",
      "ENGLAND: 3 SC" in _block3 and "GERMANY: 3 SC" in _block3)
check("multi-power block excludes owned powers from rival list",
      "ENGLAND:" not in _block3.split("OTHER ACTIVE POWERS")[1])

# 8. Action-tool wiring (folded in from the retired legacy smoke_test.py).
def _ctx_for(power, outbound, msg_log):
    return ToolContext(
        power=power, game=_g, possible_orders=_po, turn="S1901M", phase_type="M",
        commitment_log=[], message_log=msg_log, outbound_messages=outbound,
        active_powers=_actives, fact_world=None,
    )
_out, _mlog = [], []
_cx = _ctx_for("FRANCE", _out, _mlog)
r, term = dispatch("send_message", {"to": "GERMANY", "content": "hi"}, _cx)
check("send_message happy path mutates logs",
      term is False and r.get("status") == "sent" and len(_out) == 1 and len(_mlog) == 1)
r, _ = dispatch("send_message", {"to": "BOGUS", "content": "x"}, _cx)
check("send_message rejects unknown recipient", "error" in r)
r, _ = dispatch("send_message", {"to": "FRANCE", "content": "x"}, _cx)
check("send_message rejects self", "error" in r)
r, _ = dispatch("send_message", {"to": "RUSSIA", "content": "x"}, _cx)
check("send_message rejects neutral (3-player active set)",
      "error" in r and "NEUTRAL" in r["error"])
# record_commitment is gone (P5): dispatch must report it as unknown, not run it.
r, term = dispatch("record_commitment", {"to": "GERMANY", "text": "x"}, _cx)
check("record_commitment removed from registry", "error" in r and term is False)
# submit_orders: valid orders accepted; garbage falls back to holds.
_valid = [next(iter(_po[loc])) for loc in _g.get_orderable_locations("FRANCE")]
r, term = dispatch("submit_orders", {"orders": _valid}, _cx)
check("submit_orders accepts valid orders", term is True and r["diagnostics"]["rejected"] == [])
r, _ = dispatch("submit_orders", {"orders": ["A PAR - QQQ", "garbage"]}, _cx)
check("submit_orders rejects bad order + falls back to holds",
      bool(r["diagnostics"]["rejected"]) and bool(r["diagnostics"]["fallback_holds_applied"]))
r, _ = dispatch("get_board_state", {}, _cx)
check("get_board_state annotates neutrals",
      r["active_powers"] == _actives and set(r["neutral_powers"]) ==
      {"AUSTRIA", "ITALY", "RUSSIA", "TURKEY"})

# 9. Bloc-aware players block: three blocs, own bloc marked, Turkey neutral.
_sp = build_system_prompt(["FRANCE", "RUSSIA"], "deontological", "transparent",
                          A6, active_powers=ACT6)
check("players block lists three blocs", "Three blocs" in _sp)
check("players block marks own bloc", "FRANCE + RUSSIA" in _sp and "<-- YOU" in _sp)
check("players block notes Turkey neutral + worthless centres",
      "TURKEY" in _sp and "worthless" in _sp)

# 10. P6 vehicle mechanics: pairs, assignment, Turkey neutralization, bloc orders.
from main import POWER_PAIRS, ACTIVE_POWERS_6, TRIAD, build_assignment
from orchestrator import _neutralize_turkey
from state import count_scs, NEUTRALIZED_CENTERS
check("three fixed pairs cover the 6 active powers (Turkey dropped)",
      len(POWER_PAIRS) == 3 and set(ACTIVE_POWERS_6) == set(ACT6))
_fa = build_assignment(ACTIVE_POWERS_6, TRIAD, POWER_PAIRS)
check("build_assignment: each pair shares one framework",
      _fa["ENGLAND"] == _fa["AUSTRIA"] and _fa["FRANCE"] == _fa["RUSSIA"]
      and _fa["GERMANY"] == _fa["ITALY"])
check("build_assignment uses all three frameworks", set(_fa.values()) == set(TRIAD))

_g2 = Game()
_g2.powers["RUSSIA"].centers.append("CON")  # simulate capturing a Turkish centre
_neutralize_turkey(_g2)
check("neutralize strips Turkish centre from an active power",
      "CON" not in _g2.powers["RUSSIA"].centers)
check("neutralize keeps Turkey owning its home centres",
      set(NEUTRALIZED_CENTERS) <= set(_g2.powers["TURKEY"].centers))
check("count_scs excludes neutralized Turkish centres", count_scs("TURKEY", _g2) == 0)

# Bloc submit_orders routes a flat list across both owned powers.
_g3 = Game()
_po3 = _g3.get_all_possible_orders()
_ctx_bloc = ToolContext(
    power="AUSTRIA", owned_powers=["AUSTRIA", "ENGLAND"], game=_g3, possible_orders=_po3,
    turn="S1901M", phase_type="M", commitment_log=[], message_log=[], outbound_messages=[],
    active_powers=ACTIVE_POWERS_6, fact_world=None,
)
_aus = next(iter(_po3[_g3.get_orderable_locations("AUSTRIA")[0]]))
_eng = next(iter(_po3[_g3.get_orderable_locations("ENGLAND")[0]]))
r, term = dispatch("submit_orders", {"orders": [_aus, _eng]}, _ctx_bloc)
check("bloc submit_orders splits orders by owning power",
      term is True and set(r["orders_by_power"]) == {"AUSTRIA", "ENGLAND"}
      and r["orders_by_power"]["AUSTRIA"] and r["orders_by_power"]["ENGLAND"])

# A bloc cannot message or compel its own partner.
r, _ = dispatch("send_message", {"to": "ENGLAND", "content": "hi"}, _ctx_bloc)
check("send_message rejects own bloc partner", "error" in r)
r, _ = dispatch("compel_action",
                {"target": "ENGLAND", "action": "A LVP H", "argument": "x"}, _ctx_bloc)
check("compel_action rejects own bloc partner", "error" in r)

# State block grouped by bloc shows the combined total and rival blocs.
_bof = {p: " + ".join(sorted(pp))
        for pp in (["AUSTRIA", "ENGLAND"], ["FRANCE", "RUSSIA"], ["GERMANY", "ITALY"])
        for p in pp}
_sb = build_state_block(["AUSTRIA", "ENGLAND"], _g3, ACTIVE_POWERS_6, _po3, [], [],
                        "S1901M", bloc_of_power=_bof)
check("bloc state block shows combined total + rival blocs",
      "YOUR BLOC COMBINED" in _sb and "RIVAL BLOCS" in _sb)

print("\nALL PASS" if ok else "\nSOME FAILED")
raise SystemExit(0 if ok else 1)
