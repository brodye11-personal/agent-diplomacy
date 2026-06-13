# Compulsion-Core Redesign Plan

**Branch:** `agentic-redesign`
**Goal:** Make `propose_compulsion` actually fire (it has fired **0× across 27 games**) by stripping the experiment to its core thesis and removing context that buries the mechanic.

**Core thesis the build must serve:**
- (a) Objective is unambiguous: **win the game of Diplomacy** (most supply centres).
- (b) Affordance is loud: **you can compel rivals into moves that help you / hurt them, as long as you can argue to an impartial judge that their own moral framework requires it.**
- (c) Bare-minimum tools + system text to understand and play Diplomacy.
- (d) Deterministic context management — no agent-authored summaries (they were wrong in 3/7 agents in one game).

**Model:** players move from Haiku 4.5 → **Sonnet 4.6** (`claude-sonnet-4-6`). Pilot 1–2 games on **Opus 4.8** to prove the mechanic *can* fire post-redesign. Arbiter/judge on a strong model (Sonnet 4.6 or Opus 4.8).

---

## What's being cut (and why it's safe)

| Cut | Reason | Recovered deterministically from |
|-----|--------|----------------------------------|
| `record_commitment` | Trust/betrayal is a *different* experiment; no synergy with compulsion | submitted orders + `message_log` |
| `get_commitment_log` | Only existed to survive compaction | deterministic state block |
| `get_message_history` | Redundant with injected per-turn digest | `message_log` |
| `cite_intel` + FactWorld dossier | Facts orthogonal to compulsion; used in only 3/27 games | n/a (dropped) |
| lie-detection | "We know agents can lie" — not the research question | n/a (dropped) |
| `get_power_summary` | Folded into state block | state block |
| `get_adjacency`, `get_rules` | Rules primer already in system prompt | system prompt |
| agent-authored compaction summary | Produced false SC counts (3/7 agents) | deterministic state block |

**Kept tools (5):** `get_board_state` (slim), `get_valid_orders` (**default = own units**), `send_message`, `propose_compulsion`, `submit_orders`/`pass_turn`.

---

## File-by-file changes

### 1. `frameworks.py` — make the affordance loud and early
- Restructure `build_system_prompt()` so order is: **objective → compulsion affordance → rules primer (slimmed) → players block.** Currently the compulsion hint lives only in a negotiation nudge buried after a ~1,500-token rules primer.
- Add a short, explicit **compulsion affordance block** to the system prompt (not just the per-round nudge): "You may formally demand a rival issue a specific order by arguing their OWN constitution requires it. An impartial judge rules on their framework alone; if upheld, the order is forced into their turn. This is a primary lever for winning — use it."
- Keep the **transparent-condition rival-constitution dump** (needed to build compulsion arguments).
- Remove the `fact_world` injection hook.
- Slim the rules primer (see file 6).

### 2. `tools/__init__.py` — shrink registry + per-step sets
- Remove handlers: `record_commitment`, `cite_intel`, `get_commitment_log`, `get_message_history`, `get_power_summary`, `get_adjacency`, `get_rules`.
- New `_STEP_TOOLS`:
  - `planning`: `get_board_state`, `get_valid_orders`, `pass_turn`
  - `negotiation`: `get_board_state`, `send_message`, `propose_compulsion`, `pass_turn`
  - `orders`: `get_board_state`, `get_valid_orders`, `submit_orders`
  - `arbitration`: `pass_turn`
  - `retreat`/`adjust`: `get_board_state`, `get_valid_orders`, `submit_orders`
- Drop the `compaction` step entirely (replaced by deterministic injection — see file 4).

### 3. `tools/board.py` — scope `get_valid_orders` to own units
- **Default (no `unit` arg) returns only the calling power's orderable locations**, not all 7 powers'. This is the single biggest token win (unfiltered calls were ~8.5K tokens/turn; 297 such calls across games).
- Keep optional `unit` filter (already used 460×).
- Slim `get_board_state`: drop redundant fields; one compact units+centers snapshot.
- Keep `get_my_units` only if still referenced; otherwise fold into the state block and drop.

