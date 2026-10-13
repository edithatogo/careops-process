"""Observed credentialing elapsed-time measurements with whole-report privacy."""

from __future__ import annotations

import math
import re
import statistics
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)
from careops_process.credentialing_assurance import RENEWAL_STAGES

if TYPE_CHECKING:
    from careops_process.credentialing import CredentialingFact

_SAFE_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_SECONDS_PER_HOUR = 3600.0
_MINIMUM_CASES = 2
STAGE_INTERVALS = tuple(
    dict.fromkeys(
        (
            *pairwise(RENEWAL_STAGES),
            ("request_received", "case_completed"),
            ("recommendation_recorded", "delegated_decision_recorded"),
            ("decision_communicated", "register_activated"),
            ("delegated_decision_recorded", "register_activated"),
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class StageTimeMeasure:
    """One observed interval's reconciled counts and elapsed-hour quantiles."""

    interval_id: str
    eligible_case_count: int
    excluded_case_counts: tuple[tuple[str, int], ...]
    median_hours: float | None
    p75_hours: float | None
    p90_hours: float | None
    p95_hours: float | None


@dataclass(frozen=True, slots=True)
class StageTimeReport:
    """Released aggregate evidence or an entirely suppressed result."""

    suppressed: bool
    population_case_count: int | None
    measures: tuple[StageTimeMeasure, ...] | None


def _is_safe_code(value: object, limit: int) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= limit
        and _SAFE_CODE.fullmatch(value) is not None
    )


def _is_set_container(value: object) -> bool:
    return isinstance(value, AbstractSet)


def validate_measurement_scope(
    *,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
) -> tuple[frozenset[str], int]:
    """Check a trusted aggregate role, mapped case grants and technical floor.

    Args:
        role: Role resolved by the server-side authorisation layer.
        case_ids: A set of authorised references classified as cases by the adapter.
        minimum_cases: Deployment-approved distinct-case threshold, at least two.

    Returns:
        A detached immutable grant set and a validated integer threshold.

    Raises:
        CredentialingContractError: If role, references or threshold are unsafe.

    """
    if role != "report_reader":
        message = "Measurement role must be report_reader"
        raise CredentialingContractError(message)
    if (
        not isinstance(minimum_cases, int)
        or isinstance(minimum_cases, bool)
        or minimum_cases < _MINIMUM_CASES
    ):
        message = "Measurement minimum must be at least two distinct cases"
        raise CredentialingContractError(message)
    if not _is_set_container(case_ids):
        message = "Measurement case grant container must be a set"
        raise CredentialingContractError(message)
    grants = frozenset(case_ids)
    if any(not _is_safe_code(case_id, 128) for case_id in grants):
        message = "Measurement scope requires safe case references"
        raise CredentialingContractError(message)
    return grants, minimum_cases


def _case_interval(
    observed: list[CredentialingFact],
    start: str,
    finish: str,
    authority: str,
) -> float | str:
    if not observed:
        return "no_observed_evidence"
    if any(
        fact.qualifiers.pathway_code != "routine-renewal"
        or fact.qualifiers.authority_mapping_version != authority
        for fact in observed
    ):
        return "qualifier_mismatch"
    starts = [fact for fact in observed if fact.activity == start]
    finishes = [fact for fact in observed if fact.activity == finish]
    if not starts or not finishes:
        return "missing_endpoints"
    if len(starts) != 1 or len(finishes) != 1:
        return "repeated_endpoints"
    seconds = (finishes[0].timestamp_utc - starts[0].timestamp_utc).total_seconds()
    return _positive_interval(seconds)


def _positive_interval(seconds: float) -> float | str:
    if seconds == 0:
        return "tied_time"
    if seconds < 0:
        return "reversed_time"
    return seconds / _SECONDS_PER_HOUR


def _nearest_rank(ordered: list[float], percentile: int) -> float | None:
    if not ordered:
        return None
    return ordered[math.ceil(len(ordered) * percentile / 100) - 1]


def _measure(
    observed: dict[str, list[CredentialingFact]],
    start: str,
    finish: str,
    authority: str,
) -> tuple[StageTimeMeasure, tuple[int, ...]]:
    samples: list[float] = []
    excluded: dict[str, int] = {}
    for facts in observed.values():
        outcome = _case_interval(facts, start, finish, authority)
        if isinstance(outcome, str):
            excluded[outcome] = excluded.get(outcome, 0) + 1
        else:
            samples.append(outcome)
    samples.sort()
    counts = tuple(sorted(excluded.items()))
    measure = StageTimeMeasure(
        interval_id=f"{start}__{finish}",
        eligible_case_count=len(samples),
        excluded_case_counts=counts,
        median_hours=float(statistics.median(samples)) if samples else None,
        p75_hours=_nearest_rank(samples, 75),
        p90_hours=_nearest_rank(samples, 90),
        p95_hours=_nearest_rank(samples, 95),
    )
    return measure, (len(samples), *(count for _, count in counts))


def report_stage_times(
    projection: CredentialingProjection,
    *,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
    authority_version: str,
) -> StageTimeReport:
    """Measure observed administrative intervals without releasing source identities.

    Args:
        projection: Retained, privacy-minimised events, revalidated at this boundary.
        role: Trusted server-side aggregate reporting role.
        case_ids: Trusted explicitly mapped case population, including missing cases.
        minimum_cases: Approved floor for every nonzero outcome cell.
        authority_version: Current approved routine-renewal mapping reference.

    Returns:
        Frozen aggregate evidence, or no counts/quantiles if any cell is too small.

    Raises:
        CredentialingContractError: If scope or authority configuration is invalid.
        pydantic.ValidationError: If the projection violates its event contract.

    """
    grants, threshold = validate_measurement_scope(
        role=role,
        case_ids=case_ids,
        minimum_cases=minimum_cases,
    )
    if not _is_safe_code(authority_version, 80):
        message = "Measurement authority must use a bounded mapping code"
        raise CredentialingContractError(message)
    if not grants:
        return StageTimeReport(suppressed=True, population_case_count=None, measures=None)
    projection = validate_credentialing_projection(projection)
    observed: dict[str, list[CredentialingFact]] = {case_id: [] for case_id in sorted(grants)}
    for fact in projection.facts:
        if fact.observed_or_inferred == "observed":
            for case_id in grants.intersection(fact.object_ids):
                observed[case_id].append(fact)
    measures: list[StageTimeMeasure] = []
    for start, finish in STAGE_INTERVALS:
        measure, counts = _measure(observed, start, finish, authority_version)
        if any(0 < count < threshold for count in counts):
            return StageTimeReport(suppressed=True, population_case_count=None, measures=None)
        measures.append(measure)
    return StageTimeReport(
        suppressed=False,
        population_case_count=len(grants),
        measures=tuple(measures),
    )
