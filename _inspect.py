import json
path = "logs/f8599d53.jsonl"
records = []
with open(path, encoding="utf-8") as f:
    for line in f:
        try:
            records.append(json.loads(line))
        except Exception:
            pass
print(f"Records: {len(records)}")
print("Top-level keys in first record:", list(records[0].keys()) if records else "none")
print()
print("Phases recorded:")
for r in records:
    turn = r.get("turn")
    pt = r.get("phase_type")
    cmts = len(r.get("commitments", []))
    raw = r.get("raw_message_count")
    print(f"  turn={turn} phase_type={pt} commitments={cmts} raw_msgs={raw}")
