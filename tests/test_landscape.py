"""Corpus-level process landscape tests."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from careops_process.correlation import build_ocel_from_facts
from careops_process.landscape import (
    activity_mapping_sensitivity,
    discover_process_landscape,
    source_exclusion_sensitivity,
    summarize_operational_patterns,
    threshold_sensitivity,
    time_window_sensitivity,
)

if TYPE_CHECKING:
    from careops_process.ocel import OcelLog


def corpus() -> OcelLog:
    """Return a multi-source object-centric synthetic corpus."""
    facts: list[dict[str, object]] = [
        {
            "id": "t1-created",
            "activity": "task_created",
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "source_system": "planner",
            "object_ids": ["task:t1", "matter:m1"],
        },
        {
            "id": "t1-completed",
            "activity": "task_completed",
            "timestamp_utc": "2026-01-02T00:00:00Z",
            "source_system": "planner",
            "object_ids": ["task:t1", "matter:m1"],
        },
        {
            "id": "a1-created",
            "activity": "approval_created",
            "timestamp_utc": "2026-01-01T12:00:00Z",
            "source_system": "dataverse",
            "object_ids": ["approval:a1", "matter:m1"],
        },
        {
            "id": "a1-decided",
            "activity": "approval_decided",
            "timestamp_utc": "2026-01-03T00:00:00Z",
            "source_system": "dataverse",
            "object_ids": ["approval:a1", "matter:m1"],
        },
    ]
    return build_ocel_from_facts(facts, log_id="landscape", lineage="synthetic")


def test_landscape_ranks_empirical_object_traces() -> None:
    """Families are derived from observed traces and include reach/confidence."""
    result = discover_process_landscape(corpus(), similarity_threshold=0.4)

    assert result.included_event_count == len(corpus().events)
    assert result.included_object_count == len(corpus().objects)
    assert result.families
    assert result.families[0].event_count >= result.families[-1].event_count
    assert all(0.0 <= family.confidence <= 1.0 for family in result.families)
    assert all(family.activity_sequence for family in result.families)


def test_source_exclusion_reports_dependence() -> None:
    """Removing one source quantifies lost events and family instability."""
    report = source_exclusion_sensitivity(
        corpus(),
        excluded_sources=("dataverse",),
        similarity_threshold=0.4,
    )

    assert report.baseline_event_count == len(corpus().events)
    assert report.retained_event_count < report.baseline_event_count
    assert report.event_retention_fraction == (
        report.retained_event_count / report.baseline_event_count
    )
    assert report.excluded_sources == ("dataverse",)


def test_landscape_is_deterministic() -> None:
    """Equivalent corpus input returns stable family identifiers and ranks."""
    first = discover_process_landscape(corpus(), similarity_threshold=0.4)
    second = discover_process_landscape(corpus(), similarity_threshold=0.4)

    assert first == second


def test_threshold_and_time_window_sensitivity_are_explicit() -> None:
    """Family stability is tested against modelling and temporal choices."""
    thresholds = threshold_sensitivity(corpus(), (0.2, 0.8))
    windows = time_window_sensitivity(
        corpus(),
        cutoff=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert [threshold for threshold, _ in thresholds] == [0.2, 0.8]
    assert windows.earlier_event_count + windows.later_event_count == len(corpus().events)
    assert windows.earlier_family_count > 0
    assert windows.later_family_count > 0


def test_activity_mapping_sensitivity_preserves_population() -> None:
    """Vocabulary harmonisation is measured rather than silently applied."""
    report = activity_mapping_sensitivity(
        corpus(),
        {
            "task_created": "work_started",
            "approval_created": "work_started",
            "task_completed": "work_finished",
            "approval_decided": "work_finished",
        },
        similarity_threshold=0.4,
    )

    assert report.mapped_event_count == len(corpus().events)
    assert report.changed_event_count == len(corpus().events)
    assert report.baseline_family_count > 0
    assert report.mapped_family_count > 0


def test_operational_patterns_expose_sequences_handoffs_and_incomplete_work() -> None:
    """Discovery emits empirical patterns without naming a business process."""
    summary = summarize_operational_patterns(corpus())

    assert ("task_created", "task_completed", 1) in summary.directly_follows
    assert any(
        left == "planner" and right == "dataverse" for left, right, _ in summary.source_handoffs
    )
    assert summary.object_duration_seconds
    assert summary.incomplete_object_count == 0
