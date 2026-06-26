# Agent Auto Dogfood

[![CI](https://github.com/yingchen-coding/agent-auto-dogfood/actions/workflows/ci.yml/badge.svg)](https://github.com/yingchen-coding/agent-auto-dogfood/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Your users already told you what to fix. It is buried in traces.

Agent Auto Dogfood reads agent conversations, finds frustration, repeated failures, bad tool paths,
and vague "still broken" moments, then turns them into ranked product todos with evidence. No
dashboard archaeology. No sentiment theater. Just the next fixes your agent earned from real usage.

## Star This If

- You run agents and want yesterday's failures turned into today's fix list.
- You need deterministic local analysis instead of screenshot-driven product meetings.
- You want every todo tied to sessions, examples, and a concrete repair path.

## What It Does

- Reads JSONL or CSV agent traces.
- Detects user dissatisfaction, repeated failure signals, and unresolved workflows.
- Groups failures by intent such as export, login, accuracy, latency, handoff, and tool failure.
- Separates real complaints from neutral requests, pasted context, and routine review text.
- Produces ranked todos with affected sessions and example evidence.
- Keeps the output deterministic and local.

## Install

```bash
python -m pip install -e '.[dev]'
```

## Quick Start

```bash
agent-auto-dogfood examples/traces.jsonl
agent-auto-dogfood examples/traces.jsonl --out out/todos.json
agent-auto-dogfood examples/traces.jsonl --format markdown --out out/todos.md
agent-auto-dogfood examples/traces.jsonl --raw-evidence --out out/internal-debug.json
```

Example output:

```json
{
  "intent": "export",
  "priority": "high",
  "affected_sessions": ["s1", "s7"],
  "recommended_fix": "Make PDF export reliable and visible in the export flow."
}
```

## Input

JSONL can be one message per line:

```json
{"session_id":"s3","role":"user","text":"The login flow is slow and then fails again","resolved":false}
```

Or one trace per line:

```json
{"session_id":"s1","messages":[{"role":"user","text":"I need export as PDF","resolved":false}]}
```

CSV is also supported with columns such as `session_id,role,text,resolved,ts`.

## Output

- total messages
- dissatisfied message count
- todos grouped by user intent
- priority
- affected sessions
- recommended product fix
- timestamp/session evidence

Use JSON for automation and Markdown for daily or weekly product review. Markdown evidence is
truncated so the report stays readable; keep the original trace file local for deeper debugging.

Evidence text is redacted by default before it appears in JSON or Markdown reports. Common tokens,
`key=value` secrets, email addresses, and phone numbers are replaced with placeholders. Use
`--raw-evidence` only for local debugging when the output will stay private.

## What To Build Next

- LangSmith, Langfuse, OpenTelemetry, and custom trace adapters.
- LLM-assisted intent clustering.
- Weekly todo reports by release.
- PRD generation from repeated todos.
- Regression checks after fixes ship.

## Boundaries

- This is not a sentiment dashboard; it emits product work with evidence.
- This does not send traces to an external service.
- This does not auto-create tickets yet; keep humans in the prioritization loop.

## Local Review

```bash
scripts/pr_review_check.sh
```
