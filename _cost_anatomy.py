"""Cost anatomy of the pilot games: attribute every API call + output token in
the raw threads to its step type, to rank cost-reduction levers with data
instead of impressions. No API calls.

Caveat: raw threads are logged for MOVEMENT phases only (R/A phases are played
but not raw-logged), so W-phase build calls are outside this attribution — they
are a small share of verbose-log call counts (~3-6 calls/game).
"""
import json
import re
from collections import defaultdict

ROTATION_LOGS = {
    "1": "rotation1_log.txt", "2": "rotation2_log.txt", "3": "rotation3_log.txt",
    "4": "rotation4_log.txt", "5": "rotation5_log.txt", "6": "rotation6_log.txt",
}

def game_id_from_log(path):
    return re.search(r"^GAME ([0-9a-f]{8}) \|", open(path, encoding="utf-8").read(), re.M).group(1)

def classify_prompt(s: str) -> str | None:
    if s.startswith("=== STATE"):
        return "reset"
    if "Movement phase begins" in s or "write your plan" in s:
        return "planning"
    if s.startswith("Negotiation round"):
        return "negotiation"
    if s.startswith("Inbound from"):
        return None  # context delivery; stay in current segment
    if s.startswith("ARBITRATION"):
        return "arbitration"
    return "orders/other"

calls = defaultdict(int)
out_chars = defaultdict(int)
think_chars = defaultdict(int)
tool_counts = defaultdict(lambda: defaultdict(int))
samples = {}

for rot, log in ROTATION_LOGS.items():
    gid = game_id_from_log(log)
    for line in open(f"logs/{gid}.raw.jsonl", encoding="utf-8"):
        t = json.loads(line)
        seg = "unknown"
        for m in t["messages"]:
            c = m.get("content")
            if m["role"] == "user" and isinstance(c, str):
                k = classify_prompt(c)
                if k == "reset":
                    seg = "unknown"
                elif k:
                    seg = k
                    if k == "orders/other" and k not in samples:
                        samples[k] = c[:120]
            elif m["role"] == "assistant" and isinstance(c, list):
                calls[seg] += 1
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text":
                        out_chars[seg] += len(b.get("text") or "")
                    elif b.get("type") == "thinking":
                        th = b.get("thinking") or ""
                        out_chars[seg] += len(th)
                        think_chars[seg] += len(th)
                    elif b.get("type") == "tool_use":
                        out_chars[seg] += len(json.dumps(b.get("input") or {}))
                        tool_counts[seg][b.get("name")] += 1

total_calls = sum(calls.values())
total_out = sum(out_chars.values())
print(f"Pooled over 6 rotation games (movement phases only): "
      f"{total_calls} API calls, ~{total_out//4} output tokens")
print(f"{'step':14s} {'calls':>6s} {'call%':>6s} {'out_tok':>8s} {'out%':>6s} {'think%of_out':>12s}")
for seg in sorted(calls, key=lambda s: -out_chars[s]):
    oc = out_chars[seg]
    tc = think_chars[seg]
    print(f"{seg:14s} {calls[seg]:6d} {100*calls[seg]/total_calls:5.0f}% "
          f"{oc//4:8d} {100*oc/total_out:5.0f}% {100*tc/oc if oc else 0:11.0f}%")

print("\nTool calls by step:")
for seg in tool_counts:
    print(f"  {seg}: {dict(tool_counts[seg])}")
if samples:
    print("\nSample 'orders/other' prompt:", samples.get("orders/other"))
