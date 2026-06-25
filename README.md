# Agent Auto Dogfood

Agent Auto Dogfood turns AI-agent traces into product todos.

The premise is simple: if an agent frustrates users, repeats a bad answer, fails a tool call, or
cannot complete an export/login/accuracy workflow, that trace should become a concrete todo with
evidence. The agent system should dogfood itself by reading its own traces and producing the next
fix list.

## What It Does

- Reads JSONL or CSV agent traces.
- Detects user dissatisfaction and repeated failure signals.
- Groups failures by intent such as export, login, accuracy, latency, handoff, and tool failure.
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

## What To Build Next

- LangSmith, Langfuse, OpenTelemetry, and custom trace adapters.
- LLM-assisted intent clustering.
- Weekly todo reports by release.
- PRD generation from repeated todos.
- Regression checks after fixes ship.
