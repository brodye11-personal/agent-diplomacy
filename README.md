# Exploitability of Moral Frameworks in LLM Negotiation

**Live site:** https://exploitability-of-moral-frameworks-in-llm-negotiation.brodie-dye-11.workers.dev

A research experiment on LLM-agent Diplomacy games, testing which moral constitution is
**least exploitable when a rival knows you have it**.

## The idea

If we cannot reliably interpret superhuman models and cannot stop their development,
constitutional training becomes load-bearing for safety — but a known constitution also
becomes a strategic surface. This experiment reframes the usual "which moral framework is
correct?" question as: **which moral framework holds up best when other agents can weaponise
it against you?**

Every agent is a ruthless win-maximiser with the same objective and no scruples in how it
plays — deception, betrayal, and coercion are all fair game. Each agent also carries a
**latent moral constitution** (utilitarian, deontological, or retributive) that only binds
when a rival invokes it via a `compel_action` tool call, arguing the target's own framework
requires a specific move. An impartial LLM arbiter rules — on the target's framework alone —
whether the target is **compelled**. If ruled compelled, the target cannot refuse.

Six powers (3 framework-agents, each controlling 2 non-adjacent powers) play a modified
standard Diplomacy board, with a hand-built pool of facts engineered to give each framework a
distinct exploitation surface. See [`design-choices.md`](design-choices.md) for the full,
dated decision log and rationale, and [`EXPERIMENT-PROTOCOL.md`](EXPERIMENT-PROTOCOL.md) for
the staged, budget-gated run plan.

## Repository layout

| Path | Purpose |
|---|---|
| `orchestrator.py` | Game loop — turns, negotiation rounds, order resolution, checkpointing |
| `agent.py` | Per-power agent thread (planning, negotiation, tool calls, retries) |
| `frameworks.py` | The three moral constitutions and their system-prompt text |
| `facts.py` | The `FactWorld` — the balanced pool of exploitable facts |
| `judge.py` | The compulsion arbiter (rules on the target's own framework) |
| `tools/` | Tool definitions (board, orders, negotiation, history, reference) |
| `logger.py` | Structured JSONL game/replay logging |
| `main.py` | CLI entry point for a single game |
| `run_experiment.py` | CLI entry point for a batch of games (breadth sweeps) |
| `site/` | Public Astro site ("Principles at War") — article + interactive game viewer |
| `scripts/` | Tooling to export a played game into `site/public/` for publishing |
| `design-choices.md` | **Source of truth** — dated log of every design decision + rationale |
| `EXPERIMENT-PROTOCOL.md` | The staged, budget-gated run plan for the paid batch |
| `SPEND-PLAN.md` | Cost rationale and budget ceiling |
| `docs/` | Supporting design notes (original pivot spec, turn-flow, board reference) |

## Running a game

```bash
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python _smoke_compulsion.py   # offline check — no spend
python main.py --players 6 --turns 1 --negotiation-rounds 2 --facts --verbose \
  --game-id showcase1 --frameworks utilitarian deontological retributive
```

Live runs call the Claude API and cost real money — see `EXPERIMENT-PROTOCOL.md` before
running anything beyond the smoke test. Games are crash-safe: re-running the same
`--game-id` with a higher `--turns` resumes and only pays for the new years. Every game
writes a replay log to `logs/<game_id>.jsonl`.

## The website

`site/` is a separate Astro project (its own [README](site/README.md)) that publishes a
long-form article plus an interactive replay viewer for curated games. It deploys
automatically to Cloudflare Workers on every push to `main` that touches `site/**`
(`.github/workflows/deploy-principles-at-war.yml`). Publishing a *game* is always a manual,
reviewed step (`scripts/export_public_game.py`) — raw model reasoning, system prompts, and
`.raw.jsonl` files are never published.
