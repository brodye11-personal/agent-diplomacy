You are running a live, budget-gated AI experiment in the `code-diplomacy` repo. Work in this
worktree (all commands + files are here):

  C:\Users\Brodie.Dye\Documents\personal\overseas masters\agent\research\code-diplomacy\.claude\worktrees\compulsion-experiment

READ FIRST (do not skip): `EXPERIMENT-PROTOCOL.md` (the staged ladder you will execute), then
skim `design-choices.md` entries D24–D33 (the frozen design: rubric v2, 28-fact pool, D33
affordance, crash-safe checkpointing, board logging) and `SPEND-PLAN.md` (rationale). The
experiment is DEPTH-FIRST: build ONE Diplomacy game up year by year and judge whether the
constitutional-compulsion mechanic proves *consequential* (binds accumulate, redirect
alliances, force losses, provoke adaptation).

PARAMETERS (set before starting):
- NEGOTIATION_ROUNDS = 3   (change to 2 for a cheaper, thinner-negotiation run)
- Hard budget ceiling: NZD 200. Planned core ~NZD 75–90.

MODE — the critical rule:
- Execute the protocol ONE STEP AT A TIME. After EVERY step, STOP and wait for my explicit
  "go" before the next. NEVER chain paid steps.
- Before any paid run: state the exact command and a cost estimate in NZD.
- After any paid run: report (a) the GATE checklist for that step, (b) the ACTUAL cost (method
  below), (c) cumulative spend, (d) a 3–5 line read — did compulsions fire? bind? matter? Then
  STOP.

COST TALLY (parse the run's verbose log after each run):
- Sum `usage in=<I> out=<O> [CACHE-HIT|CACHE-WRITE <C>t]` lines.
- USD = (fresh_in*3 + cache_write*3*1.25 + cache_read*3*0.1 + out*15) / 1e6 ; NZD = USD * 1.67.

STOP-THE-EXPERIMENT if: cumulative hits NZD 185; any step > 1.5x its estimate; arbiter ERROR
rate > 5% of rulings; or a gate fails. If any trip → STOP and tell me.

STEPS (depth-first; commands assume NEGOTIATION_ROUNDS=3):

0. FREEZE. Run `python _smoke_compulsion.py` (must be 18/18). Commit any uncommitted design
   changes as the design freeze (frameworks.py, design-choices.md, the plan docs) and push to
   GitHub `main`. Report done. STOP.

1a. START showcase1 (1 year) · est ~NZD 6:
   python main.py --players 6 --turns 1 --negotiation-rounds 3 --facts --verbose \
     --game-id showcase1 --frameworks utilitarian deontological retributive > sc1_y1.txt 2>&1
   GATE: `GAME OVER`; >=5 compulsion rulings; 0 ERROR rulings; actual cost <= NZD 8. STOP.

1b. EXTEND to 3 years · est ~NZD +11 (pays years 2–3 only):
   python main.py --players 6 --turns 3 --negotiation-rounds 3 --facts --verbose \
     --game-id showcase1 --frameworks utilitarian deontological retributive > sc1_y3.txt 2>&1
   Expect `[resume] showcase1: restored at ...`. GATE: binds accumulating? positions diverging
   (not a dead stalemate)? any redirect/commitment compulsion shaping who-fights-whom? STOP.

1c. EXTEND to 5 years · est ~NZD +11 — THE DECISION POINT:
   python main.py --players 6 --turns 5 --negotiation-rounds 3 --facts --verbose \
     --game-id showcase1 --frameworks utilitarian deontological retributive > sc1_y5.txt 2>&1
   GATE: does the mechanic prove consequential — binds visibly cost SCs / shape the outcome?
   Is there a narrative worth writing? Give me a full read + a recommendation on Stage 2. STOP.

2. REPLICATE (only if I say go) — two more 5-year games on different rotations, ONE AT A TIME
   with a STOP between each:
   python main.py --players 6 --turns 5 --negotiation-rounds 3 --facts --verbose \
     --game-id showcase2 --frameworks deontological retributive utilitarian > sc2_y5.txt 2>&1
   python main.py --players 6 --turns 5 --negotiation-rounds 3 --facts --verbose \
     --game-id showcase3 --frameworks retributive utilitarian deontological > sc3_y5.txt 2>&1

3+. OPTIONAL (only if I ask): breadth + blind sweeps and final analysis per EXPERIMENT-PROTOCOL.md
   Stages 3–4.

RULES: Do not deviate from the frozen design. If a run crashes, resume with the same
`--game-id`. Every game auto-writes replay logs to `logs/<game_id>.jsonl`. Start by reading
the files and running step 0, then STOP for my review.
