"""Hand-calculated synthetic elapsed-time and privacy regression evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

import careops_process.credentialing_measurements as measurements
from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

STAGES = (
    "request_received",
    "request_classified",
    "application_ready",
    "committee_scheduled",
    "committee_considered",
    "recommendation_recorded",
    "decision_routed_to_delegate",
    "delegated_decision_recorded",
    "decision_communicated",
    "register_activation_requested",
    "register_activated",
    "case_completed",
    "renewal_reminder_issued",
)
FIRST_INTERVAL = "request_received__request_classified"
COHORT_SIZE = 4
CHANGED_CASES = 2


def _mutate(rows: list[dict[str, Any]], mutation: str | None, case_index: int) -> None:
    if mutation == "missing":
        rows.pop(0)
    elif mutation == "repeated":
        rows.append({**rows[0], "event_id": f"repeat-{case_index}"})
    elif mutation == "tied":
        rows[0]["timestamp_utc"] = rows[1]["timestamp_utc"]
    elif mutation == "reversed":
        rows[0]["timestamp_utc"] = rows[1]["timestamp_utc"] + timedelta(hours=1)
    elif mutation == "pathway":
        rows[0]["qualifiers"]["pathway_code"] = "different-pathway"
    elif mutation == "authority":
        rows[0]["qualifiers"]["authority_mapping_version"] = "synthetic-v2"
    elif mutation == "inferred":
        rows[0].update(observed_or_inferred="inferred", confidence=0.4)
    elif mutation == "inferred_only":
        for row in rows:
            row.update(observed_or_inferred="inferred", confidence=0.4)


def _projection(
    hours: tuple[int, ...] = (1, 2, 3, 4),
    mutation: str | None = None,
) -> CredentialingProjection:
    facts: list[dict[str, Any]] = []
    for case_index, gap in enumerate(hours):
        rows: list[dict[str, Any]] = [
            {
                "event_id": f"case-{case_index}-event-{index}",
                "activity": activity,
                "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index * gap),
                "source_system": "synthetic",
                "object_ids": [f"case-{case_index}", f"request-{case_index}"],
                "observed_or_inferred": "observed",
                "confidence": 1.0,
                "qualifiers": {
                    "pathway_code": "routine-renewal",
                    "authority_mapping_version": "synthetic-v1",
                },
            }
            for index, activity in enumerate(STAGES)
        ]
        if case_index < CHANGED_CASES:
            _mutate(rows, mutation, case_index)
        facts.extend(rows)
    return validate_credentialing_projection({"source": "careops-approve", "facts": facts})


def _report(projection: CredentialingProjection) -> measurements.StageTimeReport:
    return measurements.report_stage_times(
        projection,
        role="report_reader",
        case_ids=frozenset(f"case-{i}" for i in range(COHORT_SIZE)),
        minimum_cases=2,
        authority_version="synthetic-v1",
    )


def test_stage_time_quantiles_use_explicit_observed_endpoints() -> None:
    """Four known case durations yield independently calculated percentiles."""
    report = _report(_projection())
    assert report.suppressed is False
    assert report.population_case_count == COHORT_SIZE
    assert report.measures is not None
    measure = next(item for item in report.measures if item.interval_id == FIRST_INTERVAL)
    assert measure.eligible_case_count == COHORT_SIZE
    assert measure.excluded_case_counts == ()
    assert (measure.median_hours, measure.p75_hours, measure.p90_hours, measure.p95_hours) == (
        2.5,
        3.0,
        4.0,
        4.0,
    )
    completed = next(
        item for item in report.measures if item.interval_id == "request_received__case_completed"
    )
    assert (completed.median_hours, completed.p95_hours) == (27.5, 44.0)


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "missing_endpoints"),
        ("repeated", "repeated_endpoints"),
        ("tied", "tied_time"),
        ("reversed", "reversed_time"),
        ("pathway", "qualifier_mismatch"),
        ("authority", "qualifier_mismatch"),
        ("inferred", "missing_endpoints"),
        ("inferred_only", "no_observed_evidence"),
    ],
)
def test_each_case_has_one_reconciled_interval_outcome(mutation: str, reason: str) -> None:
    """Ambiguous, mismatched or inferred evidence cannot silently enter timing."""
    report = _report(_projection(mutation=mutation))
    assert report.suppressed is False
    assert report.measures is not None
    first = next(item for item in report.measures if item.interval_id == FIRST_INTERVAL)
    assert first.eligible_case_count == CHANGED_CASES
    assert dict(first.excluded_case_counts) == {reason: 2}
    for measure in report.measures:
        assert (
            measure.eligible_case_count + sum(count for _, count in measure.excluded_case_counts)
            == COHORT_SIZE
        )


def test_rare_exclusion_suppresses_all_intervals_and_totals() -> None:
    """A large overall cohort must not expose a one-case exclusion cell."""
    projection = _projection()
    projection.facts = [fact for fact in projection.facts if fact.event_id != "case-0-event-0"]
    report = _report(projection)
    assert asdict(report) == {
        "suppressed": True,
        "population_case_count": None,
        "measures": None,
    }


def test_no_eligible_cases_is_not_a_measured_zero_duration() -> None:
    """A sufficiently large excluded group may be reported with unavailable time."""
    projection = _projection(mutation="inferred_only", hours=(1, 2))
    report = measurements.report_stage_times(
        projection,
        role="report_reader",
        case_ids={"case-0", "case-1"},
        minimum_cases=2,
        authority_version="synthetic-v1",
    )
    assert report.suppressed is False
    assert report.measures is not None
    first = report.measures[0]
    assert first.eligible_case_count == 0
    assert first.median_hours is None
    assert first.p95_hours is None
    assert dict(first.excluded_case_counts) == {"no_observed_evidence": 2}


def test_shared_event_links_count_cases_once_without_releasing_references() -> None:
    """An event linked to two granted cases supplies one endpoint to each case."""
    projection = _projection(hours=(2,))
    for fact in projection.facts:
        fact.object_ids = ["case-a", "case-b", "ungranted-object"]
    report = measurements.report_stage_times(
        projection,
        role="report_reader",
        case_ids={"case-a", "case-b"},
        minimum_cases=2,
        authority_version="synthetic-v1",
    )
    assert report.measures is not None
    assert (report.measures[0].eligible_case_count, report.measures[0].median_hours) == (2, 2.0)
    encoded = json.dumps(asdict(report))
    assert "case-a" not in encoded
    assert "ungranted-object" not in encoded
    assert "2026-" not in encoded


@pytest.mark.parametrize("minimum", [True, 1, 2.5, "2", None])
def test_stage_time_policy_rejects_unsafe_thresholds(minimum: object) -> None:
    """Boolean, low and noninteger values cannot weaken a reporting policy."""
    with pytest.raises(CredentialingContractError, match="minimum"):
        measurements.report_stage_times(
            _projection(),
            role="report_reader",
            case_ids={"case-0", "case-1"},
            minimum_cases=minimum,
            authority_version="synthetic-v1",
        )


@pytest.mark.parametrize("role", ["case_analyst", "unknown"])
def test_elapsed_aggregate_requires_explicit_reporting_role(role: str) -> None:
    """An aggregate endpoint never treats a different role as a reader grant."""
    with pytest.raises(CredentialingContractError, match="role"):
        measurements.report_stage_times(
            _projection(),
            role=role,
            case_ids={"case-0", "case-1"},
            minimum_cases=2,
            authority_version="synthetic-v1",
        )


@pytest.mark.parametrize("authority", ["", "version with narrative", "a@example.invalid", "a" * 81])
def test_elapsed_authority_configuration_requires_a_bounded_code(authority: str) -> None:
    """Uncontrolled configuration cannot appear as an authority mapping."""
    with pytest.raises(CredentialingContractError, match="authority"):
        measurements.report_stage_times(
            _projection(),
            role="report_reader",
            case_ids={"case-0", "case-1"},
            minimum_cases=2,
            authority_version=authority,
        )


def test_empty_grants_suppress_all_elapsed_information() -> None:
    """Empty scope is suppressed even when other cases exist in the projection."""
    report = measurements.report_stage_times(
        _projection(),
        role="report_reader",
        case_ids=set(),
        minimum_cases=2,
        authority_version="synthetic-v1",
    )
    assert report.suppressed is True
    assert report.population_case_count is None
    assert report.measures is None


@given(st.lists(st.integers(min_value=1, max_value=48), min_size=2, max_size=8))
def test_complete_case_samples_remain_bounded_and_reconciled(hours: list[int]) -> None:
    """Positive observed intervals keep counts and ordered statistics bounded."""
    report = measurements.report_stage_times(
        _projection(tuple(hours)),
        role="report_reader",
        case_ids={f"case-{i}" for i in range(len(hours))},
        minimum_cases=2,
        authority_version="synthetic-v1",
    )
    assert report.measures is not None
    first = report.measures[0]
    assert first.eligible_case_count == len(hours)
    assert first.excluded_case_counts == ()
    assert first.median_hours is not None
    assert first.p95_hours is not None
    assert min(hours) <= first.median_hours <= first.p95_hours <= max(hours)


@pytest.mark.parametrize("case_id", ["", "case name", "a@example.invalid", "a" * 129])
def test_stage_time_grants_require_bounded_source_references(case_id: str) -> None:
    """Uncontrolled case-reference content is rejected before measurements."""
    with pytest.raises(CredentialingContractError, match="references"):
        measurements.report_stage_times(
            _projection(),
            role="report_reader",
            case_ids={case_id},
            minimum_cases=2,
            authority_version="synthetic-v1",
        )


def test_equivalent_aware_timezones_preserve_elapsed_intervals() -> None:
    """Equivalent instants in a different offset do not create delay differences."""
    projection = _projection()
    expected = _report(projection)
    for fact in projection.facts:
        fact.timestamp_utc = fact.timestamp_utc.astimezone(timezone(timedelta(hours=10)))
    assert _report(projection) == expected


def test_late_rare_cell_suppresses_previously_computed_intervals() -> None:
    """A rare later-stage exclusion cannot leave earlier totals available."""
    projection = _projection()
    projection.facts = [fact for fact in projection.facts if fact.event_id != "case-0-event-8"]
    report = _report(projection)
    assert report.suppressed is True
    assert report.population_case_count is None
    assert report.measures is None


def test_ungranted_case_variants_do_not_change_released_measurements() -> None:
    """Other case populations cannot introduce exclusions or change this report."""
    projection = _projection(hours=(1, 2, 3, 4, 5))
    for fact in projection.facts:
        if "case-4" in fact.object_ids:
            fact.qualifiers.pathway_code = "different-pathway"
    assert _report(projection) == _report(_projection())


@pytest.mark.parametrize(
    "container",
    [
        "cases",
        ["case-a", "case-b"],
        iter(("case-a", "case-b")),
        {"case-a": True, "case-b": True},
        None,
    ],
)
def test_case_grant_container_rejects_non_sets(container: object) -> None:
    """Text, mappings and one-shot iterators cannot fabricate or lose grant populations."""
    with pytest.raises(CredentialingContractError, match="set"):
        measurements.validate_measurement_scope(
            role="report_reader",
            case_ids=cast("AbstractSet[str]", container),
            minimum_cases=2,
        )
