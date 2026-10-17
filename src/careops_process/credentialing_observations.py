"""Strict observed effort/evaluation evidence and aggregate comparison boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Never

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_WIRE_INSTANT = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$",
)
_MAX_COUNT = 1_000_000_000
_BASE_KEYS = frozenset(
    {"kind", "contract_version", "observation_id", "case_id", "source_system", "recorded_at_utc"},
)


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _reference(value: object, limit: int = 128) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= limit
        or _REFERENCE.fullmatch(value) is None
    ):
        _fail("Observation requires a bounded source reference")
    return value


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Observation timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _count(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= _MAX_COUNT:
        _fail("Observed counts must be bounded nonnegative integers")
    return value


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        _fail("Observed flags must be booleans")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class _Observation:
    observation_id: str
    case_id: str
    source_system: str
    recorded_at_utc: datetime
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:
        if self.contract_version != "0.1.0":
            _fail("Unsupported observation contract version")
        _reference(self.observation_id)
        _reference(self.case_id)
        _reference(self.source_system, 80)
        object.__setattr__(self, "recorded_at_utc", _instant(self.recorded_at_utc))


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkObservation(_Observation):
    """An observed effort delta; completeness attests measurement coverage only."""

    manual_touch_count: int
    active_work_minutes: int
    effort_complete: bool = False
    kind: ClassVar[str] = "workload"

    def __post_init__(self) -> None:
        """Reject coercion and preserve nonnegative measured units."""
        _Observation.__post_init__(self)
        _count(self.manual_touch_count)
        _count(self.active_work_minutes)
        _boolean(self.effort_complete)


@dataclass(frozen=True, slots=True, kw_only=True)
class EvaluationObservation(_Observation):
    """One independent case-level evaluation at a controlled reference version."""

    alert_raised: bool
    requirement_present: bool
    evaluation_reference_version: str
    kind: ClassVar[str] = "evaluation"

    def __post_init__(self) -> None:
        """Require strict review labels without narrative or clinical conclusions."""
        _Observation.__post_init__(self)
        _boolean(self.alert_raised)
        _boolean(self.requirement_present)
        _reference(self.evaluation_reference_version, 80)


type Observation = WorkObservation | EvaluationObservation


def observation_payload(observation: Observation) -> dict[str, object]:
    """Export the strict versioned wire representation without raw source content."""
    payload: dict[str, object] = {
        "kind": observation.kind,
        "contract_version": observation.contract_version,
        "observation_id": observation.observation_id,
        "case_id": observation.case_id,
        "source_system": observation.source_system,
        "recorded_at_utc": observation.recorded_at_utc.isoformat(),
    }
    if isinstance(observation, WorkObservation):
        payload.update(
            manual_touch_count=observation.manual_touch_count,
            active_work_minutes=observation.active_work_minutes,
            effort_complete=observation.effort_complete,
        )
    else:
        payload.update(
            alert_raised=observation.alert_raised,
            requirement_present=observation.requirement_present,
            evaluation_reference_version=observation.evaluation_reference_version,
        )
    return payload


def _parse_instant(value: object) -> datetime:
    if not isinstance(value, str) or _WIRE_INSTANT.fullmatch(value) is None:
        _fail("Wire timestamp must use an aware RFC3339 instant")
    try:
        return _instant(datetime.fromisoformat(value.replace("z", "+00:00")))
    except ValueError:
        _fail("Wire timestamp is not a valid instant")


def parse_observation(payload: Mapping[str, object]) -> Observation:
    """Validate exact wire keys, strict scalar units and aware timestamps."""
    kind = payload.get("kind")
    extra_keys = (
        {"manual_touch_count", "active_work_minutes", "effort_complete"}
        if kind == "workload"
        else {"alert_raised", "requirement_present", "evaluation_reference_version"}
    )
    if kind not in ("workload", "evaluation") or frozenset(payload) != _BASE_KEYS | extra_keys:
        _fail("Observation kind or fields do not match the strict contract")
    if payload.get("contract_version") != "0.1.0":
        _fail("Unsupported observation contract version")
    identity = _reference(payload.get("observation_id"))
    case_id = _reference(payload.get("case_id"))
    source = _reference(payload.get("source_system"), 80)
    recorded = _parse_instant(payload.get("recorded_at_utc"))
    if kind == "workload":
        return WorkObservation(
            observation_id=identity,
            case_id=case_id,
            source_system=source,
            recorded_at_utc=recorded,
            manual_touch_count=_count(payload.get("manual_touch_count")),
            active_work_minutes=_count(payload.get("active_work_minutes")),
            effort_complete=_boolean(payload.get("effort_complete")),
        )
    return EvaluationObservation(
        observation_id=identity,
        case_id=case_id,
        source_system=source,
        recorded_at_utc=recorded,
        alert_raised=_boolean(payload.get("alert_raised")),
        requirement_present=_boolean(payload.get("requirement_present")),
        evaluation_reference_version=_reference(payload.get("evaluation_reference_version"), 80),
    )


def merge_observations(
    existing: Sequence[Observation],
    incoming: Sequence[Observation],
) -> tuple[Observation, ...]:
    """Deduplicate exact kind/ID replay and reject conflicting retained history."""
    merged: dict[tuple[str, str], Observation] = {}
    for supplied in (*existing, *incoming):
        item = parse_observation(observation_payload(supplied))
        key = (item.kind, item.observation_id)
        if key in merged and merged[key] != item:
            _fail("Conflicting observation replay")
        merged[key] = item
    return tuple(merged[key] for key in sorted(merged))


@dataclass(frozen=True, slots=True)
class EffortMetrics:
    """Observed deltas and case-coverage counts; missing effort is not zero."""

    population_case_count: int
    observed_case_count: int
    missing_case_count: int
    complete_case_count: int
    partial_case_count: int
    total_manual_touches: int | None
    total_active_work_minutes: int | None
    mean_active_minutes_per_observed_case: float | None


@dataclass(frozen=True, slots=True)
class EffortReport:
    """Released effort aggregates or whole-report suppression."""

    suppressed: bool
    metrics: EffortMetrics | None


def _effort_metrics(
    observations: Sequence[WorkObservation],
    grants: frozenset[str],
) -> EffortMetrics:
    by_case: dict[str, list[WorkObservation]] = {case: [] for case in grants}
    for item in merge_observations((), observations):
        if not isinstance(item, WorkObservation):
            _fail("Effort requires workload observations")
        if item.case_id in grants:
            by_case[item.case_id].append(item)
    observed = [items for items in by_case.values() if items]
    complete = sum(
        all(item.effort_complete for item in items if item.recorded_at_utc == latest)
        for items in observed
        for latest in [max(item.recorded_at_utc for item in items)]
    )
    minutes = sum(item.active_work_minutes for items in observed for item in items)
    touches = sum(item.manual_touch_count for items in observed for item in items)
    return EffortMetrics(
        len(grants),
        len(observed),
        len(grants) - len(observed),
        complete,
        len(observed) - complete,
        touches if observed else None,
        minutes if observed else None,
        minutes / len(observed) if observed else None,
    )


def report_effort(
    observations: Sequence[WorkObservation],
    *,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
) -> EffortReport:
    """Report observed work only when all nonzero coverage cells meet policy."""
    grants, minimum = validate_measurement_scope(
        role=role,
        case_ids=case_ids,
        minimum_cases=minimum_cases,
    )
    metrics = _effort_metrics(observations, grants)
    counts = (
        metrics.observed_case_count,
        metrics.missing_case_count,
        metrics.complete_case_count,
        metrics.partial_case_count,
    )
    if not grants or any(0 < count < minimum for count in counts):
        return EffortReport(suppressed=True, metrics=None)
    return EffortReport(suppressed=False, metrics=metrics)


@dataclass(frozen=True, slots=True)
class QualityMetrics:
    """Distinct-case confusion counts; denominators are reviewed cases, not rows."""

    evaluated_case_count: int
    missing_case_count: int
    outcome_case_counts: tuple[tuple[str, int], ...]
    false_positive_numerator: int
    false_positive_denominator: int
    false_positive_rate: float | None
    false_negative_numerator: int
    false_negative_denominator: int
    false_negative_rate: float | None


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Released case-level quality evidence or whole-report suppression."""

    suppressed: bool
    metrics: QualityMetrics | None


