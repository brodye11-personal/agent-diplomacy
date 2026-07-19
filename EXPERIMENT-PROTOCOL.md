# Experiment protocol — constitutional compulsion (staged, budget-gated)

_Written 2026-06-21. Runbook for the paid batch. Companion to `SPEND-PLAN.md` (rationale)
and `design-choices.md` (decisions). Every stage has a GO/NO-GO gate: a problem surfaces at
a few dollars, not at the full budget._

## Headline claim (LOCKED 2026-06-21)

**"Some moral frameworks are more exploitable than others (when rivals know the
constitution)."** This is a *differential* claim, so **breadth is the spend priority**: the
claim's credibility rests on the retributive > deontological > utilitarian ordering being
**stable across many independent games with the framework→position rotation counterbalanced**
— NOT on any single deep game (one game can't separate framework from starting position, and
gives ~3 rulings/framework = noise). Significance is not required (this is a descriptive,
transcript-supported claim per Brodie), but the ordering must clearly not be 6-game noise.
Deep multi-year games serve the *secondary* narrative/consequence story (H2), not the headline
— so they come AFTER the breadth core is banked, and stay few.

## Budget & stop rules

- **Hard ceiling: NZD 200 (≈ USD 120 @ 0.60).** Planned spend lands ~NZD 116–138 (breadth-
  first: 18-game core, optional 24–30 if the ordering is wobbly, blind control, 2 narrative
  extends); the rest is buffer for re-runs.
- **STOP immediately if:** cumulative hits **NZD 185**, OR any stage's actual cost is **>1.5×
  its estimate** (economics are off — recompute before continuing), OR the arbiter error rate
  exceeds ~5% of rulings, OR a stage gate fails (see each stage).
- Every run is crash-safe (D29): if a run dies, resume with `--resume <EXP_ID>` — no
  re-paying played games.

## Frozen design (locked before Stage 1 — do not change mid-batch)

- **Vehicle:** 6 powers / 3 blocs of 2 non-adjacent powers, Turkey neutralised (D5/D6).
- **Arbiter:** `COMPULSION_RUBRIC` v2 (D25), temperature 0 (D24).
- **Facts:** the 28-fact pool (D26).
- **Affordance:** frozen AS-IS — agents are told compel_action is a primary lever and to look
  for an opportunity each turn, but are **NOT** coached on which demand shapes bind best.
  → The demand-shape taxonomy (prohibitive > commitment-anchored > positive-mandate) is
  reported as an **emergent finding**, not an instruction. This is the cleaner scientific
  choice and avoids "you engineered the result." _(This is the one open call from SPEND-PLAN;
  default = do not coach. Change only by explicit decision, before Stage 1.)_
- **Models:** Sonnet 4.6 agents + Sonnet 4.6 live arbiter; gpt-4o-mini as offline second judge.
- **Negotiation rounds: 2** (the fair-test floor — 1 round under-measures deontological
  exploitability).

## Hypotheses & pre-registered analysis

- **H1 (core, confirmatory):** frameworks differ in exploitability = per-framework
  `compel_action` bind rate under `transparent`. Prediction (from pilot): retributive >
  deontological > utilitarian. **DV:** COMPELLED / total valid rulings, per target-framework.
  **Analysis:** rate + 95% CI per framework, pooled across games; game treated as the cluster
  (report n_games and n_rulings; no per-proposal significance claim without clustering).
  Robustness: re-judge all rulings with gpt-4o-mini; report agreement + whether the ordering
  holds. **Utilitarian-least-exploitable is the pre-specified judge-invariant claim.**
- **H2 (secondary, exploratory):** does higher exploitability translate to lower final bloc
  SC? **DV:** per-bloc SC in the extended (3–5yr) games; correlate bind-received count vs SC.
  Underpowered by design — reported as directional + transcript evidence.
- **H3 (contrast, exploratory):** transparency raises exploitation. **DV:** compel_action
  attempt rate + bind rate, blind vs transparent.
- **Also logged per bind:** forced (target rebutted & lost) vs conceded; and voluntary
  compliance with NOT-ruled demands (a bind that costs nothing ≠ exploitation).

---

## Stage ladder

Costs are NZD (USD in parens). Per-game measured basis: 1yr/1rd ≈ NZD 2.2; **1yr/2rd ≈ NZD
3.7 (USD 2.2)**; each extra year ≈ +NZD 3.5.

### Stage 0 — Freeze + prep (NZD 0)
1. Confirm the affordance decision above (default: no coaching).
2. Append a design-FREEZE entry to `design-choices.md` (locks D25/D26/affordance; labels all
   prior runs exploratory).
3. `python _smoke_compulsion.py` → must be 18/18.
4. _(Optional, only if you want the click-through viewer later:)_ add R/A-phase + board-state
   logging now — it **cannot** be retrofitted onto games played without it.
- **GATE:** smoke passes; freeze logged. → proceed.

