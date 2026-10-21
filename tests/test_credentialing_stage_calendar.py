# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Stage queue/calendar arithmetic, explicit source allocation and joint privacy."""

# Synthetic expected arithmetic uses deliberate literals.
# ruff: noqa: PLR2004

from dataclasses import asdict

import pytest
from hypothesis import given
from hypothesis import strategies as st

from careops_process.credentialing_local_reporting import CaseReportingObservation, WorkInterval
from careops_process.credentialing_stage_calendar import (
    StageCalendarPolicy,
    StageCalendarReport,
    report_stage_calendar,
)


def case(index: int, **changes: object) -> CaseReportingObservation:
    """Use an independently supplied complete observed case-span partition."""
    payload: dict[str, object] = {
        "observation_id": f"obs-{index}",
        "case_id": f"case-{index}",
        "source_system": "synthetic",
        "definition_version": "definition-v1",
        "window_code": "2026-Q1",
        "pathway_code": None,
        "correction_reasons": None,
        "further_information_reasons": None,
        "deferral_reasons": None,
        "exception_reasons": None,
        "observed_trace": None,
        "elapsed_minutes": 60.0,
        "intervals": (
            {"start_minute": 0, "end_minute": 40, "state": "queue"},
            {"start_minute": 40, "end_minute": 55, "state": "active"},
            {"start_minute": 55, "end_minute": 60, "state": "unknown"},
        ),
    }
    payload.update(changes)
    return CaseReportingObservation.model_validate(payload)


def policy(*, complete: bool = True) -> StageCalendarPolicy:
    """No clinical/default stage mapping is installed by the library."""
    return StageCalendarPolicy(
        definition_version="definition-v1",
        window_code="2026-Q1",
        stage_mapping_version="stage-v1",
        source_complete=complete,
        stage_codes=frozenset({"validation", "committee"}),
    )


def report(
    records: list[CaseReportingObservation],
    mapping: dict[str, tuple[str, ...]],
    *,
    complete: bool = True,
    population: int = 4,
) -> StageCalendarReport:
    """Release one full source-defined eligible case-span population."""
    return report_stage_calendar(
        records,
        stages_by_observation=mapping,
        policy=policy(complete=complete),
        role="report_reader",
        case_ids=frozenset(f"case-{i}" for i in range(population)),
        minimum_cases=2,
    )


def test_stage_queue_and_calendar_totals_reconcile_without_worker_effort() -> None:
    """Each interval is allocated once; states and stages partition observed elapsed."""
    records = [case(i) for i in range(4)]
    mapping = {item.observation_id: ("validation", "committee", "committee") for item in records}
    result = report([*records, records[0]], mapping)
    assert not result.suppressed
    assert result.elapsed_minutes == 240
    assert result.measures is not None
    stages = {item.stage: item for item in result.measures}
    assert stages["validation"].queue_minutes == 160
    assert stages["validation"].mean_queue_minutes_per_observed_case == 40
    assert stages["validation"].full_population_mean_queue_minutes == 40
    assert stages["committee"].active_minutes == 60
    assert stages["committee"].unknown_minutes == 20
    totals: list[float] = []
    for item in result.measures:
        assert item.queue_minutes is not None
        assert item.active_minutes is not None
        assert item.unknown_minutes is not None
        totals.append(item.queue_minutes + item.active_minutes + item.unknown_minutes)
    assert sum(totals) == 240
    assert "case-0" not in str(asdict(result))


def test_missing_spans_and_observed_absent_stages_differ() -> None:
    """Complete observed spans with no stage have zero; unavailable spans do not."""
    records = [case(i) for i in range(2)]
    result = report(records, {item.observation_id: ("committee",) * 3 for item in records})
    assert result.observed_case_count == result.missing_case_count == 2
    assert result.measures is not None
    validation = next(item for item in result.measures if item.stage == "validation")
    assert validation.stage_case_count == 0
    assert validation.absent_stage_case_count == 2
    assert validation.queue_minutes == 0
    assert validation.full_population_mean_queue_minutes is None
    empty = report([], {})
    assert empty.measures is not None
    assert all(item.queue_minutes is None for item in empty.measures)


