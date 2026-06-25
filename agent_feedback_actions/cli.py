from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import build_action_items, load_messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Turn dissatisfied AI-agent trace messages into action items."
    )
    parser.add_argument("trace_file", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=1.0)
    args = parser.parse_args(argv)

    report = build_action_items(load_messages(args.trace_file), min_score=args.min_score)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
