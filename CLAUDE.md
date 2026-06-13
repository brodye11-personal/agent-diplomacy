# code-diplomacy — agent instructions

This repo is the **constitutional-compulsion experiment**: LLM agents play a Diplomacy-based
game where each agent is a ruthless win-maximiser bound by a latent moral constitution that
only binds when a rival forces it via the `compel_action` mechanic and an arbiter rules it
applies. The experiment measures **which moral framework is least exploitable when rivals
know it**.

## MANDATORY: keep `design-choices.md` current

`design-choices.md` is the running decisions log and the source of truth for the
experiment's design. **Whenever you plan or make a structural design change** (frameworks,
facts, the compulsion mechanic, scoring, player/board setup, prompts, conditions), you MUST
append a dated entry to `design-choices.md` — the decision **and its rationale** — as part
of the same change, before considering the task done. Do not make a design change without
recording it. If a decision reverses an earlier one, note which entry it supersedes.

## Orientation

- `design-choices.md` — decisions log + current build plan (read this first).
- `docs/PIVOT-constitutional-compulsion.md` — the original pivot spec.
- Core code: `orchestrator.py` (game loop), `agent.py` (per-power thread), `frameworks.py`
  (constitutions), `facts.py` (FactWorld), `judge.py` (commitment + compulsion arbiter),
  `tools/` (tool registry), `logger.py`.

## Conventions

- Verify wiring offline with `_smoke_compulsion.py` before spending on live runs.
- Live runs cost money — estimate and state cost before running; prefer Haiku for iteration.
