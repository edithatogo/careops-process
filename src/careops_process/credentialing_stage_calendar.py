"""Explicit stage allocation of observed case-calendar queue/active/unknown time."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Never

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_local_reporting import CaseReportingObservation, WorkInterval
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
_STATES = ("queue", "active", "unknown")


def _fail(message: str) -> Never:
    raise CredentialingContractError(message)


def _code(value: object, limit: int = 80) -> None:
    if type(value) is not str or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Calendar stage references must be bounded concrete codes")


@dataclass(frozen=True, slots=True, kw_only=True)
class StageCalendarPolicy:
    """Trusted source/span/stage definitions, not clinical rules or authentication."""

    definition_version: str
    window_code: str
    stage_mapping_version: str
    stage_codes: frozenset[str]
    source_complete: bool

    def __post_init__(self) -> None:
        """Require explicitly registered stages and strict source-coverage metadata."""
        for value in (self.definition_version, self.window_code, self.stage_mapping_version):
            _code(value)
        if type(self.stage_codes) is not frozenset or not self.stage_codes:
            _fail("Calendar stages require a nonempty concrete frozen vocabulary")
        for stage in self.stage_codes:
            _code(stage)
        if type(self.source_complete) is not bool:
            _fail("Calendar source coverage must be a concrete boolean")


@dataclass(frozen=True, slots=True)
class StageCalendarMeasure:
    """One stage, with explicit span coverage and two different queue denominators."""

    stage: str
    stage_case_count: int
    absent_stage_case_count: int
    queue_case_count: int
    active_case_count: int
    unknown_case_count: int
    queue_minutes: float | None
    active_minutes: float | None
    unknown_minutes: float | None
    mean_queue_minutes_per_observed_case: float | None
    mean_queue_minutes_per_stage_case: float | None
    full_population_mean_queue_minutes: float | None


@dataclass(frozen=True, slots=True)
class StageCalendarReport:
    """One protected aggregate release; no counts or labels on suppression."""

    suppressed: bool
    observed_case_count: int | None = None
    missing_case_count: int | None = None
    elapsed_minutes: float | None = None
    measures: tuple[StageCalendarMeasure, ...] | None = None


def _validated(record: object) -> CaseReportingObservation:
    if type(record) is not CaseReportingObservation:
        _fail("Stage calendar requires concrete case observations")
    if record.intervals is not None and any(
        type(part) is not WorkInterval for part in record.intervals
    ):
        _fail("Stage calendar requires concrete interval observations")
    return CaseReportingObservation.model_validate(
        {key: getattr(record, key) for key in CaseReportingObservation.model_fields}
    )


def _labels(
    item: CaseReportingObservation,
    mappings: Mapping[str, tuple[str, ...]],
    policy: StageCalendarPolicy,
) -> tuple[str, ...]:
    stages = mappings.get(item.observation_id)
    if type(stages) is not tuple or len(stages) != len(item.intervals or ()):
        _fail("Stage assignments must exactly cover each observed interval")
    for stage in stages:
        _code(stage)
        if stage not in policy.stage_codes:
            _fail("Unregistered calendar stage")
    return stages


def _retained(
    observations: Sequence[CaseReportingObservation],
    assignments: Mapping[str, tuple[str, ...]],
    policy: StageCalendarPolicy,
    grants: frozenset[str],
) -> dict[str, tuple[CaseReportingObservation, tuple[str, ...]]]:
    identities: dict[str, CaseReportingObservation] = {}
    mappings = dict(assignments)
    for key in mappings:
        _code(key, 128)
    cases: dict[str, tuple[CaseReportingObservation, tuple[str, ...]]] = {}
    for supplied in observations:
        item = _validated(supplied)
        previous = identities.get(item.observation_id)
        if previous is not None and previous != item:
            _fail("Conflicting stage calendar observation replay")
        identities[item.observation_id] = item
        stages = _labels(item, mappings, policy)
        if item.case_id not in grants:
            continue
        if (item.definition_version, item.window_code) != (
            policy.definition_version,
            policy.window_code,
        ):
            _fail("Stage calendar source definition or window mismatch")
        prior_case = cases.get(item.case_id)
        if prior_case is not None and (
            prior_case[0].model_dump(exclude={"observation_id"})
            != item.model_dump(exclude={"observation_id"})
            or prior_case[1] != stages
        ):
            _fail("Conflicting stage calendar case assessment")
        cases[item.case_id] = (item, stages)
    if set(mappings) != set(identities):
        _fail("Stage assignments must exactly cover observation identities")
    return cases


def _case_states(
    record: tuple[CaseReportingObservation, tuple[str, ...]] | None,
    stages: tuple[str, ...],
) -> tuple[object, ...]:
    if record is None or record[0].intervals is None:
        return ("missing",)
    item, assigned = record
    pairs = tuple(zip(item.intervals or (), assigned, strict=True))
    return (
        "observed",
        *(
            tuple(
                any(label == stage and part.state == state for part, label in pairs)
                for state in _STATES
            )
            for stage in stages
        ),
    )


def _total(values: Iterable[float]) -> float:
    try:
        return math.fsum(values)
    except OverflowError:
        _fail("Calendar aggregate exceeds the finite minute range")


def _measure(
    stage: str,
    records: list[tuple[CaseReportingObservation, tuple[str, ...]]],
    population: int,
    *,
    source_complete: bool,
) -> StageCalendarMeasure:
    selected = [
        [part for part, label in zip(item.intervals or (), stages, strict=True) if label == stage]
        for item, stages in records
    ]
    participants = sum(bool(parts) for parts in selected)
    counts = {
        state: sum(any(part.state == state for part in parts) for parts in selected)
        for state in _STATES
    }
    totals = {
        state: _total(
            part.end_minute - part.start_minute
            for parts in selected
            for part in parts
            if part.state == state
        )
        for state in _STATES
    }
    queue = totals["queue"]
    return StageCalendarMeasure(
        stage,
        participants,
        len(records) - participants,
        counts["queue"],
        counts["active"],
        counts["unknown"],
        queue if records else None,
        totals["active"] if records else None,
        totals["unknown"] if records else None,
        queue / len(records) if records else None,
        queue / participants if participants else None,
        queue / population if source_complete and len(records) == population else None,
    )


def report_stage_calendar(  # noqa: PLR0913 - explicit policy, stage mapping and trusted scope
    observations: Sequence[CaseReportingObservation],
    *,
    stages_by_observation: Mapping[str, tuple[str, ...]],
    policy: StageCalendarPolicy,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
) -> StageCalendarReport:
    """Allocate existing observed intervals once; never infer queue from elapsed/work.

    All cases with complete observed partitions form each stage's observed-case
    denominator, including cases whose accepted span has no such stage. Missing
    partitions remain missing, not zero or proof of pathway non-applicability.
    """
    if type(role) is not str or type(minimum_cases) is not int:
        _fail("Calendar scope requires a concrete role and integer floor")
    grants, minimum = validate_measurement_scope(
        role=role, case_ids=case_ids, minimum_cases=minimum_cases
    )
    for case_id in grants:
        _code(case_id, 128)
    if type(policy) is not StageCalendarPolicy:
        _fail("Stage calendar requires concrete source policy")
    configured = StageCalendarPolicy(
        definition_version=policy.definition_version,
        window_code=policy.window_code,
        stage_mapping_version=policy.stage_mapping_version,
        stage_codes=policy.stage_codes,
        source_complete=policy.source_complete,
    )
    stages = tuple(sorted(configured.stage_codes))
    cases = _retained(observations, stages_by_observation, configured, grants)
    atoms = Counter(_case_states(cases.get(case_id), stages) for case_id in grants)
    if not grants or any(count < minimum for count in atoms.values()):
        return StageCalendarReport(suppressed=True)
    timed = [record for record in cases.values() if record[0].intervals is not None]
    elapsed = _total(record[0].elapsed_minutes or 0 for record in timed) if timed else None
    return StageCalendarReport(
        suppressed=False,
        observed_case_count=len(timed),
        missing_case_count=len(grants) - len(timed),
        elapsed_minutes=elapsed,
        measures=tuple(
            _measure(stage, timed, len(grants), source_complete=configured.source_complete)
            for stage in stages
        ),
    )