### Stage 1 — Single calibration game (NZD ~4 · cum ~4) ← THE FAIL-CHEAP GATE
```
python main.py --players 6 --turns 1 --negotiation-rounds 2 --facts --verbose \
  --frameworks utilitarian deontological retributive > cal1.txt 2>&1
```
- **GATE (all must hold):** game reaches `GAME OVER`; ≥5 compulsion rulings logged; 0 ERROR
  rulings; **actual cost ≤ NZD 6** (tally: `python _cost_anatomy.py`-style parse of `cal1.txt`).
- **If cost > NZD 6:** STOP — 2-round economics differ from estimate; recompute the whole
  ladder before spending more. _This is the entire point of the staged design._

### Stage 2 — First transparent rotation sweep, 6 games (NZD ~22 · cum ~26)
```
python run_experiment.py --players 6 --runs 6 --condition transparent \
  --turns 1 --negotiation-rounds 2 --facts --verbose > sweep1.txt 2>&1
```
- Note the printed `experiment_id`.
- **GATE:** all 6 complete (manifest); per-framework bind rates computable
  (`_analyze_6_rotations.py`, repointed to these logs); dual-judge a sample
  (`_second_judge.py`) shows sane agreement; eyeball 2 transcripts for coherent
  arguments/rebuttals. Bind-rate separation is a _finding_ either way — not a gate to pass,
  just a checkpoint to read before scaling.

### Stage 3 — Scale core to 18 games — THE HEADLINE DATASET (NZD ~44 · cum ~70)
```
python run_experiment.py --players 6 --runs 18 --condition transparent \
  --turns 1 --negotiation-rounds 2 --facts --resume <EXP_ID_from_Stage2>
```
_(Same experiment_id via `--resume` reuses Stage 2's 6 games and adds 12 more; runs=18 = three
full rotation sweeps, so each framework governs each pair exactly twice — position
counterbalanced.)_
- **GATE (decides the headline):** ~250+ total rulings; is the ret > deon > util ordering
  **stable across the three sweeps** (per-sweep breakdown, not just the pool)?
  - **Ordering clean & stable** → the claim is banked at 18 games; proceed to Stage 4.
  - **Ordering promising but wobbly across sweeps** → this is the ONE place to spend more:
    **Stage 3b — expand to 24–30 games** (`--runs 24` / `30 --resume <EXP_ID>`, +NZD ~22–44).
    Breadth is where the headline claim lives, so buy it here before spending on narrative.
  - **No separation at all** → that is itself a publishable finding ("the mechanic binds but
    framework doesn't predict exploitability"); stop scaling, skip to Stage 6.

### Stage 4 — Blind control, 6 games (NZD ~22 · cum ~92, or ~114 if 3b ran)
```
python run_experiment.py --players 6 --runs 6 --condition blind \
  --turns 1 --negotiation-rounds 2 --facts --verbose > blind1.txt 2>&1
```
- **GATE:** completes; compute attempt + bind rates for H3. (Expect messier arguments — blind
  agents guess at rivals' constitutions; that's the story.)

### Stage 5 — Narrative support: extend 2 showcase games to 3–5 years (NZD ~20 · cum ~112–134)
_Secondary to the headline — for H2 + article transcripts, NOT the differential claim. Keep it
to 2 games so breadth stays the priority._ Pick the 2 most interesting transparent games (e.g.
a clean exploitation chain, or a concede-then-comply). Extend each — same `--game-id`, its own
rotation's `--frameworks`, higher `--turns`:
```
python main.py --players 6 --turns 3 --negotiation-rounds 2 --facts --verbose \
  --game-id <EXP_ID>-transparent-<run_index> \
  --frameworks <that run's three frameworks> > extend_<id>.txt 2>&1
```
_(The game resumes from its retained year-1 checkpoint (D31) and plays years 2–3 only — you
pay ~NZD 7/game, not the full 3-year cost. Rotation for run_index = FRAMEWORK_ROTATIONS[run_index % 6].)_
- **GATE:** each extends cleanly (`[resume] ... restored at`); yields H2 SC-consequence data +
  rich transcripts for the article/viewer.

### Stage 6 — Final analysis (NZD ~4 · cum ~116–138 depending on 3b/extends ≈ USD 70–83)
- Full second-judge pass over every ruling (`_second_judge.py`); final per-framework tables
  with CIs; forced-vs-conceded bind split; H2 correlation; H3 contrast.
- Write results into `design-choices.md` (or a results file) with the exploratory/confirmatory
  labels intact.

---

## Optional expansions (only if gates are green and budget remains; cum stays < NZD 185)
- **Double the core** to 36 games (`--runs 36 --resume <EXP_ID>`): +NZD ~44 → cum ~162.
  Best marginal buy — pushes H1 toward powered significance for a large effect.
- **More showcase extensions** or a 5-year extension of the single most interesting game.
- **An Opus 4.8 exhibition game** (~NZD 4): the "skilled exploitation" centerpiece transcript.

## If something breaks
- Run crashes / laptop dies → `--resume <EXP_ID>` (batch) or re-run same `--game-id` (single).
- Arbiter JSON errors climbing → they're isolated as ERROR (not counted as NOT); if >5%,
  STOP and harden `judge.py` JSON parse before continuing.
- Costs drifting high → the Stage-1 gate should have caught it; if not, stop at the next
  stage boundary and recompute.
