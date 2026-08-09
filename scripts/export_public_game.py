"""Export an allowlisted JSONL game record for the public viewer.

Raw prompts, private dossiers, tool traces, strategic plans, and internal notes are
never copied. Public negotiation, constitutional arguments, rulings, played orders,
and board states are retained so article evidence can be checked against the log.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from diplomacy import Game


def records(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def results(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("game", {}).get("result_history", {})


def make_game(board: dict) -> Game:
    game = Game()
    state = game.get_state()
    state["name"] = board["phase"]
    state["units"] = board["units"]
    state["centers"] = board["centers"]
    game.set_state(state)
    return game


def render_board(board: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    make_game(board).render(incl_orders=False, incl_abbrev=True, output_path=str(destination))


def render_orders(board: dict, orders: dict[str, list[str]], destination: Path) -> None:
    game = make_game(board)
    for power, power_orders in orders.items():
        game.set_orders(power, power_orders)
    destination.parent.mkdir(parents=True, exist_ok=True)
    game.render(incl_orders=True, incl_abbrev=True, output_path=str(destination))


def messages(negotiations: list[dict] | None, phase: str) -> list[dict]:
    return [
        {
            "id": f"{phase}-{pair_index}-{message_index}",
            "pair": pair.get("pair", []),
            "from": message.get("role"),
            "content": message.get("content", ""),
            "round": message.get("round"),
        }
        for pair_index, pair in enumerate(negotiations or [])
        for message_index, message in enumerate(pair.get("messages", []))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--map-dir", type=Path, required=True)
    args = parser.parse_args()

    stream = records(args.source)
    order_results = results(args.checkpoint)
    events: list[dict] = []
    last_map: str | None = None
    last_board: dict | None = None
    game: dict = {"slug": args.slug, "title": args.title}

    for record in stream:
        kind = record.get("type")
        if kind == "board":
            board = {key: record.get(key, {}) for key in ("phase", "phase_type", "units", "centers", "sc_counts", "orders")}
            filename = f'{len(events) + 1:02d}-{board["phase"]}.svg'
            render_board(board, args.map_dir / filename)
            last_map = f"/maps/{args.slug}/{filename}"
            last_board = board
            events.append(
                {
                    "id": f'{board["phase"]}-board-{len(events)}',
                    "kind": "board",
                    "phase": board["phase"],
                    "title": "Board position",
                    "detail": "Position entering this phase.",
                    "board": board,
                    "map": last_map,
                }
            )
            continue

        if kind == "summary":
            summary = {
                key: record.get(key)
                for key in ("final_sc_counts", "bloc_scores", "bloc_members", "winner", "winner_powers", "phases_played")
            }
            game["summary"] = summary
            events.append(
                {
                    "id": f"summary-{len(events)}",
                    "kind": "summary",
                    "phase": "summary",
                    "title": "Year summary",
                    "detail": "Experiment checkpoint summary.",
                    "summary": summary,
                    "map": last_map,
                }
            )
            continue

        if kind or "phase" not in record:
            continue

        for key in ("condition", "model", "framework_assignment"):
            if key in record:
                game[key] = record[key]

        phase = record["phase"]
        shared = {"phase": phase, "map": last_map}
        public_messages = messages(record.get("negotiations"), phase)
        if public_messages:
            events.append(
                {
                    "id": f"{phase}-negotiation",
                    "kind": "negotiation",
                    "title": "Negotiation",
                    "detail": f"{len(public_messages)} public messages exchanged.",
                    "messages": public_messages,
                    **shared,
                }
            )

        compulsions = [
            {
                key: compulsion.get(key)
                for key in (
                    "proposer",
                    "target",
                    "action",
                    "argument",
                    "rebuttal",
                    "ruling",
                    "clause",
                    "ruling_reasoning",
                    "complied",
                    "enforced",
                    "superseded_by",
                )
            }
            for compulsion in record.get("compulsions", [])
        ]
        if compulsions:
            events.append(
                {
                    "id": f"{phase}-compulsion",
                    "kind": "compulsion",
                    "title": "Compulsion and arbitration",
                    "detail": f"{len(compulsions)} ruling(s) this phase.",
                    "compulsions": compulsions,
                    **shared,
                }
            )

        submitted_orders = record.get("submitted_orders", {})
        played_orders = record.get("resolved_orders") or submitted_orders
        order_map = last_map
        if last_board and played_orders:
            filename = f"{len(events) + 1:02d}-{phase}-orders.svg"
            render_orders(last_board, played_orders, args.map_dir / filename)
            order_map = f"/maps/{args.slug}/{filename}"

        events.append(
            {
                "id": f"{phase}-orders",
                "kind": "orders",
                "title": "Orders revealed",
                "detail": "Resolved orders and adjudication results.",
                "orders": played_orders,
                "submitted_orders": submitted_orders,
                "order_results": order_results.get(phase, {}),
                "sc_counts": record.get("sc_counts", {}),
                "dislodged": record.get("dislodged", []),
                "map": order_map,
                "before_map": last_map,
                "phase": phase,
            }
        )

    game["event_count"] = len(events)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"schema_version": 2, "game": game, "events": events}, indent=2), encoding="utf-8")
    print(f"Exported {args.out} ({len(events)} events)")


if __name__ == "__main__":
    main()
