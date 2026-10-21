# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Explicit first-submission assessments and privacy-minimised case rates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Never

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
_INSTANT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
)
_KEYS = frozenset(
    {
        "kind",
        "contract_version",
        "observation_id",
        "case_id",
        "source_system",
        "recorded_at_utc",
        "assessment_definition_version",
        "complete_at_first_submission",
    }
)
type UnavailableReason = Literal["missing_assessments", "source_coverage_unconfirmed"]


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object, limit: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("First-submission evidence requires bounded reference codes")
    return value


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        _fail("First-submission flags must be booleans")
    return value


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("First-submission timestamp must be timezone-aware")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        _fail("First-submission timestamp exceeds the supported UTC range")


@dataclass(frozen=True, slots=True, kw_only=True)
class FirstSubmissionObservation:
    """One source-defined observed assessment, never an inferred event label."""

    observation_id: str
    case_id: str
    source_system: str
    recorded_at_utc: datetime
    assessment_definition_version: str
    complete_at_first_submission: bool
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:
        """Validate strict scalar evidence and normalise the aware instant."""
        if self.contract_version != "0.1.0":
            _fail("Unsupported first-submission observation version")
        _code(self.observation_id)
        _code(self.case_id)
        _code(self.source_system, 80)
        _code(self.assessment_definition_version, 80)
        _boolean(self.complete_at_first_submission)
        object.__setattr__(self, "recorded_at_utc", _instant(self.recorded_at_utc))


def _validated(record: object) -> FirstSubmissionObservation:
    if not isinstance(record, FirstSubmissionObservation):
        _fail("First-submission evidence has the wrong record type")
    return FirstSubmissionObservation(
        observation_id=record.observation_id,
        case_id=record.case_id,
        source_system=record.source_system,
        recorded_at_utc=record.recorded_at_utc,
        assessment_definition_version=record.assessment_definition_version,
        complete_at_first_submission=record.complete_at_first_submission,
        contract_version=record.contract_version,
    )


def first_submission_observation_payload(record: FirstSubmissionObservation) -> dict[str, object]:
    """Revalidate and export exact wire fields, without raw source evidence."""
    item = _validated(record)
    return {
        "kind": "first_submission_quality",
        "contract_version": item.contract_version,
        "observation_id": item.observation_id,
        "case_id": item.case_id,
        "source_system": item.source_system,
        "recorded_at_utc": item.recorded_at_utc.isoformat(),
        "assessment_definition_version": item.assessment_definition_version,
        "complete_at_first_submission": item.complete_at_first_submission,
    }


def parse_first_submission_observation(payload: Mapping[str, object]) -> FirstSubmissionObservation:
    """Reject extra fields, coercion and timestamps outside the wire contract."""
    if frozenset(payload) != _KEYS or payload.get("kind") != "first_submission_quality":
        _fail("First-submission fields do not match the strict contract")
    if payload.get("contract_version") != "0.1.0":
        _fail("Unsupported first-submission observation version")
    timestamp = payload.get("recorded_at_utc")
    if not isinstance(timestamp, str) or _INSTANT.fullmatch(timestamp) is None:
        _fail("First-submission wire timestamp must be an aware RFC3339 instant")
    try:
        instant = datetime.fromisoformat(timestamp.replace("z", "+00:00"))
    except ValueError:
        _fail("First-submission wire timestamp is invalid")
    return FirstSubmissionObservation(
        observation_id=_code(payload.get("observation_id")),
        case_id=_code(payload.get("case_id")),
        source_system=_code(payload.get("source_system"), 80),
        recorded_at_utc=instant,
        assessment_definition_version=_code(payload.get("assessment_definition_version"), 80),
        complete_at_first_submission=_boolean(payload.get("complete_at_first_submission")),
    )


def merge_first_submission_observations(
    existing: Sequence[FirstSubmissionObservation],
    incoming: Sequence[FirstSubmissionObservation],
) -> tuple[FirstSubmissionObservation, ...]:
    """Detach exact replay and fail on changed identity, including changed source."""
    retained: dict[str, FirstSubmissionObservation] = {}
    for supplied in (*existing, *incoming):
        item = _validated(supplied)
        previous = retained.get(item.observation_id)
        if previous is not None and previous != item:
            _fail("Conflicting first-submission observation replay")
        retained[item.observation_id] = item
    return tuple(retained[key] for key in sorted(retained))


@dataclass(frozen=True, slots=True)
class FirstSubmissionReport:
    """Aggregate-only result; suppression removes all counts, rates and reasons."""

    suppressed: bool
    population_case_count: int | None = None
    assessed_case_count: int | None = None
    missing_case_count: int | None = None
    complete_case_count: int | None = None
    incomplete_case_count: int | None = None
    observed_complete_rate: float | None = None
    population_complete_rate: float | None = None
    population_rate_unavailable_reason: UnavailableReason | None = None


def report_first_submission_quality(  # noqa: PLR0913 - explicit trusted reporting inputs
    observations: Sequence[FirstSubmissionObservation],
    *,
    role: str,
    granted_case_ids: AbstractSet[str],
    assessment_definition_version: str,
    source_complete: bool,
    minimum_case_count: int,
) -> FirstSubmissionReport:
    """Count consistent observed cases under an explicit trusted population mapping.

    Roles, grants, definition and coverage attestation must come from a trusted
    adapter. This pure function does not authenticate them or approve criteria.
    """
    grants, threshold = validate_measurement_scope(
        role=role,
        case_ids=granted_case_ids,
        minimum_cases=minimum_case_count,
    )
    definition = _code(assessment_definition_version, 80)
    coverage = _boolean(source_complete)
    labels: dict[str, bool] = {}
    for item in merge_first_submission_observations((), observations):
        if item.case_id not in grants:
            continue
        if item.assessment_definition_version != definition:
            _fail("First-submission assessment definition does not match")
        if item.case_id in labels and labels[item.case_id] != item.complete_at_first_submission:
            _fail("Contradictory first-submission case assessments")
        labels[item.case_id] = item.complete_at_first_submission
    population, assessed = len(grants), len(labels)
    missing = population - assessed
    complete = sum(labels.values())
    incomplete = assessed - complete
    if not population or any(
        0 < count < threshold
        for count in (
            population,
            assessed,
            missing,
            complete,
            incomplete,
        )
    ):
        return FirstSubmissionReport(suppressed=True)
    observed_rate = complete / assessed if assessed else None
    reason: UnavailableReason | None = (
        "missing_assessments"
        if missing
        else "source_coverage_unconfirmed"
        if not coverage
        else None
    )
    return FirstSubmissionReport(
        suppressed=False,
        population_case_count=population,
        assessed_case_count=assessed,
        missing_case_count=missing,
        complete_case_count=complete,
        incomplete_case_count=incomplete,
        observed_complete_rate=observed_rate,
        population_complete_rate=observed_rate if reason is None else None,
        population_rate_unavailable_reason=reason,
    )
