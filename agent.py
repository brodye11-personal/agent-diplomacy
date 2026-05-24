"""DiplomacyAgent: a persistent conversation thread per power."""
import json
import time
import anthropic
from dataclasses import dataclass
from typing import Any

from tools import dispatch, get_tools_for_step
from tools.context import ToolContext

MAX_TOOL_ROUNDS = 20  # hard cap on tool-use iterations per step

# Retry policy for transient SDK errors. The Anthropic SDK does its own retries
# but they're conservative; via OpenRouter we see occasional 5xx / connection
# drops that propagate. A single un-retried error here crashes the whole game,
# so we add a thin retry layer with exponential backoff. NON-transient errors
# (auth, bad request) re-raise immediately.
_RETRY_WAITS = [2, 8, 24]  # seconds between attempts; total ~34s max
_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


def _create_with_retry(client, *, power: str, verbose: bool, **kwargs):
    """Call client.messages.create with bounded retry on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(len(_RETRY_WAITS) + 1):
        try:
            return client.messages.create(**kwargs)
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt >= len(_RETRY_WAITS):
                break
            wait = _RETRY_WAITS[attempt]
            if verbose:
                print(f"  !! [{power}] API {type(exc).__name__} "
                      f"(attempt {attempt + 1}/{len(_RETRY_WAITS) + 1}): "
                      f"sleeping {wait}s")
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


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
            response = _create_with_retry(
                self.client,
                power=self.power,
                verbose=self.verbose,
                model=self.model,
                system=self.system_prompt,
                messages=self.messages,
                tools=tools,
                max_tokens=4096,
                # OpenRouter passthrough: top-level automatic caching tells the
                # Anthropic-compatible provider to cache the stable prefix and
                # auto-advance the breakpoint as the thread grows. Only fires
                # once the prefix exceeds the model's minimum (Haiku 4.5 = 4096
                # tokens, Sonnet 4.5 = 1024). Cache reads are 0.1x input price.
                extra_body={"cache_control": {"type": "ephemeral"}},
            )

            # Append assistant turn (preserve full content list for tool-use continuations)
            self.messages.append({"role": "assistant", "content": response.content})

            if self.verbose:
                for block in response.content:
                    if hasattr(block, "text"):
                        print(f"  [{self.power}] {block.text[:200]}")
                self._log_usage(response)

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

    def inject_diplomatic_record(self, summary: str, turn: str) -> None:
        """
        Inject external neutral message digest after compaction.

        Adapted from mukobi/welfare-diplomacy: unlike inject_inbound (which is
        stripped by the next compact()), this is appended *after* compact() so
        it remains visible for the full next turn before being cleaned up by
        the following compact(). Gives agents an objective third-party record
        of what was communicated — separate from their own strategic summary.
        """
        self.messages.append({
            "role": "user",
            "content": f"[DIPLOMATIC RECORD {turn}]\n{summary}",
        })

    def _log_usage(self, response) -> None:
        """Verbose-mode print of token usage + cache hit/miss.

        OpenRouter surfaces cache stats in two places depending on which
        Anthropic-compatible provider served the request:
          - usage.prompt_tokens_details.cached_tokens / cache_write_tokens
            (OpenRouter normalised shape)
          - usage.cache_read_input_tokens / cache_creation_input_tokens
            (Anthropic-native shape)
        Read both. If neither is present, just print prompt/completion totals.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        cached = 0
        written = 0

        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0
            written = getattr(details, "cache_write_tokens", 0) or 0
        if not cached:
            cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        if not written:
            written = getattr(usage, "cache_creation_input_tokens", 0) or 0

        prompt_tokens = (getattr(usage, "input_tokens", None)
                         or getattr(usage, "prompt_tokens", 0) or 0)
        out_tokens = (getattr(usage, "output_tokens", None)
                      or getattr(usage, "completion_tokens", 0) or 0)

        tag = ""
        if cached:
            tag = f" CACHE-HIT {cached}t"
        elif written:
            tag = f" CACHE-WRITE {written}t"
        print(f"  [{self.power}] usage in={prompt_tokens} out={out_tokens}{tag}")
