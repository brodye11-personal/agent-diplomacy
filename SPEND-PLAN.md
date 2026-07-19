# Spend plan — constitutional-compulsion experiment

_Written 2026-06-21. Companion to `design-choices.md` (the decisions log). This file is the
budget/execution plan; put design rationale in design-choices.md._

## Budget

- **NZD 100–250** available (≈ **USD 60–150** at ~0.60 NZD→USD).
- Reality check from measured runs: a game costs **~USD 1.3 (1yr/1round) → ~2.2 (1yr/2round)
  → ~6 (3yr/2round)**, Sonnet 4.6 for agents + judge. **The budget is not the binding
  constraint** — it comfortably funds a properly-powered core batch _plus_ showcase games
  _plus_ a blind control. The binding constraints are (a) design-freeze discipline and
  (b) statistical structure, not dollars.

## The core thesis (what the spend must protect)

**Which moral framework is least exploitable when rivals know it** — measured at the
**ruling level**: the per-framework `compel_action` bind rate in the `transparent`
condition. NOT primarily "does the least-exploitable framework win games" (that is the
_secondary_ question).

## Cost anatomy (measured, `_cost_anatomy.py`, 6 pilot games, movement phases)

| Step | % of API calls | % of output tokens | thinking as % of its output |
|---|---|---|---|
| negotiation | 47% | **55%** | 70% |
| arbitration | 14% | **25%** | 55% |
| orders | 14% | 12% | 81% |
| planning | 25% | 8% | 53% |

- **Output tokens dominate cost** (5× input price, and uncacheable; input is mostly
  cache-reads at 0.1×). Negotiation + arbitration = **80% of output**.
- **Extended thinking is the single largest cost component** — 53–81% of output at every
  step. Budget is currently `THINKING_BUDGET_TOKENS = 2048` (floor is 1024).

## How to make it cheaper WITHOUT sacrificing the core thesis

Ranked. The first is the big one and is thesis-_positive_.

1. **Trade game-YEARS for game-COUNT (biggest lever).** The core thesis is priced in
   rulings, and rulings are front-loaded: ~10 rulings/game land in year 1 alone, and
   rulings/year plateaus as blocs consolidate. Cost scales ~linearly with phases (≈years).
   So **N short games beats N/3 long games** on rulings-per-dollar _and_ gives more
   independent game-clusters (better stats — pooling proposals within a game is
   pseudoreplication). Years mainly buy the _secondary_ consequence question + narrative.

2. **Run short, then EXTEND only the interesting games (D31 — already built).** Don't
   choose short-vs-long upfront. Run the whole batch at **1 year** (cheap, maximal rulings),
   inspect, then continue only the 2–4 most interesting games to 3–5 years with the same
   `--game-id` + higher `--turns`. You never pay for a long game that turns out boring.
   **This is the optimal cost strategy and it already works** (soft year-cap retains the
   checkpoint; only a true game-over clears it).

3. **Step-differentiated thinking (test-first, ~10% saving, thesis-safe).** Planning +
   orders are 20% of output but don't affect the compel _measurement_. Keep full thinking on
   negotiation + arbitration (where argument/rebuttal quality _is_ the instrument); reduce or
   disable it on planning + orders. A/B one game before trusting.

4. **Thinking budget 2048→1024 (test-first, ~10–15% saving, RISKIER).** Cuts the dominant
   component everywhere, but may degrade the arguments/rebuttals that _are_ the thesis. Only
   after an A/B shows rulings unchanged.

### Do NOT do these (they bias the measurement)

- **Don't drop below 2 negotiation rounds.** Commitment-anchored compulsions (the strongest
  _deontological_ exploit) barely occur at 1 round, so 1-round runs under-measure deon. **2
  rounds is the floor for a fair core-thesis test.** (1-round pilots were fine for wiring
  validation, not for the headline.)
- **Don't cut `send_message` chatter** — it builds the commitments deon exploits rely on;
  cutting it biases deon exploitability down.
- **Don't weaken the arbiter model** — it is the measurement instrument, and it's already
  cheap (short one-shot calls). D30 showed rulings are model-sensitive.

## Recommended allocation (targets ~NZD 175 / USD ~105; scales to the range)

All games: 6-power vehicle, `--facts`, Sonnet 4.6, **2 negotiation rounds**, dual-judge
every ruling (Sonnet live + gpt-4o-mini offline re-judge, ~USD 2 total — turns D30's
judge-sensitivity caveat into a robustness footnote).

| Tier | Config | Games | ~USD | Buys |
|---|---|---|---|---|
| **A. Core exploitability** | transparent, **1yr**/2rd | 18 (3 rotation sweeps) | ~40 | ~250+ rulings, 18 clusters — the headline per-framework bind rates |
| **B. Consequence + narrative** | **extend 2–4** of A's games to 3–5yr (D31) | 3 | ~18 | does exploitability→losing; rich transcripts for the article/viewer |
| **C. Transparency control** | **blind**, 1yr/2rd | 6 | ~13 | the transparent-vs-blind contrast (the general-audience hook) |
| Dual-judge overhead | — | — | ~2 | judge-robustness |
| **Total** | | | **~USD 73 ≈ NZD 122** | leaves headroom |

- **Low end (NZD 100):** drop C to 3 blind games, keep A at 12. Still a clean design.
- **High end (NZD 250):** double A to 36 games (~USD 40 more) → ~500 rulings, genuinely
  approaching powered significance for a large effect.

## Commands (batch runner is crash-safe + resumable, D29)

```powershell
# Tier A — core, 3 rotation sweeps (18 games), transparent, 1yr, 2 rounds
python run_experiment.py --players 6 --runs 18 --condition transparent `
  --turns 1 --negotiation-rounds 2 --facts

# Tier C — blind control, 6 games
python run_experiment.py --players 6 --runs 6 --condition blind `
  --turns 1 --negotiation-rounds 2 --facts

# Tier B — after inspecting A, extend chosen games (same game_id, higher --turns).
#   game_id form is "<exp>-<condition>-<run_index>"; resume=True is automatic in run_experiment.
#   For a one-off extend via main.py: python main.py --game-id <id> --turns 4 --frameworks <same three> ...

# If a run crashes / laptop dies: re-run with --resume <EXP_ID> (skips done games, resumes the interrupted one).
```

## Prerequisites BEFORE spending (decisions needed)

1. **Design freeze.** Lock rubric v2 (D25), the 28-fact pool (D26), and the affordance text;
   label everything so far as exploratory/pilot; write the analysis plan down before the
   batch. (Reviewer-critical — the tuning history is otherwise a "forking paths" objection.)
   - _Open decision:_ teach the bindable-shape recipe (prohibitive > commitment-anchored >
     positive-mandate) to **all** agents, or **none** — then freeze. Symmetric either way.
2. **Viewer board-logging (only if you want the click-through game viewer).** R/A phases are
   currently unlogged and there's no per-phase board snapshot — a small, behaviour-neutral
   logging addition. **Must land before the batch; cannot be retrofitted onto played games.**
3. **(Optional) step-differentiated thinking** — the ~10% thesis-safe saving from lever 3,
   if you want it; A/B one game first.

## Status of enabling infrastructure (all built + verified)

- Crash-safe checkpoint/resume (D29) — live crash-test passed (D30).
- Extensible games / run-1-then-continue (D31) — verified in code.
- Per-ruling logging, error isolation, temp-0 arbiter (D24).
- Corrected 6-rotation pilot on the current pool (D30): **retributive 37% > deontological
  18% > utilitarian 10%** bind rate; utilitarian-least-exploitable is **judge-invariant**.
