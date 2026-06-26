import json
import subprocess
import sys

from agent_auto_dogfood.analyzer import (
    Message,
    build_action_items,
    classify_message,
    load_messages,
    redact_text,
    render_markdown,
)


def test_trace_messages_become_prioritized_action_items():
    messages = load_messages("examples/traces.jsonl")
    report = build_action_items(messages)
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "export" in intents
    assert "accuracy" in intents
    assert "login" in intents
    assert intents["export"]["recommended_action"].startswith("Add or repair export")


def test_min_score_filters_low_signal_messages():
    messages = load_messages("examples/traces.jsonl")
    report = build_action_items(messages, min_score=4)
    assert report["dissatisfied_messages"] < len(messages)


def test_repeated_chinese_feedback_is_state_update():
    item = classify_message(
        Message(
            session_id="lyrics",
            role="user",
            text="还在，你自己看刚刚的输出，怎么完全没更新",
        )
    )
    assert "state_update" in item["intents"]
    assert item["repeated_question"] is True
    assert item["dissatisfaction_score"] >= 3


def test_creative_quality_feedback_is_actionable():
    report = build_action_items(
        [
            Message(
                session_id="lyrics",
                role="user",
                text="不好唱，押韵不自然，有点空了，要更真实更扎心",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "creative_quality" in intents
    assert "verify rhyme" in intents["creative_quality"]["recommended_action"]


def test_voice_transcription_feedback_is_grouped():
    report = build_action_items(
        [
            Message(
                session_id="voice",
                role="user",
                text="中英文夹杂不行，accuracy不好，latency也要提高",
            )
        ]
    )
    intents = {item["intent"] for item in report["action_items"]}
    assert "voice_transcription" in intents


def test_ci_failure_notification_requires_latest_head_check():
    report = build_action_items(
        [
            Message(
                session_id="repo",
                role="user",
                text=(
                    "[yingchen-coding/event-graph] Run failed: CI - main (f6de7ff) "
                    "what the heck"
                ),
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "ci_status" in intents
    assert "latest remote head" in intents["ci_status"]["recommended_action"]


def test_fix_all_until_clean_is_not_unknown():
    report = build_action_items(
        [
            Message(
                session_id="quality",
                role="user",
                text="fix all, find bug fix bug, run it again until no more fixes are needed",
            )
        ]
    )
    intents = {item["intent"] for item in report["action_items"]}
    assert "iterate_until_clean" in intents
    assert "unknown" not in intents


def test_neutral_chinese_ability_question_is_not_dissatisfaction():
    item = classify_message(
        Message(
            session_id="medical",
            role="user",
            text="所以做按摩跟艾灸有关系吗，能不能做按摩",
        )
    )
    assert item["negative_terms"] == []
    assert item["dissatisfaction_score"] == 0


def test_chinese_tool_complaint_still_counts():
    item = classify_message(
        Message(
            session_id="repo",
            role="user",
            text="这个功能不能用，你怎么还不会改",
        )
    )
    assert "不能" in item["negative_terms"]
    assert "不会" in item["negative_terms"]
    assert item["dissatisfaction_score"] >= 2


def test_accuracy_complaint_keeps_contextual_negative_term():
    item = classify_message(
        Message(
            session_id="voice",
            role="user",
            text="accuracy不好，latency也要提高",
        )
    )
    assert "不好" in item["negative_terms"]
    assert "voice_transcription" in item["intents"]


def test_intent_keyword_without_complaint_is_not_dissatisfaction():
    item = classify_message(
        Message(
            session_id="repo",
            role="user",
            text="commit and push",
        )
    )
    assert "process_compliance" in item["intents"]
    assert item["dissatisfaction_score"] == 0


def test_generic_haishi_question_is_not_repeated_failure():
    item = classify_message(
        Message(
            session_id="finance",
            role="user",
            text="这几股有在亏还是在涨",
        )
    )
    assert item["repeated_question"] is False
    assert item["dissatisfaction_score"] == 0


def test_unfixed_chinese_repeated_failure_still_counts():
    item = classify_message(
        Message(
            session_id="lyrics",
            role="user",
            text="还是没更新，刚才的问题还在",
        )
    )
    assert item["repeated_question"] is True
    assert item["dissatisfaction_score"] >= 2


def test_product_recommendation_complaint_is_not_unknown():
    report = build_action_items(
        [
            Message(
                session_id="shopping",
                role="user",
                text="之前买的这个产品非常不好用，根本老是掉灰，而且又点不着。",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "product_recommendation_quality" in intents
    assert "unknown" not in intents


def test_advice_plan_complaint_is_not_unknown():
    report = build_action_items(
        [
            Message(
                session_id="planning",
                role="user",
                text="为啥不能每天换？是因为你这个方案不好吗？",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "advice_plan_quality" in intents
    assert "unknown" not in intents


def test_finance_assumption_complaint_is_not_unknown():
    report = build_action_items(
        [
            Message(
                session_id="finance",
                role="user",
                text="你又不是开盘买的，凭什么用开盘的价格？",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "finance_analysis_quality" in intents
    assert "unknown" not in intents


def test_failover_code_review_prompt_does_not_match_fail():
    item = classify_message(
        Message(
            session_id="code-review",
            role="user",
            text=(
                "You are reviewing the failover logic of a quota-aware model router. "
                "The plan.order list chooses provider names by task."
            ),
        )
    )
    assert "fail" not in item["negative_terms"]
    assert item["dissatisfaction_score"] == 0


def test_long_code_review_task_prompt_is_not_dissatisfaction():
    item = classify_message(
        Message(
            session_id="code-review",
            role="user",
            text=(
                "You are reviewing the failover logic of a quota-aware model router. "
                "Find correctness bugs in this prediction-eval scorer. "
                "Rank by severity and be concrete."
            ),
        )
    )
    assert item["negative_terms"] == []
    assert item["dissatisfaction_score"] == 0


def test_web_lookup_complaint_is_source_verification():
    report = build_action_items(
        [
            Message(
                session_id="job",
                role="user",
                text="你为什么不能够上网查一下，而且datavace有什么关系。",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "source_verification" in intents
    assert "unknown" not in intents


def test_missing_ticker_complaint_is_finance_quality():
    report = build_action_items(
        [
            Message(
                session_id="stocks",
                role="user",
                text="还是没有MU？",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "finance_analysis_quality" in intents
    assert "unknown" not in intents


def test_vet_again_is_review_validation_not_repeated_failure():
    item = classify_message(
        Message(
            session_id="review",
            role="user",
            text="vet again",
        )
    )
    assert "review_validation" in item["intents"]
    assert item["repeated_question"] is False
    assert item["dissatisfaction_score"] == 0


def test_execution_quality_complaint_is_not_unknown():
    report = build_action_items(
        [
            Message(
                session_id="quality",
                role="user",
                text="你每天给我干两分钟是什么意思？质量差就是差，改的不好就是不好，能不能继续改？一直停干什么？",
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "execution_quality" in intents
    assert "unknown" not in intents


def test_failure_mode_complaint_is_not_unknown():
    report = build_action_items(
        [
            Message(
                session_id="robustness",
                role="user",
                text=(
                    "really? that's your solution? disable notification so it won't fail. "
                    "the only one no failure mode is no use"
                ),
            )
        ]
    )
    intents = {item["intent"]: item for item in report["action_items"]}
    assert "failure_mode_quality" in intents
    assert "unknown" not in intents


def test_already_shared_context_is_not_repeated_failure():
    item = classify_message(
        Message(
            session_id="offer",
            role="user",
            text="google offer, target already shared one week ago, today is follow up call",
        )
    )
    assert item["repeated_question"] is False
    assert item["dissatisfaction_score"] == 0


def test_markdown_report_truncates_evidence():
    report = build_action_items(
        [
            Message(
                session_id="s1",
                role="user",
                text="wrong " + ("very long detail " * 30),
                resolved=False,
            )
        ]
    )
    markdown = render_markdown(report, max_evidence_chars=80)
    assert "# Agent Dogfood Todos" in markdown
    assert "## 1. accuracy" in markdown
    assert "Recommended action" in markdown
    assert "very long detail very long detail" in markdown
    assert len(markdown) < 1200


def test_reports_redact_sensitive_evidence_by_default():
    report = build_action_items(
        [
            Message(
                session_id="sensitive",
                role="user",
                text=(
                    "export failed for ying@example.com with token=abc123secret "
                    "and phone 415-555-1212"
                ),
                resolved=False,
            )
        ]
    )
    text = report["action_items"][0]["evidence"][0]["text"]
    assert "ying@example.com" not in text
    assert "abc123secret" not in text
    assert "415-555-1212" not in text
    assert "[REDACTED_EMAIL]" in text
    assert "[REDACTED_SECRET]" in text
    assert "[REDACTED_PHONE]" in text


def test_raw_evidence_can_be_requested_explicitly():
    report = build_action_items(
        [
            Message(
                session_id="sensitive",
                role="user",
                text="export failed for ying@example.com",
                resolved=False,
            )
        ],
        redact=False,
    )
    assert "ying@example.com" in report["action_items"][0]["evidence"][0]["text"]


def test_redact_text_covers_github_style_tokens():
    token = "gh" + "p_" + ("x" * 24)
    assert redact_text(f"tool failed with {token}") == "tool failed with [REDACTED_TOKEN]"


def test_cli_can_emit_markdown(tmp_path):
    trace = tmp_path / "traces.jsonl"
    trace.write_text(
        json.dumps(
            {
                "session_id": "s1",
                "role": "user",
                "text": "export failed again and the pdf download is broken",
                "resolved": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "agent_auto_dogfood", str(trace), "--format", "markdown"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "# Agent Dogfood Todos" in result.stdout
    assert "export" in result.stdout
