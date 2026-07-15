"""Synthetic semantic-model and improvement-loop tests."""

import pytest

from careops_process.improve import ActivityMetric, recommend_improvements


def test_recommendations_are_guardrail_driven_and_ranked() -> None:
    """High-priority dual breaches are returned before single breaches."""
    metrics = [
        ActivityMetric("decided", 10, 30.0, 0.2),
        ActivityMetric("escalated", 2, 40.0, 0.8),
        ActivityMetric("received", 10, 1.0, 0.0),
    ]
    actions = recommend_improvements(metrics, duration_limit_hours=24.0, deviation_limit=0.5)
    assert [action.activity for action in actions] == ["escalated", "decided"]
    assert actions[0].priority == "high"


def test_clean_metrics_produce_no_automation() -> None:
    """Healthy activities do not generate speculative changes."""
    metric = ActivityMetric("received", 1, 1.0, 0.0)
    assert recommend_improvements([metric], duration_limit_hours=24.0, deviation_limit=0.5) == []


def test_invalid_guardrails_fail_closed() -> None:
    """Invalid policy limits cannot create recommendations."""
    with pytest.raises(ValueError, match="guardrails"):
        recommend_improvements([], duration_limit_hours=0, deviation_limit=0.5)
