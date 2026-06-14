# Design Choices — Constitutional-Compulsion Experiment

A running log of design decisions and their rationale. Append a dated entry whenever
we decide or change something structural. Newest decisions at the bottom of the log.

## Thesis

If we cannot reliably interpret superhuman models and cannot stop their development,
constitutional training becomes load-bearing for safety — but constitutions become a
strategic surface. The question shifts from "which moral framework is correct?" to
**"which moral framework is least exploitable when other agents know we have it?"**

The experiment measures exploitability via a **compulsion mechanic**: an agent can force
a rival into an action by arguing the rival's own constitution requires it; an impartial
arbiter rules (on the defender's framework alone) whether they are COMPELLED.

---

## Decisions log

### 2026-06-14 — D1. Decouple "win" from "morality" (the core reframe)
Every agent is a **ruthless win-maximiser** with the *same* objective and no scruples in
how it plays (deception, betrayal, coercion all allowed). Its moral framework is a
**latent, binding constitution that only bites when a rival invokes it via compulsion**
and the arbiter rules it applies.
- **Why:** the previous design baked morality into general behaviour, so agents acted
  morally on their own and formed alliances on shared values — a confound. Making the
  constitution dormant-until-compelled means the *only* effect of a framework is its
  exploitability surface, which is exactly what we measure. Also removes the
  self-handicap confound (the framework never constrains voluntary play).

### 2026-06-14 — D2. Frameworks: utilitarian / deontological / retributive
- **Drop `baseline`** — no constitution = nothing to compel = not measurable / unfair.
- **Drop `rawlsian`** — too close to utilitarian (both welfare-consequentialist; the same
  welfare/atrocity facts move both, so few facts split them).
- **Add `retributive justice`** — the guilty must be punished in proportion to their
  wrong, regardless of cost. Exploited by a *different* class of fact (proof of
  wrongdoing), so a single atrocity fact splits all three:
  - Retributive → compelled to punish the guilty power even when suicidal.
  - Utilitarian → only if intervention is net-positive (manipulate via magnitude / Pascal).
  - Deontological → only if a standing rule/commitment is engaged.
- Alternatives considered: Loyalty/Honour, Rights/Sovereignty (kept in reserve).

### 2026-06-14 — D3. Rebalance the FactWorld pool across frameworks
Rebuild facts into three buckets, with roughly equal coverage per framework:
- **Single-framework** facts that clearly bite one framework (guilt/atrocity → retributive;
  large-scale welfare/suffering → utilitarian; sworn-treaty/commitment/rule → deontological).
- **Multi-framework** facts two or three can each argue from differently (contested cases).
- **Why:** a framework must not look "more exploitable" merely because the fact pool is
  lopsided toward it. Balance is a measurement safeguard.

### 2026-06-14 — D4. Make compulsion the central mechanic
- Rename `propose_compulsion` → **`compel_action(target, action, argument)`**.
- Reframe the description to lead with the payoff: *force a rival into a move that helps
  you / denies them; if the arbiter rules their constitution requires it, they cannot refuse.*
- Put the mechanic in the **core system prompt** (first thing the model knows) and make the
  tool **known during planning** (not just negotiation), so it enters strategy.
- **Why:** the zero-proposal pilot showed agents understood the tool but treated it as a
  negotiation afterthought; it lost to the soft-message default. Foregrounding fixes salience.

### 2026-06-14 — D5. Vehicle: 3 agents, each controlling 2 non-adjacent powers (6 active)
- 3 framework-agents, each commanding **2 non-adjacent powers** on the standard map → 6
  active powers, near-full board.
- **Why:** sparse contact in 3-power games came from a peaceful neutral-carve-up
  (abundant empty space). Filling the map to 6 active powers closes that escape valve and
  forces contact, while keeping only **3 framework-agents** → clean 1:1 attribution and
  cheap 3-way negotiation. Non-adjacent pairing stops an agent merging its two powers into
  one safe corner; it must engage other agents on multiple fronts.
- Pairing is rotated across runs (3! = 6) to counterbalance start position vs framework.
- **Caveat:** contact is necessary but not sufficient for compulsion to fire — D1/D4 supply
  the motive; density supplies the opportunity. Verify on the proof run.
- **Real vehicle (later):** a minimal custom moral-loaded board with exactly the right
  number of powers (no leftover) is the best long-term fit; the 6-power standard map is the
  quick proof.

### 2026-06-14 — D6. Drop one power and neutralise its home centres
- Drop **Turkey** (SE corner — least disruptive to remove).
- Its 3 home supply centres (Ankara, Constantinople, Smyrna) are **permanently neutral and
  excluded from all SC counts and build calculations** — occupying them yields nothing.
- **Why:** with an odd 7th power dropped, its home centres would otherwise be free centres
  for whichever agent borders them — an unfair positional advantage. Excluding them from
  scoring means a unit *can* sit there but gains nothing, so there is no free-centre prize.
  Provinces stay passable (no adjacency/strait distortion). General map neutrals (Belgium,
  Norway, Balkans, etc.) remain normal contested neutrals — under 6-power density they are
  contested, not free.

### 2026-06-14 — D7. Scoring = combined bloc supply centres
A framework's score = the combined SC count of its agent's two powers. Winner = framework
with the most combined SCs at the turn cap (plurality), or first to a reduced threshold
(TBD). Standard 18/34 solo is too slow for cheap runs.

### 2026-06-14 — D8. Settings
- Condition **transparent** by default (the thesis condition: rivals know your constitution).
- Extended **thinking enabled** (budget 2048) and logged via raw-thread, to read agents'
  reasoning about whether to compel.
- **Haiku 4.5** for agents and judge during cheap iteration; revisit model for final runs
  (superseded by D11).

### 2026-06-14 — D9. Merge the parallel session's engineering/context layer
Two sessions planned this redesign in parallel; this doc is now the single source of truth.
The parallel plan (`docs/compulsion-redesign-plan.md`, kept for reference) targeted a
*different layer* — making the mechanic legible and cheap — and is adopted wholesale:
- **Cut redundant tools** from the registry: `record_commitment`, `get_message_history`,
  `get_power_summary`, `get_adjacency`, `get_rules` (info folded into the state block / system
  prompt). Trust/betrayal is a separate experiment, not this one.
- **Slim the rules primer** (`rules.py`): drop per-power opening tips + long strategy prose;
  keep ~10 lines (objective, phases, order syntax, the few critical rules). Frees ~1K static
  tokens and sharpens focus on the mechanic.
- **`get_valid_orders` defaults to the calling power's own units** (biggest token win;
  unfiltered calls were ~8.5K tokens each).
