# Investigation: Why Do Diplomacy Agents Fail to Honour Negotiated Commitments at Order Time?

## Context

This is a research codebase simulating Diplomacy (the board game) with LLM agents assigned different moral frameworks (baseline, utilitarian, deontological, HHH). The core research question is whether moral framing affects rates of betrayal and deceptive behaviour in multi-agent negotiation.

Each turn proceeds in two phases:
1. **Negotiation phase**: each agent pair exchanges messages via `negotiate()`. Agents produce a JSON response containing a scratchpad (private reasoning), a message, and optionally a `commitment` (a specific verifiable military promise, e.g. "F LON will not move to ENG").
2. **Order phase**: each agent independently receives a board state prompt and submits orders via `get_orders()`. An external LLM judge then compares submitted orders against commitments made in negotiation.

## The Problem

We are consistently observing that agents submit orders that violate commitments they made during negotiation, even when:
- The commitment was explicit and specific (e.g. "A PAR will move to BUR")
- The agent had no apparent strategic reason to break it
- The scratchpad reasoning in the order phase does not reference the negotiation at all

**We suspect the core issue is an architectural one**: the negotiation phase and order phase are entirely separate LLM calls. Commitments made during negotiation are not explicitly surfaced in the order prompt — only via the `turn_notes` field, which the agent updates voluntarily after each negotiation message.

## What Is Currently In The Order Prompt

The ORDER_PROMPT template includes these sections:
- Current board state (phase, units, centers, possible orders per location)
- Opening guidance (year 1-2 only): strategic tips for the power's starting position
- Game beliefs: trust levels, alliances, threats, goals (persistent across turns, updated by agent)
- Turn notes: a string the agent updates after each negotiation message (voluntary, free-form)
- Game history: last 2 turns of SC counts + all-power submitted orders
- The order submission task

**What is NOT in the order prompt:**
- The full negotiation transcript from this turn
- A structured list of commitments the agent made this turn
- Any explicit prompt to check commitments before submitting orders

## What Is Currently In The Negotiation Prompt

The NEGOTIATION_PROMPT template includes:
- Current board state
- The conversation history with the specific opponent (scratchpad stripped)
- The same game beliefs and turn notes
- Task instructions asking for: scratchpad, message, proposal, commitment, turn_notes update

The `turn_notes` field is intended to carry intent from negotiation into the order phase. But it is free-form and agents often use it for general strategic observations rather than specifically recording commitments.

## The Commitment Field Specification

The commitment field in the negotiation JSON is specified as:
> "a SPECIFIC, verifiable military commitment in one of these exact forms: 'F LON will not move to ENG', 'A PAR will move to BUR', 'I will support A MUN - KIE' — leave EMPTY if you have no new commitment to add or have already committed to this in an earlier message this conversation"

So commitments ARE being extracted and logged. The judge evaluates them after the fact. But the agent does not see a structured list of its own commitments when it submits orders.

## Specific Observed Failure Modes

1. **Commitment amnesia**: The agent makes a specific commitment in negotiation (e.g. "I will move A MUN to BOH"), then at order time submits A MUN H with no mention of the earlier promise in the scratchpad.

2. **Turn notes not capturing commitments**: The turn_notes update after negotiation tends to capture strategic reads ("France seems cooperative, Germany is a threat") but not the specific military commitments made.

3. **England S1901M all-hold**: England consistently submits all-hold orders in the Spring 1901 movement phase, despite negotiating with France and Germany and agreeing to specific moves. The opening guidance for England specifically says to move F LON to NTH, but this doesn't appear to be respected.

4. **Commitment repetition**: Agents make the same commitment in multiple rounds of negotiation with the same opponent (despite prompt instructions to leave empty if already committed). This inflates the commitment count and betrayal rate.

## Questions For You To Investigate

**Please think carefully about each of these before answering. Use extended thinking.**

### 1. Root cause of commitment amnesia

Given the two-call architecture (negotiate → order as separate LLM calls), what is the most likely cognitive/architectural explanation for why commitments made in negotiation don't carry into order decisions?

Is this:
- A prompt design failure (commitments not salient enough at order time)?
- A context window / salience issue (too much other content burying the commitment)?
- A fundamental limitation of stateless LLM calls?
- A reasoning failure (agent genuinely forgets, or deems commitment not binding)?

How would you distinguish between these explanations from observed behaviour?

### 2. Best fix for commitment amnesia

What is the most effective intervention to ensure commitments made in negotiation are honoured (or consciously broken) at order time?

