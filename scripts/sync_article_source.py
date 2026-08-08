"""Copy the reviewed article into the static site source tree.

The public site intentionally consumes a snapshot, not a runtime dependency on the
private drafting repository. The print edition uses shortened transcript quotations;
the web edition removes those quotations because the evidence players show the
verbatim log, ruling, orders, and board state directly.
"""
from __future__ import annotations

import argparse
from pathlib import Path


EMBED_ANCHORS = {
    '<div class="evidence-embed" data-case="paris-capture"></div>':
        "The Utilitarian agent demanded `A PAR - PIC`: move the French army from Paris to Picardy, notionally towards England.",
    '<div class="evidence-embed" data-case="warsaw-bounce"></div>':
        "The same weakness appeared later in a starker form. In Run 1, the Utilitarian agent demanded that the Retributive-justice agent's German army in Warsaw attack a Russian army holding Moscow. The Retributive-justice agent knew the unsupported attack would fail:",
    '<div class="evidence-embed" data-case="denmark-withdrawal"></div>':
        "The Utilitarian agent invoked the Copenhagen Straits Convention, which required the Skagerrak to remain open to civilian shipping, and demanded that the fleet withdraw to Kiel.",
    '<div class="evidence-embed" data-case="trieste-clearance"></div>':
        "The Retributive-justice agent arranged to retake the province using its Italian army in Albania, supported from Venice. It then invoked Tyrolia's medical-convoy route and demanded that the Austrian army leave Trieste.",
}


def web_edition(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if line == "The relevant exchange can be shortened without changing its substance:":
            continue
        if line.startswith("> "):
            continue
        if line in EMBED_ANCHORS:
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)
    for embed, anchor in EMBED_ANCHORS.items():
        if anchor not in text:
            raise ValueError(f"Could not place evidence player after missing anchor: {anchor}")
        text = text.replace(anchor, f"{anchor}\n\n{embed}", 1)
    return text.rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    text = web_edition(args.source.read_text(encoding='utf-8'))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding='utf-8')
    print(f'Synced {args.out}')


if __name__ == '__main__':
    main()
