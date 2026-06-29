from __future__ import annotations

from collections import Counter
from typing import Any

from .analyzer import Message, redact_text

MEMORY_READ_TERMS = (
    "read memory",
    "search memory",
    "look at memory",
    "past memory",
    "memory file",
    "读记忆",
    "查记忆",
)
MEMORY_WRITE_TERMS = (
    "update memory",
    "update memory",
    "checkpoint",
    "save as",
    "记下来",
    "更新记忆",
)
MEMORY_MISS_TERMS = (
    "already told you",
    "i said",
    "you forgot",
    "don't ask again",
    "why are you asking",
    "read again",
    "我说了",
    "不是说了",
    "你忘了",
    "还问",
)
CONTEXT_PRESSURE_TERMS = (
    "compact",
    "context window",
    "long context",
    "run /compact",
    "上下文",
    "压缩",
)


def build_memory_benchmark(messages: list[Message], *, redact: bool = True) -> dict[str, Any]:
    user_messages = [message for message in messages if message.role != "assistant"]
    classified = [_classify_memory(message) for message in user_messages]
    findings = [item for item in classified if item["signals"]]
    sessions = {message.session_id for message in user_messages}
    affected_sessions = {item["session_id"] for item in findings}
    signal_counts = Counter(signal for item in findings for signal in item["signals"])
    session_counts = Counter(message.session_id for message in user_messages)
    repeated_sessions = sum(
        1
        for count in session_counts.values()
        if count > 1
    )
    score = _score(signal_counts, repeated_sessions, len(sessions))
    return {
        "total_user_messages": len(user_messages),
        "sessions": len(sessions),
        "memory_signal_messages": len(findings),
        "affected_sessions": len(affected_sessions),
        "memory_read_requests": signal_counts.get("memory_read", 0),
        "memory_update_requests": signal_counts.get("memory_update", 0),
        "memory_miss_complaints": signal_counts.get("memory_miss", 0),
        "context_pressure": signal_counts.get("context_pressure", 0),
        "repeated_session_rate": _ratio(repeated_sessions, len(sessions)),
        "memory_risk_score": score,
        "recommendation": _recommendation(score, signal_counts),
        "evidence": [
            {
                "session_id": item["session_id"],
                "ts": item["ts"],
                "signals": item["signals"],
                "text": redact_text(item["text"]) if redact else item["text"],
            }
            for item in findings[:8]
        ],
    }


def render_memory_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Memory Benchmark",
        "",
        f"- User messages: {report.get('total_user_messages', 0)}",
        f"- Sessions: {report.get('sessions', 0)}",
        f"- Memory signal messages: {report.get('memory_signal_messages', 0)}",
        f"- Affected sessions: {report.get('affected_sessions', 0)}",
        f"- Memory read requests: {report.get('memory_read_requests', 0)}",
        f"- Memory update requests: {report.get('memory_update_requests', 0)}",
        f"- Memory-miss complaints: {report.get('memory_miss_complaints', 0)}",
        f"- Context pressure: {report.get('context_pressure', 0)}",
        f"- Repeated session rate: {_pct(report.get('repeated_session_rate', 0))}",
        f"- Memory risk score: {report.get('memory_risk_score', 0)}",
        f"- Recommendation: {report.get('recommendation', '')}",
        "",
        "## Evidence",
        "",
    ]
    evidence = report.get("evidence") or []
    if not evidence:
        lines.append("No memory-specific signals found.")
        return "\n".join(lines) + "\n"
    for item in evidence:
        signals = ", ".join(item.get("signals") or [])
        text = str(item.get("text") or "")
        if len(text) > 180:
            text = text[:177] + "..."
        lines.append(f"- {item.get('session_id', '')}: {signals} — {text}")
    return "\n".join(lines) + "\n"


def _classify_memory(message: Message) -> dict[str, Any]:
    text = message.text
    lowered = text.lower()
    signals = []
    if _has_any(text, lowered, MEMORY_READ_TERMS):
        signals.append("memory_read")
    if _has_any(text, lowered, MEMORY_WRITE_TERMS):
        signals.append("memory_update")
    if _has_any(text, lowered, MEMORY_MISS_TERMS):
        signals.append("memory_miss")
    if _has_any(text, lowered, CONTEXT_PRESSURE_TERMS):
        signals.append("context_pressure")
    return {
        "session_id": message.session_id,
        "ts": message.ts,
        "text": text,
        "signals": signals,
    }


def _has_any(text: str, lowered: str, terms: tuple[str, ...]) -> bool:
    return any(term in lowered or term in text for term in terms)


def _score(signal_counts: Counter[str], repeated_sessions: int, session_count: int) -> int:
    score = (
        signal_counts.get("memory_miss", 0) * 4
        + signal_counts.get("context_pressure", 0) * 2
        + signal_counts.get("memory_read", 0)
        + signal_counts.get("memory_update", 0)
    )
    if session_count:
        score += round((repeated_sessions / session_count) * 3)
    return int(score)


def _recommendation(score: int, signal_counts: Counter[str]) -> str:
    if signal_counts.get("memory_miss", 0):
        return "Add a regression fixture for memory recall before changing prompts."
    if signal_counts.get("context_pressure", 0):
        return "Add compact-safe state summaries and test them across long sessions."
    if score:
        return "Track memory reads and writes as explicit dogfood metrics."
    return "No memory-specific action needed."


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
