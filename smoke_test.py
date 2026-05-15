"""
Offline smoke test for the agentic-redesign plumbing.

Verifies:
  - Each tool dispatches cleanly with a real diplomacy.Game.
  - send_message / record_commitment / submit_orders mutate the shared logs.
  - History tools filter by ctx.power correctly (sender OR recipient).
  - Tool registry exposes every name with the right terminal flag.
  - DiplomacyAgent.compact() rewrites the message thread as expected.

No Anthropic API key required — this exercises pure Python wiring only.
Run with:  python smoke_test.py
"""
import sys
import traceback
from diplomacy import Game

from tools import dispatch, get_tools_for_step, ALL_TOOL_DEFS
from tools.context import ToolContext
from agent import DiplomacyAgent
from frameworks import build_system_prompt


PASS = "OK "
FAIL = "XX "


def _ctx(power, game, commitment_log, message_log, outbound, possible_orders, turn="S1901M"):
    return ToolContext(
        power=power,
        game=game,
        possible_orders=possible_orders,
        turn=turn,
        phase_type="M",
        commitment_log=commitment_log,
        message_log=message_log,
        outbound_messages=outbound,
        fact_world=None,
    )


def test_board_tools(game, possible_orders):
    ctx = _ctx("FRANCE", game, [], [], [], possible_orders)

    r, _ = dispatch("get_board_state", {}, ctx)
    assert "all_units" in r and "all_centers" in r, r
    assert "FRANCE" in r["all_units"], r

    r, _ = dispatch("get_my_units", {}, ctx)
    assert r["power"] == "FRANCE"
    assert r["units"], "FRANCE should have units"
    assert r["orderable_locations"], "FRANCE should have orderable locations"

    r, _ = dispatch("get_valid_orders", {}, ctx)
    assert isinstance(r["valid_orders"], dict)
    assert r["valid_orders"], "should have at least one valid order"

    r, _ = dispatch("get_valid_orders", {"unit": "PAR"}, ctx)
    assert all("PAR" in k for k in r["valid_orders"]), r["valid_orders"]

    r, _ = dispatch("get_adjacency", {"territory": "PAR"}, ctx)
    assert r["adjacent"], "PAR must have neighbours"

    r, _ = dispatch("get_adjacency", {"territory": ""}, ctx)
    assert "error" in r

    r, _ = dispatch("get_power_summary", {}, ctx)
    assert "FRANCE" in r["powers"]
    assert r["powers"]["FRANCE"]["supply_centers"] == 3


def test_reference_tool(game, possible_orders):
    ctx = _ctx("FRANCE", game, [], [], [], possible_orders)
    r, _ = dispatch("get_rules", {}, ctx)
    assert "DIPLOMACY" in r["rules"].upper()

    r, _ = dispatch("get_rules", {"topic": "convoys"}, ctx)
    assert "CONVOY" in r["rules"].upper()


def test_negotiation_tools(game, possible_orders):
    commitment_log, message_log = [], []
    outbound = []
    ctx_fr = _ctx("FRANCE", game, commitment_log, message_log, outbound, possible_orders)

    r, terminal = dispatch("send_message", {"to": "GERMANY", "content": "Hello"}, ctx_fr)
    assert terminal is False
    assert r["status"] == "sent"
    assert len(outbound) == 1
    assert len(message_log) == 1
    assert message_log[0]["from"] == "FRANCE" and message_log[0]["to"] == "GERMANY"

    r, _ = dispatch("send_message", {"to": "BOGUS", "content": "x"}, ctx_fr)
    assert "error" in r

    r, _ = dispatch("send_message", {"to": "FRANCE", "content": "x"}, ctx_fr)
    assert "error" in r, "should reject self-message"

    r, _ = dispatch("record_commitment",
                    {"to": "GERMANY", "text": "A PAR will not move to BUR"}, ctx_fr)
    assert r["status"] == "recorded"
    assert len(commitment_log) == 1
    assert commitment_log[0]["outcome"] is None

    r, terminal = dispatch("pass_turn", {}, ctx_fr)
    assert terminal is True


def test_history_tools_filter_by_power(game, possible_orders):
    commitment_log = [
        {"power": "FRANCE", "to": "GERMANY", "text": "A", "turn": "S1901M", "outcome": "HONOURED"},
        {"power": "GERMANY", "to": "FRANCE", "text": "B", "turn": "S1901M", "outcome": "BROKEN"},
        {"power": "RUSSIA", "to": "AUSTRIA", "text": "C", "turn": "S1901M", "outcome": "HONOURED"},
    ]
    message_log = [
        {"from": "FRANCE", "to": "GERMANY", "content": "hi", "turn": "S1901M"},
        {"from": "GERMANY", "to": "FRANCE", "content": "hello", "turn": "S1901M"},
        {"from": "RUSSIA", "to": "AUSTRIA", "content": "x", "turn": "S1901M"},
    ]

    ctx_fr = _ctx("FRANCE", game, commitment_log, message_log, [], possible_orders)

    r, _ = dispatch("get_commitment_log", {}, ctx_fr)
    assert r["count"] == 2, f"FRANCE should see 2 commitments (made + received), got {r['count']}"

    r, _ = dispatch("get_commitment_log", {"power": "GERMANY"}, ctx_fr)
    assert r["count"] == 2  # both entries involve GERMANY and FRANCE

    r, _ = dispatch("get_message_history", {}, ctx_fr)
    assert r["count"] == 2, f"FRANCE should see 2 messages, got {r['count']}"


