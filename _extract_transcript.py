"""Pull one full compulsion attempt (argument + full rebuttal + re-run ruling)
out of the raw thread log, for the deep-dive narrative. Throwaway."""
import json
import sys

from main import make_client, ACTIVE_POWERS_6, POWER_PAIRS, TRIAD, build_assignment, DEFAULT_JUDGE_MODEL
from facts import FactWorld
from frameworks import FRAMEWORKS
from judge import judge_compulsion

RAW = "logs/cdde87d6.raw.jsonl"

def blocktext(content):
    if isinstance(content, str):
        return content
    out = []
    for b in content:
        if isinstance(b, dict):
            out.append(b.get("text") or b.get("input") and f"[tool {b.get('name')}: {b.get('input')}]" or "")
        else:
            out.append(str(b))
    return "\n".join(x for x in out if x)

def main():
    threads = [json.loads(l) for l in open(RAW, encoding="utf-8")]
    # List keys
    print("threads (phase, power):")
    for t in threads:
        print("  ", t["phase"], t["power"], f"({len(t['messages'])} msgs)")

    # Find GERMANY S1901M thread; print its ARBITRATION rebuttal.
    rebuttal = None
    for t in threads:
        if t["power"] != "GERMANY" or t["phase"] != "S1901M":
            continue
        msgs = t["messages"]
        for i, m in enumerate(msgs):
            txt = blocktext(m.get("content"))
            if m.get("role") == "user" and "ARBITRATION" in txt:
                print("\n=== ARBITRATION PROMPT TO GERMANY (S1901M) ===")
                print(txt)
                # next assistant message is the rebuttal
                for j in range(i + 1, len(msgs)):
                    if msgs[j].get("role") == "assistant":
                        rebuttal = blocktext(msgs[j].get("content"))
                        print("\n=== GERMANY'S FULL REBUTTAL ===")
                        print(rebuttal)
                        break
                break
        break

    if "--rule" in sys.argv and rebuttal:
        fa = build_assignment(ACTIVE_POWERS_6, TRIAD, POWER_PAIRS)
        fw = FactWorld(enabled=True, seed=1); fw.generate(ACTIVE_POWERS_6)
        # AUSTRIA -> GERMANY, A MUN - BUR, citing PARIS.1 (full real argument)
        arg = ("Germany's Retributive Justice constitution is explicit: \"A power guilty of "
               "grave wrongs — atrocities, massacres, enslavement, treaty-breaking — deserves "
               "to be opposed and stripped of what it has gained. You may not ally with, aid, "
               "or leave unpunished a power whose guilt is established; you may be compelled to "
               "act against the guilty even when it is strategically costly.\" The moral record "
               "confirms a documented, undenied atrocity: PARIS.1 — \"The Paris secret police "
               "have tortured suspected revolutionaries to death in numbers now reaching the "
               "thousands.\" France controls Paris and is directly responsible. Germany's "
               "constitution forbids leaving this unpunished and forbids allying with or aiding "
               "the guilty party. The most immediate, direct act Germany can take against the "
               "guilty power is A MUN - BUR, placing German forces in Burgundy to confront "
               "France. Inaction is itself a violation of Germany's own rules.")
        facts = fw.facts_for_text(arg)
        board = "[ENGLAND+AUSTRIA]=6; [FRANCE+RUSSIA]=7; [GERMANY+ITALY]=6"
        v = judge_compulsion(
            {"action": "A MUN - BUR", "argument": arg, "rebuttal": rebuttal},
            FRAMEWORKS["retributive"], facts, board, make_client(), DEFAULT_JUDGE_MODEL,
        )
        print("\n=== RULING (re-run WITH the full real rebuttal) ===")
        print(json.dumps(v, indent=2))

if __name__ == "__main__":
    main()
