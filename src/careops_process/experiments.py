"""Human-reviewed improvement experiments with no automatic mutations."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal

ReviewStatus = Literal["pending", "accepted", "rejected"]
ExperimentStatus = Literal["proposed", "active", "complete", "cancelled"]


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    """A human decision about whether an observed finding is representative."""

    status: ReviewStatus
    reviewer: str | None = None
    note: str | None = None
    decided_at_utc: datetime | None = None


@dataclass(frozen=True, slots=True)
class ImprovementExperiment:
    """A measurable experiment that requires explicit human acceptance."""

    experiment_id: str
    hypothesis: str
    guardrails: dict[str, float]
    baseline: dict[str, float]
    review: ReviewDecision
    status: ExperimentStatus = "proposed"


def create_experiment(
    *,
    experiment_id: str,
    hypothesis: str,
    guardrails: dict[str, float],
    baseline: dict[str, float],
) -> ImprovementExperiment:
    """Create a proposed experiment without changing any external workflow."""
    if not experiment_id or not hypothesis:
        message = "experiment_id and hypothesis are required"
        raise ValueError(message)
    if not guardrails or any(value < 0 for value in guardrails.values()):
        message = "guardrails must contain non-negative values"
        raise ValueError(message)
    if not baseline:
        message = "baseline must contain at least one metric"
        raise ValueError(message)
    return ImprovementExperiment(
        experiment_id=experiment_id,
        hypothesis=hypothesis,
        guardrails=dict(guardrails),
        baseline=dict(baseline),
        review=ReviewDecision("pending"),
    )


def record_review(
    experiment: ImprovementExperiment,
    *,
    status: ReviewStatus,
    reviewer: str,
    note: str,
) -> ImprovementExperiment:
    """Record a human review; acceptance activates measurement only."""
    if not reviewer or not note:
        message = "reviewer and note are required"
        raise ValueError(message)
    review = ReviewDecision(status, reviewer, note, datetime.now(UTC))
    next_status: ExperimentStatus = "active" if status == "accepted" else "cancelled"
    return replace(experiment, review=review, status=next_status)
