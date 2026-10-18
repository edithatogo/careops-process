# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Human process-family review queue tests."""

import pytest

from careops_process.landscape import ProcessFamilyMetric, ProcessLandscape
from careops_process.review_queue import ReviewDecision, build_review_queue, record_review_decision


def landscape() -> ProcessLandscape:
    """Return family proposals with different uncertainty profiles."""
    return ProcessLandscape(
        included_event_count=20,
        included_object_count=10,
        families=(
            ProcessFamilyMetric("family-1", 8, 16, 2, ("created", "closed"), 0.9, 0.9, 0.6),
            ProcessFamilyMetric("family-2", 2, 4, 1, ("created",), 0.5, 0.5, 1.0),
        ),
    )


def test_review_queue_prioritizes_uncertain_source_dependent_family() -> None:
    """Ambiguous, single-source families are reviewed first."""
    queue = build_review_queue(landscape())

    assert queue[0].family_id == "family-2"
    assert queue[0].status == "pending"
    assert queue[0].evidence_reference == "family:family-2"


def test_review_decision_preserves_version_and_rationale() -> None:
    """Owner decisions are explicit and configuration-versioned."""
    item = build_review_queue(landscape())[0]
    decision = record_review_decision(
        item,
        decision=ReviewDecision.MERGE,
        reviewer_id="reviewer:r1",
        rationale_code="same_operational_process",
        configuration_version="discovery-1.0.0",
        target_family_ids=("family-1",),
    )

    assert decision.status == "decided"
    assert decision.decision is ReviewDecision.MERGE
    assert decision.target_family_ids == ("family-1",)


def test_merge_requires_target_and_pending_item() -> None:
    """Invalid or repeated decisions fail closed."""
    item = build_review_queue(landscape())[0]
    with pytest.raises(ValueError, match="target"):
        record_review_decision(
            item,
            decision=ReviewDecision.MERGE,
            reviewer_id="reviewer:r1",
            rationale_code="same_process",
            configuration_version="discovery-1.0.0",
        )
    decided = record_review_decision(
        item,
        decision=ReviewDecision.ACCEPT,
        reviewer_id="reviewer:r1",
        rationale_code="validated",
        configuration_version="discovery-1.0.0",
    )
    with pytest.raises(ValueError, match="pending"):
        record_review_decision(
            decided,
            decision=ReviewDecision.REJECT,
            reviewer_id="reviewer:r2",
            rationale_code="duplicate_review",
            configuration_version="discovery-1.0.0",
        )
