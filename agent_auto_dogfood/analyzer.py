from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STRICT_NEGATIVE_TERMS = {
    "bad",
    "broken",
    "confusing",
    "doesn't work",
    "didn't work",
    "fail",
    "failed",
    "frustrated",
    "hate",
    "incorrect",
    "not helpful",
    "slow",
    "stuck",
    "useless",
    "what the heck",
    "wrong",
    "same issue",
    "不对",
    "不好唱",
    "不好用",
    "不自然",
    "不押韵",
    "卡住",
    "卡住了",
    "啥也没发生",
    "没发生",
    "没更新",
    "没有改",
    "太差",
    "太奇怪",
    "没用",
    "没救",
    "有毛病",
    "生硬",
    "空了",
    "怪",
    "还在",
    "错",
}

CONTEXTUAL_NEGATIVE_TERMS = {
    "不好",
    "不会",
    "不能",
}

COMPLAINT_CONTEXT_TERMS = {
    "accuracy",
    "agent",
    "api",
    "bug",
    "error",
    "fail",
    "failed",
    "latency",
    "tool",
    "wrong",
    "不行",
    "不能用",
    "你",
    "功能",
    "又",
    "咋",
    "怎么",
    "没",
    "没有",
    "还是",
    "还",
    "错",
}

INTENT_PATTERNS = {
    "export": ("export", "download", "pdf", "csv", "导出", "下载"),
    "login": ("login", "sign in", "auth", "password", "登录", "密码"),
    "accuracy": ("wrong", "incorrect", "hallucination", "不对", "错", "瞎编"),
    "latency": ("slow", "timeout", "卡", "慢", "latency"),
    "handoff": ("human", "support", "escalate", "handoff", "人工", "客服"),
    "tool_failure": ("tool", "api", "error", "exception", "failed", "报错"),
    "state_update": (
        "same issue",
        "same bug",
        "still wrong",
        "still broken",
        "still there",
        "还在",
        "没更新",
        "没有改",
        "啥也没发生",
    ),
    "creative_quality": ("歌词", "押韵", "好唱", "质感", "生硬", "空了", "扎心", "不自然"),
    "voice_transcription": (
        "voice",
        "transcript",
        "transcriber",
        "accuracy",
        "latency",
        "中英文",
        "转录",
        "语音",
    ),
    "process_compliance": ("pr-review", "commit", "push", "upload", "validate", "验证", "提交"),
    "ci_status": (
        "ci",
        "github actions",
        "run failed",
        "workflow",
        "head",
        "commit",
        "actions/runs",
    ),
    "iterate_until_clean": (
        "fix all",
        "find bug fix bug",
        "until no more",
        "until no more fixes",
        "keep improve",
        "continue until",
        "run it again",
    ),
    "product_recommendation_quality": (
        "不好用",
        "掉灰",
        "点不着",
        "产品",
        "recommendation",
        "recommended",
    ),
    "advice_plan_quality": (
        "方案",
        "计划",
        "怎么安排",
        "为啥不能",
        "make sense",
        "does this make sense",
        "plan",
        "schedule",
    ),
    "finance_analysis_quality": (
        "开盘",
        "价格",
        "亏",
        "涨",
        "portfolio",
        "stock",
        "position",
        "market",
        "ticker",
        "missing ticker",
        "没有mu",
    ),
    "source_verification": (
        "上网查",
        "查一下",
        "source",
        "verify",
        "look up",
        "search web",
    ),
    "review_validation": (
        "vet",
        "review again",
        "validate again",
        "再检查",
        "重新检查",
    ),
    "execution_quality": (
        "质量差",
        "继续改",
        "一直停",
        "停干",
        "只干",
        "keep going",
        "keep improving",
    ),
    "failure_mode_quality": (
        "failure mode",
        "won't fail",
        "no use",
        "disable notification",
        "that's your solution",
    ),
}


@dataclass(frozen=True)
class Message:
    session_id: str
    role: str
    text: str
    ts: str = ""
    resolved: bool | None = None


