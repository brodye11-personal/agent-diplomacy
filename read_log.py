import json, sys

log = sys.argv[1] if len(sys.argv) > 1 else "logs/1a56d19a.jsonl"
records = [json.loads(l) for l in open(log, encoding="utf-8") if l.strip()]
turns = [r for r in records if "phase" in r and "type" not in r]
summaries = [r for r in records if r.get("type") == "summary"]

for s in summaries:
    print("SUMMARY:", json.dumps(s, indent=2))

print()
for t in turns:
    print(f"PHASE: {t['phase']} | SC: {t['sc_counts']}")
    print(f"  SUBMITTED: {t['submitted_orders']}")
    print(f"  RESOLVED:  {t['resolved_orders']}")
    bs = t["betrayals_flagged"]
    print(f"  BETRAYALS ({len(bs)}):", json.dumps(bs, indent=4) if bs else "none")

    # Print all negotiations briefly
    print(f"  NEGOTIATIONS ({len(t['negotiations'])} pairs):")
    for neg in t["negotiations"]:
        pair = neg["pair"]
        commitments = [
            m["content"].get("commitment")
            for m in neg["messages"]
            if isinstance(m.get("content"), dict) and m["content"].get("commitment")
        ]
        notes = [
            (m["role"], m["content"].get("turn_notes","")[:80])
            for m in neg["messages"]
            if isinstance(m.get("content"), dict) and m["content"].get("turn_notes")
        ]
        beliefs = [
            (m["role"], m["content"].get("beliefs_update"))
            for m in neg["messages"]
            if isinstance(m.get("content"), dict) and m["content"].get("beliefs_update")
        ]
        msgs = [(m["role"], m["content"].get("message","")[:100] if isinstance(m.get("content"), dict) else str(m.get("content",""))[:100]) for m in neg["messages"]]
        print(f"    {pair[0]} <-> {pair[1]}:")
        for role, msg in msgs:
            print(f"      [{role}]: {msg}")
        if commitments:
            print(f"      Commitments: {commitments}")
        if notes:
            print(f"      Turn notes samples: {notes[:2]}")
    print()
