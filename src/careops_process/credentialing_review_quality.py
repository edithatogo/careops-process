# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Source-defined review obligations: completion rates and distinct-case privacy."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Never

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
_WIRE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
)
_TIMES = frozenset(
    {
        "snapshot_as_of_utc",
        "captured_at_utc",
        "effective_deadline_utc",
        "completion_at_utc",
    }
)
_REQUIRED_TIMES = frozenset({"snapshot_as_of_utc", "captured_at_utc"})
_KINDS = frozenset({"condition_review", "supervision_review"})
_STATES = frozenset({"pending", "completed", "out_of_scope", "unknown"})
CLASSIFICATIONS = (
    "missing_snapshot",
    "censored_out_of_scope",
    "unknown_status",
    "missing_deadline",
    "not_yet_due",
    "matured_completed_on_time",
    "matured_completed_late",
    "matured_outstanding",
)
_MATURED = frozenset(CLASSIFICATIONS[-3:])
_INCOMPLETE = frozenset({"missing_snapshot", "unknown_status", "missing_deadline"})
type UnavailableReason = Literal[
    "incomplete_obligation_evidence",
    "source_coverage_unconfirmed",
    "no_matured_obligations",
]


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object, limit: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Review evidence requires bounded reference codes")
    return value


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        _fail("Review evidence flags must be booleans")
    return value


def _member(value: object, choices: frozenset[str]) -> bool:
    return isinstance(value, str) and value in choices


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Review timestamp must be timezone-aware")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        _fail("Review timestamp exceeds supported UTC range")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewObligationSnapshot:
    """One explicit observation of administrative review completion, not clinical effect."""

    observation_id: str
    obligation_id: str
    case_id: str
    source_system: str
    definition_version: str
    review_kind: str
    snapshot_as_of_utc: datetime
    captured_at_utc: datetime
    effective_deadline_utc: datetime | None
    state: str
    completion_at_utc: datetime | None
    coverage_complete: bool
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:
        """Validate supplied state, identity and chronology without adding policy."""
        if self.contract_version != "0.1.0":
            _fail("Unsupported review snapshot version")
        for name in ("observation_id", "obligation_id", "case_id"):
            _code(getattr(self, name))
        _code(self.source_system, 80)
        _code(self.definition_version, 80)
        if not _member(self.review_kind, _KINDS) or not _member(self.state, _STATES):
            _fail("Review kind or state is not registered")
        _boolean(self.coverage_complete)
        for name in _TIMES:
            value = getattr(self, name)
            if value is not None or name in _REQUIRED_TIMES:
                object.__setattr__(self, name, _instant(value))
        if self.captured_at_utc < self.snapshot_as_of_utc:
            _fail("Review capture precedes snapshot instant")
        if self.state == "completed":
            if self.completion_at_utc is None or self.completion_at_utc > self.snapshot_as_of_utc:
                _fail("Completed review requires completion at or before snapshot")
        elif self.completion_at_utc is not None:
            _fail("Non-completed review cannot carry completion instant")


def _snapshot(supplied: object) -> ReviewObligationSnapshot:
    if not isinstance(supplied, ReviewObligationSnapshot):
        _fail("Review evidence has wrong record type")
    return ReviewObligationSnapshot(
        **{field.name: getattr(supplied, field.name) for field in fields(ReviewObligationSnapshot)}
    )


def review_obligation_snapshot_payload(snapshot: ReviewObligationSnapshot) -> dict[str, object]:
    """Revalidate/detach exact wire payload without raw source data."""
    item = _snapshot(snapshot)
    payload: dict[str, object] = {"kind": "review_obligation_snapshot"}
    for field in fields(ReviewObligationSnapshot):
        value = getattr(item, field.name)
        payload[field.name] = value.isoformat() if isinstance(value, datetime) else value
    return payload


def _wire_instant(value: object) -> datetime:
    if not isinstance(value, str) or not _WIRE_TIME.fullmatch(value):
        _fail("Review wire timestamp must be an aware RFC3339 instant")
    try:
        instant = datetime.fromisoformat(value.replace("z", "+00:00"))
    except ValueError:
        _fail("Review wire timestamp is invalid")
    return _instant(instant)


