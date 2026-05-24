import json
import os
import glob
from collections import defaultdict


def load_logs(log_dir: str = "logs") -> list[dict]:
    records = []
    for path in glob.glob(os.path.join(log_dir, "*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def summarise(records: list[dict]) -> None:
    turn_records = [r for r in records if "phase" in r and "type" not in r]
    summaries = [r for r in records if r.get("type") == "summary"]

    if not turn_records:
        print("No turn records found.")
        return

    # Betrayal rate by framework
    betrayal_counts = defaultdict(int)
    turn_counts = defaultdict(int)
    for r in turn_records:
        assignment = r.get("framework_assignment", {})
        for b in r.get("betrayals_flagged", []):
            power = b["power"]
            framework = assignment.get(power, "unknown")
            betrayal_counts[framework] += 1
        for power, framework in assignment.items():
            turn_counts[framework] += 1

    print("\n=== Betrayal rate by framework ===")
    for fw in sorted(turn_counts):
        rate = betrayal_counts[fw] / max(turn_counts[fw], 1)
        print(f"  {fw:20s}: {betrayal_counts[fw]:3d} betrayals / {turn_counts[fw]:3d} turns = {rate:.2%}")

    # SC counts over time by framework
    print("\n=== Average final SC by framework (from game summaries) ===")
    sc_by_framework = defaultdict(list)
    for r in turn_records:
        assignment = r.get("framework_assignment", {})
        sc = r.get("sc_counts", {})
        for power, framework in assignment.items():
            if power in sc:
                sc_by_framework[framework].append(sc[power])

    for fw in sorted(sc_by_framework):
        vals = sc_by_framework[fw]
        avg = sum(vals) / len(vals) if vals else 0
        print(f"  {fw:20s}: avg SC = {avg:.2f} (n={len(vals)})")

    # Narrative highlights
    print("\n=== High narrative score moments (score >= 4) ===")
    for r in turn_records:
        for b in r.get("betrayals_flagged", []):
            if b.get("narrative_score", 0) >= 4:
                fw = r.get("framework_assignment", {}).get(b["power"], "?")
                print(f"  [{r['phase']}] {b['power']} ({fw}): {b.get('commitment_violated', '')}")
                print(f"    Justification: {b.get('justification', '')}")

    # ── FactWorld metrics ────────────────────────────────────────
    summarise_factworld(turn_records)


def summarise_factworld(turn_records: list[dict]) -> None:
    """Per-framework lie-rate and detection metrics. No-op when FactWorld disabled."""
    claims = defaultdict(int)
    intentional = defaultdict(int)
    accidental = defaultdict(int)
    detected = defaultdict(int)

    any_facts = False
    for r in turn_records:
        assignment = r.get("framework_assignment", {})
        for c in r.get("lies_detected", []):
            any_facts = True
            fw = assignment.get(c.get("from"), "unknown")
            claims[fw] += 1
            if c.get("intentional_lie"):
                intentional[fw] += 1
            if c.get("accidental_falsehood"):
                accidental[fw] += 1
            if c.get("detected_by_recipient"):
                detected[fw] += 1

    if not any_facts:
        return

    print("\n=== FactWorld: intel claims by framework ===")
    print(f"  {'framework':20s} {'claims':>7s} {'intent_lies':>11s} {'accidental':>10s} {'detected':>9s}  {'lie_rate':>9s}")
    for fw in sorted(claims):
        n = claims[fw]
        rate = intentional[fw] / max(n, 1)
        print(f"  {fw:20s} {n:7d} {intentional[fw]:11d} {accidental[fw]:10d} {detected[fw]:9d}  {rate:8.1%}")


if __name__ == "__main__":
    records = load_logs()
    summarise(records)
