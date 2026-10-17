"""Source-defined renewal snapshots and outstanding overdue prevalence."""

from __future__ import annotations

import re
from dataclasses import dataclass
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
_STATES = frozenset({"pending", "completed", "out_of_scope", "unknown"})
_FIELDS = (
    "contract_version",
    "observation_id",
    "case_id",
    "renewal_cycle_code",
    "source_system",
    "definition_version",
    "snapshot_as_of_utc",
    "captured_at_utc",
    "effective_deadline_utc",
    "state",
    "completion_at_utc",
    "coverage_complete",
)
_TIME_FIELDS = frozenset(
    {
        "snapshot_as_of_utc",
        "captured_at_utc",
        "effective_deadline_utc",
        "completion_at_utc",
    }
)
CLASSIFICATIONS = (
    "missing_snapshot",
    "censored_out_of_scope",
    "unknown_status",
    "missing_deadline",
    "not_yet_due",
    "matured_completed",
    "matured_outstanding_overdue",
)
type UnavailableReason = Literal[
    "incomplete_case_evidence",
    "source_coverage_unconfirmed",
    "no_matured_cases",
]


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object, limit: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Renewal evidence requires bounded reference codes")
    return value


def _valid_state(value: object) -> bool:
    return isinstance(value, str) and value in _STATES


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        _fail("Renewal evidence flags must be booleans")
    return value


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Renewal timestamp must be timezone-aware")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        _fail("Renewal timestamp exceeds supported UTC range")


@dataclass(frozen=True, slots=True, kw_only=True)
class RenewalSnapshot:
    """One explicit source assertion about one renewal cycle at one instant."""

    observation_id: str
    case_id: str
    renewal_cycle_code: str
    source_system: str
    definition_version: str
    snapshot_as_of_utc: datetime
    captured_at_utc: datetime
    effective_deadline_utc: datetime | None
    state: str
    completion_at_utc: datetime | None
    coverage_complete: bool
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:
        """Validate explicit times/state without supplying renewal policy."""
        if self.contract_version != "0.1.0":
            _fail("Unsupported renewal snapshot version")
        for field in ("observation_id", "case_id", "renewal_cycle_code"):
            _code(getattr(self, field))
        _code(self.source_system, 80)
        _code(self.definition_version, 80)
        if not _valid_state(self.state):
            _fail("Unknown renewal snapshot state")
        _boolean(self.coverage_complete)
        for field in _TIME_FIELDS:
            value = getattr(self, field)
            if value is not None or field in {"snapshot_as_of_utc", "captured_at_utc"}:
                object.__setattr__(self, field, _instant(value))
        if self.captured_at_utc < self.snapshot_as_of_utc:
            _fail("Renewal capture precedes snapshot instant")
        if self.state == "completed":
            if self.completion_at_utc is None or self.completion_at_utc > self.snapshot_as_of_utc:
                _fail("Completed renewal requires completion at or before snapshot instant")
        elif self.completion_at_utc is not None:
            _fail("Non-completed renewal cannot carry completion time")


def _validated(supplied: object) -> RenewalSnapshot:
    if not isinstance(supplied, RenewalSnapshot):
        _fail("Renewal evidence has wrong record type")
    return RenewalSnapshot(**{field: getattr(supplied, field) for field in _FIELDS})


def renewal_snapshot_payload(snapshot: RenewalSnapshot) -> dict[str, object]:
    """Revalidate and detach exact wire payload, excluding raw source evidence."""
    item = _validated(snapshot)
    payload: dict[str, object] = {"kind": "renewal_snapshot"}
    for field in _FIELDS:
        value = getattr(item, field)
        payload[field] = value.isoformat() if isinstance(value, datetime) else value
    return payload


def _wire_instant(value: object) -> datetime:
    if not isinstance(value, str) or not _WIRE_TIME.fullmatch(value):
        _fail("Renewal wire timestamp must be an aware RFC3339 instant")
    try:
        return _instant(datetime.fromisoformat(value.replace("z", "+00:00")))
    except ValueError:
        _fail("Renewal wire timestamp is invalid")


def parse_renewal_snapshot(payload: Mapping[str, object]) -> RenewalSnapshot:
    """Validate exact keys and strict wire evidence before domain construction."""
    if (
        frozenset(payload) != frozenset((*_FIELDS, "kind"))
        or payload.get("kind") != "renewal_snapshot"
    ):
        _fail("Renewal fields do not match strict snapshot contract")
    data = {field: payload[field] for field in _FIELDS}
    for field in _TIME_FIELDS:
        value = data[field]
        if value is not None or field in {"snapshot_as_of_utc", "captured_at_utc"}:
            data[field] = _wire_instant(value)
    return RenewalSnapshot(**data)  # type: ignore[arg-type]


