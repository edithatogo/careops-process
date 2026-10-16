"""Explicit temporary episode and review evidence; no clinical duration defaults."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Never, cast

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,6})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
)
EPISODE_CELLS = (
    "missing_snapshot",
    "censored_out_of_scope",
    "unknown_status",
    "missing_start",
    "missing_expiry",
    "not_yet_matured",
    "matured_converted_by_expiry",
    "matured_converted_after_expiry",
    "matured_observed_expired",
    "matured_closed_without_conversion",
    "matured_source_active_past_expiry",
)
EXPIRY_CELLS = (
    "transition_before_effective_expiry",
    "transition_at_effective_expiry",
    "transition_after_effective_expiry",
)
REVIEW_CELLS = (
    "missing_snapshot",
    "censored_out_of_scope",
    "unknown_status",
    "missing_deadline",
    "not_yet_due",
    "matured_completed_on_time",
    "matured_completed_late",
    "matured_outstanding",
)


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object, limit: int = 128) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Temporary evidence requires bounded reference codes")


def _boolean(value: object) -> None:
    if not isinstance(value, bool):
        _fail("Temporary evidence flags must be booleans")


def _state(value: object, choices: tuple[str, ...]) -> None:
    if not isinstance(value, str) or value not in choices:
        _fail("Temporary evidence state is not registered")


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Temporary evidence requires aware timestamps")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        _fail("Temporary evidence exceeds supported UTC range")


@dataclass(frozen=True, slots=True, kw_only=True)
class _Snapshot:
    observation_id: str
    episode_id: str
    case_id: str
    source_system: str
    definition_version: str
    snapshot_as_of_utc: datetime
    captured_at_utc: datetime
    coverage_complete: bool
    contract_version: str = "0.1.0"
    kind: ClassVar[str]
    nullable_times: ClassVar[tuple[str, ...]]

    def __post_init__(self) -> None:
        if self.contract_version != "0.1.0":
            _fail("Unsupported temporary evidence version")
        for name in ("observation_id", "episode_id", "case_id"):
            _code(getattr(self, name))
        _code(self.source_system, 80)
        _code(self.definition_version, 80)
        _boolean(self.coverage_complete)
        for name in ("snapshot_as_of_utc", "captured_at_utc", *self.nullable_times):
            value = getattr(self, name)
            if value is not None or name not in self.nullable_times:
                object.__setattr__(self, name, _instant(value))
        if self.captured_at_utc < self.snapshot_as_of_utc:
            _fail("Temporary capture precedes snapshot instant")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryEpisodeSnapshot(_Snapshot):
    """Observed episode state; elapsed expiry does not imply an expiry transition."""

    observed_start_utc: datetime | None
    effective_expiry_utc: datetime | None
    state: str
    conversion_at_utc: datetime | None
    observed_expiry_at_utc: datetime | None
    kind: ClassVar[str] = "temporary_episode_snapshot"
    nullable_times: ClassVar[tuple[str, ...]] = (
        "observed_start_utc",
        "effective_expiry_utc",
        "conversion_at_utc",
        "observed_expiry_at_utc",
    )

    def __post_init__(self) -> None:
        """Validate supplied chronology without inventing an approval interval."""
        _Snapshot.__post_init__(self)
        _state(
            self.state,
            (
                "active",
                "converted",
                "expired",
                "closed_without_conversion",
                "out_of_scope",
                "unknown",
            ),
        )
        start = self.observed_start_utc
        if start is not None and start > self.snapshot_as_of_utc:
            _fail("Temporary observed start exceeds snapshot instant")
        if (
            start is not None
            and self.effective_expiry_utc is not None
            and self.effective_expiry_utc < start
        ):
            _fail("Temporary effective expiry precedes observed start")
        for state, name in (
            ("converted", "conversion_at_utc"),
            ("expired", "observed_expiry_at_utc"),
        ):
            value = getattr(self, name)
            if self.state == state:
                if (
                    value is None
                    or value > self.snapshot_as_of_utc
                    or (start is not None and value < start)
                ):
                    _fail("Temporary terminal state requires a valid observed transition instant")
            elif value is not None:
                _fail("Temporary transition instant does not match supplied state")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryReviewSnapshot(_Snapshot):
    """One explicit temporary-review obligation, independent of episode conversion."""

    review_obligation_id: str
    effective_deadline_utc: datetime | None
    state: str
    completion_at_utc: datetime | None
    kind: ClassVar[str] = "temporary_review_snapshot"
    nullable_times: ClassVar[tuple[str, ...]] = ("effective_deadline_utc", "completion_at_utc")

    def __post_init__(self) -> None:
        """Require explicit completion evidence and source-defined deadline."""
        _Snapshot.__post_init__(self)
        _code(self.review_obligation_id)
        _state(self.state, ("pending", "completed", "out_of_scope", "unknown"))
        if self.state == "completed":
            if self.completion_at_utc is None or self.completion_at_utc > self.snapshot_as_of_utc:
                _fail("Completed temporary review requires completion at or before snapshot")
        elif self.completion_at_utc is not None:
            _fail("Non-completed temporary review cannot carry completion instant")


def _copy[T: _Snapshot](supplied: object, expected: type[T]) -> T:
    if not isinstance(supplied, expected):
        _fail("Temporary evidence has wrong record type")
    return expected(**{field.name: getattr(supplied, field.name) for field in fields(expected)})


def _payload[T: _Snapshot](snapshot: T, expected: type[T]) -> dict[str, object]:
    item = _copy(snapshot, expected)
    result: dict[str, object] = {"kind": expected.kind}
    for field in fields(expected):
        value = getattr(item, field.name)
        result[field.name] = value.isoformat() if isinstance(value, datetime) else value
    return result


def temporary_episode_payload(snapshot: TemporaryEpisodeSnapshot) -> dict[str, object]:
    """Revalidate and export exact episode wire fields."""
    return _payload(snapshot, TemporaryEpisodeSnapshot)


def temporary_review_payload(snapshot: TemporaryReviewSnapshot) -> dict[str, object]:
    """Revalidate and export exact review wire fields."""
    return _payload(snapshot, TemporaryReviewSnapshot)


def _parse[T: _Snapshot](payload: Mapping[str, object], expected: type[T]) -> T:
    names = frozenset(field.name for field in fields(expected))
    if frozenset(payload) != names | {"kind"} or payload.get("kind") != expected.kind:
        _fail("Temporary fields do not match strict wire contract")
    data = {name: payload[name] for name in names}
    for name in ("snapshot_as_of_utc", "captured_at_utc", *expected.nullable_times):
        value = data[name]
        if value is None and name in expected.nullable_times:
            continue
        if not isinstance(value, str) or not _TIME.fullmatch(value):
            _fail("Temporary wire instant must be aware RFC3339")
        try:
            instant = datetime.fromisoformat(value.replace("z", "+00:00"))
        except ValueError:
            _fail("Temporary wire instant is invalid")
        data[name] = _instant(instant)
    return expected(**data)  # type: ignore[arg-type]


def parse_temporary_episode(payload: Mapping[str, object]) -> TemporaryEpisodeSnapshot:
    """Reject raw fields, coercion and malformed episode evidence."""
    return _parse(payload, TemporaryEpisodeSnapshot)


def parse_temporary_review(payload: Mapping[str, object]) -> TemporaryReviewSnapshot:
    """Reject raw fields, coercion and malformed review evidence."""
    return _parse(payload, TemporaryReviewSnapshot)


def _merge[T: _Snapshot](
    existing: Sequence[T],
    incoming: Sequence[T],
    expected: type[T],
) -> tuple[T, ...]:
    retained: dict[str, T] = {}
    for supplied in (*existing, *incoming):
        item = _copy(supplied, expected)
        previous = retained.get(item.observation_id)
        if previous is not None and previous != item:
            _fail("Conflicting temporary observation replay")
        retained[item.observation_id] = item
    return tuple(retained[key] for key in sorted(retained))


def merge_temporary_episodes(
    existing: Sequence[TemporaryEpisodeSnapshot],
    incoming: Sequence[TemporaryEpisodeSnapshot],
) -> tuple[TemporaryEpisodeSnapshot, ...]:
    """Detach exact episode replay; changed IDs/content fail."""
    return _merge(existing, incoming, TemporaryEpisodeSnapshot)


def merge_temporary_reviews(
    existing: Sequence[TemporaryReviewSnapshot],
    incoming: Sequence[TemporaryReviewSnapshot],
) -> tuple[TemporaryReviewSnapshot, ...]:
    """Detach exact review replay; changed IDs/content fail."""
    return _merge(existing, incoming, TemporaryReviewSnapshot)


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryEpisodeGrant:
    """Trusted episode-to-case mapping, including episodes without observations."""

    episode_id: str
    case_id: str

    def __post_init__(self) -> None:
        """Validate opaque identity without authenticating access."""
        _code(self.episode_id)
        _code(self.case_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryReviewGrant(TemporaryEpisodeGrant):
    """One required review obligation within an explicit episode/case mapping."""

    review_obligation_id: str

    def __post_init__(self) -> None:
        """Validate the separate obligation identity."""
        TemporaryEpisodeGrant.__post_init__(self)
        _code(self.review_obligation_id)


type EpisodeGrants = tuple[TemporaryEpisodeGrant, ...] | frozenset[TemporaryEpisodeGrant]
type ReviewGrants = tuple[TemporaryReviewGrant, ...] | frozenset[TemporaryReviewGrant]


def _grants[T: TemporaryEpisodeGrant](values: object, expected: type[T], key: str) -> tuple[T, ...]:
    if not isinstance(values, (tuple, frozenset)):
        _fail("Temporary grants must be explicit tuple or frozenset")
    retained: dict[str, T] = {}
    for supplied in cast("tuple[object, ...] | frozenset[object]", values):
        if type(supplied) is not expected:
            _fail("Temporary grant has wrong record type")
        item = replace(supplied)
        identity = getattr(item, key)
        previous = retained.get(identity)
        if previous is not None and previous != item:
            _fail("Conflicting temporary grant mapping")
        retained[identity] = item
    return tuple(retained[key] for key in sorted(retained))


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryReportScope:
    """Detached explicit episode population; roles/grants require a trusted adapter."""

    role: str
    granted_episodes: EpisodeGrants

    def __post_init__(self) -> None:
        """Freeze grants and validate role/case population."""
        grants = _grants(self.granted_episodes, TemporaryEpisodeGrant, "episode_id")
        validate_measurement_scope(
            role=self.role, case_ids=frozenset(item.case_id for item in grants), minimum_cases=2
        )
        object.__setattr__(self, "granted_episodes", grants)


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryReviewReportScope(TemporaryReportScope):
    """Explicit required-review population nested within granted episodes."""

    granted_reviews: ReviewGrants

    def __post_init__(self) -> None:
        """Reject reviews outside their trusted episode/case grant mapping."""
        TemporaryReportScope.__post_init__(self)
        reviews = _grants(self.granted_reviews, TemporaryReviewGrant, "review_obligation_id")
        episodes = {item.episode_id: item.case_id for item in self.granted_episodes}
        if any(episodes.get(item.episode_id) != item.case_id for item in reviews):
            _fail("Temporary review grant does not match an episode grant")
        object.__setattr__(self, "granted_reviews", reviews)


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryReportPolicy:
    """Explicit definition, reporting instant and source-coverage assertion."""

    definition_version: str
    as_of_utc: datetime
    source_complete: bool
    minimum_case_count: int

    def __post_init__(self) -> None:
        """Reject coercion and implicit privacy or time defaults."""
        _code(self.definition_version, 80)
        _boolean(self.source_complete)
        object.__setattr__(self, "as_of_utc", _instant(self.as_of_utc))
        validate_measurement_scope(
            role="report_reader", case_ids=frozenset(), minimum_cases=self.minimum_case_count
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporaryReviewReportPolicy(TemporaryReportPolicy):
    """Explicit assertion that all required review obligations were enumerated."""

    required_review_population_complete: bool

    def __post_init__(self) -> None:
        """Unknown required populations never become a fabricated zero count."""
        TemporaryReportPolicy.__post_init__(self)
        _boolean(self.required_review_population_complete)


@dataclass(frozen=True, slots=True)
class TemporaryEpisodeReport:
    """Episode-weighted conversion and separate observed expiry distribution."""

    suppressed: bool
    population_episode_count: int | None = None
    population_case_count: int | None = None
    episode_counts: tuple[tuple[str, int], ...] | None = None
    matured_episode_count: int | None = None
    observed_conversion_rate: float | None = None
    observed_conversion_by_expiry_rate: float | None = None
    population_conversion_rate: float | None = None
    population_conversion_by_expiry_rate: float | None = None
    population_rate_unavailable_reason: str | None = None
    expiry_transition_episode_count: int | None = None
    expiry_transition_counts: tuple[tuple[str, int], ...] | None = None
    expiry_transition_excluded_episode_count: int | None = None


@dataclass(frozen=True, slots=True)
class TemporaryReviewReport:
    """Known-obligation rates with explicit required-population uncertainty."""

    suppressed: bool
    population_episode_count: int | None = None
    population_case_count: int | None = None
    known_review_obligation_count: int | None = None
    review_counts: tuple[tuple[str, int], ...] | None = None
    matured_review_count: int | None = None
    observed_completion_rate: float | None = None
    observed_on_time_rate: float | None = None
    population_completion_rate: float | None = None
    population_on_time_rate: float | None = None
    population_rate_unavailable_reason: str | None = None
    required_review_population_complete: bool | None = None


def _observed[T: _Snapshot](
    rows: Sequence[T],
    expected: type[T],
    key: str,
    grants: Mapping[str, tuple[str, str]],
    policy: TemporaryReportPolicy,
) -> dict[str, T]:
    observed: dict[str, T] = {}
    for item in _merge((), rows, expected):
        identity = getattr(item, key)
        if identity not in grants:
            continue
        if (
            grants[identity] != (item.episode_id, item.case_id)
            or item.definition_version != policy.definition_version
            or item.snapshot_as_of_utc != policy.as_of_utc
        ):
            _fail("Temporary snapshot does not match grants, definition or as-of")
        previous = observed.get(identity)
        if previous is not None and any(
            getattr(previous, field.name) != getattr(item, field.name)
            for field in fields(expected)
            if field.name not in {"observation_id", "captured_at_utc"}
        ):
            _fail("Contradictory temporary episode or review evidence")
        observed[identity] = item
    return observed


def _episode_cell(item: TemporaryEpisodeSnapshot, instant: datetime) -> str:  # noqa: PLR0911 - disjoint evidence precedence
    if item.state == "out_of_scope":
        return "censored_out_of_scope"
    if not item.coverage_complete or item.state == "unknown":
        return "unknown_status"
    if item.observed_start_utc is None:
        return "missing_start"
    if item.effective_expiry_utc is None:
        return "missing_expiry"
    if item.effective_expiry_utc >= instant:
        return "not_yet_matured"
    if item.conversion_at_utc is not None:
        return (
            "matured_converted_by_expiry"
            if item.conversion_at_utc <= item.effective_expiry_utc
            else "matured_converted_after_expiry"
        )
    return {
        "expired": "matured_observed_expired",
        "closed_without_conversion": "matured_closed_without_conversion",
        "active": "matured_source_active_past_expiry",
    }[item.state]


def _review_cell(item: TemporaryReviewSnapshot, instant: datetime) -> str:
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


def _rare(groups: Sequence[set[str]], threshold: int) -> bool:
    return any(0 < len(group) < threshold for group in groups)


def report_temporary_episodes(
    snapshots: Sequence[TemporaryEpisodeSnapshot],
    *,
    scope: TemporaryReportScope,
    policy: TemporaryReportPolicy,
) -> TemporaryEpisodeReport:
    """Reconcile conversion and expiry observations without clinical implications."""
    trusted = TemporaryReportScope(role=scope.role, granted_episodes=scope.granted_episodes)
    current = TemporaryReportPolicy(
        **{field.name: getattr(policy, field.name) for field in fields(TemporaryReportPolicy)}
    )
    grants = {item.episode_id: (item.episode_id, item.case_id) for item in trusted.granted_episodes}
    observed = _observed(snapshots, TemporaryEpisodeSnapshot, "episode_id", grants, current)
    counts: dict[str, int] = dict.fromkeys(EPISODE_CELLS, 0)
    cases = {key: set[str]() for key in EPISODE_CELLS}
    transitions: dict[str, int] = dict.fromkeys(EXPIRY_CELLS, 0)
    transition_cases = {key: set[str]() for key in EXPIRY_CELLS}
    excluded_cases: set[str] = set()
    for identity, (_, case_id) in grants.items():
        item = observed.get(identity)
        category = "missing_snapshot" if item is None else _episode_cell(item, current.as_of_utc)
        counts[category] += 1
        cases[category].add(case_id)
        if (
            item is not None
            and item.state == "expired"
            and item.coverage_complete
            and item.observed_start_utc is not None
            and item.effective_expiry_utc is not None
            and item.observed_expiry_at_utc is not None
        ):
            transition = (
                EXPIRY_CELLS[0]
                if item.observed_expiry_at_utc < item.effective_expiry_utc
                else EXPIRY_CELLS[1]
                if item.observed_expiry_at_utc == item.effective_expiry_utc
                else EXPIRY_CELLS[2]
            )
            transitions[transition] += 1
            transition_cases[transition].add(case_id)
        else:
            excluded_cases.add(case_id)
    population_cases = {case for _, case in grants.values()}
    matured_cases = {case for key in EPISODE_CELLS[6:] for case in cases[key]}
    expiry_cases = {case for group in transition_cases.values() for case in group}
    if not grants or _rare(
        (
            *cases.values(),
            *transition_cases.values(),
            population_cases,
            matured_cases,
            expiry_cases,
            excluded_cases,
        ),
        current.minimum_case_count,
    ):
        return TemporaryEpisodeReport(suppressed=True)
    matured = sum(counts[key] for key in EPISODE_CELLS[6:])
    by_expiry = counts["matured_converted_by_expiry"]
    converted = by_expiry + counts["matured_converted_after_expiry"]
    observed_rate = converted / matured if matured else None
    timely_rate = by_expiry / matured if matured else None
    reason = (
        "incomplete_episode_evidence"
        if any(
            counts[key]
            for key in ("missing_snapshot", "unknown_status", "missing_start", "missing_expiry")
        )
        else "source_coverage_unconfirmed"
        if not current.source_complete
        else "no_matured_episodes"
        if not matured
        else None
    )
    expiry_count = sum(transitions.values())
    return TemporaryEpisodeReport(
        suppressed=False,
        population_episode_count=len(grants),
        population_case_count=len(population_cases),
        episode_counts=tuple(counts.items()),
        matured_episode_count=matured,
        observed_conversion_rate=observed_rate,
        observed_conversion_by_expiry_rate=timely_rate,
        population_conversion_rate=observed_rate if reason is None else None,
        population_conversion_by_expiry_rate=timely_rate if reason is None else None,
        population_rate_unavailable_reason=reason,
        expiry_transition_episode_count=expiry_count,
        expiry_transition_counts=tuple(transitions.items()),
        expiry_transition_excluded_episode_count=len(grants) - expiry_count,
    )


def report_temporary_reviews(
    snapshots: Sequence[TemporaryReviewSnapshot],
    *,
    scope: TemporaryReviewReportScope,
    policy: TemporaryReviewReportPolicy,
) -> TemporaryReviewReport:
    """Report known review obligations without assuming the required population is complete."""
    trusted = TemporaryReviewReportScope(
        role=scope.role,
        granted_episodes=scope.granted_episodes,
        granted_reviews=scope.granted_reviews,
    )
    current = TemporaryReviewReportPolicy(
        **{field.name: getattr(policy, field.name) for field in fields(TemporaryReviewReportPolicy)}
    )
    grants = {
        item.review_obligation_id: (item.episode_id, item.case_id)
        for item in trusted.granted_reviews
    }
    observed = _observed(
        snapshots, TemporaryReviewSnapshot, "review_obligation_id", grants, current
    )
    counts: dict[str, int] = dict.fromkeys(REVIEW_CELLS, 0)
    cases = {key: set[str]() for key in REVIEW_CELLS}
    for identity, (_, case_id) in grants.items():
        item = observed.get(identity)
        category = "missing_snapshot" if item is None else _review_cell(item, current.as_of_utc)
        counts[category] += 1
        cases[category].add(case_id)
    population_cases = {item.case_id for item in trusted.granted_episodes}
    known_cases = {case for _, case in grants.values()}
    matured_cases = {case for key in REVIEW_CELLS[5:] for case in cases[key]}
    if not trusted.granted_episodes or _rare(
        (*cases.values(), population_cases, known_cases, matured_cases), current.minimum_case_count
    ):
        return TemporaryReviewReport(suppressed=True)
    matured = sum(counts[key] for key in REVIEW_CELLS[5:])
    timely = counts["matured_completed_on_time"]
    completed = timely + counts["matured_completed_late"]
    observed_rate = completed / matured if matured else None
    timely_rate = timely / matured if matured else None
    reason = (
        "incomplete_review_evidence"
        if any(counts[key] for key in ("missing_snapshot", "unknown_status", "missing_deadline"))
        else "review_population_unconfirmed"
        if not current.required_review_population_complete
        else "source_coverage_unconfirmed"
        if not current.source_complete
        else "no_matured_reviews"
        if not matured
        else None
    )
    return TemporaryReviewReport(
        suppressed=False,
        population_episode_count=len(trusted.granted_episodes),
        population_case_count=len(population_cases),
        known_review_obligation_count=len(grants),
        review_counts=tuple(counts.items()),
        matured_review_count=matured,
        observed_completion_rate=observed_rate,
        observed_on_time_rate=timely_rate,
        population_completion_rate=observed_rate if reason is None else None,
        population_on_time_rate=timely_rate if reason is None else None,
        population_rate_unavailable_reason=reason,
        required_review_population_complete=current.required_review_population_complete,
    )
