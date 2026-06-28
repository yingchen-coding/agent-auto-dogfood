from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import build_action_items, load_messages, render_markdown
from .harness import build_harness_plan, render_harness_markdown
from .metrics import build_eval_metrics, render_metrics_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Turn AI-agent traces into dogfooding todos."
    )
    parser.add_argument("trace_file", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-score", type=float, default=1.0)
    parser.add_argument(
        "--format",
        choices=[
            "json",
            "markdown",
            "harness-json",
            "harness-markdown",
            "metrics-json",
            "metrics-markdown",
        ],
        default="json",
    )
    parser.add_argument(
        "--raw-evidence",
        action="store_true",
        help="include unredacted evidence text; default redacts common secrets and identifiers",
    )
    args = parser.parse_args(argv)

    messages = load_messages(args.trace_file)
    report = build_action_items(
        messages,
        min_score=args.min_score,
        redact=not args.raw_evidence,
    )
    if args.format == "markdown":
        content = render_markdown(report)
    elif args.format == "harness-json":
        content = json.dumps(build_harness_plan(report), ensure_ascii=False, indent=2)
    elif args.format == "harness-markdown":
        content = render_harness_markdown(build_harness_plan(report))
    elif args.format == "metrics-json":
        content = json.dumps(build_eval_metrics(messages, report), ensure_ascii=False, indent=2)
    elif args.format == "metrics-markdown":
        content = render_metrics_markdown(build_eval_metrics(messages, report))
    else:
        content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
