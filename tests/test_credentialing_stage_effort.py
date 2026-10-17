"""Explicit administrative-stage work attribution and joint case privacy."""

# Numeric expectations describe independent synthetic arithmetic.
# ruff: noqa: PLR2004

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from careops_process.credentialing_observations import (
    MeasurementWindow,
    WorkObservation,
    report_effort,
)
from careops_process.credentialing_stage_effort import StageEffortReport, report_stage_effort


def work(index: int, stage: str, minutes: int = 10) -> WorkObservation:
    """Use source-observed worker effort; calendar duration is independent."""
    return WorkObservation(
        observation_id=f"work-{index}-{stage}",
        case_id=f"case-{index}",
        source_system="synthetic",
        recorded_at_utc=datetime(2026, 1, 2, tzinfo=UTC),
        manual_touch_count=1,
        active_work_minutes=minutes,
        effort_complete=True,
    )


def report(
    records: list[WorkObservation],
    mapping: dict[str, str],
    *,
    complete: bool = True,
    population_size: int = 4,
) -> StageEffortReport:
    """Pin a synthetic source/cohort window and a separate stage-definition version."""
    return report_stage_effort(
        records,
        stage_by_observation=mapping,
        stage_mapping_version="stage-map-v1",
        role="report_reader",
        case_ids=frozenset(f"case-{i}" for i in range(population_size)),
        minimum_cases=2,
        window=MeasurementWindow(
            start_utc=datetime(2026, 1, 1, tzinfo=UTC),
            end_utc=datetime(2026, 2, 1, tzinfo=UTC),
            source_mapping_version="source-v1",
            cohort_definition_version="cohort-v1",
            source_complete=complete,
        ),
    )


def test_professional_and_committee_work_are_separate_and_replay_safe() -> None:
    """Case-based means do not become calendar time or worker counts."""
    records = [
        work(i, stage, minutes)
        for i in range(4)
        for stage, minutes in (("professional_review", 30), ("committee_preparation", 20))
    ]
    mapping = {
        item.observation_id: stage
        for item, stage in zip(
            records, ["professional_review", "committee_preparation"] * 4, strict=True
        )
    }
    result = report([*records, records[0]], mapping)
    assert not result.suppressed
    assert result.measures is not None
    measures = {item.stage: item for item in result.measures}
    professional = measures["professional_review"]
    committee = measures["committee_preparation"]
    assert professional.metrics.total_active_work_minutes == 120
    assert committee.metrics.total_active_work_minutes == 80
    assert professional.full_cohort_mean_minutes == 30
    assert committee.metrics.mean_active_minutes_per_observed_case == 20
    assert measures["other"].metrics.missing_case_count == 4
    assert measures["other"].metrics.total_active_work_minutes is None


def test_missing_assignment_is_not_guessed_from_event_or_source() -> None:
    """No stage classification is inferred from an observation ID or elapsed time."""
    with pytest.raises(ValueError, match="exactly"):
        report([work(0, "professional_review")], {})


def test_safe_marginals_cannot_hide_rare_stage_intersections() -> None:
    """Four observed/four missing for each stage hide singleton cross-stage cells."""
    records = [work(i, "professional_review") for i in (0, 1, 2, 3)] + [
        work(i, "committee_preparation") for i in (1, 2, 3, 4)
    ]
    mapping = {
        item.observation_id: (
            "professional_review"
            if "professional" in item.observation_id
            else "committee_preparation"
        )
        for item in records
    }
    for stage in ("professional_review", "committee_preparation"):
        standalone = report_effort(
            [item for item in records if mapping[item.observation_id] == stage],
            role="report_reader",
            case_ids=frozenset(f"case-{i}" for i in range(8)),
            minimum_cases=2,
        )
        assert not standalone.suppressed
    assert asdict(report(records, mapping, population_size=8)) == {
        "suppressed": True,
        "measures": None,
    }


