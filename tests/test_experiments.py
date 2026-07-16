"""Human review and improvement experiment tests."""

from careops_process.experiments import create_experiment, record_review


def test_accepted_review_activates_measurement_only() -> None:
    """Explicit human acceptance activates an experiment without mutation."""
    experiment = create_experiment(
        experiment_id="baseline-1",
        hypothesis="Approval turnaround remains within guardrails",
        guardrails={"duration_hours": 48.0},
        baseline={"mean_duration_hours": 0.01},
    )
    reviewed = record_review(
        experiment,
        status="accepted",
        reviewer="executive-review",
        note="Sample reviewed for baseline measurement.",
    )
    assert reviewed.status == "active"
    assert reviewed.review.status == "accepted"


def test_rejected_review_cancels_experiment() -> None:
    """A rejected finding cannot become an active experiment."""
    experiment = create_experiment(
        experiment_id="baseline-2",
        hypothesis="Test",
        guardrails={"duration_hours": 48.0},
        baseline={"mean_duration_hours": 0.01},
    )
    reviewed = record_review(
        experiment, status="rejected", reviewer="reviewer", note="Not representative"
    )
    assert reviewed.status == "cancelled"
