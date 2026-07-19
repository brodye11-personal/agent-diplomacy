# Experiment spend plan — constitutional-compulsion Diplomacy

_Written 2026-06-21. Budget: NZD 100–250 (≈ USD 60–150). Goal: interesting, article-worthy
results — transcript/log insight counts, statistical significance not required._

All costs USD unless marked NZD. Per-game figures are extrapolated from real 1-round,
1–2-year runs (year 2 ran ~1.6× year 1; negotiation rounds scale super-linearly:
1→3 rounds was ~4.5×). **Treat the first game of any batch as a calibration check** — the
D31 checkpointing means you can stop mid-batch having lost nothing.

FX assumption for this doc: USD 1 ≈ NZD 1.65 (adjust to the live rate before committing).

---

## What you already own at $0 (the backbone of the article)

Do not re-run anything to get these — they're already in `design-choices.md` + the logs:

- **The debugging arc** (D19→D25): 0% compulsions → found a real rebuttal-drop bug →
  isolated the "specificity gap" (constitutions state duties, not specific moves) → rubric
  redesign → mechanic now binds. A methods narrative in itself.
- **The demand-shape taxonomy** (D23): compulsions bind when they're **prohibitive**
  ("you may not aid the guilty"), **commitment-anchored** (citing the target's own stated
  promise), or the **only causally-effective move** — and fail as vague positive mandates.
- **The judge-sensitivity finding** (D30): "utilitarian is least exploitable" is
  judge-invariant; absolute rates and the ret-vs-deon order are not (Cohen's kappa ≈ 0–0.2
  across Sonnet / Haiku / gpt-4o-mini).
- **Qualitative gems**: Germany conceding a compulsion then playing the move voluntarily;
  the arbiter voiding a new demand by citing a *prior* compelled order on the same unit.

## Current best numeric result (6-rotation pilot, 1yr/1round, all on the 28-fact pool)

| Target framework | COMPELLED rate |
|---|---|
| Retributive | 7/19 (37%) |
| Deontological | 3/17 (18%) |
| Utilitarian | 2/20 (10%) |

Descriptive only (n≈17–20 per framework, 1 game per rotation). Pilot cost: ~$7.9.

---

## The plan — priorities in spend order

### Priority 1 — Realistic-scope transparent pass (THE core spend)
- **Settings:** 6 rotations × `--turns 3` × `--negotiation-rounds 2`, transparent, facts on.
- **Buys what the pilot can't:** 3 years lets binds have downstream SC consequences and lets
  agents **adapt** (stop making commitments after being burned? retaliate? phrase promises
  evasively?) — adaptation dynamics live in transcripts and are the "insight-without-
  significance" material. 2 rounds is required for commitment-trap compulsions (the strongest
  deontological exploit) to occur at all.
- **Est. cost:** ~$52–70 (**NZD ~85–115**). 6 games × ~$8.5–11.5.
- **Extensible (D31):** run at 3 years; if promising, continue the SAME games to 5 without
  re-paying years 1–3 (see "How to extend" below).

### Priority 2 — Blind-condition games (the article's headline contrast)
- **Settings:** 3 games, same scope, `--condition blind` (rivals' constitutions hidden).
- **Buys:** the general-audience hook — "we published the agents' ethics and watched rivals
  weaponise them" needs the blind baseline to contrast. Zero data on this condition today.
  Expect entertaining transcripts of agents guessing at hidden constitutions.
- **Est. cost:** ~$25–35 (**NZD ~40–55**).

### Priority 3 — Dual-judge every new ruling with gpt-4o-mini
- Turns the D30 judge-sensitivity caveat into a robustness footnote. Re-judge offline from
  logs (like `_second_judge.py`), no new games.
- **Est. cost:** ~$1–2 (**NZD ~2–3**).

### Priority 4 (only if budget remains) — One Opus 4.8 "exhibition game"
- **Settings:** 1 game, `--model anthropic/claude-opus-4.8`, 3yr/2round, read deeply.
- **Buys:** the "what does *skilled* exploitation look like" centerpiece — D20 showed Opus
  fires multiple adjacency-perfect compulsions per round. One richly-annotated transcript.
- **Est. cost:** ~$20–35 (**NZD ~35–55**).

### Budget roll-up
| Bundle | USD | NZD |
|---|---|---|
| P1 + P2 + P3 | ~$78–107 | **~130–175** |
| P1 + P2 + P3 + P4 | ~$98–142 | **~165–225** |
| Low-budget variant: P1 at 2yr/2round + P2 + P3 | ~$50–70 | **~85–115** |

---

## Before spending: two decisions + one optional build

1. **Design freeze (recommended).** The rubric (v2) and 28-fact pool were tuned this session
   *to produce* differentiation — a reviewer will call that a garden-of-forking-paths risk.
   Declare everything so far exploratory/pilot, freeze rubric+facts+affordance, write the
   analysis plan down, and run the paid batch on the frozen design. The rubric-v1-vs-v2 story
   then becomes a methods *finding*, not a liability.
2. **Affordance symmetry.** Decide whether to teach the bindable-shapes recipe to **all**
   agents or **none** — either is defensible; asymmetric is not. Apply, then freeze.
3. **Optional viewer-logging build (MUST land before the paid batch if you want it).** Logs
   are already good for a message/compulsion/thinking click-through with pins. For a
   board-map replay they need: (a) log retreat/adjust phases (currently only movement is
   logged), (b) dump `game.get_state()` per phase. Small, behaviour-neutral — but can't be
   retrofitted onto games already played, so it must go in first.

---

## How to run

**One rotation (main.py), crash-safe + extensible:**
```
python main.py --players 6 --turns 3 --negotiation-rounds 2 --facts --verbose \
  --frameworks utilitarian deontological retributive --game-id run_r1 > run_r1.txt 2>&1
```
`--frameworks` maps to (ENG+AUS, FRA+RUS, GER+ITA). The 6 rotations are the 6 permutations
of `utilitarian deontological retributive`.

**Full batch (run_experiment.py) — does all 6 rotations, crash-safe:**
```
python run_experiment.py --players 6 --runs 6 --turns 3 --negotiation-rounds 2 \
  --condition transparent --facts --verbose
```
(`--condition` now defaults to transparent only, D27. Add `blind` for Priority 2.)

**How to EXTEND a promising game to more years (D31):** re-run the SAME command with a
higher `--turns`. Years already played are NOT re-billed.
```
# later, if results look good:
python main.py ... --game-id run_r1 --turns 5   # continues run_r1 from year 3 into 4–5
# batch equivalent:
python run_experiment.py ... --turns 5 --resume <EXP_ID>
```

**Recover after a crash:** re-run the identical command (main.py) or
`python run_experiment.py --resume <EXP_ID>`. A crash costs at most one in-flight phase.

**Cleanup when a batch is truly done (cap-stopped games retain checkpoints, D31):**
```
rm logs/*.checkpoint.json
```

---

## Analysis (from logs, $0)

- Pooled bind rate by target framework, per rotation and per demand-shape:
  `_analyze_6_rotations.py` (repoint `ROTATION_LOGS` at the new logs).
- Judge robustness: `_second_judge.py` + `_judge_framework_rates.py`.
- Report at the **ruling level with game-level clustering** (≈10 rulings/game are NOT
  independent — pooling them as if they were is pseudoreplication a reviewer will flag).
- Separate **forced** binds (target rebutted and lost) from **conceded** binds (target
  agreed) — a bind the target wanted costs nothing and isn't exploitation.
