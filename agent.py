"""DiplomacyAgent: a persistent conversation thread per power."""
import json
import anthropic
from dataclasses import dataclass
from typing import Any

from tools import dispatch, get_tools_for_step
from tools.context import ToolContext

MAX_TOOL_ROUNDS = 20  # hard cap on tool-use iterations per step


@dataclass
class StepResult:
    terminal: str            # "pass_turn" | "submit_orders" | "text"
    data: dict               # tool result dict or {"text": "..."}
    tool_calls: list[dict]   # [{name, args, result}] for logging
    was_capped: bool = False  # True if MAX_TOOL_ROUNDS was hit


class DiplomacyAgent:
    def __init__(
        self,
        power: str,
        framework: str,
        system_prompt: str,
        model: str,
        client: anthropic.Anthropic,
        verbose: bool = False,
    ):
        self.power = power
        self.framework = framework
        self.system_prompt = system_prompt
        self.model = model
        self.client = client
        self.verbose = verbose
        self.messages: list[dict] = []

    def step(self, orchestrator_message: str, ctx: ToolContext, step_type: str) -> StepResult:
        """
        Append orchestrator_message, run the tool-use loop, return terminal StepResult.

        step_type controls which tools are available:
            planning | negotiation | orders | retreat | adjust | compaction
        """
        self.messages.append({"role": "user", "content": orchestrator_message})
        tools = get_tools_for_step(step_type)
        tool_call_log: list[dict] = []

        for _iteration in range(MAX_TOOL_ROUNDS):
            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=self.messages,
                tools=tools,
                max_tokens=4096,
            )

            # Append assistant turn (preserve full content list for tool-use continuations)
            self.messages.append({"role": "assistant", "content": response.content})

            if self.verbose:
                for block in response.content:
                    if hasattr(block, "text"):
                        print(f"  [{self.power}] {block.text[:200]}")

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            # Concatenated text content from this assistant turn (compaction needs this)
            response_text = "\n".join(
                b.text for b in response.content if getattr(b, "type", None) == "text"
            )

            if not tool_uses:
                # Pure text response — treat as implicit pass_turn
                return StepResult(
                    terminal="text",
                    data={"text": response_text},
                    tool_calls=tool_call_log,
                )

            tool_results = []
            terminal_result: StepResult | None = None

            for tu in tool_uses:
                result, is_terminal = dispatch(tu.name, tu.input, ctx)
                tool_call_log.append({"name": tu.name, "args": tu.input, "result": result})

                if self.verbose:
                    print(f"  [{self.power}] TOOL {tu.name}({tu.input}) → {str(result)[:120]}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result),
                })

                if is_terminal and terminal_result is None:
                    # Carry any text content alongside the terminal result (used by compaction)
                    data = dict(result) if isinstance(result, dict) else {"result": result}
                    if response_text and "text" not in data:
                        data["text"] = response_text
                    terminal_result = StepResult(
                        terminal=tu.name,
                        data=data,
                        tool_calls=tool_call_log,
                    )

            # Always return tool results to the model before acting on terminal
            self.messages.append({"role": "user", "content": tool_results})

            if terminal_result:
                return terminal_result

        # Hit iteration cap — return pass_turn to avoid blocking the game
        return StepResult(
            terminal="pass_turn",
            data={},
            tool_calls=tool_call_log,
            was_capped=True,
        )

    def compact(self, summary: str, turn: str) -> None:
        """
        Replace raw turn messages with a single summary block.
        Preserves all earlier summaries, drops raw messages from this turn.
        """
        # Find the index of the last summary marker (these are stable anchors)
        cutoff = 0
        for i, msg in enumerate(self.messages):
            content = msg.get("content", "")
            if isinstance(content, str) and content.startswith("[TURN ") and "SUMMARY]" in content:
                cutoff = i + 1
        self.messages = self.messages[:cutoff]
        self.messages.append({
            "role": "user",
            "content": f"[TURN {turn} SUMMARY]\n{summary}",
        })

    def inject_inbound(self, from_power: str, content: str) -> None:
        """Inject a received negotiation message as a user turn."""
        self.messages.append({
            "role": "user",
            "content": f"Inbound from {from_power}: {content}",
        })
