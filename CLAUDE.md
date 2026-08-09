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

## MANDATORY: commit every change, and check the repo before asserting a negative

**Commit as you go — one commit per coherent change, in the same turn you make it.** Do not
leave finished work sitting in the working tree waiting for a "natural" batching point.
A commit is cheap; a five-week gap is not. Committing on a feature branch is always fine
without asking. **Merging into `main` still requires Brodie's explicit OK on that specific
merge** — commit freely, merge never, unless told.

Two failures this rule exists to prevent, both of which have already happened here:

- **The mega-commit.** `fd56a43` squashed five weeks and roughly D14–D32 into one commit.
  When that happens the design log becomes the *only* history of the period — you cannot
  bisect, diff a single decision, or recover an intermediate state.
- **The stale-checkout wrong answer.** A pre-spend audit reported that decision D33 "does
  not exist" and that the frozen experiment design was a phantom, because `grep` over the
  working tree came back clean. D33 was real — decided, recorded and implemented in
  `b5855eb` — but local `main` was 5 commits behind `origin/main` and had never merged it.
  Uncommitted local edits had also been hand-copied in from those commits, which made the
  tree look internally inconsistent for a reason that had nothing to do with the design.

So, before asserting that any decision, file, fact or feature **does not exist or was never
done**: run `git fetch`, check `git log origin/main ^main` and `git status`, and search the
repository — not just the working tree. Grepping the checkout answers "is it in my files",
which is not the question. A negative claim about this experiment's design is only safe once
the checkout is known to be current.

Log data (`logs/*.jsonl`) is produced by **paid** API runs and is deliberately NOT gitignored
(see `.gitignore`). Commit new logs with the run that produced them — they are the
experiment's results, and they exist nowhere else.

## Orientation

- `design-choices.md` — decisions log + current build plan (read this first).
- `docs/PIVOT-constitutional-compulsion.md` — the original pivot spec.
- Core code: `orchestrator.py` (game loop), `agent.py` (per-power thread), `frameworks.py`
  (constitutions), `facts.py` (FactWorld), `judge.py` (commitment + compulsion arbiter),
  `tools/` (tool registry), `logger.py`.

## Conventions

- Verify wiring offline with `_smoke_compulsion.py` before spending on live runs.
- Live runs cost money — estimate and state cost before running; prefer Haiku for iteration.
- Never hardcode a low/arbitrary `max_tokens`. Look up the model's verified output
  ceiling (via the `claude-api` skill / `shared/models.md` — don't guess) and use that:
  64000 for both Haiku 4.5 and Sonnet 4.6, the two models this repo uses. A cap that's
  too low silently truncates a response mid-thought (bit us twice in one session
  picking 400/600/1200 for a free-text arbiter follow-up). At a 64000 ceiling, route the
  call through `client.messages.stream(...)` + `.get_final_message()` instead of
  `.create()` — a non-streaming call at that size risks the SDK's own ~10-minute
  timeout-estimate guard. `agent.py::_create_with_retry` and `judge.py::judge_compulsion`
  both do this already; follow the same pattern for any new call site.