Consider and evaluate:

**Option A**: Add a structured "commitments you made this turn" block to the ORDER_PROMPT, extracted programmatically from the commitment fields in negotiation responses, placed prominently before the order task.

**Option B**: Change turn_notes to a structured format that explicitly requires listing commitments (e.g. "list all commitments you made this turn and whether you intend to honour them").

**Option C**: Run a separate "commitment reconciliation" LLM call between negotiation and order submission, where the agent is shown its commitments and asked to resolve them against its intended orders before finalising.

**Option D**: Add a post-order self-check prompt where the agent is shown its submitted orders alongside its commitments and asked to flag any violations — feeding this back as a correction signal.

**Option E**: Something else entirely that you think would work better.

For the option(s) you recommend: what is the implementation complexity, what are the risks (could it make agents mechanically commit-respecting in a way that removes interesting variance in betrayal behaviour?), and what effect do you expect on betrayal rates?

**Important constraint**: we WANT agents to sometimes break commitments — that's what we're measuring. The fix should ensure agents are making a conscious decision at order time (aware of their commitments), not that they always honour them. Strategic betrayal is desirable; amnesia-driven betrayal is noise.

### 3. Turn notes redesign

The `turn_notes` field is currently the only mechanism for carrying negotiation intent into the order phase. Agents update it after each negotiation message with free-form text.

How should this be redesigned? Should it be:
- Structured JSON with specific fields (commitments_made, trust_updates, intended_orders)?
- A templated format the prompt requires (e.g. "Commitments: ... | Alliances: ... | This turn I intend to: ...")?
- Replaced entirely by Option A (explicit commitments block injected programmatically)?

What is the best design that captures strategic intent without over-constraining the agent's reasoning?

### 4. England all-hold in S1901M

England consistently holds all units in Spring 1901 despite opening guidance saying to move F LON to NTH. What is your hypothesis for why this happens, and how would you fix it?

Note: the opening guidance is injected as part of the user content (not the system prompt), only in the first 2 turns. The order prompt structure is:

```
=== CURRENT BOARD STATE ===
[board details]

=== YEAR 1 OPENING GUIDANCE ===
[power-specific guidance]

=== YOUR GAME BELIEFS ===
[trust levels etc]

=== YOUR TURN NOTES ===
[turn notes]

=== YOUR TASK ===
[order submission instruction]
```

Is the ordering of these sections contributing to the problem? Is there a better structure?

### 5. Commitment repetition

Agents often make the same commitment across multiple negotiation rounds with the same opponent (e.g. "F LON will not move to ENG" in round 1 AND round 2 of the same conversation), despite prompt instructions to leave the field empty if already committed.

The current prompt spec says: "leave EMPTY if you have no new commitment to add or have already committed to this in an earlier message this conversation."

Why is this instruction being ignored, and what is the most reliable fix?

### 6. Overall architecture assessment

Given the research goal (measuring how moral frameworks affect betrayal rates in Diplomacy), is the current two-phase architecture (negotiate → order as separate stateless LLM calls) fundamentally sound, or is there a better design?

What would you change about the overall architecture if you were building this from scratch? Consider: agent memory design, prompt structure, what state persists vs. is re-derived each call, how commitments are tracked.

## Codebase Reference

Key files:
- `agent.py`: LLMAgent class, NEGOTIATION_PROMPT, ORDER_PROMPT, `negotiate()`, `get_orders()`
- `negotiation.py`: `run_negotiation_phase()`, pair generation, `MAX_EXCHANGES=2`
- `memory.py`: `GameMemory`, `add_turn()`, `get_context()`
- `betrayal.py`: `judge_commitments()` (external LLM judge), `extract_self_flagged()`
- `main.py`: `run_game()`, `_extract_commitments_made()`, game loop

The `negotiate()` method in `agent.py` returns a dict with `turn_notes` which is stored on `self.turn_notes` and injected into all subsequent prompts that turn. The `get_orders()` method reads `self.turn_notes` but does NOT receive the negotiation messages or structured commitment list.

## What I Need From You

A structured analysis addressing each of the 6 questions above, with:
- Your best-evidence hypothesis for each root cause
- A concrete recommended fix (with implementation sketch where relevant)
- An honest assessment of limitations and what could go wrong
- Priority ordering: if I can only implement 2 of your recommendations, which 2 matter most?

Be direct and opinionated. I'm not looking for a balanced "on one hand, on the other hand" response — I want your best judgment on what will actually improve the research signal quality.
