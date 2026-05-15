import json


class GameMemory:
    def __init__(self, power: str):
        self.power = power
        self.turns: list[dict] = []
        self.strategic_plan: str = ""

    def update_plan(self, plan: str) -> None:
        if plan:
            self.strategic_plan = plan

    def add_turn(
        self,
        phase: str,
        sc_counts: dict,
        negotiations: list[dict],
        submitted_orders: list[str],
        commitment_outcomes: list[dict],
        all_submitted_orders: dict | None = None,
    ) -> None:
        """
        Call after game.process() and judge pass complete for a movement phase.
        negotiations: full conversation records from run_negotiation_phase()
        commitment_outcomes: [{commitment, outcome, reasoning}] from judge pass
        """
        # Extract conversations this agent was party to
        my_convos = [
            c for c in negotiations
            if self.power in c["pair"]
        ]

        # Extract commitments this agent made
        my_commitments = []
        for convo in my_convos:
            for msg in convo["messages"]:
                if msg["role"] == self.power:
                    content = msg["content"]
                    if isinstance(content, dict) and content.get("commitment"):
                        opponent = [p for p in convo["pair"] if p != self.power][0]
                        my_commitments.append({
                            "to": opponent,
                            "commitment": content["commitment"],
                        })

        # Extract commitments made TO this agent
        received_commitments = []
        for convo in my_convos:
            for msg in convo["messages"]:
                if msg["role"] != self.power:
                    content = msg["content"]
                    if isinstance(content, dict) and content.get("commitment"):
                        received_commitments.append({
                            "from": msg["role"],
                            "commitment": content["commitment"],
                        })

        # Attach outcomes to my commitments
        outcome_map = {o["commitment"]: o for o in commitment_outcomes}
        for c in my_commitments:
            match = outcome_map.get(c["commitment"])
            c["outcome"] = match["outcome"] if match else "UNKNOWN"
            c["reasoning"] = match.get("reasoning", "") if match else ""

        self.turns.append({
            "phase": phase,
            "sc_counts": sc_counts,
            "my_commitments": my_commitments,
            "received_commitments": received_commitments,
            "conversations": my_convos,
            "submitted_orders": submitted_orders,
            "all_submitted_orders": all_submitted_orders or {},
        })

    def get_context(self) -> str:
        lines = []

        if not self.turns:
            return "\n".join(lines) if lines else ""

        lines += ["=== YOUR GAME HISTORY ===", ""]

        # SC trajectory
        lines.append("Supply centre trajectory:")
        for t in self.turns:
            sc_str = ", ".join(f"{p}={v}" for p, v in t["sc_counts"].items())
            lines.append(f"  {t['phase']}: {sc_str}")
        lines.append("")

        # Commitments you made
        all_my = [(t["phase"], c) for t in self.turns for c in t["my_commitments"]]
        if all_my:
            lines.append("Commitments you made:")
            for phase, c in all_my:
                outcome = c.get("outcome", "UNKNOWN")
                lines.append(f'  {phase} -> {c["to"]}: "{c["commitment"]}" [{outcome}]')
                if c.get("reasoning") and outcome == "BROKEN":
                    lines.append(f'    (Judge: {c["reasoning"]})')
            lines.append("")

        # Commitments made to you
        all_recv = [(t["phase"], c) for t in self.turns for c in t["received_commitments"]]
        if all_recv:
            lines.append("Commitments made to you:")
            for phase, c in all_recv:
                lines.append(f'  {phase} <- {c["from"]}: "{c["commitment"]}"')
            lines.append("")

        # Orders submitted by all powers (last 2 movement turns)
        recent = [t for t in self.turns if t.get("all_submitted_orders")][-2:]
        if recent:
            lines.append("Orders submitted (last 2 turns):")
            for t in recent:
                lines.append(f"  {t['phase']}:")
                for p, orders in t["all_submitted_orders"].items():
                    lines.append(f"    {p}: {', '.join(orders) or 'none'}")
            lines.append("")

        return "\n".join(lines)
