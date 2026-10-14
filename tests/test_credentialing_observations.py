"""Synthetic observation units, missingness, replay and distinct-case privacy."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

import careops_process.credentialing_observations as observations
from careops_process.credentialing import CredentialingContractError


def _work(  # noqa: PLR0913 - synthetic observation fixture dimensions
    case: str,
    *,
    minutes: int = 10,
    complete: bool = True,
    day: int = 1,
    hour: int = 0,
    identity: str | None = None,
) -> observations.WorkObservation:
    return observations.WorkObservation(
        observation_id=identity or f"work-{case}",
        case_id=case,
        source_system="synthetic",
        recorded_at_utc=datetime(2026, 6, day, tzinfo=UTC) + timedelta(hours=hour),
        manual_touch_count=1,
        active_work_minutes=minutes,
        effort_complete=complete,
    )


def _evaluation(
    case: str, label: str, *, identity: str | None = None, reference: str = "synthetic-v1"
) -> observations.EvaluationObservation:
    alert, present = {
        "tp": (True, True),
        "fp": (True, False),
        "tn": (False, False),
        "fn": (False, True),
    }[label]
    return observations.EvaluationObservation(
        observation_id=identity or f"evaluation-{case}",
        case_id=case,
        source_system="synthetic",
        recorded_at_utc=datetime(2026, 6, 1, tzinfo=UTC),
        alert_raised=alert,
        requirement_present=present,
        evaluation_reference_version=reference,
    )


def _window(day: int) -> observations.MeasurementWindow:
    return observations.MeasurementWindow(
        start_utc=datetime(2026, 6, day, tzinfo=UTC),
        end_utc=datetime(2026, 6, day + 1, tzinfo=UTC),
        source_mapping_version="source-v1",
        cohort_definition_version="cohort-v1",
        source_complete=True,
    )


def test_observation_wire_roundtrip_and_strict_units() -> None:
    """Canonical JSON-like records preserve UTC instants and actual measured units."""
    work = _work("case-1")
    payload = observations.observation_payload(work)
    assert payload["kind"] == "workload"
    assert observations.parse_observation(payload) == work
    evaluation = _evaluation("case-1", "fp")
    assert (
        observations.parse_observation(observations.observation_payload(evaluation)) == evaluation
    )
    assert work.manual_touch_count == 1


@pytest.mark.parametrize("kind", ["workload", "evaluation"])
def test_fractional_export_roundtrip_preserves_microseconds(kind: str) -> None:
    """Both wire variants preserve observed fractional seconds without rounding."""
    item = _work("case-0") if kind == "workload" else _evaluation("case-0", "tp")
    fractional = replace(item, recorded_at_utc=item.recorded_at_utc.replace(microsecond=123456))
    payload = observations.observation_payload(fractional)
    assert payload["recorded_at_utc"] == "2026-06-01T00:00:00.123456+00:00"
    assert observations.parse_observation(payload) == fractional


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("name", "synthetic-forbidden"),
        ("manual_touch_count", True),
        ("manual_touch_count", -1),
        ("active_work_minutes", "10"),
        ("active_work_minutes", 1_000_000_001),
        ("effort_complete", "yes"),
        ("source_system", "synthetic@example.invalid"),
        ("case_id", "case name"),
        ("recorded_at_utc", "2026-06-01T00:00:00"),
        ("contract_version", "0.2.0"),
        ("kind", "unknown"),
    ],
)
def test_uncontrolled_observation_fields_fail_closed(key: str, value: object) -> None:
    """Narrative, identity-like tokens and wrong numeric/boolean units are rejected."""
    payload = observations.observation_payload(_work("case-1"))
    payload[key] = value
    with pytest.raises(CredentialingContractError):
        observations.parse_observation(payload)


def test_exact_observation_replay_is_idempotent_and_changed_replay_rejected() -> None:
    """Stable kind/ID identity deduplicates exact evidence without overwriting it."""
    item = _work("case-1")
    assert observations.merge_observations((item,), (item,)) == (item,)
    with pytest.raises(CredentialingContractError, match="Conflicting"):
        observations.merge_observations((item,), (replace(item, active_work_minutes=11),))


def test_tied_partial_work_keeps_measurement_incomplete() -> None:
    """A simultaneous incomplete delta cannot be hidden by another complete marker."""
    items = tuple(
        item
        for case in ("case-0", "case-1")
        for item in (_work(case), _work(case, complete=False, identity=f"partial-{case}"))
    )
    report = observations.report_effort(
        items,
        role="report_reader",
        case_ids={"case-0", "case-1"},
        minimum_cases=2,
    )
    assert report.metrics is not None
    assert (report.metrics.complete_case_count, report.metrics.partial_case_count) == (0, 2)


def test_retained_observation_is_revalidated_before_aggregation() -> None:
    """Bypassed frozen-instance validation cannot introduce negative effort."""
    item = _work("case-0")
    object.__setattr__(item, "active_work_minutes", -1)
    with pytest.raises(CredentialingContractError):
        observations.report_effort(
            (item,),
            role="report_reader",
            case_ids={"case-0", "case-1"},
            minimum_cases=2,
        )


@pytest.mark.parametrize("value", [[], {}, None, "2026-02-30T00:00:00Z"])
def test_malformed_wire_values_fail_with_controlled_errors(value: object) -> None:
    """Invalid structured kinds and calendar dates remain contract errors."""
    payload = observations.observation_payload(_work("case-0"))
    payload["recorded_at_utc" if isinstance(value, str) else "kind"] = value
    with pytest.raises(CredentialingContractError):
        observations.parse_observation(payload)


@pytest.mark.parametrize("offset", ["+00:60", "+24:00", "-01:99"])
def test_wire_offset_cannot_be_silently_normalized(offset: str) -> None:
    """RFC3339 offset components must be valid before Python normalizes dates."""
    payload = observations.observation_payload(_work("case-0"))
    payload["recorded_at_utc"] = f"2026-06-01T00:00:00{offset}"
    with pytest.raises(CredentialingContractError):
        observations.parse_observation(payload)


def test_effort_uses_observed_minutes_and_zero_is_not_missing() -> None:
    """Observed zero effort remains zero while absent case evidence remains unknown."""
    report = observations.report_effort(
        (_work("case-0", minutes=0), _work("case-1", minutes=0)),
        role="report_reader",
        case_ids={"case-0", "case-1"},
        minimum_cases=2,
    )
    assert report.metrics is not None
    assert (
        report.metrics.total_active_work_minutes,
        report.metrics.mean_active_minutes_per_observed_case,
    ) == (0, 0.0)
    missing = observations.report_effort(
        (),
        role="report_reader",
        case_ids={"case-0", "case-1"},
        minimum_cases=2,
    )
    assert missing.metrics is not None
    assert missing.metrics.total_active_work_minutes is None
    assert missing.metrics.mean_active_minutes_per_observed_case is None


def test_rare_missing_or_partial_effort_suppresses_totals() -> None:
    """One missing/partial case cannot be revealed through complete-case totals."""
    missing = observations.report_effort(
        (_work("case-0"), _work("case-1")),
        role="report_reader",
        case_ids={"case-0", "case-1", "case-2"},
        minimum_cases=2,
    )
    assert missing.suppressed is True
    assert missing.metrics is None
    partial = observations.report_effort(
        (_work("case-0"), _work("case-1", complete=False)),
        role="report_reader",
        case_ids={"case-0", "case-1"},
        minimum_cases=2,
    )
    assert partial.suppressed is True


def test_ungranted_observations_do_not_change_released_reports() -> None:
    """Valid excluded cases contribute neither effort nor evaluation labels."""
    work = (_work("case-0"), _work("case-1"))
    scope = {"case-0", "case-1"}
    before = observations.report_effort(
        work,
        role="report_reader",
        case_ids=scope,
        minimum_cases=2,
    )
    assert (
        observations.report_effort(
            (*work, _work("outside", minutes=999)),
            role="report_reader",
            case_ids=scope,
            minimum_cases=2,
        )
        == before
    )
    evaluations = (_evaluation("case-0", "tn"), _evaluation("case-1", "tn"))
    quality = observations.report_quality(
        evaluations,
        role="report_reader",
        case_ids=scope,
        minimum_cases=2,
        reference_version="synthetic-v1",
    )
    assert (
        observations.report_quality(
            (*evaluations, _evaluation("outside", "fp", reference="unapproved")),
            role="report_reader",
            case_ids=scope,
            minimum_cases=2,
            reference_version="synthetic-v1",
        )
        == quality
    )


def test_case_level_quality_rates_reconcile_distinct_reviewed_cases() -> None:
    """Four two-case cells give independently specified false-positive/negative rates."""
    items = tuple(
        _evaluation(f"{label}-{i}", label) for label in ("tp", "fp", "tn", "fn") for i in range(2)
    )
    report = observations.report_quality(
        items,
        role="report_reader",
        case_ids={item.case_id for item in items},
        minimum_cases=2,
        reference_version="synthetic-v1",
    )
    assert report.metrics is not None
    assert dict(report.metrics.outcome_case_counts) == {"tp": 2, "fp": 2, "tn": 2, "fn": 2}
    assert (
        report.metrics.false_positive_numerator,
        report.metrics.false_positive_denominator,
        report.metrics.false_positive_rate,
    ) == (2, 4, 0.5)
    assert (
        report.metrics.false_negative_numerator,
        report.metrics.false_negative_denominator,
        report.metrics.false_negative_rate,
    ) == (2, 4, 0.5)


def test_repeated_case_evaluations_do_not_inflate_rates_or_privacy_cells() -> None:
    """Different observation IDs cannot turn one case into a two-case cell."""
    items = tuple(_evaluation("case-1", "fp", identity=f"repeat-{i}") for i in range(10))
    report = observations.report_quality(
        items,
        role="report_reader",
        case_ids={"case-1", "case-2"},
        minimum_cases=2,
        reference_version="synthetic-v1",
    )
    assert report.suppressed is True
    assert report.metrics is None


def test_repeated_identical_classification_counts_once_and_zero_denominator_is_unavailable() -> (
    None
):
    """One case/reference is the rate unit even with several equivalent reviews."""
    items = (
        _evaluation("case-0", "tp"),
        _evaluation("case-1", "tp"),
        _evaluation("case-0", "tp", identity="another-review"),
    )
    report = observations.report_quality(
        items,
        role="report_reader",
        case_ids={"case-0", "case-1"},
        minimum_cases=2,
        reference_version="synthetic-v1",
    )
    assert report.metrics is not None
    assert dict(report.metrics.outcome_case_counts) == {"tp": 2, "fp": 0, "tn": 0, "fn": 0}
    assert report.metrics.false_positive_rate is None
    assert report.metrics.false_positive_denominator == 0
    assert report.metrics.false_negative_rate == 0.0


@pytest.mark.parametrize("mismatch", ["outcome", "reference"])
def test_conflicting_case_evaluations_fail_closed(mismatch: str) -> None:
    """Contradictory case-level judgements or a wrong reference cannot become rates."""
    first = _evaluation("case-0", "tp")
    second = _evaluation(
        "case-0",
        "fn" if mismatch == "outcome" else "tp",
        identity="another-review",
        reference="synthetic-v2" if mismatch == "reference" else "synthetic-v1",
    )
    with pytest.raises(CredentialingContractError):
        observations.report_quality(
            (first, second),
            role="report_reader",
            case_ids={"case-0", "case-1"},
            minimum_cases=2,
            reference_version="synthetic-v1",
        )


def test_effort_comparison_requires_complete_matched_cohorts() -> None:
    """Complete matched observations yield an arithmetic difference, not causal capacity."""
    baseline = (_work("b-0", minutes=30), _work("b-1", minutes=30))
    current = (_work("c-0", minutes=20, day=2), _work("c-1", minutes=20, day=2))
    report = observations.compare_effort(
        baseline,
        current,
        baseline_window=_window(1),
        current_window=_window(2),
        baseline_case_ids={"b-0", "b-1"},
        current_case_ids={"c-0", "c-1"},
        role="report_reader",
        minimum_cases=2,
    )
    assert report.available is True
    assert (
        report.baseline_minutes_per_case,
        report.current_minutes_per_case,
        report.observed_minutes_per_case_difference,
    ) == (30.0, 20.0, 10.0)


@pytest.mark.parametrize("gap", ["partial", "source", "cohort", "overlap", "late_work"])
def test_incomplete_or_noncomparable_effort_never_yields_a_capacity_difference(gap: str) -> None:
    """Missing attestations, incompatible windows and post-marker work block comparisons."""
    baseline = (_work("b-0"), _work("b-1"))
    current = (
        _work("c-0", day=2, complete=gap != "partial"),
        _work("c-1", day=2, complete=gap != "partial"),
    )
    window = _window(2)
    if gap == "source":
        window = replace(window, source_complete=False)
    elif gap == "cohort":
        window = replace(window, cohort_definition_version="different-cohort")
    elif gap == "overlap":
        window = _window(1)
    elif gap == "late_work":
        current += (
            _work("c-0", day=2, hour=1, complete=False, identity="late-0"),
            _work("c-1", day=2, hour=1, complete=False, identity="late-1"),
        )
    report = observations.compare_effort(
        baseline,
        current,
        baseline_window=_window(1),
        current_window=window,
        baseline_case_ids={"b-0", "b-1"},
        current_case_ids={"c-0", "c-1"},
        role="report_reader",
        minimum_cases=2,
    )
    assert report.available is False
    assert report.observed_minutes_per_case_difference is None
