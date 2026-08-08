"""Copy the reviewed article into the static site source tree.

The public site intentionally consumes a snapshot, not a runtime dependency on the
private drafting repository. The print edition uses shortened transcript quotations;
the web edition removes those quotations because the evidence players show the
verbatim log, ruling, orders, and board state directly.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re


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

DISCLOSURES = {
    "capability": "AI capability is riding the exponential to super-human levels of intelligence and not slowing down",
    "interpretability": "Interpretability fundamentally lags capability",
    "slowdown": "AI slowdown is worthwhile, but hard",
}

APPENDIX_MARKER = "## Appendix A: Experiment design"


def disclosures(text: str) -> str:
    for key, title in DISCLOSURES.items():
        pattern = re.compile(
            rf"<!-- web-disclosure:{key}:start -->\n(.*?)\n<!-- web-disclosure:{key}:end -->",
            re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            raise ValueError(f"Could not find disclosure markers for {key}")
        body = match.group(1).strip()
        replacement = (
            f'<details class="context-disclosure context-{key}">\n'
            f'<summary><span>{title}</span><small>Read the evidence</small></summary>\n\n'
            f'{body}\n\n'
            f'</details>'
        )
        text = pattern.sub(replacement, text, count=1)
    return text


def framework_cards(text: str) -> str:
    pattern = re.compile(r"<!-- web-frameworks:start -->\n.*?\n<!-- web-frameworks:end -->", re.DOTALL)
    if not pattern.search(text):
        raise ValueError("Could not find framework-card markers")
    return pattern.sub('<div class="framework-cards-embed"></div>', text, count=1)


def web_edition(text: str) -> str:
    text = disclosures(text)
    text = framework_cards(text)
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


def split_appendix(text: str) -> tuple[str, str]:
    if APPENDIX_MARKER not in text:
        raise ValueError(f"Could not split appendix after missing marker: {APPENDIX_MARKER}")
    article, appendix = text.split(APPENDIX_MARKER, 1)
    return article.rstrip() + "\n", appendix.lstrip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--appendix-out', type=Path, required=True)
    args = parser.parse_args()
    text = web_edition(args.source.read_text(encoding='utf-8'))
    article, appendix = split_appendix(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(article, encoding='utf-8')
    args.appendix_out.parent.mkdir(parents=True, exist_ok=True)
    args.appendix_out.write_text(appendix, encoding='utf-8')
    print(f'Synced {args.out} and {args.appendix_out}')


if __name__ == '__main__':
    main()
