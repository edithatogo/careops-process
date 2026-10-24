# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Cross-source object-centric reconstruction tests."""

import pytest

from careops_process.correlation import (
    CorrelationHypothesis,
    build_ocel_from_facts,
    corpus_fingerprint,
    evaluate_corpus_quality,
    hypothesis_relation,
)


def multi_source_facts() -> list[dict[str, object]]:
    """Return minimized events sharing governance and document objects."""
    return [
        {
            "id": "planner-1-created",
            "activity": "planner_task_created",
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "source_system": "planner",
            "object_ids": ["task:t1", "plan:p1", "governance:m1"],
        },
        {
            "id": "meeting-1-held",
            "activity": "meeting_held",
            "timestamp_utc": "2026-01-02T00:00:00Z",
            "source_system": "teams",
            "object_ids": [
                "meeting:mt1",
                "governance:m1",
                "document:d1",
                "message:msg1",
                "organisation:o1",
            ],
        },
        {
            "id": "approval-1-decided",
            "activity": "approval_decided",
            "timestamp_utc": "2026-01-03T00:00:00Z",
            "source_system": "dataverse",
            "object_ids": [
                "approval:a1",
                "governance:m1",
                "document:d1",
                "flow:f1",
                "organisation:o1",
            ],
        },
    ]


def test_reconstruction_preserves_many_to_many_cross_source_links() -> None:
    """Shared objects link events without forcing a single case ID."""
    log = build_ocel_from_facts(
        multi_source_facts(),
        log_id="cross-source",
        lineage="synthetic multi-source fixture",
    )

    assert len(log.events) == len(multi_source_facts())
    assert {item.object_type for item in log.objects} >= {
        "task",
        "plan",
        "governance",
        "meeting",
        "document",
        "approval",
        "message",
        "flow",
        "organisation",
    }
    governance_events = [event for event in log.events if "governance:m1" in event.object_ids]
    assert len(governance_events) == len(multi_source_facts())
    assert all(event.observed_or_inferred == "observed" for event in log.events)


def test_reconstruction_accepts_explicit_object_type_overrides() -> None:
    """An approved mapping can assign a semantic type independently of an ID prefix."""
    facts = multi_source_facts()
    facts[1]["object_ids"] = ["meeting:mt1", "governance:m1", "task:t1"]
    facts[1]["object_types"] = {"task:t1": "document"}

    log = build_ocel_from_facts(facts, log_id="mapped", lineage="synthetic")
    assert any(item.object_type == "document" for item in log.objects)


def test_hypothesis_relation_requires_bounded_non_certain_confidence() -> None:
    """Hypotheses remain distinguishable from deterministic observed links."""
    hypothesis = CorrelationHypothesis(
        source_object_id="task:t1",
        target_object_id="document:d1",
        relation_type="possibly_concerns",
        confidence=0.7,
        rule_version="correlation-1.0.0",
    )
    relation = hypothesis_relation(hypothesis)
    assert relation.observed_or_inferred == "inferred"
    assert relation.confidence == hypothesis.confidence
    with pytest.raises(ValueError, match="less than 1"):
        CorrelationHypothesis(
            source_object_id="task:t1",
            target_object_id="document:d1",
            relation_type="possibly_concerns",
            confidence=1.0,
            rule_version="correlation-1.0.0",
        )


def test_quality_report_identifies_incomplete_lifecycle_and_orphans() -> None:
    """Missing completion and single-event objects remain visible."""
    log = build_ocel_from_facts(
        multi_source_facts(),
        log_id="quality",
        lineage="synthetic multi-source fixture",
    )
    report = evaluate_corpus_quality(log)

    assert "task:t1" in report.incomplete_lifecycle_objects
    assert "plan:p1" in report.single_event_objects
    assert report.event_count == len(log.events)
    assert report.object_count == len(log.objects)


def test_quality_report_detects_completion_before_creation() -> None:
    """Clock or ordering anomalies remain visible after deterministic sorting."""
    facts: list[dict[str, object]] = [
        {
            "id": "task-completed",
            "activity": "planner_task_completed",
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "source_system": "planner",
            "object_ids": ["task:t1"],
        },
        {
            "id": "task-created",
            "activity": "planner_task_created",
            "timestamp_utc": "2026-01-02T00:00:00Z",
            "source_system": "planner",
            "object_ids": ["task:t1"],
        },
    ]
    log = build_ocel_from_facts(facts, log_id="clock", lineage="synthetic")

    assert evaluate_corpus_quality(log).out_of_order_objects == ("task:t1",)


def test_rebuild_is_deterministic_for_reordered_input() -> None:
    """Equivalent source facts produce the same canonical corpus hash."""
    facts = multi_source_facts()
    first = build_ocel_from_facts(facts, log_id="stable", lineage="manifest-hash")
    second = build_ocel_from_facts(
        list(reversed(facts)),
        log_id="stable",
        lineage="manifest-hash",
    )

    assert corpus_fingerprint(first) == corpus_fingerprint(second)