def _case_evaluations(
    observations: Sequence[EvaluationObservation],
    grants: frozenset[str],
    reference: str,
) -> dict[str, tuple[bool, bool]]:
    cases: dict[str, tuple[bool, bool]] = {}
    for item in merge_observations((), observations):
        if not isinstance(item, EvaluationObservation):
            _fail("Quality requires evaluation observations")
        if item.case_id not in grants:
            continue
        if item.evaluation_reference_version != reference:
            _fail("Evaluation reference does not match the approved mapping")
        outcome = (item.alert_raised, item.requirement_present)
        if item.case_id in cases and cases[item.case_id] != outcome:
            _fail("Conflicting case-level evaluation at the same reference version")
        cases[item.case_id] = outcome
    return cases


def report_quality(
    observations: Sequence[EvaluationObservation],
    *,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
    reference_version: str,
) -> QualityReport:
    """Count one consistent independent evaluation per granted case/reference."""
    grants, minimum = validate_measurement_scope(
        role=role,
        case_ids=case_ids,
        minimum_cases=minimum_cases,
    )
    _reference(reference_version, 80)
    cases = _case_evaluations(observations, grants, reference_version)
    labels = {(True, True): "tp", (True, False): "fp", (False, False): "tn", (False, True): "fn"}
    groups: dict[str, set[str]] = {label: set() for label in labels.values()}
    for case, outcome in cases.items():
        groups[labels[outcome]].add(case)
    counts = {label: len(contributors) for label, contributors in groups.items()}
    missing = len(grants) - len(cases)
    cells = (*counts.values(), len(cases), missing)
    if not grants or any(0 < count < minimum for count in cells):
        return QualityReport(suppressed=True, metrics=None)
    negative = counts["fp"] + counts["tn"]
    positive = counts["fn"] + counts["tp"]
    return QualityReport(
        suppressed=False,
        metrics=QualityMetrics(
            len(cases),
            missing,
            tuple(sorted(counts.items())),
            counts["fp"],
            negative,
            counts["fp"] / negative if negative else None,
            counts["fn"],
            positive,
            counts["fn"] / positive if positive else None,
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class MeasurementWindow:
    """A source-attested reporting window with versioned cohort definitions."""

    start_utc: datetime
    end_utc: datetime
    source_mapping_version: str
    cohort_definition_version: str
    source_complete: bool

    def __post_init__(self) -> None:
        """Normalize aware bounds and reject ambiguous windows/configuration."""
        object.__setattr__(self, "start_utc", _instant(self.start_utc))
        object.__setattr__(self, "end_utc", _instant(self.end_utc))
        if self.end_utc <= self.start_utc:
            _fail("Measurement window must have increasing bounds")
        _reference(self.source_mapping_version, 80)
        _reference(self.cohort_definition_version, 80)
        _boolean(self.source_complete)


@dataclass(frozen=True, slots=True)
class EffortComparison:
    """Arithmetic observed difference, never a causal released-capacity claim."""

    suppressed: bool
    available: bool
    reason: str | None = None
    baseline_minutes_per_case: float | None = None
    current_minutes_per_case: float | None = None
    observed_minutes_per_case_difference: float | None = None


def _comparison_limit(
    baseline: MeasurementWindow,
    current: MeasurementWindow,
) -> str | None:
    if (
        baseline.source_mapping_version != current.source_mapping_version
        or baseline.cohort_definition_version != current.cohort_definition_version
    ):
        return "cohort_or_source_mismatch"
    if baseline.end_utc > current.start_utc:
        return "overlapping_windows"
    if not baseline.source_complete or not current.source_complete:
        return "source_completeness_unverified"
    return None


def compare_effort(  # noqa: PLR0913 - explicit independent cohort grants and windows
    baseline: Sequence[WorkObservation],
    current: Sequence[WorkObservation],
    *,
    baseline_window: MeasurementWindow,
    current_window: MeasurementWindow,
    baseline_case_ids: AbstractSet[str],
    current_case_ids: AbstractSet[str],
    role: str,
    minimum_cases: object,
) -> EffortComparison:
    """Compare complete matched windows without inferring work from event timing."""
    before = report_effort(
        tuple(
            item
            for item in baseline
            if baseline_window.start_utc <= item.recorded_at_utc < baseline_window.end_utc
        ),
        role=role,
        case_ids=baseline_case_ids,
        minimum_cases=minimum_cases,
    )
    after = report_effort(
        tuple(
            item
            for item in current
            if current_window.start_utc <= item.recorded_at_utc < current_window.end_utc
        ),
        role=role,
        case_ids=current_case_ids,
        minimum_cases=minimum_cases,
    )
    if before.metrics is None or after.metrics is None:
        return EffortComparison(suppressed=True, available=False)
    reason = _comparison_limit(baseline_window, current_window)
    if reason is not None:
        return EffortComparison(suppressed=False, available=False, reason=reason)
    if (
        before.metrics.missing_case_count
        or after.metrics.missing_case_count
        or before.metrics.partial_case_count
        or after.metrics.partial_case_count
    ):
        return EffortComparison(
            suppressed=False,
            available=False,
            reason="incomplete_effort_population",
        )
    before_mean = before.metrics.mean_active_minutes_per_observed_case
    after_mean = after.metrics.mean_active_minutes_per_observed_case
    if before_mean is None or after_mean is None:
        return EffortComparison(suppressed=False, available=False, reason="unavailable_effort")
    return EffortComparison(
        suppressed=False,
        available=True,
        baseline_minutes_per_case=before_mean,
        current_minutes_per_case=after_mean,
        observed_minutes_per_case_difference=before_mean - after_mean,
    )