def merge_renewal_snapshots(
    existing: Sequence[RenewalSnapshot],
    incoming: Sequence[RenewalSnapshot],
) -> tuple[RenewalSnapshot, ...]:
    """Deduplicate exact IDs and reject changed replay, including changed source."""
    retained: dict[str, RenewalSnapshot] = {}
    for supplied in (*existing, *incoming):
        item = _validated(supplied)
        prior = retained.get(item.observation_id)
        if prior is not None and prior != item:
            _fail("Conflicting renewal observation replay")
        retained[item.observation_id] = item
    return tuple(retained[key] for key in sorted(retained))


@dataclass(frozen=True, slots=True, kw_only=True)
class RenewalReportPolicy:
    """Explicit reporting definition, instant and source-coverage assertion."""

    definition_version: str
    as_of_utc: datetime
    source_complete: bool
    minimum_case_count: int

    def __post_init__(self) -> None:
        """Reject coercion and detach the reporting instant."""
        _code(self.definition_version, 80)
        _boolean(self.source_complete)
        object.__setattr__(self, "as_of_utc", _instant(self.as_of_utc))
        validate_measurement_scope(
            role="report_reader",
            case_ids=frozenset(),
            minimum_cases=self.minimum_case_count,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class RenewalReportScope:
    """Trusted role and explicit case/cycle grants; this does not authenticate."""

    role: str
    granted_case_ids: frozenset[str]

    def __post_init__(self) -> None:
        """Freeze and validate actual set grants without accepting iterators."""
        grants, _ = validate_measurement_scope(
            role=self.role,
            case_ids=self.granted_case_ids,
            minimum_cases=2,
        )
        object.__setattr__(self, "granted_case_ids", grants)


@dataclass(frozen=True, slots=True)
class OverdueRenewalReport:
    """Counts and rates only; suppression removes every released value."""

    suppressed: bool
    population_case_count: int | None = None
    case_counts: tuple[tuple[str, int], ...] | None = None
    matured_case_count: int | None = None
    observed_overdue_rate: float | None = None
    population_overdue_rate: float | None = None
    population_rate_unavailable_reason: UnavailableReason | None = None


def _classification(item: RenewalSnapshot, instant: datetime) -> str:
    if item.state == "out_of_scope":
        return "censored_out_of_scope"
    if not item.coverage_complete or item.state == "unknown":
        return "unknown_status"
    if item.effective_deadline_utc is None:
        return "missing_deadline"
    if item.effective_deadline_utc >= instant:
        return "not_yet_due"
    return "matured_completed" if item.state == "completed" else "matured_outstanding_overdue"


def report_overdue_renewals(
    snapshots: Sequence[RenewalSnapshot],
    *,
    policy: RenewalReportPolicy,
    scope: RenewalReportScope,
) -> OverdueRenewalReport:
    """Measure current outstanding prevalence, never clinical or causal effect."""
    current = RenewalReportPolicy(
        definition_version=policy.definition_version,
        as_of_utc=policy.as_of_utc,
        source_complete=policy.source_complete,
        minimum_case_count=policy.minimum_case_count,
    )
    grants = RenewalReportScope(role=scope.role, granted_case_ids=scope.granted_case_ids)
    cases: dict[str, RenewalSnapshot] = {}
    for item in merge_renewal_snapshots((), snapshots):
        if item.case_id not in grants.granted_case_ids:
            continue
        if (
            item.definition_version != current.definition_version
            or item.snapshot_as_of_utc != current.as_of_utc
        ):
            _fail("Renewal snapshot definition or as-of instant does not match")
        previous = cases.get(item.case_id)
        if previous is not None and any(
            getattr(previous, field) != getattr(item, field)
            for field in _FIELDS
            if field not in {"observation_id", "captured_at_utc"}
        ):
            _fail("Contradictory renewal case/cycle snapshot evidence")
        cases[item.case_id] = item
    counts: dict[str, int] = dict.fromkeys(CLASSIFICATIONS, 0)
    counts["missing_snapshot"] = len(grants.granted_case_ids) - len(cases)
    for item in cases.values():
        counts[_classification(item, current.as_of_utc)] += 1
    population = len(grants.granted_case_ids)
    matured = counts["matured_completed"] + counts["matured_outstanding_overdue"]
    if not population or any(
        0 < value < current.minimum_case_count for value in (*counts.values(), population, matured)
    ):
        return OverdueRenewalReport(suppressed=True)
    observed = counts["matured_outstanding_overdue"] / matured if matured else None
    reason: UnavailableReason | None = None
    if any(counts[key] for key in ("missing_snapshot", "unknown_status", "missing_deadline")):
        reason = "incomplete_case_evidence"
    elif not current.source_complete:
        reason = "source_coverage_unconfirmed"
    elif not matured:
        reason = "no_matured_cases"
    return OverdueRenewalReport(
        suppressed=False,
        population_case_count=population,
        case_counts=tuple(counts.items()),
        matured_case_count=matured,
        observed_overdue_rate=observed,
        population_overdue_rate=observed if reason is None else None,
        population_rate_unavailable_reason=reason,
    )