@pytest.mark.parametrize(
    "mapping",
    [{}, {"obs-0": ("validation",)}, {"obs-0": ("validation", "committee", "unregistered")}],
)
def test_mapping_must_explicitly_cover_intervals(mapping: dict[str, tuple[str, ...]]) -> None:
    """Missing labels are never guessed from activities, endpoints or worker minutes."""
    with pytest.raises(ValueError, match=r"assignments|stage"):
        report([case(0)], mapping)


def test_safe_stage_marginals_cannot_hide_single_case_intersections() -> None:
    """Each stage has four participants but their unique membership is private."""
    records = [case(i) for i in range(8)]
    # Joint membership: validation-only 1, committee-only 1, both 3, neither 3.
    mapping: dict[str, tuple[str, ...]] = {}
    for item in records:
        index = int(item.case_id.split("-")[-1])
        left = "validation" if index in (0, 1, 2, 3) else "other"
        right = "committee" if index in (1, 2, 3, 4) else "other"
        mapping[item.observation_id] = (left, right, right)
    configured = StageCalendarPolicy(
        definition_version="definition-v1",
        window_code="2026-Q1",
        stage_mapping_version="stage-v1",
        source_complete=True,
        stage_codes=frozenset({"validation", "committee", "other"}),
    )
    result = report_stage_calendar(
        records,
        stages_by_observation=mapping,
        policy=configured,
        role="report_reader",
        case_ids=frozenset(f"case-{i}" for i in range(8)),
        minimum_cases=2,
    )
    assert asdict(result) == {
        "suppressed": True,
        "observed_case_count": None,
        "missing_case_count": None,
        "elapsed_minutes": None,
        "measures": None,
    }


def test_source_coverage_does_not_create_population_mean() -> None:
    """Observed means remain observed when source coverage is unconfirmed."""
    records = [case(i) for i in range(4)]
    result = report(
        records, {item.observation_id: ("validation",) * 3 for item in records}, complete=False
    )
    assert result.measures is not None
    stage = next(item for item in result.measures if item.stage == "validation")
    assert stage.mean_queue_minutes_per_stage_case == 40
    assert stage.full_population_mean_queue_minutes is None


def test_zero_span_and_missing_snapshot_are_distinct() -> None:
    """A genuinely observed zero span is not an unknown partition."""
    records = [case(i, elapsed_minutes=0.0, intervals=()) for i in range(4)]
    result = report(records, {item.observation_id: () for item in records})
    assert result.elapsed_minutes == 0
    assert result.observed_case_count == 4
    assert result.measures is not None
    assert all(item.queue_minutes == 0 for item in result.measures)
    missing = [case(i, elapsed_minutes=None, intervals=None) for i in range(4)]
    absent = report(missing, {item.observation_id: () for item in missing})
    assert absent.observed_case_count == 0
    assert absent.elapsed_minutes is None
    assert report([], {}, population=0).suppressed


def test_consistent_snapshots_count_once_and_conflicts_fail() -> None:
    """Repeated consistent case snapshots are not extra cases; changed replay fails."""
    records = [case(i) for i in range(4)]
    mapping = {item.observation_id: ("validation",) * 3 for item in records}
    repeated = case(0, observation_id="repeat")
    assert report([*records, repeated], {**mapping, "repeat": ("validation",) * 3}) == report(
        records, mapping
    )
    with pytest.raises(ValueError, match="case assessment"):
        report([*records, repeated], {**mapping, "repeat": ("committee",) * 3})
    with pytest.raises(ValueError, match="observation replay"):
        report([case(0), case(0, source_system="changed")], {"obs-0": ("validation",) * 3})


def test_ungranted_case_and_extra_map_identity() -> None:
    """Out-of-scope records cannot inflate time, but stale extra mapping fails."""
    records = [case(i) for i in range(4)]
    mapping = {item.observation_id: ("validation",) * 3 for item in records}
    assert report([*records, case(99)], {**mapping, "obs-99": ("committee",) * 3}) == report(
        records, mapping
    )
    with pytest.raises(ValueError, match="observation identities"):
        report(records, {**mapping, "stale": ()})