def parse_review_obligation_snapshot(payload: Mapping[str, object]) -> ReviewObligationSnapshot:
    """Enforce exact keys and strict scalar/time evidence at ingestion."""
    names = frozenset(field.name for field in fields(ReviewObligationSnapshot))
    if (
        frozenset(payload) != names | {"kind"}
        or payload.get("kind") != "review_obligation_snapshot"
    ):
        _fail("Review fields do not match strict snapshot contract")
    data = {name: payload[name] for name in names}
    for name in _TIMES:
        if data[name] is not None or name in _REQUIRED_TIMES:
            data[name] = _wire_instant(data[name])
    return ReviewObligationSnapshot(**data)  # type: ignore[arg-type]


def merge_review_obligation_snapshots(
    existing: Sequence[ReviewObligationSnapshot],
    incoming: Sequence[ReviewObligationSnapshot],
) -> tuple[ReviewObligationSnapshot, ...]:
    """Preserve exact replay identity and reject changed source/content."""
    retained: dict[str, ReviewObligationSnapshot] = {}
    for supplied in (*existing, *incoming):
        item = _snapshot(supplied)
        previous = retained.get(item.observation_id)
        if previous is not None and previous != item:
            _fail("Conflicting review observation replay")
        retained[item.observation_id] = item
    return tuple(retained[key] for key in sorted(retained))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewObligationGrant:
    """Trusted mapping of one review obligation to its privacy case unit."""

    obligation_id: str
    case_id: str

    def __post_init__(self) -> None:
        """Validate bounded opaque references without authenticating the grant."""
        _code(self.obligation_id)
        _code(self.case_id)


def _grant(supplied: object) -> ReviewObligationGrant:
    if not isinstance(supplied, ReviewObligationGrant):
        _fail("Review grant has wrong record type")
    return ReviewObligationGrant(obligation_id=supplied.obligation_id, case_id=supplied.case_id)


