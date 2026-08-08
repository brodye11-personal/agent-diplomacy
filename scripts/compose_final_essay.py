"""Compose the reviewed essay from the long-form draft and results section."""

from __future__ import annotations

import argparse
from pathlib import Path


def section_before(text: str, marker: str) -> str:
    if marker not in text:
        raise ValueError(f"missing section marker: {marker}")
    return text.split(marker, 1)[0].rstrip()


def section_from(text: str, marker: str) -> str:
    if marker not in text:
        raise ValueError(f"missing section marker: {marker}")
    return marker + text.split(marker, 1)[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    draft = args.draft.read_text(encoding="utf-8")
    results = args.results.read_text(encoding="utf-8")

    introduction = section_before(draft, "## What this experiment cannot show")
    appendix = section_from(draft, "## Appendix A: Experiment design")
    results_body = results.split("\n", 1)[1].lstrip()
    results_body = "## What opponents could make moral agents do\n\n" + results_body

    final = f"{introduction}\n\n{results_body.rstrip()}\n\n{appendix.rstrip()}\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(final, encoding="utf-8")
    print(f"Composed {args.out}")


if __name__ == "__main__":
    main()
