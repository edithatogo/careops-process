# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Human review and improvement experiment tests."""

from typing import Any

import pytest

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


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"experiment_id": "", "hypothesis": "x"}, "required"),
        ({"experiment_id": "x", "hypothesis": ""}, "required"),
        ({"experiment_id": "x", "hypothesis": "x", "guardrails": {}}, "non-negative"),
        ({"experiment_id": "x", "hypothesis": "x", "guardrails": {"x": -1}}, "non-negative"),
        (
            {"experiment_id": "x", "hypothesis": "x", "guardrails": {"x": 1}, "baseline": {}},
            "baseline",
        ),
    ],
)
def test_invalid_experiment_inputs_fail_closed(kwargs: dict[str, object], message: str) -> None:
    """Invalid experiment definitions cannot enter the review queue."""
    defaults: dict[str, Any] = {"guardrails": {"x": 1.0}, "baseline": {"metric": 1.0}}
    defaults.update(kwargs)
    with pytest.raises(ValueError, match=message):
        create_experiment(**defaults)  # type: ignore[arg-type]


def test_review_requires_reviewer_and_note() -> None:
    """A status without accountable review metadata is rejected."""
    experiment = create_experiment(
        experiment_id="baseline-3",
        hypothesis="Test",
        guardrails={"duration_hours": 48.0},
        baseline={"mean_duration_hours": 0.01},
    )
    with pytest.raises(ValueError, match="required"):
        record_review(experiment, status="accepted", reviewer="", note="note")
