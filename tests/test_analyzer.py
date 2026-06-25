from agent_auto_dogfood.analyzer import build_action_items, load_messages


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