@pytest.mark.parametrize("changes", [{"definition_version": "other"}, {"window_code": "other"}])
def test_definition_and_window_binding(changes: dict[str, object]) -> None:
    """Metadata cannot silently change the requested span population."""
    with pytest.raises(ValueError, match="mismatch"):
        report([case(0, **changes)], {"obs-0": ("validation",) * 3})


@pytest.mark.parametrize(
    "changes",
    [
        {"stage_codes": frozenset[str]()},
        {"stage_codes": frozenset({"stage\n"})},
        {"source_complete": 1},
        {"stage_mapping_version": "raw narrative"},
        {"definition_version": "v1\n"},
        {"window_code": "q1\n"},
    ],
)
def test_mutated_policy_rejected(changes: dict[str, object]) -> None:
    """Frozen source policy is revalidated at the reporting boundary."""
    configured = policy()
    for key, value in changes.items():
        object.__setattr__(configured, key, value)
    with pytest.raises(ValueError, match=r"Calendar|calendar"):
        report_stage_calendar(
            [],
            stages_by_observation={},
            policy=configured,
            role="report_reader",
            case_ids=frozenset(),
            minimum_cases=2,
        )


def test_policy_subclass_is_not_trusted_configuration() -> None:
    """A subclass cannot disable concrete policy validation."""

    class UnsafePolicy(StageCalendarPolicy):
        def __post_init__(self) -> None:
            pass

    configured = UnsafePolicy(
        definition_version="bad",
        window_code="bad",
        stage_mapping_version="bad",
        stage_codes=frozenset(),
        source_complete=False,
    )
    with pytest.raises(ValueError, match="concrete source policy"):
        report_stage_calendar(
            [],
            stages_by_observation={},
            policy=configured,
            role="report_reader",
            case_ids=frozenset(),
            minimum_cases=2,
        )


def test_record_and_interval_boundaries_revalidated() -> None:
    """Frozen nested intervals still require a valid positive partition."""
    item = case(0)
    assert item.intervals is not None
    object.__setattr__(item.intervals[0], "end_minute", -1)
    with pytest.raises(ValueError, match="validation error"):
        report([item], {"obs-0": ("validation",) * 3})

    class UnsafeInterval(WorkInterval):
        pass

    item = case(0)
    object.__setattr__(
        item,
        "intervals",
        (UnsafeInterval.model_construct(start_minute=0, end_minute=60, state="queue"),),
    )
    with pytest.raises(ValueError, match="concrete interval"):
        report([item], {"obs-0": ("validation",)})

    class UnsafeCase(CaseReportingObservation):
        pass

    with pytest.raises(ValueError, match="concrete case"):
        report([UnsafeCase.model_construct(**case(0).model_dump())], {"obs-0": ("validation",) * 3})


def test_finite_spans_cannot_overflow_report() -> None:
    """Individually finite observations cannot release an infinite total."""
    records = [
        case(
            i,
            elapsed_minutes=1e308,
            intervals=({"start_minute": 0, "end_minute": 1e308, "state": "queue"},),
        )
        for i in range(4)
    ]
    with pytest.raises(ValueError, match="finite minute"):
        report(records, {item.observation_id: ("validation",) for item in records})


@pytest.mark.parametrize(
    ("role", "floor"), [("case_analyst", 2), ("report_reader", True), ("report_reader", 1)]
)
def test_scope_rejected(role: str, floor: object) -> None:
    """Role and threshold validation precede protected evidence processing."""
    with pytest.raises(ValueError, match=r"Calendar scope|Measurement"):
        report_stage_calendar(
            [],
            stages_by_observation={},
            policy=policy(),
            role=role,
            case_ids=frozenset(),
            minimum_cases=floor,
        )


@given(st.lists(st.integers(min_value=0, max_value=3), max_size=20))
def test_replay_and_order_do_not_change_stage_time(indices: list[int]) -> None:
    """Snapshot arithmetic is stable under arbitrary exact replay."""
    records = [case(i) for i in range(4)]
    mapping = {item.observation_id: ("validation", "committee", "committee") for item in records}
    assert report([*reversed(records), *(records[index] for index in indices)], mapping) == report(
        records, mapping
    )
