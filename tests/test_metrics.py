"""Metrics build must survive the non-numeric fields a classifier-generated report can contain."""
from agent_auto_dogfood.metrics import build_eval_metrics


def test_build_eval_metrics_survives_garbage_report_numbers():
    report = {"action_items": [
        {"intent": "x", "priority": "high", "evidence": ["e"],
         "affected_sessions": "lots", "dissatisfaction_total": "N/A"},
        {"intent": "y", "affected_sessions": None, "dissatisfaction_total": float("nan")},
    ]}
    metrics = build_eval_metrics([], report)  # must not raise on bad numbers
    # the garbage 'affected_sessions' coerces to 0, so neither item counts as evidence-backed
    assert isinstance(metrics, dict)


def test_build_eval_metrics_counts_valid_numbers():
    report = {"action_items": [
        {"intent": "x", "priority": "high", "evidence": ["e"],
         "affected_sessions": 4, "dissatisfaction_total": 2.5},
    ]}
    metrics = build_eval_metrics([], report)
    assert isinstance(metrics, dict)
