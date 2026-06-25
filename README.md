# Agent Feedback Actions

Agent Feedback Actions is a local Brizz-style prototype for AI-agent product analytics.

It reads AI conversation traces, finds dissatisfied user messages, groups them by intent, and turns
the evidence into prioritized action items. The goal is to move from "users are unhappy" to "ship
PDF export", "fix login failure", or "improve grounding for missing-file answers."

## Install

```bash
python -m pip install -e '.[dev]'
```

## Quick Start

```bash
agent-feedback-actions examples/traces.jsonl
agent-feedback-actions examples/traces.jsonl --out out/action-items.json
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
- action items grouped by user intent
- priority
- affected sessions
- recommended product fix
- timestamp/session evidence

## What To Build Next

- LLM-assisted intent labeling.
- Integration adapters for LangSmith, Langfuse, OpenTelemetry, and custom agent traces.
- Trend windows by week/release.
- PRD generation from repeated action items.
- Regression checks after fixes ship.
