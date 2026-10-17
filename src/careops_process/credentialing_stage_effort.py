"""Explicit stage assignments over observed worker effort, with joint case privacy."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Never

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope
from careops_process.credentialing_observations import (
    EffortMetrics,
    MeasurementWindow,
    WorkObservation,
    merge_observations,
    observation_payload,
    parse_observation,
    report_effort,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

type WorkStage = Literal["professional_review", "committee_preparation", "other"]
_STAGES: tuple[WorkStage, ...] = ("professional_review", "committee_preparation", "other")
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")


def _fail(message: str) -> Never:
    raise CredentialingContractError(message)


def _code(value: object, limit: int = 128) -> None:
    if type(value) is not str or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Stage effort requires bounded concrete reference codes")


def _validated(item: object) -> WorkObservation:
    if type(item) is not WorkObservation:
        _fail("Stage effort requires concrete workload observations")
    for value in (item.observation_id, item.case_id, item.contract_version):
        _code(value)
    _code(item.source_system, 80)
    if (
        type(item.manual_touch_count) is not int
        or type(item.active_work_minutes) is not int
        or type(item.effort_complete) is not bool
        or type(item.recorded_at_utc) is not datetime
    ):
        _fail("Stage effort requires concrete work units, flags and instants")
    try:
        detached = parse_observation(observation_payload(item))
    except OverflowError:
        _fail("Stage effort instant exceeds the supported UTC range")
    if not isinstance(detached, WorkObservation):
        _fail("Stage effort requires workload evidence")
    return detached


def _window(value: MeasurementWindow) -> MeasurementWindow:
    if type(value) is not MeasurementWindow:
        _fail("Stage effort requires a concrete measurement window")
    _code(value.source_mapping_version, 80)
    _code(value.cohort_definition_version, 80)
    if (
        type(value.start_utc) is not datetime
        or type(value.end_utc) is not datetime
        or type(value.source_complete) is not bool
    ):
        _fail("Stage effort window requires concrete instants and coverage flag")
    return MeasurementWindow(
        start_utc=value.start_utc,
        end_utc=value.end_utc,
        source_mapping_version=value.source_mapping_version,
        cohort_definition_version=value.cohort_definition_version,
        source_complete=value.source_complete,
    )


@dataclass(frozen=True, slots=True)
class StageEffortMeasure:
    """One administrative stage's worker-effort minutes and case coverage."""

    stage: WorkStage
    metrics: EffortMetrics
    full_cohort_mean_minutes: float | None


@dataclass(frozen=True, slots=True)
class StageEffortReport:
    """One aggregate release, suppressing every stage when a joint cell is rare."""

    suppressed: bool
    measures: tuple[StageEffortMeasure, ...] | None = None


def _signature(items: list[WorkObservation]) -> tuple[object, ...]:
    if not items:
        return ("missing",)
    latest = max(item.recorded_at_utc for item in items)
    return (
        "complete"
        if all(item.effort_complete for item in items if item.recorded_at_utc == latest)
        else "partial",
        any(item.active_work_minutes > 0 for item in items),
        any(item.manual_touch_count > 0 for item in items),
    )


def _assignments(
    supplied: Mapping[str, str],
    retained: tuple[WorkObservation, ...],
) -> dict[str, WorkStage]:
    assignments: dict[str, WorkStage] = {}
    for observation_id, stage in dict(supplied).items():
        _code(observation_id)
        if type(stage) is not str or stage not in _STAGES:
            _fail("Unknown administrative work stage")
        assignments[observation_id] = stage
    if set(assignments) != {item.observation_id for item in retained}:
        _fail("Stage assignments must exactly cover the retained observation identities")
    return assignments


def report_stage_effort(  # noqa: PLR0913 - explicit trusted source mappings and population
    observations: Sequence[WorkObservation],
    *,
    stage_by_observation: Mapping[str, str],
    stage_mapping_version: str,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
    window: MeasurementWindow,
) -> StageEffortReport:
    """Break down observed work using source-approved assignments, never event guesses.

    Each observation ID must have exactly one explicit stage. Units are summed
    worker minutes and touches, not calendar time or distinct-worker counts.
    Source/cohort/window, disjoint minute allocation and classification approval
    are adapter responsibilities. This pure function authenticates no caller.
    """
    if type(role) is not str or type(minimum_cases) is not int:
        _fail("Stage effort scope requires concrete role and integer floor")
    grants, minimum = validate_measurement_scope(
        role=role, case_ids=case_ids, minimum_cases=minimum_cases
    )
    for case_id in grants:
        _code(case_id)
    _code(stage_mapping_version, 80)
    retained_window = _window(window)
    retained = tuple(_validated(item) for item in observations)
    assignments = _assignments(stage_by_observation, retained)
    groups: dict[WorkStage, list[WorkObservation]] = {stage: [] for stage in _STAGES}
    by_case: dict[str, dict[WorkStage, list[WorkObservation]]] = {
        case_id: {stage: [] for stage in _STAGES} for case_id in grants
    }
    for supplied in merge_observations((), retained):
        item = _validated(supplied)
        if item.case_id not in grants:
            continue
        if not retained_window.start_utc <= item.recorded_at_utc < retained_window.end_utc:
            _fail("Granted work observation is outside the measurement window")
        stage = assignments[item.observation_id]
        groups[stage].append(item)
        by_case[item.case_id][stage].append(item)
    joint = Counter(
        tuple(_signature(cases[stage]) for stage in _STAGES) for cases in by_case.values()
    )
    if not grants or any(count < minimum for count in joint.values()):
        return StageEffortReport(suppressed=True)
    measures: list[StageEffortMeasure] = []
    for stage in _STAGES:
        report = report_effort(groups[stage], role=role, case_ids=grants, minimum_cases=minimum)
        if report.metrics is None:
            return StageEffortReport(suppressed=True)
        metrics = report.metrics
        complete = retained_window.source_complete and metrics.complete_case_count == len(grants)
        measures.append(
            StageEffortMeasure(
                stage,
                metrics,
                metrics.mean_active_minutes_per_observed_case if complete else None,
            )
        )
    return StageEffortReport(suppressed=False, measures=tuple(measures))