def load_messages(path: str | Path) -> list[Message]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        with source.open(newline="", encoding="utf-8") as handle:
            return [_message_from_dict(row) for row in csv.DictReader(handle)]
    messages = []
    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at {source}:{line_number}: {error}") from error
            if isinstance(payload.get("messages"), list):
                session_id = str(payload.get("session_id") or payload.get("id") or line_number)
                for item in payload["messages"]:
                    record = dict(item)
                    record.setdefault("session_id", session_id)
                    messages.append(_message_from_dict(record))
            else:
                messages.append(_message_from_dict(payload))
    return messages


def _message_from_dict(row: dict[str, Any]) -> Message:
    text = str(row.get("text") or row.get("content") or row.get("message") or "")
    if not text:
        raise ValueError(f"message is missing text/content: {row}")
    resolved_value = row.get("resolved")
    resolved = None
    if isinstance(resolved_value, bool):
        resolved = resolved_value
    elif isinstance(resolved_value, str) and resolved_value:
        resolved = resolved_value.lower() in {"1", "true", "yes", "resolved"}
    return Message(
        session_id=str(row.get("session_id") or row.get("trace_id") or row.get("id") or "unknown"),
        role=str(row.get("role") or "user"),
        text=text,
        ts=str(row.get("ts") or row.get("timestamp") or ""),
        resolved=resolved,
    )


def classify_message(message: Message) -> dict[str, Any]:
    lowered = message.text.lower()
    task_prompt = _looks_like_task_prompt(message.text, lowered)
    negative_hits = [] if task_prompt else _negative_hits(message.text, lowered)
    intents = [
        name
        for name, terms in INTENT_PATTERNS.items()
        if any(_contains_term(message.text, lowered, term) for term in terms)
    ]
    repeated_question = bool(
        re.search(
            r"\b(same issue|still (wrong|broken|there|failing|not|bad))\b",
            lowered,
        )
        or any(
            term in message.text
            for term in ("还在", "还是没", "还是不", "又没", "又不", "没有改", "没更新")
        )
    )
    unresolved = message.resolved is False
    base_signal = len(negative_hits) + repeated_question + unresolved
    process_request = "iterate_until_clean" in intents
    score = 0.0
    if base_signal or process_request:
        score = base_signal + len(intents) * 0.5
    if process_request and score < 1.0:
        score = 1.0
    if task_prompt:
        score = 0.0
    return {
        "session_id": message.session_id,
        "role": message.role,
        "text": message.text,
        "ts": message.ts,
        "negative_terms": negative_hits,
        "intents": intents or ["unknown"],
        "repeated_question": repeated_question,
        "unresolved": unresolved,
        "dissatisfaction_score": round(score, 2),
    }


def _negative_hits(text: str, lowered: str) -> list[str]:
    hits = {term for term in STRICT_NEGATIVE_TERMS if _contains_term(text, lowered, term)}
    if any(_contains_term(text, lowered, term) for term in COMPLAINT_CONTEXT_TERMS):
        hits.update(
            term for term in CONTEXTUAL_NEGATIVE_TERMS if _contains_term(text, lowered, term)
        )
    return sorted(hits)


def _contains_term(text: str, lowered: str, term: str) -> bool:
    lowered_term = term.lower()
    if lowered_term.isascii():
        pattern = rf"(?<![a-z0-9]){re.escape(lowered_term)}(?![a-z0-9])"
        return re.search(pattern, lowered) is not None
    return lowered_term in lowered or term in text


def _looks_like_task_prompt(text: str, lowered: str) -> bool:
    task_markers = (
        "you are reviewing",
        "find correctness bugs",
        "rank by severity",
        "here is the core loop",
        "domain-agnostic",
    )
    complaint_markers = (
        "what the heck",
        "why not",
        "still wrong",
        "still broken",
        "质量差",
        "你为什么",
        "你怎么",
    )
    return any(marker in lowered for marker in task_markers) and not any(
        marker in lowered or marker in text for marker in complaint_markers
    )


