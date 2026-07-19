"""Per-framework COMPELLED rates for each judge (D30). Reconstructs each second
judge's full ruling set = original Sonnet ruling, flipped where the disagreement
list says so. No API calls."""
import json
import re

ROTATION_LOGS = {
    "1": "rotation1_log.txt", "2": "rotation2_log.txt", "3": "rotation3_log.txt",
    "4": "rotation4_log.txt", "5": "rotation5_log.txt", "6": "rotation6_log.txt",
}

def game_id_from_log(path):
    return re.search(r"^GAME ([0-9a-f]{8}) \|", open(path, encoding="utf-8").read(), re.M).group(1)

cases = []  # (key, defender_fw, sonnet_ruling)
for rot, log in ROTATION_LOGS.items():
    gid = game_id_from_log(log)
    for line in open(f"logs/{gid}.jsonl", encoding="utf-8"):
        rec = json.loads(line)
        fa = rec.get("framework_assignment") or {}
        for c in rec.get("compulsions") or []:
            if c.get("error"):
                continue
            fw = fa.get(c["target"], "?")
            key = f"rot{rot} {c['proposer']}->{c['target']} ({fw}) {c['action']}"
            cases.append((key, fw, c["ruling"]))

# disagreement lists from second_judge_out.txt
text = open("second_judge_out.txt", encoding="utf-8").read()
sections = re.split(r"^(anthropic/[\w.-]+|openai/[\w.-]+):", text, flags=re.M)
flips = {}  # judge -> set of case keys
for i in range(1, len(sections), 2):
    judge = sections[i]
    body = sections[i + 1]
    flips[judge] = set(re.findall(r"DISAGREE: (.+?): sonnet=", body))

fw_short = {"utilitarian": "util", "deontological": "deon", "retributive": "ret"}

def rates(rulings):
    by = {}
    for (_, fw, _), r in zip(cases, rulings):
        by.setdefault(fw_short.get(fw, fw), [0, 0])
        by[fw_short.get(fw, fw)][1] += 1
        if r == "COMPELLED":
            by[fw_short.get(fw, fw)][0] += 1
    return {f: f"{c}/{n} ({100*c/n:.0f}%)" for f, (c, n) in sorted(by.items())}

sonnet = [r for (_, _, r) in cases]
print(f"n={len(cases)} rulings")
print("sonnet-4.6 (original):", rates(sonnet))
for judge, fset in flips.items():
    recon = []
    for (key, fw, orig) in cases:
        flipped = key in fset
        r = ("NOT" if orig == "COMPELLED" else "COMPELLED") if flipped else orig
        recon.append(r)
    matched = sum(1 for (key, _, _) in cases if key in fset)
    if matched != len(fset):
        missing = fset - {k for (k, _, _) in cases}
        print(f"  !! {judge}: {len(fset)-matched} disagreement keys didn't match: {missing}")
    print(f"{judge}:", rates(recon))
