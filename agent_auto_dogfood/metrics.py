from __future__ import annotations

from collections import Counter
from typing import Any

from .analyzer import Message, classify_message


def build_eval_metrics(messages: list[Message], report: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic completion and evidence metrics from local traces."""
    user_messages = [message for message in messages if message.role != "assistant"]
    classified = [classify_message(message) for message in user_messages]
    sessions = {message.session_id for message in user_messages}
    resolved_sessions = {
        message.session_id for message in user_messages if message.resolved is True
    }
    unresolved_sessions = {
        message.session_id for message in user_messages if message.resolved is False
    }
    repeated_failures = [item for item in classified if item["repeated_question"]]
    dissatisfied = [
        item for item in classified if _num(item.get("dissatisfaction_score", 0)) > 0
    ]
    action_items = report.get("action_items", [])
    action_count = len(action_items)
    evidence_backed = [
        item
        for item in action_items
        if item.get("evidence") and _int(item.get("affected_sessions")) > 0
    ]
    priority_counts = Counter(str(item.get("priority") or "unknown") for item in action_items)
    intent_rows = []
    for item in action_items:
        affected_sessions = _int(item.get("affected_sessions"))
        total = _num(item.get("dissatisfaction_total"))
        intent_rows.append(
            {
                "intent": item.get("intent", "unknown"),
                "priority": item.get("priority", "unknown"),
                "affected_sessions": affected_sessions,
                "dissatisfaction_total": round(total, 2),
                "evidence_samples": len(item.get("evidence") or []),
            }
        )

    total_user_messages = len(user_messages)
    total_sessions = len(sessions)
    unresolved_message_count = sum(1 for message in user_messages if message.resolved is False)
    resolved_message_count = sum(1 for message in user_messages if message.resolved is True)

    return {
        "total_messages": len(messages),
        "user_messages": total_user_messages,
        "sessions": total_sessions,
        "resolved_sessions": len(resolved_sessions),
        "unresolved_sessions": len(unresolved_sessions),
        "completion_proxy": _ratio(len(resolved_sessions), total_sessions),
        "unresolved_message_rate": _ratio(unresolved_message_count, total_user_messages),
        "resolved_message_rate": _ratio(resolved_message_count, total_user_messages),
        "dissatisfied_message_rate": _ratio(len(dissatisfied), total_user_messages),
        "repeated_failure_rate": _ratio(len(repeated_failures), total_user_messages),
        "action_items": action_count,
        "high_priority_items": priority_counts.get("high", 0),
        "medium_priority_items": priority_counts.get("medium", 0),
        "low_priority_items": priority_counts.get("low", 0),
        "evidence_coverage": _ratio(len(evidence_backed), action_count),
        "top_intents": intent_rows,
    }


def render_metrics_markdown(metrics: dict[str, Any]) -> str:
    lines = [
        "# Agent Eval Metrics",
        "",
        f"- Total messages: {metrics.get('total_messages', 0)}",
        f"- User messages: {metrics.get('user_messages', 0)}",
        f"- Sessions: {metrics.get('sessions', 0)}",
        f"- Completion proxy: {_pct(metrics.get('completion_proxy', 0))}",
        f"- Unresolved message rate: {_pct(metrics.get('unresolved_message_rate', 0))}",
        f"- Dissatisfied message rate: {_pct(metrics.get('dissatisfied_message_rate', 0))}",
        f"- Repeated failure rate: {_pct(metrics.get('repeated_failure_rate', 0))}",
        f"- Evidence coverage: {_pct(metrics.get('evidence_coverage', 0))}",
        f"- Action items: {metrics.get('action_items', 0)}",
        f"- High-priority items: {metrics.get('high_priority_items', 0)}",
        "",
        "## Top Intents",
        "",
    ]
    intents = metrics.get("top_intents") or []
    if not intents:
        lines.append("No dissatisfied intents above the configured threshold.")
        return "\n".join(lines) + "\n"
    for item in intents:
        lines.append(
            "- {intent} ({priority}): {sessions} sessions, {total} dissatisfaction, "
            "{evidence} evidence samples".format(
                intent=item.get("intent", "unknown"),
                priority=item.get("priority", "unknown"),
                sessions=item.get("affected_sessions", 0),
                total=item.get("dissatisfaction_total", 0),
                evidence=item.get("evidence_samples", 0),
            )
        )
    return "\n".join(lines) + "\n"


def _num(value: Any) -> float:
    """Coerce a report field to float, tolerating the non-numeric values a classifier-generated
    JSON report can carry (a string, null, a truncated line). A single bad field must not crash the
    whole metrics build."""
    if value is None:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number and number not in (float("inf"), float("-inf")) else 0.0


def _int(value: Any) -> int:
    return int(_num(value))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number * 100:.1f}%"