def test_unconfirmed_source_coverage_never_becomes_full_cohort_mean() -> None:
    """Observed measured minutes remain separate from a population assertion."""
    records = [work(i, "professional_review") for i in range(4)]
    result = report(
        records, {item.observation_id: "professional_review" for item in records}, complete=False
    )
    assert result.measures is not None
    professional = next(item for item in result.measures if item.stage == "professional_review")
    assert professional.metrics.mean_active_minutes_per_observed_case == 10
    assert professional.full_cohort_mean_minutes is None


def test_observations_outside_window_rejected() -> None:
    """Capture-window membership is explicit, including an exclusive upper bound."""
    item = work(0, "professional_review")
    object.__setattr__(item, "recorded_at_utc", datetime(2026, 2, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="window"):
        report([item], {item.observation_id: "professional_review"})


def test_complete_and_partial_at_latest_instant_are_kept_separate() -> None:
    """Latest complete evidence closes stage measurement, not clinical review."""
    records = [work(i, "professional_review") for i in range(4)]
    for item in records[2:]:
        object.__setattr__(item, "effort_complete", False)
    result = report(records, {item.observation_id: "professional_review" for item in records})
    assert result.measures is not None
    measure = next(item for item in result.measures if item.stage == "professional_review")
    assert (measure.metrics.complete_case_count, measure.metrics.partial_case_count) == (2, 2)
    assert measure.full_cohort_mean_minutes is None


def test_consistent_later_measurement_complete_does_not_remove_earlier_effort() -> None:
    """Source deltas sum once, while only latest measurement status sets coverage."""
    records = [work(i, "professional_review") for i in range(4)]
    extra = [work(i, "later", minutes=5) for i in range(4)]
    for item in extra:
        object.__setattr__(item, "recorded_at_utc", item.recorded_at_utc + timedelta(days=1))
    result = report(
        [*records, *extra],
        {item.observation_id: "professional_review" for item in [*records, *extra]},
    )
    assert result.measures is not None
    measure = next(item for item in result.measures if item.stage == "professional_review")
    assert measure.metrics.total_active_work_minutes == 60
    assert measure.metrics.observed_case_count == 4


@pytest.mark.parametrize(
    "stage", ["unknown", "professional_review\n", "clinical decision narrative"]
)
def test_unknown_or_raw_stages_fail(stage: str) -> None:
    """Every stage needs a controlled explicit assignment."""
    item = work(0, "professional_review")
    with pytest.raises(ValueError, match="Unknown"):
        report([item], {item.observation_id: stage})


def test_extra_mapping_and_conflicting_replay_fail() -> None:
    """A mapping cannot silently include stale identities or hide changed work."""
    item = work(0, "professional_review")
    with pytest.raises(ValueError, match="exactly"):
        report([item], {item.observation_id: "professional_review", "extra": "other"})
    with pytest.raises(ValueError, match="Conflicting"):
        report(
            [item, replace(item, active_work_minutes=20)],
            {item.observation_id: "professional_review"},
        )


def test_missing_work_and_explicit_zero_are_different() -> None:
    """Unobserved work is unavailable, while a source-observed zero remains zero."""
    missing = report([], {})
    assert missing.measures is not None
    assert all(item.metrics.total_active_work_minutes is None for item in missing.measures)
    assert report([], {}, population_size=0).suppressed
    records = [work(i, "professional_review", minutes=0) for i in range(4)]
    result = report(records, {item.observation_id: "professional_review" for item in records})
    assert result.measures is not None
    professional = result.measures[0]
    assert (
        professional.metrics.total_active_work_minutes == professional.full_cohort_mean_minutes == 0
    )
    assert professional.metrics.observed_case_count == 4


def test_ungranted_observations_do_not_change_released_work() -> None:
    """Protected records outside the grant set cannot inflate any stage denominator."""
    records = [work(i, "professional_review") for i in range(4)]
    mapping = {item.observation_id: "professional_review" for item in records}
    expected = report(records, mapping)
    outside = work(99, "committee_preparation")
    assert (
        report([*records, outside], {**mapping, outside.observation_id: "committee_preparation"})
        == expected
    )
    assert "case-" not in str(asdict(expected))
    assert "synthetic" not in str(asdict(expected))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("active_work_minutes", True),
        ("manual_touch_count", -1),
        ("observation_id", "raw text"),
        ("case_id", "case-0\n"),
        ("source_system", "a@example.org"),
        ("effort_complete", 1),
    ],
)
def test_mutated_work_revalidated(field: str, value: object) -> None:
    """Frozen inputs cannot bypass scalar/unit validation after mutation."""
    item = work(0, "professional_review")
    object.__setattr__(item, field, value)
    with pytest.raises(ValueError, match=r"Stage effort|Observed counts"):
        report([item], {item.observation_id: "professional_review"})


