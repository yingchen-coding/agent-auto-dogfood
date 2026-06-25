from agent_auto_dogfood.analyzer import Message, build_action_items, classify_message, load_messages


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
