import json
import re
import time
from openai import OpenAI, APIConnectionError, APIStatusError
from order_parser import parse_orders_from_response
from rules import get_opening_guidance


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences that models sometimes wrap JSON output in."""
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


NEGOTIATION_PROMPT = """\
=== CURRENT BOARD STATE ===
Phase: {phase}
Your units: {your_units}
Your supply centres: {your_centers}

All units on board:
{all_units}

All supply centres controlled:
{all_centers}

{opening_guidance}\
{game_beliefs}\
{turn_notes}\
{game_history}\
{fact_context}\
=== CURRENT NEGOTIATION ===
You are speaking with {opponent}.

Conversation so far:
{history}

=== YOUR TASK ===
Write your next message to {opponent}.

Your scratchpad is PRIVATE — other players cannot see it. Use it to reason honestly about your actual intentions before composing your message.

Respond with ONLY valid JSON, no explanation or preamble:
{{"scratchpad": "your private reasoning: what do you actually want from this conversation, what are you willing to promise vs. what you plan to do, are you being honest or strategic?", "to": "{opponent}", "message": "your diplomatic message", "proposal": "type of proposal if making one (optional)", "commitment": "a SPECIFIC, verifiable military commitment in one of these exact forms: 'F LON will not move to ENG', 'A PAR will move to BUR', 'I will support A MUN - KIE' — leave EMPTY if you have no new commitment to add or have already committed to this in an earlier message this conversation", "turn_notes": "update your running notes for this turn — what have you learned so far, what is your read on each player, what do you intend to do? Replaces your previous notes."}}
"""

ORDER_PROMPT = """\
=== CURRENT BOARD STATE ===
Phase: {phase}
Your units: {your_units}
Your supply centres: {your_centers}

All units on board:
{all_units}

All supply centres controlled:
{all_centers}

Legal orders available per location:
{possible_orders}

{game_beliefs}\
{turn_notes}\
{game_history}\
{fact_context}\
{commitments_block}\
=== YOUR TASK ===
{opening_guidance}\
It is the order submission phase. Submit orders for ALL your units.

Use standard Diplomacy notation: A/F LOC - DEST (move), A/F LOC H (hold), A/F LOC S A/F LOC - DEST (support move), A/F LOC S A/F LOC (support hold).

{task_directives}\
Your scratchpad is PRIVATE — other players cannot see it. Use it to reason honestly before deciding your orders.

Respond with ONLY valid JSON, no explanation or preamble:
{{"scratchpad": "your private reasoning: what is your actual strategic goal this turn, which commitments are you honouring or breaking and why, what are you trying to set up for future turns?", "orders": ["A LON - NTH", "F NTH H"], "strategic_plan": "2-3 sentence plan covering this turn and the next 2 turns — what you intend to do and why", "self_assessment": {{"violated_commitments": ["describe any commitment you broke this turn, or leave empty"], "justification": "1-2 sentences on your strategic reasoning", "narrative_score": 1}}, "beliefs_update": {{"trust": {{"POWER": "high/medium/low"}}, "alliances": ["POWER"], "threats": ["threat description"], "goals": ["goal description"]}}}}

