"""Source-defined case snapshots and jointly protected local reporting.

These observations are independent source assessments, not labels inferred from
event absence. Trusted adapters resolve populations, versions and vocabularies.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from careops_process.credentialing import Activity, CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Sequence
    from collections.abc import Set as AbstractSet

type Code = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*(?![\s\S])",
    ),
]
type Reference = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*(?![\s\S])",
    ),
]
type Minutes = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
type Measure = Literal["correction", "further_information", "deferral", "exception"]
_MEASURES: tuple[Measure, ...] = ("correction", "further_information", "deferral", "exception")


class _Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        regex_engine="python-re",
        hide_input_in_errors=True,
    )


class WorkInterval(_Contract):
    """An observed exclusive state interval, in offsets from the case span start."""

    start_minute: Minutes
    end_minute: Minutes
    state: Literal["queue", "active", "unknown"]

    @model_validator(mode="after")
    def positive_interval(self) -> Self:
        """Reject zero-length and reversed observations."""
        if self.end_minute <= self.start_minute:
            msg = "Work interval must have positive duration"
            raise ValueError(msg)
        return self


class ReportingDefinition(_Contract):
    """Deployment-supplied criteria; code shape does not establish approval."""

    definition_version: Code
    window_code: Code
    pathway_codes: frozenset[Code]
    reason_codes: frozenset[Code]


class CaseReportingObservation(_Contract):
    """One observed case/window assessment, with no free text or person identity.

    None means unavailable; empty reasons mean an explicitly observed negative.
    A positive has one or more controlled process reason codes. Trace is the
    source's observed administrative sequence, never an inferred sequence.
    """

    kind: Literal["credentialing_case_reporting"] = "credentialing_case_reporting"
    contract_version: Literal["0.1.0"] = "0.1.0"
    observation_id: Reference
    case_id: Reference
    source_system: Code
    definition_version: Code
    window_code: Code
    pathway_code: Code | None
    correction_reasons: tuple[Code, ...] | None
    further_information_reasons: tuple[Code, ...] | None
    deferral_reasons: tuple[Code, ...] | None
    exception_reasons: tuple[Code, ...] | None
    observed_trace: tuple[Activity, ...] | None
    elapsed_minutes: Minutes | None
    intervals: tuple[WorkInterval, ...] | None

    @model_validator(mode="after")
    def coherent_evidence(self) -> Self:
        """Canonicalise sets and require an exhaustive non-overlapping partition."""
        for measure in _MEASURES:
            field = f"{measure}_reasons"
            reasons = getattr(self, field)
            if reasons is not None:
                if len(set(reasons)) != len(reasons):
                    msg = "Reason codes must be unique"
                    raise ValueError(msg)
                object.__setattr__(self, field, tuple(sorted(reasons)))
        if self.observed_trace == ():
            msg = "Empty trace is unavailable; use null"
            raise ValueError(msg)
        if (self.elapsed_minutes is None) != (self.intervals is None):
            msg = "Elapsed time and partition must be supplied together"
            raise ValueError(msg)
        if self.intervals is not None:
            cursor = 0.0
            for interval in self.intervals:
                if interval.start_minute != cursor:
                    msg = "Intervals must partition elapsed time without gaps or overlap"
                    raise ValueError(msg)
                cursor = interval.end_minute
            if cursor != self.elapsed_minutes:
                msg = "Intervals must partition elapsed time exactly"
                raise ValueError(msg)
        return self


def _validated(item: CaseReportingObservation) -> CaseReportingObservation:
    if type(item) is not CaseReportingObservation:
        msg = "Expected concrete case reporting observation"
        raise CredentialingContractError(msg)
    if item.intervals is not None and any(
        type(part) is not WorkInterval for part in item.intervals
    ):
        msg = "Expected concrete work intervals"
        raise CredentialingContractError(msg)
    return CaseReportingObservation.model_validate(
        {name: getattr(item, name) for name in CaseReportingObservation.model_fields},
    )


@dataclass(frozen=True, slots=True)
class CaseReasonRate:
    """Case-based numerator and explicit assessment denominator for one measure."""

    measure: Measure
    assessed_case_count: int
    missing_case_count: int
    positive_case_count: int
    negative_case_count: int
    observed_rate: float | None
    population_rate: float | None
    population_rate_unavailable_reason: str | None
    reason_case_counts: tuple[tuple[str, int], ...]
    reason_observed_rates: tuple[tuple[str, float], ...]
    reason_population_rates: tuple[tuple[str, float], ...] | None


@dataclass(frozen=True, slots=True)
class TimeDecomposition:
    """Total observed case minutes; active minutes are not worker effort."""

    assessed_case_count: int
    missing_case_count: int
    elapsed_minutes: float
    queue_minutes: float
    active_minutes: float
    unknown_minutes: float


@dataclass(frozen=True, slots=True)
class LocalCredentialingReport:
    """One combined aggregate release; rare joint cells redact the entire report."""

    suppressed: bool
    population_case_count: int | None = None
    observed_case_count: int | None = None
    missing_case_count: int | None = None
    pathway_counts: tuple[tuple[str, int], ...] | None = None
    pathway_mix: tuple[tuple[str, float], ...] | None = None
    missing_pathway_case_count: int | None = None
    rates: tuple[CaseReasonRate, ...] | None = None
    time: TimeDecomposition | None = None
    variants: tuple[tuple[tuple[str, ...], int], ...] | None = None
    missing_trace_case_count: int | None = None


def _reasons(item: CaseReportingObservation, measure: Measure) -> tuple[str, ...] | None:
    return {
        "correction": item.correction_reasons,
        "further_information": item.further_information_reasons,
        "deferral": item.deferral_reasons,
        "exception": item.exception_reasons,
    }[measure]


def _case_signature(item: CaseReportingObservation | None) -> tuple[object, ...]:
    if item is None:
        return ("missing",)
    return (
        item.pathway_code,
        *(_reasons(item, measure) for measure in _MEASURES),
        item.observed_trace,
        item.intervals is not None,
        *(
            any(part.state == state for part in item.intervals or ())
            for state in ("queue", "active", "unknown")
        ),
    )


def _rate(
    cases: dict[str, CaseReportingObservation],
    population: int,
    measure: Measure,
    *,
    source_complete: bool,
) -> CaseReasonRate:
    values = [_reasons(item, measure) for item in cases.values()]
    assessed = [value for value in values if value is not None]
    positive = sum(bool(value) for value in assessed)
    missing = population - len(assessed)
    reason = (
        "missing_assessments"
        if missing
        else "source_coverage_unconfirmed"
        if not source_complete
        else None
    )
    rate = positive / len(assessed) if assessed else None
    counts = Counter(code for value in assessed for code in value)
    reason_rates = tuple((code, count / len(assessed)) for code, count in sorted(counts.items()))
    return CaseReasonRate(
        measure,
        len(assessed),
        missing,
        positive,
        len(assessed) - positive,
        rate,
        rate if reason is None else None,
        reason,
        tuple(sorted(counts.items())),
        reason_rates,
        reason_rates if reason is None else None,
    )


def _times(cases: dict[str, CaseReportingObservation], population: int) -> TimeDecomposition:
    assessed = [item for item in cases.values() if item.intervals is not None]
    try:
        totals = {
            state: math.fsum(
                part.end_minute - part.start_minute
                for item in assessed
                for part in item.intervals or ()
                if part.state == state
            )
            for state in ("queue", "active", "unknown")
        }
        elapsed = math.fsum(item.elapsed_minutes or 0 for item in assessed)
    except OverflowError:
        msg = "Reporting time aggregate exceeds finite range"
        raise CredentialingContractError(msg) from None
    return TimeDecomposition(
        len(assessed),
        population - len(assessed),
        elapsed,
        totals["queue"],
        totals["active"],
        totals["unknown"],
    )


def _retained(
    observations: Sequence[CaseReportingObservation],
    grants: frozenset[str],
    definition: ReportingDefinition,
) -> dict[str, CaseReportingObservation]:
    identities: dict[str, CaseReportingObservation] = {}
    cases: dict[str, CaseReportingObservation] = {}
    for supplied in observations:
        item = _validated(supplied)
        previous = identities.get(item.observation_id)
        if previous is not None and previous != item:
            msg = "Conflicting reporting observation replay"
            raise CredentialingContractError(msg)
        identities[item.observation_id] = item
        if item.case_id not in grants:
            continue
        if (item.definition_version, item.window_code) != (
            definition.definition_version,
            definition.window_code,
        ):
            msg = "Reporting definition or window mismatch"
            raise CredentialingContractError(msg)
        if item.pathway_code is not None and item.pathway_code not in definition.pathway_codes:
            msg = "Unregistered reporting pathway code"
            raise CredentialingContractError(msg)
        for measure in _MEASURES:
            if not set(_reasons(item, measure) or ()).issubset(definition.reason_codes):
                msg = "Unregistered process reason code"
                raise CredentialingContractError(msg)
        previous_case = cases.get(item.case_id)
        if previous_case is not None:
            left = previous_case.model_dump(exclude={"observation_id"})
            right = item.model_dump(exclude={"observation_id"})
            if left != right:
                msg = "Conflicting reporting case assessments"
                raise CredentialingContractError(msg)
        cases[item.case_id] = item
    return cases


def report_local_credentialing(  # noqa: PLR0913 - explicit trusted boundaries
    observations: Sequence[CaseReportingObservation],
    *,
    role: str,
    granted_case_ids: AbstractSet[str],
    definition: ReportingDefinition,
    source_complete: bool,
    minimum_case_count: int,
) -> LocalCredentialingReport:
    """Release demand, case rates, time partition and observed trace frequencies.

    The grant set is the full eligible case/window denominator, including cases
    without observations. Exact replay and consistent repeat assessments count
    once. Every nonzero JOINT categorical atom must meet the distinct-case floor.
    This does not provide cross-query privacy accounting or authenticate grants.
    """
    if type(minimum_case_count) is not int or type(role) is not str:
        msg = "Reporting floor and role must use concrete scalar types"
        raise CredentialingContractError(msg)
    grants, threshold = validate_measurement_scope(
        role=role,
        case_ids=granted_case_ids,
        minimum_cases=minimum_case_count,
    )
    if any(type(case_id) is not str for case_id in grants):
        msg = "Reporting case grants must use concrete reference strings"
        raise CredentialingContractError(msg)
    if type(source_complete) is not bool or type(definition) is not ReportingDefinition:
        msg = "Expected strict coverage and reporting definition"
        raise CredentialingContractError(msg)
    definition = ReportingDefinition.model_validate(
        {name: getattr(definition, name) for name in ReportingDefinition.model_fields},
    )
    cases = _retained(observations, grants, definition)
    atoms = Counter(_case_signature(cases.get(case_id)) for case_id in grants)
    if not grants or any(count < threshold for count in atoms.values()):
        return LocalCredentialingReport(suppressed=True)
    pathways = Counter(
        item.pathway_code for item in cases.values() if item.pathway_code is not None
    )
    known_pathways = sum(pathways.values())
    variants = Counter(
        item.observed_trace for item in cases.values() if item.observed_trace is not None
    )
    return LocalCredentialingReport(
        suppressed=False,
        population_case_count=len(grants),
        observed_case_count=len(cases),
        missing_case_count=len(grants) - len(cases),
        pathway_counts=tuple(sorted(pathways.items())),
        pathway_mix=tuple(
            (code, count / known_pathways) for code, count in sorted(pathways.items())
        ),
        missing_pathway_case_count=len(grants) - known_pathways,
        rates=tuple(
            _rate(cases, len(grants), measure, source_complete=source_complete)
            for measure in _MEASURES
        ),
        time=_times(cases, len(grants)),
        variants=tuple(sorted(variants.items())),
        missing_trace_case_count=len(grants) - sum(variants.values()),
    )
