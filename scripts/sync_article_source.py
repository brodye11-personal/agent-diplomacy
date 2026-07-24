"""Copy the reviewed article structure into the static site source tree.

The public site intentionally consumes a snapshot, not a runtime dependency on the
private drafting repository. Run this explicitly when the draft is ready to refresh.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    text = args.source.read_text(encoding='utf-8')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding='utf-8')
    print(f'Synced {args.out}')


if __name__ == '__main__':
    main()