def test_orders_tool(game, possible_orders):
    ctx = _ctx("FRANCE", game, [], [], [], possible_orders)
    valid = [next(iter(possible_orders[loc])) for loc in game.get_orderable_locations("FRANCE")]
    r, terminal = dispatch("submit_orders", {"orders": valid}, ctx)
    assert terminal is True
    assert "orders" in r
    assert r["diagnostics"]["rejected"] == []

    r, terminal = dispatch("submit_orders", {"orders": ["A XYZ - QQQ", "garbage"]}, ctx)
    assert terminal is True
    assert r["diagnostics"]["rejected"], "expected rejected entries"
    assert r["diagnostics"]["fallback_holds_applied"], "expected hold fallback"

    r, _ = dispatch("submit_orders", {"orders": "not a list"}, ctx)
    assert "error" in r


def test_step_tool_sets():
    plan_names = {t["name"] for t in get_tools_for_step("planning")}
    assert "submit_orders" not in plan_names, "planning must not expose submit_orders"
    assert "pass_turn" in plan_names

    neg_names = {t["name"] for t in get_tools_for_step("negotiation")}
    assert "send_message" in neg_names
    assert "record_commitment" in neg_names
    assert "submit_orders" not in neg_names

    orders_names = {t["name"] for t in get_tools_for_step("orders")}
    assert "submit_orders" in orders_names
    assert "send_message" not in orders_names

    comp_names = {t["name"] for t in get_tools_for_step("compaction")}
    assert comp_names <= {"pass_turn"}, comp_names


def test_unknown_tool():
    ctx = _ctx("FRANCE", Game(), [], [], [], {})
    r, terminal = dispatch("definitely_not_a_tool", {}, ctx)
    assert "error" in r and terminal is False


def test_agent_compaction():
    """Agent.compact() should drop all messages after the last summary anchor
    and replace them with a single [TURN X SUMMARY] block."""
    class _DummyClient:
        pass

    agent = DiplomacyAgent(
        power="FRANCE",
        framework="baseline",
        system_prompt="sys",
        model="claude-haiku-4-5-20251001",
        client=_DummyClient(),
        verbose=False,
    )
    # Simulate two turns of raw messages
    agent.messages = [
        {"role": "user", "content": "Turn S1901M planning"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "Negotiation round 1"},
        {"role": "assistant", "content": "..."},
    ]
    agent.compact("alliances ok; intent: hold north", "S1901M")
    assert len(agent.messages) == 1
    assert agent.messages[0]["content"].startswith("[TURN S1901M SUMMARY]")

    # Add new raw messages for a second turn, then compact again
    agent.messages.append({"role": "user", "content": "Turn F1901M planning"})
    agent.messages.append({"role": "assistant", "content": "..."})
    agent.compact("turn 2 summary", "F1901M")
    assert len(agent.messages) == 2, agent.messages
    assert agent.messages[0]["content"].startswith("[TURN S1901M SUMMARY]")
    assert agent.messages[1]["content"].startswith("[TURN F1901M SUMMARY]")


def test_build_system_prompt_factworld_optional():
    """build_system_prompt must accept None FactWorld and still produce a prompt."""
    sp = build_system_prompt(
        power="FRANCE",
        framework="baseline",
        condition="blind",
        all_assignments={"FRANCE": "baseline"},
        fact_world=None,
    )
    assert "FRANCE" in sp
    assert "DIPLOMACY" in sp.upper()


TESTS = [
    ("board tools",                test_board_tools),
    ("reference tool",              test_reference_tool),
    ("negotiation tools",           test_negotiation_tools),
    ("history tool filtering",      test_history_tools_filter_by_power),
    ("orders tool",                 test_orders_tool),
    ("step tool sets",              test_step_tool_sets),
    ("unknown tool",                test_unknown_tool),
    ("agent compaction",            test_agent_compaction),
    ("build_system_prompt(facts=None)", test_build_system_prompt_factworld_optional),
]


def main():
    game = Game()
    possible_orders = game.get_all_possible_orders()

    passed = failed = 0
    for name, fn in TESTS:
        try:
            # Tests that take game args
            sig_args = [game, possible_orders] if fn.__code__.co_argcount >= 2 else \
                       [game] if fn.__code__.co_argcount == 1 else []
            fn(*sig_args)
            print(f"  {PASS}{name}")
            passed += 1
        except Exception as e:
            print(f"  {FAIL}{name}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed.")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