def build_action_items(messages: list[Message], min_score: float = 1.0) -> dict[str, Any]:
    classified = [classify_message(message) for message in messages if message.role != "assistant"]
    pain = [item for item in classified if item["dissatisfaction_score"] >= min_score]
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in pain:
        for intent in item["intents"]:
            buckets[intent].append(item)

    action_items = []
    for intent, items in sorted(
        buckets.items(),
        key=lambda pair: (-sum(i["dissatisfaction_score"] for i in pair[1]), pair[0]),
    ):
        examples = items[:3]
        sessions = sorted({item["session_id"] for item in items})
        terms = Counter(term for item in items for term in item["negative_terms"])
        action_items.append(
            {
                "intent": intent,
                "priority": _priority(items),
                "affected_sessions": len(sessions),
                "dissatisfaction_total": round(sum(i["dissatisfaction_score"] for i in items), 2),
                "top_negative_terms": [term for term, _count in terms.most_common(5)],
                "recommended_action": _recommended_action(intent),
                "evidence": [
                    {
                        "session_id": item["session_id"],
                        "ts": item["ts"],
                        "text": item["text"],
                    }
                    for item in examples
                ],
            }
        )
    return {
        "total_messages": len(messages),
        "dissatisfied_messages": len(pain),
        "action_items": action_items,
    }


def _priority(items: list[dict[str, Any]]) -> str:
    total = sum(item["dissatisfaction_score"] for item in items)
    if total >= 8 or len(items) >= 5:
        return "high"
    if total >= 3 or len(items) >= 2:
        return "medium"
    return "low"


def _recommended_action(intent: str) -> str:
    return {
        "export": "Add or repair export flow; include PDF/CSV acceptance tests.",
        "login": "Audit authentication failure path, copy, retries, and support handoff.",
        "accuracy": "Review answer grounding, retrieval coverage, and hallucination guardrails.",
        "latency": "Profile slow traces and add timeout/retry visibility.",
        "handoff": "Improve escalation trigger and human handoff instructions.",
        "tool_failure": "Fix failing tool/API path and add trace-level error reporting.",
        "state_update": (
            "Compare latest output against the requested change and block completion if the "
            "same defect remains."
        ),
        "creative_quality": (
            "Extract concrete style constraints, preserve locked text, and verify rhyme/"
            "singability before responding."
        ),
        "voice_transcription": (
            "Measure mixed-language accuracy and latency from real traces before changing "
            "transcription defaults."
        ),
        "process_compliance": (
            "Turn repeated workflow instructions into preflight checks that run before commit, "
            "push, or completion."
        ),
        "ci_status": (
            "When a user shows a failed CI notification, compare the failed commit to the latest "
            "remote head and latest workflow run before reporting status; stale failures should "
            "be labeled as old runs, while current-head failures must be fixed."
        ),
        "iterate_until_clean": (
            "Treat fix-all requests as a loop: inspect, patch, run validation, inspect the new "
            "output, and repeat until clean or concretely blocked."
        ),
        "product_recommendation_quality": (
            "When product advice is challenged, verify the exact product behavior and user "
            "constraints before recommending alternatives."
        ),
        "advice_plan_quality": (
            "Expose the assumptions behind a plan, then re-check the plan against the user's "
            "constraints instead of defending the first answer."
        ),
        "finance_analysis_quality": (
            "Use the user's actual fill prices, lots, and timestamps before judging P&L or "
            "portfolio performance."
        ),
        "source_verification": (
            "When the user asks why sources were not checked, verify current external facts "
            "before answering and cite the source boundary."
        ),
        "review_validation": (
            "Treat review-again requests as a validation pass: inspect the artifact, report "
            "specific findings, and fix concrete defects found."
        ),
        "execution_quality": (
            "When the user says work quality is low or progress keeps stopping, continue the "
            "implementation loop and validate concrete improvements before responding."
        ),
        "failure_mode_quality": (
            "Do not hide failures by disabling signals; preserve observability and fix the "
            "underlying failure mode."
        ),
        "unknown": "Review examples manually and add a new intent classifier pattern.",
    }.get(intent, "Review examples and convert repeated failure into a product fix.")
