# Experiment protocol — constitutional compulsion (staged, budget-gated, DEPTH-FIRST)

_Written 2026-06-21. Runbook for the paid batch. Companion to `SPEND-PLAN.md` (rationale)
and `design-choices.md` (decisions). Every stage has a GO/NO-GO gate: a problem surfaces at
a few dollars, not at the full budget._

## Approach (updated 2026-06-21 — DEPTH-FIRST)

Earlier drafts led with the breadth claim ("some frameworks are more exploitable than
others"). Decision: **go depth-first** — the pilots showed 1-year games end in consequence-
free near-ties, and the more compelling (and honest) question is **can exploiting a rival's
moral constitution actually WIN over a full game** — do binds accumulate, redirect
alliances, force losses, provoke adaptation? That story lives in a few *deep* (5-year) games,
read closely.

- **Primary (depth):** does the compulsion mechanic prove *consequential* over a full game?
  (Mechanism + narrative + transcripts.) One game built to 5 years is the core bet.
- **Secondary (supported-if-it-emerges):** *differential* exploitability — do
  retributive/deon/util differ in bind rate? Because we run the few deep games on DIFFERENT
  rotations (each framework in different board seats), we get a cross-position read that can
  *gesture* at the ordering — but this is not the powered-breadth version, and we say so.
- **Untested assumption being tested:** nobody has run a full game; whether depth delivers
  drama or fizzles (contact drops as blocs consolidate) is exactly what Stage 1 buys.

## Budget & stop rules

- **Hard ceiling: NZD 200 (≈ USD 120 @ 0.60).** Planned core spend lands ~NZD 75; with the
  optional breadth/blind add-on ~NZD 118. The rest is buffer for re-runs.
- **STOP immediately if:** cumulative hits **NZD 185**, OR any stage's actual cost is **>1.5×
  its estimate** (economics off — recompute), OR arbiter error rate exceeds ~5% of rulings,
  OR a stage gate fails.
- Every run is crash-safe (D29) and extensible (D31): a run that dies resumes with the same
  `--game-id`; a capped game continues to more years with a higher `--turns`, never re-paying
  played years.

## Frozen design (locked before Stage 1 — do not change mid-batch)

- **Vehicle:** 6 powers / 3 blocs of 2 non-adjacent powers, Turkey neutralised (D5/D6).
- **Arbiter:** `COMPULSION_RUBRIC` v2 (D25), temperature 0 (D24).
- **Facts:** the 28-fact pool (D26).
- **Affordance (D33):** agents are told compel_action is a primary lever AND to compel only
  moves that genuinely advance their bloc ("would you want this order even if you couldn't
  force it?"). They are **NOT** coached on which demand shapes bind best — the demand-shape
  taxonomy (prohibitive > commitment-anchored > positive-mandate) stays an **emergent
  finding**. The D33 strategic-payoff gate is not recipe-coaching: it asks agents to play
  rationally, doesn't touch which frameworks the arbiter finds exploitable.
- **Models:** Sonnet 4.6 agents + Sonnet 4.6 live arbiter; gpt-4o-mini as offline second judge.
- **Negotiation rounds: 2** (the fair-test floor). _Lever: bump the showcase games to **3**
  for richer negotiation + more commitment-anchored compulsions — decide BEFORE Stage 1a, as
  it locks when the game starts (you extend the same game). 3 rounds ≈ 1.5–2× the cost._
- **Board/replay logging (D32):** on — every game is viewer-ready.

## Hypotheses & analysis

- **H1 (primary, depth):** exploiting a rival's constitution is a *consequential* lever —
  binds accumulate and affect the game. **DV:** in the 5-year games, bind-received count vs
  final bloc SC; transcript evidence of redirects reshaping alliances and of agents adapting
  (ceasing exploitable commitments / retaliating) after being compelled. Case-study +
  few-game; reported with transcripts, not significance.
- **H2 (secondary, supported-if-it-emerges):** frameworks differ in exploitability = bind
  rate per target-framework across the deep rotations. Cross-position (each framework in
  different seats) but n small — directional, robustness-checked with the gpt-4o-mini second
  judge. **Utilitarian-least-exploitable is the pre-specified judge-invariant sub-claim.**
- **H3 (optional, only if Stage 3 runs):** transparency raises exploitation (blind vs
  transparent attempt + bind rate).
- **Logged per bind:** forced (rebutted & lost) vs conceded; voluntary compliance with
  NOT-ruled demands (a bind that costs nothing ≠ exploitation).

---

## Stage ladder (depth-first)

Costs NZD. Basis: 1yr/2rd ≈ NZD 4; each extra year ≈ +NZD 4 (at 2 rounds). The staged
year-by-year extend means the *actual* cost is measured as you go — the gates, not the
estimates, control spend.

### Stage 0 — Freeze + prep (NZD 0)
1. Confirm the affordance is the D33 version (strategic-payoff gate) and the round count (2,
   or 3 for richer showcase — locks at Stage 1a).
2. Append a design-FREEZE marker to `design-choices.md` (locks D25/D26/D33; labels prior runs
   exploratory).
3. `python _smoke_compulsion.py` → 18/18.
4. Board/replay logging (D32) — already in.
- **GATE:** smoke passes; freeze logged. → proceed.

### Stage 1 — Build ONE showcase game to 5 years, gated at each step ← THE CORE BET
Same `--game-id showcase1` throughout; each step resumes the previous via D31 and pays only
for the new years.

**1a — Start + calibrate (1 year) · NZD ~4 · cum ~4  ← THE FAIL-CHEAP GATE**
```
python main.py --players 6 --turns 1 --negotiation-rounds 2 --facts --verbose \
  --game-id showcase1 --frameworks utilitarian deontological retributive > sc1_y1.txt 2>&1
```
- **GATE:** `GAME OVER`; ≥5 compulsion rulings; 0 ERROR; **actual cost ≤ NZD 6** (parse
  `sc1_y1.txt`). If cost > NZD 6 → STOP, recompute (economics differ). This one game proves
  the mechanic + economics before any depth spend.

**1b — Extend to 3 years · NZD ~+8 · cum ~12**
```
python main.py --players 6 --turns 3 --negotiation-rounds 2 --facts --verbose \
  --game-id showcase1 --frameworks utilitarian deontological retributive > sc1_y3.txt 2>&1
```
- Expect `[resume] showcase1: restored at ...` and only years 2–3 billed.
- **GATE (read it):** are binds accumulating? positions diverging (not a dead stalemate)? any
  redirect/commitment compulsion visibly shaping who-fights-whom? If it's already inert here,
  that's an early signal depth won't deliver — consider stopping before 1c.

**1c — Extend to 5 years · NZD ~+12 · cum ~24  ← THE DECISION POINT**
```
python main.py --players 6 --turns 5 --negotiation-rounds 2 --facts --verbose \
  --game-id showcase1 --frameworks utilitarian deontological retributive > sc1_y5.txt 2>&1
```
- **GATE — the whole bet:** does the mechanic prove *consequential*? Do binds visibly cost
  SCs / shape the outcome? Is there a narrative worth writing (a redirect that flips a front,
  an agent adapting after being burned)?
  - **Compelling** → Stage 2 (replicate across rotations).
  - **Fizzles** (binds inert, contact drops, normal tactics dominate) → you learned it for
    ~NZD 24. Pivot to the breadth ladder (in git history / `SPEND-PLAN.md`) or stop.

### Stage 2 — Replicate depth across rotations (only if 1c compelling) · NZD ~+50 · cum ~74
Two more games built straight to 5 years on DIFFERENT rotations, so each framework sits in
new board seats (narrative robustness + the cross-position differential read for H2):
```
python main.py --players 6 --turns 5 --negotiation-rounds 2 --facts --verbose \
  --game-id showcase2 --frameworks deontological retributive utilitarian > sc2_y5.txt 2>&1
python main.py --players 6 --turns 5 --negotiation-rounds 2 --facts --verbose \
  --game-id showcase3 --frameworks retributive utilitarian deontological > sc3_y5.txt 2>&1
```
- **GATE:** both complete; you now have 3 deep games, each framework seen in ≥2 seats.

### Stage 3 — OPTIONAL breadth + blind (only if budget/interest remains) · NZD ~+44 · cum ~118
For a firmer H2 rate and the H3 transparency contrast — a quick 1-year rotation sweep and a
blind sweep:
```
python run_experiment.py --players 6 --runs 6 --condition transparent --turns 1 \
  --negotiation-rounds 2 --facts --verbose > breadth.txt 2>&1
python run_experiment.py --players 6 --runs 6 --condition blind --turns 1 \
  --negotiation-rounds 2 --facts --verbose > blind.txt 2>&1
```
- **GATE:** completes; adds ~120 rulings (H2) + the blind contrast (H3).

### Stage 4 — Final analysis · NZD ~+4
- Depth read: per-game bind timelines, redirect/adaptation transcripts, bind-vs-SC.
- Second-judge pass (`_second_judge.py`) over all rulings; per-framework tables with the
  judge-robustness note; forced-vs-conceded split.
- Write results into `design-choices.md` / a results file, exploratory-vs-confirmatory
  labels intact.

---

## If something breaks
- Run crashes / laptop dies → re-run same `--game-id` (single) or `--resume <EXP_ID>` (batch).
- Arbiter JSON errors climbing → isolated as ERROR (not counted as NOT); if >5%, STOP and
  harden `judge.py` JSON parse first.
- Costs drifting high → the Stage-1a gate should catch it; if not, stop at the next stage
  boundary and recompute.
- Depth fizzles → not a failure, it's a result; the breadth ladder is the documented fallback.