def test_work_subclass_is_rejected() -> None:
    """A subclass overriding validation must not reach the existing aggregate helper."""

    class UntrustedWork(WorkObservation):
        def __post_init__(self) -> None:
            pass

    item = UntrustedWork(
        observation_id="bad",
        case_id="case-0",
        source_system="synthetic",
        recorded_at_utc=datetime(2026, 1, 2, tzinfo=UTC),
        manual_touch_count=-1,
        active_work_minutes=-1,
    )
    with pytest.raises(ValueError, match="concrete workload"):
        report([item], {"bad": "professional_review"})


@given(st.lists(st.integers(min_value=0, max_value=3), max_size=20))
def test_replay_and_input_order_are_invariant(indices: list[int]) -> None:
    """Exact source replays cannot change stage work or its coverage."""
    records = [work(i, "professional_review") for i in range(4)]
    mapping = {item.observation_id: "professional_review" for item in records}
    assert report([*reversed(records), *(records[index] for index in indices)], mapping) == report(
        records, mapping
    )


@pytest.mark.parametrize(
    ("role", "minimum"), [("case_analyst", 2), ("report_reader", True), ("report_reader", 1)]
)
def test_reporting_scope_is_checked_before_measurement(role: str, minimum: object) -> None:
    """A user-selected nonreporting role or unsafe floor cannot release work."""
    with pytest.raises(ValueError, match=r"Stage effort scope|Measurement"):
        report_stage_effort(
            [],
            stage_by_observation={},
            stage_mapping_version="stage-v1",
            role=role,
            case_ids=frozenset({"case-0"}),
            minimum_cases=minimum,
            window=MeasurementWindow(
                start_utc=datetime(2026, 1, 1, tzinfo=UTC),
                end_utc=datetime(2026, 2, 1, tzinfo=UTC),
                source_mapping_version="source-v1",
                cohort_definition_version="cohort-v1",
                source_complete=True,
            ),
        )


def test_concrete_window_and_coverage_are_revalidated() -> None:
    """A frozen window is not a trusted source assertion after mutation."""
    window = MeasurementWindow(
        start_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_utc=datetime(2026, 2, 1, tzinfo=UTC),
        source_mapping_version="source-v1",
        cohort_definition_version="cohort-v1",
        source_complete=True,
    )
    object.__setattr__(window, "source_complete", 1)
    with pytest.raises(ValueError, match="coverage flag"):
        report_stage_effort(
            [],
            stage_by_observation={},
            stage_mapping_version="stage-v1",
            role="report_reader",
            case_ids=frozenset(),
            minimum_cases=2,
            window=window,
        )

    class UntrustedWindow(MeasurementWindow):
        pass

    unsafe = UntrustedWindow(
        start_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_utc=datetime(2026, 2, 1, tzinfo=UTC),
        source_mapping_version="source-v1",
        cohort_definition_version="cohort-v1",
        source_complete=True,
    )
    with pytest.raises(ValueError, match="concrete measurement window"):
        report_stage_effort(
            [],
            stage_by_observation={},
            stage_mapping_version="stage-v1",
            role="report_reader",
            case_ids=frozenset(),
            minimum_cases=2,
            window=unsafe,
        )


def test_work_utc_overflow_rejected_without_releasing_values() -> None:
    """An aware instant outside representable UTC is invalid evidence."""
    item = work(0, "professional_review")
    object.__setattr__(
        item, "recorded_at_utc", datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1)))
    )
    with pytest.raises(ValueError, match="UTC range"):
        report([item], {item.observation_id: "professional_review"})