def _grant_container(value: object) -> bool:
    return isinstance(value, (tuple, frozenset))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewReportScope:
    """Explicit detached obligation population, including unobserved obligations."""

    role: str
    granted_obligations: tuple[ReviewObligationGrant, ...] | frozenset[ReviewObligationGrant]

    def __post_init__(self) -> None:
        """Reject ambiguous mappings and iterable coercion; freeze validated grants."""
        if not _grant_container(self.granted_obligations):
            _fail("Review grants must be an explicit tuple or frozenset")
        retained: dict[str, ReviewObligationGrant] = {}
        for supplied in self.granted_obligations:
            item = _grant(supplied)
            previous = retained.get(item.obligation_id)
            if previous is not None and previous != item:
                _fail("Conflicting review obligation-to-case grant mapping")
            retained[item.obligation_id] = item
        validate_measurement_scope(
            role=self.role,
            case_ids=frozenset(item.case_id for item in retained.values()),
            minimum_cases=2,
        )
        object.__setattr__(
            self, "granted_obligations", tuple(retained[key] for key in sorted(retained))
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewReportPolicy:
    """One source-defined review kind, definition and explicit reporting instant."""

    definition_version: str
    review_kind: str
    as_of_utc: datetime
    source_complete: bool
    minimum_case_count: int

    def __post_init__(self) -> None:
        """Validate strict policy inputs without supplying clinical defaults."""
        _code(self.definition_version, 80)
        if not _member(self.review_kind, _KINDS):
            _fail("Review policy kind is not registered")
        _boolean(self.source_complete)
        object.__setattr__(self, "as_of_utc", _instant(self.as_of_utc))
        validate_measurement_scope(
            role="report_reader",
            case_ids=frozenset(),
            minimum_cases=self.minimum_case_count,
        )


@dataclass(frozen=True, slots=True)
class ReviewCompletionReport:
    """Obligation-weighted rates released only under distinct-case privacy."""

    suppressed: bool
    population_obligation_count: int | None = None
    population_case_count: int | None = None
    obligation_counts: tuple[tuple[str, int], ...] | None = None
    matured_obligation_count: int | None = None
    observed_completion_rate: float | None = None
    observed_on_time_rate: float | None = None
    population_completion_rate: float | None = None
    population_on_time_rate: float | None = None
    population_rate_unavailable_reason: UnavailableReason | None = None


def _classification(item: ReviewObligationSnapshot, instant: datetime) -> str:
    if item.state == "out_of_scope":
        return "censored_out_of_scope"
    if not item.coverage_complete or item.state == "unknown":
        return "unknown_status"
    if item.effective_deadline_utc is None:
        return "missing_deadline"
    if item.effective_deadline_utc >= instant:
        return "not_yet_due"
    if item.completion_at_utc is None:
        return "matured_outstanding"
    return (
        "matured_completed_on_time"
        if item.completion_at_utc <= item.effective_deadline_utc
        else "matured_completed_late"
    )


def _consistent(left: ReviewObligationSnapshot, right: ReviewObligationSnapshot) -> bool:
    return all(
        getattr(left, field.name) == getattr(right, field.name)
        for field in fields(ReviewObligationSnapshot)
        if field.name not in {"observation_id", "captured_at_utc"}
    )


def report_review_completion(
    snapshots: Sequence[ReviewObligationSnapshot],
    *,
    scope: ReviewReportScope,
    policy: ReviewReportPolicy,
) -> ReviewCompletionReport:
    """Reconcile review obligations, preserving missingness and case privacy."""
    trusted = ReviewReportScope(role=scope.role, granted_obligations=scope.granted_obligations)
    current = ReviewReportPolicy(
        **{field.name: getattr(policy, field.name) for field in fields(ReviewReportPolicy)}
    )
    grants = {grant.obligation_id: grant.case_id for grant in trusted.granted_obligations}
    observed: dict[str, ReviewObligationSnapshot] = {}
    for item in merge_review_obligation_snapshots((), snapshots):
        if item.obligation_id not in grants:
            continue
        if (
            item.case_id != grants[item.obligation_id]
            or item.review_kind != current.review_kind
            or item.definition_version != current.definition_version
            or item.snapshot_as_of_utc != current.as_of_utc
        ):
            _fail("Review snapshot does not match trusted grant or report definition")
        prior = observed.get(item.obligation_id)
        if prior is not None and not _consistent(prior, item):
            _fail("Contradictory review obligation evidence")
        observed[item.obligation_id] = item
    counts: dict[str, int] = dict.fromkeys(CLASSIFICATIONS, 0)
    contributors: dict[str, set[str]] = {key: set() for key in CLASSIFICATIONS}
    for obligation_id, case_id in grants.items():
        item = observed.get(obligation_id)
        category = "missing_snapshot" if item is None else _classification(item, current.as_of_utc)
        counts[category] += 1
        contributors[category].add(case_id)
    population_cases = set(grants.values())
    matured_cases = {case for key in _MATURED for case in contributors[key]}
    if not grants or any(
        0 < len(cases) < current.minimum_case_count
        for cases in (*contributors.values(), population_cases, matured_cases)
    ):
        return ReviewCompletionReport(suppressed=True)
    matured = sum(counts[key] for key in _MATURED)
    completed = counts["matured_completed_on_time"] + counts["matured_completed_late"]
    completion_rate = completed / matured if matured else None
    on_time_rate = counts["matured_completed_on_time"] / matured if matured else None
    reason: UnavailableReason | None = None
    if any(counts[key] for key in _INCOMPLETE):
        reason = "incomplete_obligation_evidence"
    elif not current.source_complete:
        reason = "source_coverage_unconfirmed"
    elif not matured:
        reason = "no_matured_obligations"
    return ReviewCompletionReport(
        suppressed=False,
        population_obligation_count=len(grants),
        population_case_count=len(population_cases),
        obligation_counts=tuple(counts.items()),
        matured_obligation_count=matured,
        observed_completion_rate=completion_rate,
        observed_on_time_rate=on_time_rate,
        population_completion_rate=completion_rate if reason is None else None,
        population_on_time_rate=on_time_rate if reason is None else None,
        population_rate_unavailable_reason=reason,
    )
