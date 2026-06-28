from __future__ import annotations

from typing import Any


def build_harness_plan(report: dict[str, Any]) -> dict[str, Any]:
    """Turn ranked dogfood todos into a small experiment harness plan."""
    experiments = []
    for index, item in enumerate(report.get("action_items", []), start=1):
        intent = str(item.get("intent") or "unknown")
        recommended_action = str(item.get("recommended_action") or "")
        priority = str(item.get("priority") or "low")
        evidence = item.get("evidence") or []
        experiments.append(
            {
                "id": f"exp-{index:03d}-{intent.replace('_', '-')}",
                "intent": intent,
                "priority": priority,
                "hypothesis": _hypothesis(intent, recommended_action),
                "change": recommended_action,
                "regression_check": _regression_check(intent),
                "release_gate": _release_gate(priority, intent),
                "evidence_sessions": [
                    str(sample.get("session_id", "unknown"))
                    for sample in evidence
                    if isinstance(sample, dict)
                ],
            }
        )
    return {
        "total_messages": report.get("total_messages", 0),
        "dissatisfied_messages": report.get("dissatisfied_messages", 0),
        "experiments": experiments,
    }


def render_harness_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Agent Harness Plan",
        "",
        f"- Total messages: {plan.get('total_messages', 0)}",
        f"- Dissatisfied messages: {plan.get('dissatisfied_messages', 0)}",
        f"- Experiments: {len(plan.get('experiments', []))}",
        "",
    ]
    experiments = plan.get("experiments", [])
    if not experiments:
        lines.append("No experiments generated.")
        return "\n".join(lines) + "\n"

    for experiment in experiments:
        lines.extend(
            [
                f"## {experiment['id']} ({experiment['priority']})",
                "",
                f"- Intent: {experiment['intent']}",
                f"- Hypothesis: {experiment['hypothesis']}",
                f"- Change: {experiment['change']}",
                f"- Regression check: {experiment['regression_check']}",
                f"- Release gate: {experiment['release_gate']}",
            ]
        )
        sessions = experiment.get("evidence_sessions") or []
        if sessions:
            lines.append(f"- Evidence sessions: {', '.join(sessions)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _hypothesis(intent: str, recommended_action: str) -> str:
    if intent == "unknown":
        return "If we classify the repeated failure correctly, the next todo can become actionable."
    change = (recommended_action[0].lower() + recommended_action[1:]).rstrip(".")
    return f"If we {change}, user dissatisfaction for {intent} should drop."


def _regression_check(intent: str) -> str:
    checks = {
        "accuracy": (
            "Run a grounded-answer fixture that fails if cited files or facts are invented."
        ),
        "ci_status": (
            "Replay stale and current CI notifications; require latest-head status classification."
        ),
        "creative_quality": (
            "Replay locked-style prompts and verify constraints, rhyme, and singability notes."
        ),
        "export": "Run an end-to-end export fixture and assert the requested file artifact exists.",
        "iterate_until_clean": (
            "Run a failing fixture twice; require the second pass to inspect new output."
        ),
        "process_compliance": (
            "Run preflight checks before commit/push completion and fail on skipped evidence."
        ),
        "state_update": (
            "Replay a repeated-change request and assert the previous defect is absent."
        ),
        "tool_failure": (
            "Replay the failing tool path and assert the error is surfaced with a recovery action."
        ),
        "voice_transcription": (
            "Measure mixed-language transcript accuracy and latency on a fixed fixture."
        ),
    }
    return checks.get(
        intent,
        "Replay the evidence session and assert the repeated complaint no longer appears.",
    )


def _release_gate(priority: str, intent: str) -> str:
    if priority == "high":
        return f"Block release until the {intent} regression check passes and evidence is attached."
    if priority == "medium":
        return f"Require the {intent} regression check in the next release candidate."
    return f"Track the {intent} regression check; do not block release unless it repeats."
