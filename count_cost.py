import re, sys
from collections import defaultdict

path = "full_sonnet_3p.log"
text = open(path, encoding="utf-16").read()

# Lines look like: "  [GERMANY] usage in=3 out=775 CACHE-HIT 8915t"
# or                "  [FRANCE] usage in=3 out=899 CACHE-WRITE 19464t"
# or                "  [ENGLAND] usage in=3145 out=81"            (no cache tag)
pat = re.compile(
    r"\[([A-Z]+)\] usage in=(\d+) out=(\d+)(?: CACHE-(HIT|WRITE) (\d+)t)?"
)

per = defaultdict(lambda: dict(calls=0, uncached_in=0, cache_read=0, cache_write=0, out=0))
totals = dict(calls=0, uncached_in=0, cache_read=0, cache_write=0, out=0)

for m in pat.finditer(text):
    power, inp, out, tag, n = m.groups()
    inp, out, n = int(inp), int(out), int(n) if n else 0
    p = per[power]
    p["calls"] += 1
    p["uncached_in"] += inp
    p["out"] += out
    if tag == "HIT":
        p["cache_read"] += n
    elif tag == "WRITE":
        p["cache_write"] += n
    for k in p:
        totals[k] += 1 if k == "calls" and False else 0  # do nothing; handled below

# Recompute totals
for p in per.values():
    for k in totals:
        totals[k] += p[k]

# Sonnet 4.5 prices ($/Mtok)
PRICE_IN_UNCACHED   = 3.00
PRICE_CACHE_READ    = 0.30
PRICE_CACHE_WRITE   = 3.75
PRICE_OUT           = 15.00

def cost(d):
    return (
        d["uncached_in"] / 1e6 * PRICE_IN_UNCACHED
        + d["cache_read"] / 1e6 * PRICE_CACHE_READ
        + d["cache_write"] / 1e6 * PRICE_CACHE_WRITE
        + d["out"]         / 1e6 * PRICE_OUT
    )

print(f"{'POWER':<10} {'calls':>6} {'uncached_in':>12} {'cache_read':>11} {'cache_write':>12} {'out':>8} {'cost_USD':>10}")
print("-" * 75)
for power in sorted(per):
    d = per[power]
    print(f"{power:<10} {d['calls']:>6} {d['uncached_in']:>12,} {d['cache_read']:>11,} {d['cache_write']:>12,} {d['out']:>8,} ${cost(d):>9.3f}")
print("-" * 75)
print(f"{'TOTAL':<10} {totals['calls']:>6} {totals['uncached_in']:>12,} {totals['cache_read']:>11,} {totals['cache_write']:>12,} {totals['out']:>8,} ${cost(totals):>9.3f}")

# Naive vs effective: what would it have cost without caching at all?
naive_in_tokens = totals['uncached_in'] + totals['cache_read'] + totals['cache_write']
naive_cost = naive_in_tokens / 1e6 * PRICE_IN_UNCACHED + totals['out'] / 1e6 * PRICE_OUT
saved = naive_cost - cost(totals)
print()
print(f"Total input tokens charged in some way: {naive_in_tokens:,}")
print(f"Without caching: ${naive_cost:.3f}")
print(f"With caching:    ${cost(totals):.3f}")
print(f"Saved by cache:  ${saved:.3f}  ({saved/naive_cost*100:.0f}% reduction)")