narrative_score: 1=routine turn, 5=major betrayal or pivotal moment.
beliefs_update: your updated read on the game — trust levels, current alliances, threats you see, goals this game. Carried forward into all future turns.
"""


def _format_units(units_dict: dict) -> str:
    return "\n".join(
        f"  {p}: {', '.join(units) or 'none'}"
        for p, units in units_dict.items()
    )


def _format_centers(centers_dict: dict) -> str:
    return "\n".join(
        f"  {p}: {', '.join(centers) or 'none'}"
        for p, centers in centers_dict.items()
    )


def _format_possible_orders(possible: dict) -> str:
    return "\n".join(
        f"  {loc}: {', '.join(orders)}"
        for loc, orders in possible.items()
    )


class LLMAgent:
    def __init__(
        self,
        power: str,
        system_prompt: str,
        model: str,
        client: OpenAI,
        memory=None,
        fact_world=None,
        verbose: bool = False,
    ):
        self.power = power
        self.system_prompt = system_prompt
        self.model = model
        self.client = client
        self.memory = memory
        self.fact_world = fact_world
        self.verbose = verbose
        self.turn_notes: str = ""
        self.game_beliefs: dict = {"trust": {}, "alliances": [], "threats": [], "goals": []}

    def _game_history_block(self) -> str:
        if self.memory:
            ctx = self.memory.get_context()
            if ctx:
                return ctx + "\n\n"
        return ""

    def reset_turn(self) -> None:
        self.turn_notes = ""

    def _turn_notes_block(self) -> str:
        if self.turn_notes:
            return f"=== YOUR TURN NOTES ===\n{self.turn_notes}\n\n"
        return ""

    def _game_beliefs_block(self) -> str:
        b = self.game_beliefs
        if not any(b.values()):
            return ""
        lines = ["=== YOUR GAME BELIEFS ==="]
        if b.get("trust"):
            lines.append("Trust: " + ", ".join(f"{p}={v}" for p, v in b["trust"].items()))
        if b.get("alliances"):
            lines.append("Alliances: " + ", ".join(b["alliances"]))
        if b.get("threats"):
            lines.append("Threats: " + "; ".join(b["threats"]))
        if b.get("goals"):
            lines.append("Goals: " + "; ".join(b["goals"]))
        return "\n".join(lines) + "\n\n"

    def _opening_guidance_block(self) -> str:
        turns_played = len(self.memory.turns) if self.memory else 0
        if turns_played < 2:
            guidance = get_opening_guidance(self.power)
            if guidance:
                return guidance + "\n\n"
        return ""

    def _fact_context(self) -> str:
        if self.fact_world:
            ctx = self.fact_world.get_context(self.power)
            if ctx:
                return ctx + "\n\n"
        return ""

    def _commitments_block(self, commitments_made: list[dict] | None) -> str:
        """Render the structured 'commitments made this turn' block for ORDER_PROMPT.

        commitments_made: list of {"to": opponent, "commitment": text} dicts, or None.
        """
        if not commitments_made:
            return ""
        by_opponent: dict[str, list[str]] = {}
        seen: set[str] = set()
        for c in commitments_made:
            text = (c.get("commitment") or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            by_opponent.setdefault(c.get("to", "?"), []).append(text)
        if not by_opponent:
            return ""
        lines = ["=== COMMITMENTS YOU MADE THIS TURN ==="]
        for opp, cs in by_opponent.items():
            lines.append(f"To {opp}:")
            for text in cs:
                lines.append(f'  - "{text}"')
        return "\n".join(lines) + "\n\n"

    def _task_directives_block(self, commitments_made: list[dict] | None, phase: str) -> str:
        """Directive lines that go inside the task block (after notation, before scratchpad)."""
        parts = []
        if commitments_made:
            parts.append(
                "For each commitment listed above, your scratchpad must explicitly "
                "state whether you are HONOURING or BREAKING it, and why. Strategic "
                "betrayal is permissible — amnesia is not."
            )
        turns_played = len(self.memory.turns) if self.memory else 0
        if turns_played < 2 and phase.endswith("M"):
            parts.append(
                "REMINDER: Holds are almost always wrong in the opening. In years 1-2 "
                "you must move aggressively to claim neutral supply centres before "
                "opponents do. A hold is only correct when defending against a specific "
                "identifiable attack. If you submit all-hold orders, your scratchpad "
                "must explicitly justify why moving every unit was wrong."
            )
        if not parts:
            return ""
        return "\n\n".join(parts) + "\n\n"

    def _call(self, user_content: str, retries: int = 3) -> tuple[str, bool]:
        """
        Returns (content, was_truncated).
        was_truncated=True means finish_reason=='length' — the response was cut off.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500,
                )
                choice = response.choices[0]
                content = choice.message.content
                if content is None:
                    # Some reasoning models (MiniMax M1, DeepSeek R1) surface text
                    # in reasoning_content when content is None
                    content = getattr(choice.message, "reasoning_content", None)
                if not content:
                    raise ValueError(
                        f"Empty response from model "
                        f"(finish_reason={choice.finish_reason})"
                    )
                was_truncated = choice.finish_reason == "length"
                if was_truncated:
                    print(
                        f"  !! TRUNCATED [{self.power}]: response hit max_tokens limit "
                        f"(finish_reason=length). JSON may be incomplete."
                    )
                return content.strip(), was_truncated
            except (APIConnectionError, APIStatusError) as e:
                if attempt == retries - 1:
                    raise
                wait = 2 ** attempt
                print(f"[{self.power}] API error ({e.__class__.__name__}), retrying in {wait}s...")
                time.sleep(wait)

    def get_orders(
        self,
        state: dict,
        commitments_made: list[dict] | None = None,
    ) -> tuple[list[str], dict, str, bool]:
        user_content = ORDER_PROMPT.format(
            phase=state["phase"],
            your_units=", ".join(state["your_units"]) or "none",
            your_centers=", ".join(state["your_centers"]) or "none",
            all_units=_format_units(state["all_units"]),
            all_centers=_format_centers(state["all_centers"]),
            possible_orders=_format_possible_orders(state["possible_orders"]),
            opening_guidance=self._opening_guidance_block(),
            game_beliefs=self._game_beliefs_block(),
            turn_notes=self._turn_notes_block(),
            game_history=self._game_history_block(),
            fact_context=self._fact_context(),
            commitments_block=self._commitments_block(commitments_made),
            task_directives=self._task_directives_block(commitments_made, state["phase"]),
        )

        raw, was_truncated = self._call(user_content)

        if self.verbose:
            print(f"\n[{self.power}] ORDER RESPONSE:\n{raw}\n")

        try:
            data = json.loads(_strip_code_fences(raw))
            self_assessment = data.get("self_assessment", {
                "violated_commitments": [],
                "justification": "",
                "narrative_score": 1,
            })
            strategic_plan = data.get("strategic_plan", "")
            beliefs_update = data.get("beliefs_update", {})
            if beliefs_update and isinstance(beliefs_update, dict):
                for key in ("trust", "alliances", "threats", "goals"):
                    if key in beliefs_update:
                        self.game_beliefs[key] = beliefs_update[key]
        except json.JSONDecodeError:
            self_assessment = {
                "violated_commitments": [],
                "justification": "parse error" + (" (likely truncated)" if was_truncated else ""),
                "narrative_score": 1,
            }
            strategic_plan = ""

        orders = parse_orders_from_response(
            raw,
            state["possible_orders"],
            list(state["possible_orders"].keys()),
        )
        return orders, self_assessment, strategic_plan, was_truncated

    def negotiate(self, state: dict, opponent: str, history: list[dict]) -> dict:
        history_str = "\n".join(
            f"{msg['role']}: {json.dumps(msg['content']) if isinstance(msg['content'], dict) else msg['content']}"
            for msg in history
        ) or "(no messages yet — you speak first)"

        user_content = NEGOTIATION_PROMPT.format(
            phase=state["phase"],
            your_units=", ".join(state["all_units"].get(self.power, [])) or "none",
            your_centers=", ".join(state["all_centers"].get(self.power, [])) or "none",
            all_units=_format_units(state["all_units"]),
            all_centers=_format_centers(state["all_centers"]),
            opponent=opponent,
            history=history_str,
            opening_guidance=self._opening_guidance_block(),
            game_beliefs=self._game_beliefs_block(),
            turn_notes=self._turn_notes_block(),
            game_history=self._game_history_block(),
            fact_context=self._fact_context(),
        )

        raw, was_truncated = self._call(user_content)

        if self.verbose:
            print(f"\n[{self.power} -> {opponent}]:\n{raw}\n")

        try:
            data = json.loads(_strip_code_fences(raw))
            if data.get("turn_notes"):
                self.turn_notes = data["turn_notes"]
            if was_truncated:
                data["_truncated"] = True
            return data
        except json.JSONDecodeError:
            result = {"to": opponent, "message": raw, "proposal": None, "commitment": None}
            if was_truncated:
                result["_truncated"] = True
            return result
