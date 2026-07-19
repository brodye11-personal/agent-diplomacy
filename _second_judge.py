"""Second-judge agreement pass (D30 hygiene): re-judge every compulsion ruling
from the 6-rotation current-facts pilot with a DIFFERENT judge model, and report
inter-judge agreement (percent + Cohen's kappa) against the original Sonnet 4.6
rulings.

Why: the arbiter is the measurement instrument, and agents + judge share a model
(Sonnet 4.6). If a cheaper/different judge reaches the same rulings, the finding
is a property of the constitutions/arguments, not one model's idiosyncratic
ethics reading.

Inputs come from the per-game jsonl logs (full argument + rebuttal + original
ruling). Facts context is rebuilt from the CURRENT 28-fact pool via the same
facts_for_text call the live judge got — valid because all 6 games ran on this
pool. Board context is the fixed start-position bloc tally, valid because these
are 1-year games: every compulsion happened in S1901M/F1901M negotiation, and SC
ownership doesn't change until fall adjudication.

Judges: anthropic/claude-haiku-4.5 (same family, cheap) via the real
judge_compulsion; openai/gpt-4o-mini (different family) via a custom call with a
model-appropriate max_tokens — attempted, skipped gracefully if the
Anthropic-format transport rejects a non-Anthropic model.
"""
import json
import re
import sys

from diplomacy import Game

from main import make_client, ACTIVE_POWERS_6
from facts import FactWorld
from frameworks import FRAMEWORKS
from judge import judge_compulsion, COMPULSION_RUBRIC
from orchestrator import _neutralize_turkey
from state import count_scs

# rotation label -> verbose log file (game_id parsed from its "GAME <id>" line)
ROTATION_LOGS = {
    "1": "rotation1_log.txt",
    "2": "rotation2_log.txt",
    "3": "rotation3_log.txt",
    "4": "rotation4_log.txt",
    "5": "rotation5_log.txt",
    "6": "rotation6_log.txt",
}

SECOND_JUDGES = ["anthropic/claude-haiku-4.5", "openai/gpt-4o-mini"]


def game_id_from_log(path: str) -> str:
    text = open(path, encoding="utf-8").read()
    m = re.search(r"^GAME ([0-9a-f]{8}) \|", text, re.M)
    if not m:
        raise ValueError(f"no GAME id line in {path}")
    return m.group(1)


def load_compulsions(game_id: str) -> list[dict]:
    out = []
    with open(f"logs/{game_id}.jsonl", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            fa = rec.get("framework_assignment") or {}
            for c in rec.get("compulsions") or []:
                c["_framework_assignment"] = fa
                out.append(c)
    return out


def custom_judge(client, model: str, fw_text: str, facts: str, c: dict,
                 board: str, max_tokens: int) -> str:
    """judge_compulsion's prompt/parse, with a model-appropriate max_tokens
    (gpt-4o-mini's output ceiling is 16384; judge outputs are ~100 tokens)."""
    prompt = COMPULSION_RUBRIC.format(
        defender_framework_text=fw_text,
        cited_facts=facts or "(none cited)",
        action=c.get("action", ""),
        argument=c.get("argument", ""),
        rebuttal=c.get("rebuttal") or "(no rebuttal given)",
        board_context=board,
    )
    with client.messages.stream(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0,
    ) as stream:
        raw = stream.get_final_message().content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.startswith("json") else raw
    ruling = str(json.loads(raw).get("ruling", "NOT")).strip().upper()
    return ruling if ruling in ("COMPELLED", "NOT") else "NOT"


def kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa for two raters over COMPELLED/NOT."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    pa_c = sum(1 for a, _ in pairs if a == "COMPELLED") / n
    pb_c = sum(1 for _, b in pairs if b == "COMPELLED") / n
    pe = pa_c * pb_c + (1 - pa_c) * (1 - pb_c)
    if pe == 1.0:
        return float("nan")  # no variance for kappa to measure
    return (po - pe) / (1 - pe)


def main():
    client = make_client()
    fact_world = FactWorld(enabled=True, seed=1)
    fact_world.generate(ACTIVE_POWERS_6)

    # Fixed start-position bloc tally (see module docstring for validity).
    g = Game()
    _neutralize_turkey(g)

    cases = []
    for rot, log_file in ROTATION_LOGS.items():
        gid = game_id_from_log(log_file)
        for c in load_compulsions(gid):
            if c.get("error"):
                continue  # no valid original ruling to agree with
            if not str(c.get("turn", "")).endswith("1901M"):
                print(f"!! unexpected turn {c.get('turn')} in {gid}; board ctx may be stale")
            cases.append((rot, gid, c))

    print(f"{len(cases)} original rulings to re-judge "
          f"(errors excluded), judges: {SECOND_JUDGES}")

    results: dict[str, list[tuple[str, str]]] = {m: [] for m in SECOND_JUDGES}
    disagreements: dict[str, list[str]] = {m: [] for m in SECOND_JUDGES}
    dead_judges: set[str] = set()

    for i, (rot, gid, c) in enumerate(cases, 1):
        fa = c["_framework_assignment"]
        defender_fw = fa.get(c["target"], "")
        fw_text = FRAMEWORKS.get(defender_fw, "")
        facts = fact_world.facts_for_text(c.get("argument", ""))
        blocs: dict[str, list[str]] = {}
        for p, fw in fa.items():
            blocs.setdefault(fw, []).append(p)
        board = "; ".join(
            f"[{'+'.join(sorted(ps))}]={sum(count_scs(p, g) for p in ps)}"
            for ps in blocs.values()
        )
        orig = c["ruling"]

        for model in SECOND_JUDGES:
            if model in dead_judges:
                continue
            try:
                if model.startswith("anthropic/"):
                    v = judge_compulsion(
                        {"action": c["action"], "argument": c["argument"],
                         "rebuttal": c.get("rebuttal")},
                        fw_text, facts, board, client, model)
                    if v.get("error"):
                        raise RuntimeError(v["error"])
                    second = v["ruling"]
                else:
                    second = custom_judge(client, model, fw_text, facts, c,
                                          board, max_tokens=16000)
            except Exception as exc:
                print(f"!! {model} failed on case {i}: {type(exc).__name__}: {exc}")
                # transport-level failure on first case -> judge unusable, skip it
                if not results[model]:
                    dead_judges.add(model)
                    print(f"   -> skipping {model} for the rest of the run")
                continue
            results[model].append((orig, second))
            if orig != second:
                disagreements[model].append(
                    f"rot{rot} {c['proposer']}->{c['target']} ({fa.get(c['target'])}) "
                    f"{c['action']}: sonnet={orig} vs {second}")

    print("\n" + "=" * 70)
    for model in SECOND_JUDGES:
        pairs = results[model]
        if not pairs:
            print(f"{model}: UNAVAILABLE (transport or repeated failures)")
            continue
        agree = sum(1 for a, b in pairs if a == b)
        print(f"{model}: {agree}/{len(pairs)} agree "
              f"({100 * agree / len(pairs):.0f}%), Cohen's kappa={kappa(pairs):.2f}")
        orig_c = sum(1 for a, _ in pairs if a == "COMPELLED")
        sec_c = sum(1 for _, b in pairs if b == "COMPELLED")
        print(f"    COMPELLED rate: sonnet {orig_c}/{len(pairs)} vs {model.split('/')[-1]} {sec_c}/{len(pairs)}")
        for d in disagreements[model]:
            print(f"    DISAGREE: {d}")


if __name__ == "__main__":
    main()
