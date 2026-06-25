# Agent Auto Dogfood

[![CI](https://github.com/yingchen-coding/agent-auto-dogfood/actions/workflows/ci.yml/badge.svg)](https://github.com/yingchen-coding/agent-auto-dogfood/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Agent Auto Dogfood turns AI-agent traces into product todos with evidence.

The premise is simple: if an agent frustrates users, repeats a bad answer, fails a tool call, or
cannot complete an export/login/accuracy workflow, that trace should become a concrete todo with
evidence. The agent system should dogfood itself by reading its own traces and producing the next
fix list.

## Star This If

- You run agents and need to know why users are unhappy without reading every trace.
- You want a deterministic, local alternative to dashboard screenshots and anecdotal bug reports.
- You want every product todo tied to sessions, examples, and a proposed fix.

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
