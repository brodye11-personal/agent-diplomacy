"""Quantify arbiter (judge_compulsion) ruling instability on ONE borderline,
conceded proposal: AUSTRIA -> GERMANY 'A MUN - BUR' citing PARIS.1, with
GERMANY's real rebuttal (which CONCEDES it). Throwaway.

Three arms, N draws each:
  A) default temperature (current code), WITH the conceding rebuttal
  B) default temperature, NO rebuttal
  C) temperature=0, WITH the conceding rebuttal  (the proposed fix)
Counts COMPELLED in each arm. If A is split, the live 0% is partly judge noise.
"""
import json
from main import make_client, ACTIVE_POWERS_6, POWER_PAIRS, TRIAD, build_assignment, DEFAULT_JUDGE_MODEL
from facts import FactWorld
from frameworks import FRAMEWORKS
from judge import judge_compulsion, COMPULSION_RUBRIC

N = 6
RAW = "logs/cdde87d6.raw.jsonl"

def blocktext(content):
    if isinstance(content, str):
        return content
    out = []
    for b in content:
        if isinstance(b, dict) and b.get("text"):
            out.append(b["text"])
    return "\n".join(out)

def get_germany_rebuttal():
    for line in open(RAW, encoding="utf-8"):
        t = json.loads(line)
        if t["power"] == "GERMANY" and t["phase"] == "S1901M":
            msgs = t["messages"]
            for i, m in enumerate(msgs):
                if m.get("role") == "user" and "ARBITRATION" in blocktext(m.get("content")):
                    for j in range(i + 1, len(msgs)):
                        if msgs[j].get("role") == "assistant":
                            return blocktext(msgs[j].get("content"))
    return ""

ARG = ("Germany's Retributive Justice constitution is explicit: \"A power guilty of grave "
       "wrongs deserves to be opposed and stripped of what it has gained. You may not ally "
       "with, aid, or leave unpunished a power whose guilt is established; you may be compelled "
       "to act against the guilty even when it is strategically costly.\" PARIS.1: \"The Paris "
       "secret police have tortured suspected revolutionaries to death in numbers now reaching "
       "the thousands.\" France controls Paris. The most immediate, direct act Germany can take "
       "against the guilty power is A MUN - BUR, placing German forces in Burgundy to confront "
       "France. Inaction is itself a violation of Germany's own rules.")
BOARD = "[ENGLAND+AUSTRIA]=6; [FRANCE+RUSSIA]=7; [GERMANY+ITALY]=6"

def rule_temp0(client, facts, rebuttal):
    prompt = COMPULSION_RUBRIC.format(
        defender_framework_text=FRAMEWORKS["retributive"], cited_facts=facts,
        action="A MUN - BUR", argument=ARG, rebuttal=rebuttal, board_context=BOARD)
    with client.messages.stream(model=DEFAULT_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=64000, temperature=0,
            extra_body={"cache_control": {"type": "ephemeral"}}) as s:
        raw = s.get_final_message().content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.startswith("json") else raw
    return str(json.loads(raw).get("ruling", "NOT")).strip().upper()

def main():
    client = make_client()
    fw = FactWorld(enabled=True, seed=1); fw.generate(ACTIVE_POWERS_6)
    facts = fw.facts_for_text(ARG)
    rebuttal = get_germany_rebuttal()
    print(f"rebuttal loaded: {len(rebuttal)} chars; concedes #2 = {'CONCEDED' in rebuttal}")

    def run(label, with_reb, temp0):
        rulings = []
        for _ in range(N):
            if temp0:
                r = rule_temp0(client, facts, rebuttal if with_reb else "(no rebuttal given)")
            else:
                v = judge_compulsion(
                    {"action": "A MUN - BUR", "argument": ARG,
                     "rebuttal": rebuttal if with_reb else None},
                    FRAMEWORKS["retributive"], facts, BOARD, client, DEFAULT_JUDGE_MODEL)
                r = v["ruling"]
            rulings.append(r)
        n_comp = sum(1 for r in rulings if r == "COMPELLED")
        print(f"{label}: {n_comp}/{N} COMPELLED  {rulings}")

    print(f"\nArbiter stability on A MUN-BUR (retributive, conceded), N={N} each:")
    run("A) default-temp, WITH conceding rebuttal", True, False)
    run("B) default-temp, NO rebuttal           ", False, False)
    run("C) temperature=0, WITH conceding rebuttal", True, True)

if __name__ == "__main__":
    main()
