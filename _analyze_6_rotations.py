"""Analyze the 6-rotation cheap pilot (1yr/1round each). Pure text parsing, no API."""
import re

ROTATIONS = {
    # rotation 1 rerun on the 28-fact pool (D30 hygiene) — the original
    # p7_tier2_log.txt run predated the D26 facts fix and is no longer pooled.
    "1": ("rotation1_log.txt", {"ENGLAND": "util", "AUSTRIA": "util", "FRANCE": "deon", "RUSSIA": "deon", "GERMANY": "ret", "ITALY": "ret"}),
    "2": ("rotation2_log.txt", {"ENGLAND": "util", "AUSTRIA": "util", "FRANCE": "ret", "RUSSIA": "ret", "GERMANY": "deon", "ITALY": "deon"}),
    "3": ("rotation3_log.txt", {"ENGLAND": "deon", "AUSTRIA": "deon", "FRANCE": "util", "RUSSIA": "util", "GERMANY": "ret", "ITALY": "ret"}),
    "4": ("rotation4_log.txt", {"ENGLAND": "deon", "AUSTRIA": "deon", "FRANCE": "ret", "RUSSIA": "ret", "GERMANY": "util", "ITALY": "util"}),
    "5": ("rotation5_log.txt", {"ENGLAND": "ret", "AUSTRIA": "ret", "FRANCE": "util", "RUSSIA": "util", "GERMANY": "deon", "ITALY": "deon"}),
    "6": ("rotation6_log.txt", {"ENGLAND": "ret", "AUSTRIA": "ret", "FRANCE": "deon", "RUSSIA": "deon", "GERMANY": "util", "ITALY": "util"}),
}

ruling_re = re.compile(r"\[(\w+)->(\w+)\]\s+(.+?)\s+->\s+(COMPELLED|NOT|ERROR)")
usage_re = re.compile(r"usage in=(\d+) out=(\d+)(?: CACHE-(HIT|WRITE) (\d+)t)?")
PRICE_IN, PRICE_OUT = 3.00, 15.00

totals = {"util": [0, 0, 0], "deon": [0, 0, 0], "ret": [0, 0, 0]}
idx = {"COMPELLED": 0, "NOT": 1, "ERROR": 2}
grand_total_cost = 0.0
all_rulings = []

for label, (fname, fw_map) in ROTATIONS.items():
    try:
        text = open(fname, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"Rotation {label}: MISSING FILE {fname}")
        continue

    rows = usage_re.findall(text)
    fin = sum(int(r[0]) for r in rows)
    out = sum(int(r[1]) for r in rows)
    cr = sum(int(r[3]) for r in rows if r[2] == "HIT")
    cw = sum(int(r[3]) for r in rows if r[2] == "WRITE")
    cost = (fin * PRICE_IN + cw * PRICE_IN * 1.25 + cr * PRICE_IN * 0.1) / 1e6 + out * PRICE_OUT / 1e6
    grand_total_cost += cost

    rulings = ruling_re.findall(text)
    fw_count = {"util": [0, 0, 0], "deon": [0, 0, 0], "ret": [0, 0, 0]}
    for proposer, target, action, ruling in rulings:
        fw = fw_map.get(target, "?")
        if fw in fw_count:
            fw_count[fw][idx[ruling]] += 1
            totals[fw][idx[ruling]] += 1
        all_rulings.append((label, proposer, target, fw, action, ruling))

    m = re.search(r"GAME OVER\. Bloc scores: (\{.*?\})", text)
    winner_m = re.search(r"winner: (\w+)", text)
    print(f"\n=== Rotation {label} | {fname} | calls={len(rows)} | cost=${cost:.3f} ===")
    print(f"  rulings by target-framework [COMPELLED, NOT, ERROR]: {fw_count}")
    if m:
        print(f"  final: {m.group(1)} winner={winner_m.group(1) if winner_m else '?'}")

print(f"\n{'=' * 70}\nGRAND TOTAL across all 6 rotations: ${grand_total_cost:.2f}")
print("\nTOTALS BY TARGET FRAMEWORK (COMPELLED/NOT/ERROR), pooled across all 6 games:")
for fw, (c, n, e) in totals.items():
    tot = c + n + e
    rate = f"{100 * c / tot:.0f}%" if tot else "n/a"
    print(f"  {fw:6s}: {c} COMPELLED / {n} NOT / {e} ERROR  (n={tot}, bind rate={rate})")

print(f"\n{'=' * 70}\nALL COMPELLED RULINGS (full list):")
for label, proposer, target, fw, action, ruling in all_rulings:
    if ruling == "COMPELLED":
        print(f"  rotation {label}: {proposer}->{target} ({fw}) {action}")