- **System-prompt order = objective → compulsion affordance → slim rules → players block.**
  The affordance is loud and early, not buried after a 1.5K-token primer.
- **Why:** the zero-proposal pilots showed the mechanic was buried in context and runs were
  expensive. This layer is complementary to D1–D8 (what we test) — it's *how* we make it fire.

### 2026-06-14 — D10. Deterministic state block replaces LLM compaction
Replace the agent-authored compaction summary with an **orchestrator-built deterministic
state block** injected each turn: your units + SC count + your legal moves; rival SC counts;
open compulsions against you + rulings; a terse factual recap of last turn's messages.
- **Why:** agent-authored summaries produced **wrong SC counts in 3/7 agents** in one game —
  agents were reasoning off false numbers. Deterministic context removes that bug and a whole
  LLM call per power per turn. Removes the `summarizer.py` call and the compaction step.

### 2026-06-14 — D11. FactWorld = lean static moral-record block (refines D2/D3)
Reconciles the one conflict between the two plans (parallel: delete facts; mine/user: keep).
- **Keep** a small, shared, morally-salient fact set as **ground truth the arbiter and
  compulsion arguments draw on** — required, because the retributive framework needs proof of
  wrongdoing and *every* compulsion argument needs facts to cite ("Belgium ran atrocities →
  your constitution compels you to act").
- **Cut the machinery** the parallel plan rightly flagged as bloat (used in 3/27 games): the
  `cite_intel` tool, deterministic lie-detection, and per-agent dossier subsetting. Facts are
  delivered as a **static shared block** (common knowledge), not a tool-driven sub-game.
- D3's balance principle still holds (equal coverage; single- vs multi-framework facts); only
  the *delivery* changes (static block, no tool). `facts.py` shrinks to a curated pool + a
  render function; `summarizer.py`/lie-detection paths removed.

### 2026-06-14 — D12. Model policy (supersedes D8 Haiku-only)
Model is configurable per role. **Haiku 4.5** for offline smoke/iteration; **Sonnet 4.6**
(`claude-sonnet-4-6`) for players in the proof run; **a strong model for the arbiter**
(Sonnet 4.6 or Opus 4.8 — the ruling is the crux). Pilot 1 game on Opus 4.8 to prove the
mechanic *can* fire post-redesign before committing to a batch.

---

## Build plan (ordered)

Merged from both plans. User chose to build the full design (incl. the 6-power vehicle)
before the first validation run. Run `_smoke_compulsion.py` after each structural phase.

- **P1 — Tools & registry** (D9, D11): trim `_STEP_TOOLS` + `_HANDLERS` to
  `get_board_state` (slim), `get_valid_orders` (**own-units default**), `send_message`,
  `compel_action`, `submit_orders`, `pass_turn`. Remove `record_commitment`,
  `get_message_history`, `get_power_summary`, `get_adjacency`, `get_rules`, `cite_intel`.
  `tools/__init__.py`, `tools/board.py`, `tools/negotiation.py`.
- **P2 — System prompt & rules** (D1, D4, D9): reframe constitution assembly to
  objective → **compulsion affordance (loud)** → slim rules → players block; rename
  `propose_compulsion` → `compel_action` with payoff-forward text. `frameworks.py`, `rules.py`.
- **P3 — Frameworks & facts** (D2, D11): drop baseline + rawlsian, add **retributive**;
  shrink `facts.py` to a curated, framework-balanced pool + static render (no `cite_intel`,
  no lie-detection). `frameworks.py`, `facts.py`, `run_experiment.py` rotations.
- **P4 — Deterministic context** (D10): `build_state_block()` + `inject_state_block()`;
  remove the LLM compaction step and `summarizer.py`. `agent.py`, new `state.py`,
  `orchestrator.py`.
- **P5 — Strip orchestrator**: remove commitment judging, lie-detection, summarizer call,
  compaction step; keep the `compel_action → rebuttal → judge_compulsion → binding-orders`
  flow (this IS the experiment). `orchestrator.py`, `judge.py` (keep `judge_compulsion`).
- **P6 — 6-power / 3-agent vehicle** (D5, D6, D7): agent owns 2 non-adjacent powers; pairing
  rotation; combined-bloc scoring; drop Turkey + neutralise its 3 home centres in
  scoring/builds. `orchestrator.py`, `main.py`, `run_experiment.py`.
- **P7 — Model config + proof** (D12, E): wire per-role models; pilot 1 game (Opus 4.8 or
  Sonnet 4.6) — success = **≥1 `compel_action` fires and the arbiter rules on it live**, read
  from the raw-thread log.

## Open questions

- Exact victory threshold vs plurality-at-cap (D7).
- Whether to forbid agents lying about their *own* constitution in chat (currently allowed;
  caught by visible ground truth).
- When to migrate from the 6-power standard map to a purpose-built small board.