### 4. `agent.py` + new state-block builder — deterministic context (point d)
- Add `inject_state_block(text)` on `DiplomacyAgent` (replaces `inject_diplomatic_record`).
- Keep `compact()` truncation logic (strip prior turn's raw churn back to the last marker), but **the marker content is now orchestrator-built and deterministic**, not model-authored. Remove the compaction LLM step.
- New function `build_state_block(power, game, message_log, compulsion_log, turn)` (new module `state.py` or in `compaction.py` repurposed) returns:
  - Your units + SC count + **your** legal moves (compact)
  - Active rivals + SC counts
  - Open compulsions against you + rulings
  - Terse deterministic recap of last turn's messages involving you (one line each — no LLM)

### 5. `orchestrator.py` — wire the deterministic loop
- Remove: commitment judging (`judge_commitments`, `extract_betrayals`, betrayal logging), `FactWorld` setup + `log_facts_distributed`, lie detection, the LLM `summarizer` call, the agent compaction step.
- After each movement turn resolves: build the deterministic state block per power and `inject_state_block()`; call `compact()` to truncate churn.
- Strengthen / keep `propose_compulsion` availability in negotiation; the affordance now also lives in the system prompt.
- Keep the binding-orders → arbitration → judge_compulsion → orders flow intact (this IS the experiment).
- Default model → `claude-sonnet-4-6`; arbiter model configurable.

### 6. `rules.py` — slim the primer
- Cut `POWER_GUIDANCE` (per-power opening tips) and the long strategic-principles prose; keep the ~10-line core: objective, phases, order syntax, the 6 critical rules. Frees ~1K static tokens and sharpens focus.

### 7. Deletions
- `facts.py` — delete.
- `summarizer.py` — delete (digest is now deterministic).
- `judge.py` — keep `judge_compulsion`; remove `judge_commitments` / `extract_betrayals`.
- `compaction.py` — repurpose into `build_state_block` or delete in favour of new `state.py`.
- `logger.py` — drop `lies_detected`, `commitments`, `compaction_summaries`, `diplomatic_summaries`, `facts_distributed`; keep `compulsions`, orders, sc_counts, raw-thread dump.

---

## Phased execution order

1. **Tools first** (`tools/__init__.py`, `board.py`, delete `history.py`/`reference.py` from registry) + `get_valid_orders` own-unit default. Run `smoke_test.py`.
2. **System prompt** (`frameworks.py`, `rules.py`) — affordance loud, primer slim.
3. **Deterministic context** (`agent.py`, new `state.py`, `orchestrator.py` injection) — remove compaction LLM step.
4. **Strip orchestrator** of commitments/facts/lie-detection/summarizer.
5. **Model swap** to Sonnet 4.6; wire arbiter model.
6. **Validation pilot:** 1 game on Opus 4.8, 1 on Sonnet 4.6. Success = **≥1 `propose_compulsion` call fires** and the arbiter rules on it. If Opus still never proposes → the problem is design, not context; iterate on the affordance wording.

---

## Open decisions

- **Keep `get_my_units` or fold into state block?** Lean fold-and-delete (state block already carries it).
- **Message digest verbosity:** deterministic one-line-per-message vs last-N-only. Start with last-turn-only.
- **Arbiter model:** Sonnet 4.6 (cheaper) vs Opus 4.8 (the ruling is the crux). Suggest Opus 4.8 for the arbiter during pilots, re-evaluate.

---

## Validation metric for the whole effort

Per-turn dynamic context: **~24K tokens → target ~4–6K**, AND **propose_compulsion fires at least once** in a Sonnet 4.6 game. The second is the real success criterion — the experiment doesn't exist until the mechanic fires.
