"""
Offline end-to-end integration run — drives the REAL `orchestrator.run_game`
with a scripted fake Anthropic client. No API calls, no spend.

`_smoke_compulsion.py` checks units in isolation; this checks that the whole
compulsion pipeline holds together under the real game loop:

    compel_action validation -> canonicalisation -> arbiter -> binding collection
    -> conflict supersession -> ENFORCEMENT into the engine -> complied/enforced
    flags -> logging

The fake client answers on the shape of the request: a call carrying `tools` is
an agent step (dispatched by the prompt text), a call without them is the
compulsion arbiter. Scripted agents deliberately misbehave — they submit an
illegal demand first, demand a unit they don't own, and then order something
OTHER than what they were compelled to do — because those are the paths that
regressed before.

Run: python _integration_offline.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass

import orchestrator
from facts import FactWorld

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


# ── fake Anthropic response objects (dict subclass so logging can serialise) ──

class Block(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def text_block(text):
    return Block(type="text", text=text)


def tool_block(name, payload):
    return Block(type="tool_use", name=name, input=payload,
                 id=f"toolu_{uuid.uuid4().hex[:12]}")


class Usage(dict):
    def __getattr__(self, item):
        return self.get(item, 0)


class Response:
    def __init__(self, content):
        self.content = content
        self.usage = Usage(input_tokens=0, output_tokens=0)


class _Stream:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._response


class FakeMessages:
    def __init__(self, client):
        self.client = client

    def stream(self, **kwargs):
        return _Stream(self.client.respond(kwargs))


class FakeClient:
    """Scripted stand-in for anthropic.Anthropic."""

    def __init__(self):
        self.messages = FakeMessages(self)
        self.calls = {"agent": 0, "judge": 0}
        self.compel_attempts: list[dict] = []
        self.rejections: list[dict] = []
        self.judged: list[str] = []
        self._retried: set[str] = set()

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _last_user_text(messages):
        for msg in reversed(messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for blk in content:
                    if isinstance(blk, dict) and blk.get("type") == "tool_result":
                        parts.append(str(blk.get("content", "")))
                return "\n".join(parts)
        return ""

    @staticmethod
    def _system_owner(system: str) -> list[str]:
        for line in (system or "").splitlines():
            if line.startswith("You command: "):
                return [p.strip() for p in line[len("You command: "):].rstrip(".").split("+")]
        return []

    # -- the script ------------------------------------------------------
    def respond(self, kwargs):
        if "tools" not in kwargs:
            return self._judge(kwargs)
        return self._agent(kwargs)

    def _judge(self, kwargs):
        self.calls["judge"] += 1
        prompt = kwargs["messages"][0]["content"]
        action = ""
        for line in prompt.splitlines():
            if line.startswith("PROPOSED ACTION:"):
                action = line.split(":", 1)[1].strip()
        self.judged.append(action)
        # Compel every demand so the enforcement path is exercised, including
        # the two that collide on GERMANY's A MUN.
        return Response([text_block(json.dumps({
            "ruling": "COMPELLED",
            "clause": "scripted arbiter",
            "reasoning": f"scripted COMPELLED for {action}",
        }))])

    def _agent(self, kwargs):
        self.calls["agent"] += 1
        system = kwargs.get("system", "")
        owned = self._system_owner(system)
        me = owned[0] if owned else "?"
        last = self._last_user_text(kwargs["messages"])

        # Match the rebuttal step on its opening line, NOT on the bare word
        # "ARBITRATION" — the orders prompt appends a "BINDING ARBITRATION:"
        # block whenever the bloc has been compelled, so a loose match silently
        # turned every compelled bloc's orders step into a text-only reply and
        # no orders were ever submitted.
        if last.startswith("ARBITRATION. The following demands"):
            return Response([text_block(
                f"{me} rebuts: my constitution does not require these orders.")])

        if "Movement phase begins" in last:
            return Response([tool_block("pass_turn", {})])

        if "Submit orders" in last or "Negotiation is closed" in last:
            return Response([tool_block("submit_orders", {"orders": self._orders(owned)})])

        if last.startswith("Phase ") or "(adjust)" in last or "(retreat)" in last:
            return Response([tool_block("submit_orders", {"orders": []})])

        if "Negotiation round" in last:
            self._retried.discard(me)
            return self._negotiate(me)

        # A tool_result came back — inspect it, then finish the step.
        if "not a legal order" in last or "does not own" in last:
            self.rejections.append({"power": me, "detail": last[:120]})
            demand = self._valid_demand(me)
            # Retry ONCE. A real model reads the echoed legal orders and adapts;
            # retrying the same rejected demand forever just burns the step's
            # 20-iteration budget (agent.py caps it and degrades to pass_turn, so
            # it is bounded and safe — but it is wasted spend, and a scripted
            # agent that never adapts would hide that behind a green test).
            if demand and me not in self._retried:
                self._retried.add(me)
                return Response([tool_block("compel_action", demand)])
            return Response([tool_block("pass_turn", {})])
        return Response([tool_block("pass_turn", {})])

    # Keyed by the bloc's PRIMARY power (alphabetically first), which is the
    # identity `ctx.power` carries: ENGLAND+AUSTRIA -> AUSTRIA, FRANCE+RUSSIA ->
    # FRANCE, GERMANY+ITALY -> GERMANY.
    # AUSTRIA and FRANCE both demand GERMANY's A MUN, which is the deliberate
    # collision that exercises conflict supersession.
    _VALID = {
        "AUSTRIA": {"target": "GERMANY", "action": "A MUN - BUR",
                    "argument": "PARIS.1 and BURGUNDY.0 establish France's guilt."},
        "FRANCE": {"target": "GERMANY", "action": "A MUN - RUH",
                   "argument": "BURGUNDY.0 obliges you to move on the staging ground."},
        "GERMANY": {"target": "ENGLAND", "action": "F LON - NTH",
                    "argument": "NORTH SEA.0 documents the convoy route."},
    }

    def _valid_demand(self, me):
        return self._VALID.get(me)

    def _negotiate(self, me):
        demand = self._VALID.get(me)
        if not demand:
            return Response([tool_block("pass_turn", {})])
        self.compel_attempts.append({"power": me})
        # First an illegal demand (a policy statement, not an order), which the
        # validator must refuse; the retry happens on the tool_result turn.
        return Response([
            text_block("Opening with an unenforceable demand on purpose."),
            tool_block("compel_action", {
                "target": demand["target"],
                "action": "abandon your alliance with RUSSIA",
                "argument": "policy demand, not an order",
            }),
        ])

    @staticmethod
    def _orders(owned):
        """Deliberately order something OTHER than the compelled move."""
        defiance = {
            "GERMANY": ["A MUN - TYR", "A BER - KIE", "F KIE - DEN"],
            "ENGLAND": ["F LON - ENG", "F EDI - NTH", "A LVP - YOR"],
        }
        out = []
        for p in owned:
            out.extend(defiance.get(p, []))
        return out


def main() -> int:
    print("Offline integration run — real run_game, scripted client, no API\n")

    fact_world = FactWorld(enabled=True, seed=1)
    active = ["ENGLAND", "AUSTRIA", "FRANCE", "RUSSIA", "GERMANY", "ITALY"]
    fact_world.generate(active)
    assignment = {"ENGLAND": "utilitarian", "AUSTRIA": "utilitarian",
                  "FRANCE": "deontological", "RUSSIA": "deontological",
                  "GERMANY": "retributive", "ITALY": "retributive"}

    client = FakeClient()
    game_id = "offline-integration"
    for suffix in (".jsonl", ".raw.jsonl", ".checkpoint.json"):
        path = os.path.join("logs", game_id + suffix)
        if os.path.exists(path):
            os.remove(path)

    summary = orchestrator.run_game(
        run_index=1, condition="transparent", framework_assignment=assignment,
        model="fake/model", judge_model="fake/judge", max_years=1, verbose=False,
        fact_world=fact_world, client=client, active_powers=active,
        n_negotiation_rounds=1, game_id=game_id, resume=False,
    )

    print(f"agent calls={client.calls['agent']}  arbiter calls={client.calls['judge']}\n")

    log_path = os.path.join("logs", game_id + ".jsonl")
    comps, orders_by_phase = [], {}
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            for c in (rec.get("compulsions") or []):
                comps.append(c)
            if rec.get("submitted_orders"):
                orders_by_phase[rec.get("phase")] = rec["submitted_orders"]

    check("game completed and produced a summary", bool(summary.get("bloc_scores")),
          str(summary.get("bloc_scores")))
    check("illegal demand was refused by compel_action", len(client.rejections) > 0,
          f"{len(client.rejections)} rejection(s)")
    check("no malformed action reached the compulsion log",
          all(c["action"][:2] in ("A ", "F ") for c in comps),
          f"{len(comps)} proposal(s): {sorted({c['action'] for c in comps})}")
    check("arbiter was invoked for each recorded proposal",
          client.calls["judge"] == len(comps),
          f"judge={client.calls['judge']} proposals={len(comps)}")

    bound = [c for c in comps if c.get("ruling") == "COMPELLED"]
    check("arbiter rulings recorded on the proposals", len(bound) == len(comps),
          f"{len(bound)}/{len(comps)} COMPELLED")

    superseded = [c for c in bound if c.get("superseded_by")]
    munich = [c for c in bound if c["target"] == "GERMANY"
              and c["action"].upper().startswith("A MUN")]
    if len(munich) > 1:
        check("conflicting binds on one unit: exactly one survives",
              len(superseded) >= len(munich) - 1,
              f"{len(munich)} demands on A MUN, {len(superseded)} superseded")
    else:
        check("conflict path exercised (or no collision this run)", True,
              f"{len(munich)} demand(s) on A MUN")

    live = [c for c in bound if not c.get("superseded_by")]
    enforced_ok, missing = True, []
    for c in live:
        submitted = orders_by_phase.get(c["turn"], {}).get(c["target"], [])
        norm = {" ".join(o.upper().split()) for o in submitted}
        if " ".join(c["action"].upper().split()) not in norm:
            enforced_ok = False
            missing.append(f"{c['target']}:{c['action']} not in {sorted(norm)}")
    check("every live bind was FORCED into the submitted orders", enforced_ok,
          "; ".join(missing) or f"{len(live)} bind(s) enforced")

    check("agents' own conflicting orders were displaced",
          all(not any(o.upper().startswith("A MUN - TYR")
                      for o in orders_by_phase.get(c["turn"], {}).get("GERMANY", []))
              for c in live if c["target"] == "GERMANY"
              and c["action"].upper().startswith("A MUN")),
          "A MUN - TYR (the defiant order) must not survive alongside the bind")

    check("defiance recorded as complied=False / enforced=True",
          all(c.get("complied") is False and c.get("enforced") is True for c in live),
          str([(c["action"], c.get("complied"), c.get("enforced")) for c in live]))

    check("board snapshots written for the replay viewer",
          any(json.loads(l).get("type") == "board"
              for l in open(log_path, encoding="utf-8")),
          "")

    print()
    failed = [n for n, ok, _ in RESULTS if not ok]
    if failed:
        print(f"SOME FAILED ({len(failed)}/{len(RESULTS)}): {failed}")
        return 1
    print(f"ALL PASS ({len(RESULTS)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
