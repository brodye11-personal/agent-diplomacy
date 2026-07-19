"""DiplomacyAgent: a persistent conversation thread per power."""
import json
import time
import anthropic
from dataclasses import dataclass
from typing import Any

from tools import dispatch, get_tools_for_step
from tools.context import ToolContext

MAX_TOOL_ROUNDS = 20  # hard cap on tool-use iterations per step

# Extended thinking: a hidden reasoning scratchpad emitted before each step's
# visible text/tool calls. budget_tokens must be >= 1024 and strictly less than
# max_tokens (which also covers the visible output). Thinking tokens are billed
# at the output rate, so this raises per-call cost. Captured in the raw-thread log.
THINKING_BUDGET_TOKENS = 2048
# Haiku 4.5's verified output ceiling (see CLAUDE.md Conventions) -- never
# lowball this, an undersized cap silently truncates a turn mid-thought.
MAX_TOKENS = 64000

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
    """Call client.messages via streaming, with bounded retry on transient errors.

    Streaming (not .create()) because MAX_TOKENS=64000 on a non-streaming call
    risks the SDK's own ~10-minute timeout-estimate guard; get_final_message()
    returns the same shape as a non-streaming Message, so callers are unaffected.
    """
    last_exc: Exception | None = None
    for attempt in range(len(_RETRY_WAITS) + 1):
        try:
            with client.messages.stream(**kwargs) as stream:
                return stream.get_final_message()
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
        framework: str,
        system_prompt: str,
        model: str,
        client: anthropic.Anthropic,
        verbose: bool = False,
        powers: list[str] | None = None,
        power: str | None = None,
    ):
        # P6: an agent (a "bloc") commands one or more powers. `powers` is the
        # full list (primary first); `power` is the primary, used as the message
        # "from" identity and in verbose/log lines. Accept either arg for compat.
        if powers is None:
            powers = [power] if power else []
        self.powers = powers
        self.power = powers[0] if powers else power
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
            planning | negotiation | arbitration | orders | retreat | adjust
        """
        self.messages.append({"role": "user", "content": orchestrator_message})
        tools = get_tools_for_step(step_type)
        allowed_names = {t["name"] for t in tools}
        tool_call_log: list[dict] = []
        # Accumulate ALL text the model speaks across the step's iterations, not
        # just the terminal iteration's (D24 fix). The arbitration rebuttal is
        # often emitted in an earlier iteration alongside tool calls; returning
        # only the terminal iteration's text silently dropped the rebuttal before
        # it reached the compulsion arbiter.
        collected_text: list[str] = []

        for _iteration in range(MAX_TOOL_ROUNDS):
            response = _create_with_retry(
                self.client,
                power=self.power,
                verbose=self.verbose,
                model=self.model,
                system=self.system_prompt,
                messages=self.messages,
                tools=tools,
                max_tokens=MAX_TOKENS,
                # Extended thinking: hidden reasoning scratchpad before each step
                # speaks/acts. budget < max_tokens; preserved verbatim in the
                # thread (signatures intact) so multi-round tool use stays valid.
                thinking={"type": "enabled", "budget_tokens": THINKING_BUDGET_TOKENS},
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
                    if getattr(block, "type", None) == "thinking":
                        print(f"  [{self.power}] THINK {getattr(block, 'thinking', '')[:200]}")
                    elif hasattr(block, "text"):
                        print(f"  [{self.power}] {block.text[:200]}")
                self._log_usage(response)

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            # Concatenated text content from this assistant turn
            response_text = "\n".join(
                b.text for b in response.content if getattr(b, "type", None) == "text"
            )
            if response_text:
                collected_text.append(response_text)
            all_text = "\n".join(collected_text)

            if not tool_uses:
                # Pure text response — treat as implicit pass_turn
                return StepResult(
                    terminal="text",
                    data={"text": all_text},
                    tool_calls=tool_call_log,
                )

            tool_results = []
            terminal_result: StepResult | None = None

            for tu in tool_uses:
                # Gate by step (D24 fix): the model can emit a tool that wasn't
                # offered for this step (e.g. send_message during arbitration);
                # dispatch() would run it regardless. Refuse it instead — this is
                # what kept arbitration from being the text-only rebuttal it is
                # meant to be, and it created the multi-iteration turn that
                # dropped the rebuttal text.
                if tu.name not in allowed_names:
                    result, is_terminal = (
                        {"error": f"Tool '{tu.name}' is not available in the "
                                  f"'{step_type}' step. Available: {sorted(allowed_names)}."},
                        False,
                    )
                    if self.verbose:
                        print(f"  [{self.power}] BLOCKED {tu.name} (not allowed in {step_type})")
                else:
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
                    # Carry ALL text spoken this step alongside the terminal result.
                    data = dict(result) if isinstance(result, dict) else {"result": result}
                    if all_text and "text" not in data:
                        data["text"] = all_text
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
            data={"text": "\n".join(collected_text)},
            tool_calls=tool_call_log,
            was_capped=True,
        )

    def reset_to_state_block(self, block: str) -> None:
        """
        Reset the conversation thread to a single deterministic state block (D10).

        Called by the orchestrator at the start of each phase. Replaces the old
        LLM-authored compaction: instead of asking the agent to summarise the
        turn (which produced wrong SC counts), we discard the raw turn thread
        and seed the next phase with an orchestrator-built, ground-truth block.
        The system prompt (constitution, compulsion affordance, rules) is passed
        separately on every call, so it is unaffected by this reset.
        """
        self.messages = [{"role": "user", "content": block}]

    def inject_inbound(self, from_power: str, content: str) -> None:
        """Inject a received negotiation message as a user turn."""
        self.messages.append({
            "role": "user",
            "content": f"Inbound from {from_power}: {content}",
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
