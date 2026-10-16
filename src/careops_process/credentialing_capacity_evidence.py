"""Observed redeployment and protected attribution judgments, never causal proof."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, cast

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_measurements import validate_measurement_scope
from careops_process.credentialing_observations import (
    EffortComparison,
    MeasurementWindow,
    WorkObservation,
    compare_effort,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
_PURPOSES = frozenset(
    {"exception_management", "practitioner_support", "quality_assurance", "other"}
)
_MAXIMUM = 1_000_000_000_000
_MINIMUM_PERSONS = 2


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object, limit: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not _CODE.fullmatch(value):
        _fail("Capacity evidence requires bounded reference codes")
    return value


def _digest(value: object) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        _fail("Capacity evidence requires canonical SHA-256 fingerprints")


def _count(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= _MAXIMUM:
        _fail("Capacity units require bounded nonnegative integer counts or minutes")
    return value


def _flag(value: object) -> None:
    if not isinstance(value, bool):
        _fail("Capacity attestations must be strict booleans")


def _member(value: object, choices: AbstractSet[str]) -> bool:
    return isinstance(value, str) and value in choices


def _instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Capacity instants must be timezone-aware")
    try:
        return value.astimezone(UTC)
    except OverflowError:
        _fail("Capacity instant exceeds supported UTC range")


def _tuple(value: object) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        _fail("Capacity contract collections must be explicit tuples")
    return cast("tuple[object, ...]", value)


def _codes(value: object) -> frozenset[str]:
    if not isinstance(value, AbstractSet):
        _fail("Capacity grants and joint memberships require actual sets")
    return frozenset(_code(item) for item in cast("AbstractSet[object]", value))


def _floor(value: object) -> int:
    number = _count(value)
    if number < _MINIMUM_PERSONS:
        _fail("Capacity privacy threshold must be at least two distinct persons")
    return number


@dataclass(frozen=True, slots=True, kw_only=True)
class _Contract:
    """Marker for concrete, reconstructed evidence records."""


def _concrete[T: _Contract](value: object, expected: type[T]) -> T:
    if not isinstance(value, expected):
        _fail("Capacity record has wrong contract type")
    return expected(**{field.name: getattr(value, field.name) for field in fields(expected)})


def _wire(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _wire(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, datetime):
        return _instant(value).isoformat()
    if isinstance(value, (tuple, list)):
        return [_wire(item) for item in cast("Sequence[object]", value)]
    if isinstance(value, frozenset):
        return sorted(cast("frozenset[str]", value))
    if isinstance(value, dict):
        return {key: _wire(item) for key, item in cast("dict[str, object]", value).items()}
    return value


def _hash(value: object) -> str:
    encoded = json.dumps(_wire(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class RedeploymentActivityRule(_Contract):
    """Source-defined activity classification, not an intrinsic value judgment."""

    activity_code: str
    purpose: str

    def __post_init__(self) -> None:
        """Require controlled source mapping without narrative."""
        _code(self.activity_code, 80)
        if not _member(self.purpose, _PURPOSES):
            _fail("Capacity activity purpose is not registered")


@dataclass(frozen=True, slots=True, kw_only=True)
class RedeploymentActivityDefinition(_Contract):
    """Versioned complete source classification; canonical activity order."""

    version: str
    activities: tuple[RedeploymentActivityRule, ...]

    def __post_init__(self) -> None:
        """Detach nested rules and reject duplicate or empty definitions."""
        _code(self.version, 80)
        rules = tuple(_concrete(item, RedeploymentActivityRule) for item in _tuple(self.activities))
        if not rules or len({item.activity_code for item in rules}) != len(rules):
            _fail("Capacity definition requires unique nonempty activity codes")
        object.__setattr__(
            self, "activities", tuple(sorted(rules, key=lambda item: item.activity_code))
        )


def activity_definition_digest(definition: RedeploymentActivityDefinition) -> str:
    """Pin the complete supplied source classification, not just its version label."""
    return _hash(_concrete(definition, RedeploymentActivityDefinition))


@dataclass(frozen=True, slots=True, kw_only=True)
class RedeploymentCohort(_Contract):
    """One frozen source-produced aggregate population and half-open window."""

    cohort_ref: str
    source_system: str
    aggregation_definition_version: str
    release_epoch: str
    start_utc: datetime
    end_utc: datetime
    activity_definition_digest: str

    def __post_init__(self) -> None:
        """Bind identity, aware window, aggregation and full activity definition."""
        for name in (
            "cohort_ref",
            "source_system",
            "aggregation_definition_version",
            "release_epoch",
        ):
            _code(getattr(self, name), 80)
        _digest(self.activity_definition_digest)
        object.__setattr__(self, "start_utc", _instant(self.start_utc))
        object.__setattr__(self, "end_utc", _instant(self.end_utc))
        if self.end_utc <= self.start_utc:
            _fail("Capacity window must have increasing bounds")


@dataclass(frozen=True, slots=True, kw_only=True)
class RedeploymentActivityCount(_Contract):
    """Observed integer work minutes and distinct source-counted contributors."""

    activity_code: str
    observed_work_minutes: int
    distinct_observed_workers: int

    def __post_init__(self) -> None:
        """Require participating workers to have positive minutes in this activity."""
        _code(self.activity_code, 80)
        _count(self.observed_work_minutes)
        _count(self.distinct_observed_workers)
        if bool(self.observed_work_minutes) != bool(self.distinct_observed_workers):
            _fail("Capacity positive work and contributor presence must agree")


@dataclass(frozen=True, slots=True, kw_only=True)
class JointParticipationGroup(_Contract):
    """Disjoint worker atom defined by the exact nonempty activity-membership set."""

    activity_codes: frozenset[str]
    distinct_workers: int

    def __post_init__(self) -> None:
        """Detach membership and require nonzero atoms, with no worker identities."""
        codes = _codes(self.activity_codes)
        if not codes or not _count(self.distinct_workers):
            _fail("Capacity joint atoms require nonempty codes and positive worker counts")
        object.__setattr__(self, "activity_codes", codes)


@dataclass(frozen=True, slots=True, kw_only=True)
class RedeploymentSnapshot(_Contract):
    """Source-supplied aggregate; attestations are assertions, not authentication."""

    snapshot_id: str
    cohort: RedeploymentCohort
    eligible_worker_count: int
    observed_worker_count: int
    participating_worker_count: int
    higher_value_distinct_workers: int
    other_distinct_workers: int
    activities: tuple[RedeploymentActivityCount, ...]
    joint_groups: tuple[JointParticipationGroup, ...]
    source_complete: bool
    distinct_person_aggregation_attested: bool
    joint_counts_complete_attested: bool
    activity_time_partition_attested: bool
    purpose_union_counts_attested: bool
    contract_version: str = "0.1.0"

    def __post_init__(self) -> None:  # noqa: C901 - joint aggregate reconciliation invariants
        """Reconstruct nested contracts and reconcile source joint participation."""
        _code(self.snapshot_id)
        if self.contract_version != "0.1.0":
            _fail("Unsupported capacity snapshot contract version")
        object.__setattr__(self, "cohort", _concrete(self.cohort, RedeploymentCohort))
        for name in (
            "eligible_worker_count",
            "observed_worker_count",
            "participating_worker_count",
            "higher_value_distinct_workers",
            "other_distinct_workers",
        ):
            _count(getattr(self, name))
        for name in (
            "source_complete",
            "distinct_person_aggregation_attested",
            "joint_counts_complete_attested",
            "activity_time_partition_attested",
            "purpose_union_counts_attested",
        ):
            _flag(getattr(self, name))
        if (
            not self.eligible_worker_count
            >= self.observed_worker_count
            >= self.participating_worker_count
        ):
            _fail("Capacity eligible, observed and participating workers do not reconcile")
        counts = tuple(
            _concrete(item, RedeploymentActivityCount) for item in _tuple(self.activities)
        )
        groups = tuple(
            _concrete(item, JointParticipationGroup) for item in _tuple(self.joint_groups)
        )
        codes = {item.activity_code for item in counts}
        if (
            not counts
            or len(codes) != len(counts)
            or len({item.activity_codes for item in groups}) != len(groups)
        ):
            _fail("Capacity activity counts and joint atoms must be unique")
        if any(not group.activity_codes <= codes for group in groups):
            _fail("Capacity joint atom contains an unknown activity")
        workers = sum(group.distinct_workers for group in groups)
        if workers > self.participating_worker_count:
            _fail("Capacity joint atoms exceed participating workers")
        if self.joint_counts_complete_attested and workers != self.participating_worker_count:
            _fail("Complete capacity joint atoms must partition participating workers")
        for item in counts:
            joint_workers = sum(
                group.distinct_workers
                for group in groups
                if item.activity_code in group.activity_codes
            )
            if (
                joint_workers > item.distinct_observed_workers
                or item.distinct_observed_workers > self.participating_worker_count
                or (
                    self.joint_counts_complete_attested
                    and joint_workers != item.distinct_observed_workers
                )
            ):
                _fail("Capacity per-activity workers disagree with joint counts")
        if (
            max(self.higher_value_distinct_workers, self.other_distinct_workers)
            > self.participating_worker_count
        ):
            _fail("Capacity purpose unions exceed participating workers")
        object.__setattr__(
            self, "activities", tuple(sorted(counts, key=lambda item: item.activity_code))
        )
        object.__setattr__(
            self,
            "joint_groups",
            tuple(sorted(groups, key=lambda item: tuple(sorted(item.activity_codes)))),
        )


def merge_redeployment_snapshots(
    existing: Sequence[RedeploymentSnapshot],
    incoming: Sequence[RedeploymentSnapshot],
) -> tuple[RedeploymentSnapshot, ...]:
    """Do not add overlapping cohorts or overwrite frozen source release epochs."""
    ids: dict[str, RedeploymentSnapshot] = {}
    epochs: dict[tuple[str, str, str], RedeploymentSnapshot] = {}
    for supplied in (*existing, *incoming):
        item = _concrete(supplied, RedeploymentSnapshot)
        previous = ids.get(item.snapshot_id)
        epoch = (item.cohort.source_system, item.cohort.cohort_ref, item.cohort.release_epoch)
        prior_epoch = epochs.get(epoch)
        if (
            (previous is not None and previous != item)
            or (prior_epoch is not None and _wire(prior_epoch.activities) != _wire(item.activities))
            or (
                prior_epoch is not None
                and _snapshot_content(prior_epoch) != _snapshot_content(item)
            )
        ):
            _fail("Conflicting capacity snapshot replay or frozen epoch")
        ids[item.snapshot_id] = item
        epochs[epoch] = item
    return tuple(ids[key] for key in sorted(ids))


def _snapshot_content(item: RedeploymentSnapshot) -> dict[str, object]:
    return {
        field.name: _wire(getattr(item, field.name))
        for field in fields(RedeploymentSnapshot)
        if field.name != "snapshot_id"
    }


@dataclass(frozen=True, slots=True)
class RedeploymentMetrics:
    """Destination work and coverage, without source identities or causal inference."""

    eligible_worker_count: int
    observed_worker_count: int
    missing_worker_count: int
    participating_worker_count: int
    observed_nonparticipating_worker_count: int
    activities: tuple[RedeploymentActivityCount, ...]
    total_observed_minutes: int
    observed_higher_value_minutes: int
    observed_other_minutes: int
    higher_value_distinct_workers: int
    other_distinct_workers: int
    observed_higher_value_share: float | None
    mean_minutes_per_observed_worker: float | None
    full_cohort_mean_minutes: float | None
    full_cohort_unavailable_reason: str | None


@dataclass(frozen=True, slots=True)
class RedeploymentReport:
    """Whole released aggregate, or no metrics at all."""

    suppressed: bool
    metrics: RedeploymentMetrics | None


def _scope(role: str, grants: object, minimum: object) -> tuple[frozenset[str], int]:
    if role != "report_reader":
        _fail("Capacity reporting requires a trusted report-reader role")
    return _codes(grants), _floor(minimum)


def report_redeployment(  # noqa: PLR0913 - explicit source/cohort/privacy binding
    snapshot: RedeploymentSnapshot,
    definition: RedeploymentActivityDefinition,
    *,
    role: str,
    granted_cohort_refs: AbstractSet[str],
    expected_cohort: RedeploymentCohort,
    minimum_persons: int,
) -> RedeploymentReport:
    """Release one bound source aggregate only with safe complete joint atoms."""
    grants, floor = _scope(role, granted_cohort_refs, minimum_persons)
    value = _concrete(snapshot, RedeploymentSnapshot)
    profile = _concrete(definition, RedeploymentActivityDefinition)
    bound = _concrete(expected_cohort, RedeploymentCohort)
    if (
        value.cohort != bound
        or bound.cohort_ref not in grants
        or bound.activity_definition_digest != activity_definition_digest(profile)
    ):
        _fail("Capacity snapshot does not match the granted frozen cohort or definition")
    purposes = {item.activity_code: item.purpose for item in profile.activities}
    if set(purposes) != {item.activity_code for item in value.activities}:
        _fail("Capacity activity counts do not match complete supplied definition")
    higher = {code for code, purpose in purposes.items() if purpose != "other"}
    higher_workers = sum(
        group.distinct_workers for group in value.joint_groups if group.activity_codes & higher
    )
    other_workers = sum(
        group.distinct_workers for group in value.joint_groups if group.activity_codes - higher
    )
    if value.joint_counts_complete_attested and (
        higher_workers != value.higher_value_distinct_workers
        or other_workers != value.other_distinct_workers
    ):
        _fail("Capacity purpose unions disagree with source joint atoms")
    missing = value.eligible_worker_count - value.observed_worker_count
    nonparticipating = value.observed_worker_count - value.participating_worker_count
    cells = [
        value.eligible_worker_count,
        value.observed_worker_count,
        missing,
        value.participating_worker_count,
        nonparticipating,
        higher_workers,
        other_workers,
        value.participating_worker_count - higher_workers,
        value.participating_worker_count - other_workers,
    ]
    cells.extend(group.distinct_workers for group in value.joint_groups)
    cells.extend(item.distinct_observed_workers for item in value.activities)
    cells.extend(
        value.participating_worker_count - item.distinct_observed_workers
        for item in value.activities
    )
    if (
        not value.eligible_worker_count
        or not all(
            (
                value.distinct_person_aggregation_attested,
                value.joint_counts_complete_attested,
                value.activity_time_partition_attested,
                value.purpose_union_counts_attested,
            )
        )
        or any(0 < count < floor for count in cells)
    ):
        return RedeploymentReport(suppressed=True, metrics=None)
    total = sum(item.observed_work_minutes for item in value.activities)
    higher_minutes = sum(
        item.observed_work_minutes for item in value.activities if item.activity_code in higher
    )
    reason = (
        "missing_worker_coverage"
        if missing
        else "source_coverage_unconfirmed"
        if not value.source_complete
        else None
    )
    return RedeploymentReport(
        suppressed=False,
        metrics=RedeploymentMetrics(
            value.eligible_worker_count,
            value.observed_worker_count,
            missing,
            value.participating_worker_count,
            nonparticipating,
            value.activities,
            total,
            higher_minutes,
            total - higher_minutes,
            higher_workers,
            other_workers,
            higher_minutes / total if total else None,
            total / value.observed_worker_count if value.observed_worker_count else None,
            total / value.eligible_worker_count if reason is None else None,
            reason,
        ),
    )


def _window(value: object) -> MeasurementWindow:
    if not isinstance(value, MeasurementWindow):
        _fail("Capacity effort window has wrong record type")
    return MeasurementWindow(
        start_utc=_instant(value.start_utc),
        end_utc=_instant(value.end_utc),
        source_mapping_version=value.source_mapping_version,
        cohort_definition_version=value.cohort_definition_version,
        source_complete=value.source_complete,
    )


def _work(values: object) -> tuple[WorkObservation, ...]:
    retained: dict[str, WorkObservation] = {}
    for supplied in _tuple(values):
        if not isinstance(supplied, WorkObservation):
            _fail("Capacity effort evidence must be explicit work observations")
        item = WorkObservation(
            observation_id=supplied.observation_id,
            case_id=supplied.case_id,
            source_system=supplied.source_system,
            recorded_at_utc=_instant(supplied.recorded_at_utc),
            contract_version=supplied.contract_version,
            manual_touch_count=supplied.manual_touch_count,
            active_work_minutes=supplied.active_work_minutes,
            effort_complete=supplied.effort_complete,
        )
        prior = retained.get(item.observation_id)
        if prior is not None and prior != item:
            _fail("Conflicting retained capacity effort observation replay")
        retained[item.observation_id] = item
    return tuple(retained[key] for key in sorted(retained))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityEvidenceBundle(_Contract):
    """Protected retained inputs; no client-computed effort comparison is accepted."""

    snapshot: RedeploymentSnapshot
    definition: RedeploymentActivityDefinition
    expected_cohort: RedeploymentCohort
    baseline_work: tuple[WorkObservation, ...]
    current_work: tuple[WorkObservation, ...]
    baseline_case_ids: frozenset[str]
    current_case_ids: frozenset[str]
    baseline_window: MeasurementWindow
    current_window: MeasurementWindow

    def __post_init__(self) -> None:
        """Detach concrete nested contracts, work records, windows and actual grants."""
        object.__setattr__(self, "snapshot", _concrete(self.snapshot, RedeploymentSnapshot))
        object.__setattr__(
            self, "definition", _concrete(self.definition, RedeploymentActivityDefinition)
        )
        object.__setattr__(
            self, "expected_cohort", _concrete(self.expected_cohort, RedeploymentCohort)
        )
        for name in ("baseline_work", "current_work"):
            object.__setattr__(self, name, _work(getattr(self, name)))
        for name in ("baseline_case_ids", "current_case_ids"):
            object.__setattr__(self, name, _codes(getattr(self, name)))
        for name in ("baseline_window", "current_window"):
            object.__setattr__(self, name, _window(getattr(self, name)))
        if (
            self.current_window.start_utc != self.expected_cohort.start_utc
            or self.current_window.end_utc != self.expected_cohort.end_utc
        ):
            _fail("Capacity redeployment and current effort windows must match exactly")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityReportScope(_Contract):
    """Trusted cohort access; case grants are retained separately in the bundle."""

    role: str
    granted_cohort_refs: frozenset[str]

    def __post_init__(self) -> None:
        """Detach actual set grants without authenticating them."""
        grants, _ = _scope(self.role, self.granted_cohort_refs, 2)
        object.__setattr__(self, "granted_cohort_refs", grants)


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityReportPolicy(_Contract):
    """Distinct-person and distinct-case privacy floors remain separate."""

    minimum_persons: int
    minimum_cases: int

    def __post_init__(self) -> None:
        """Reject unsafe or coerced release parameters."""
        _floor(self.minimum_persons)
        validate_measurement_scope(
            role="report_reader", case_ids=frozenset(), minimum_cases=self.minimum_cases
        )


@dataclass(frozen=True, slots=True)
class CapacityEvidenceRecord:
    """Protected recomputed binding; its digest is not a public identity or proof."""

    evidence_digest: str
    redeployment: RedeploymentReport
    effort: EffortComparison
    suppressed: bool
    unavailable_reason: str | None


def build_capacity_evidence(
    bundle: CapacityEvidenceBundle,
    *,
    scope: CapacityReportScope,
    policy: CapacityReportPolicy,
) -> CapacityEvidenceRecord:
    """Recompute effort from retained public records, never infer total released minutes."""
    value = _concrete(bundle, CapacityEvidenceBundle)
    trusted = _concrete(scope, CapacityReportScope)
    current = _concrete(policy, CapacityReportPolicy)
    redeployment = report_redeployment(
        value.snapshot,
        value.definition,
        role=trusted.role,
        granted_cohort_refs=trusted.granted_cohort_refs,
        expected_cohort=value.expected_cohort,
        minimum_persons=current.minimum_persons,
    )
    effort = compare_effort(
        value.baseline_work,
        value.current_work,
        baseline_window=value.baseline_window,
        current_window=value.current_window,
        baseline_case_ids=value.baseline_case_ids,
        current_case_ids=value.current_case_ids,
        role=trusted.role,
        minimum_cases=current.minimum_cases,
    )
    suppressed = redeployment.suppressed or effort.suppressed
    if suppressed:
        redeployment = RedeploymentReport(suppressed=True, metrics=None)
        effort = EffortComparison(suppressed=True, available=False)
    reason = None
    if not suppressed:
        if redeployment.metrics is not None and redeployment.metrics.full_cohort_unavailable_reason:
            reason = "redeployment_coverage_incomplete"
        elif not effort.available:
            reason = "effort_comparison_unavailable"
    return CapacityEvidenceRecord(
        _hash({"bundle": value, "scope": trusted, "policy": current}),
        redeployment,
        effort,
        suppressed,
        reason,
    )


_ARTIFACT_KINDS = frozenset(
    {"evaluation_method", "population_alignment", "evaluation_design", "study_results"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityEvidenceArtifact(_Contract):
    """Protected reference and hash; syntax cannot establish authenticity or existence."""

    reference: str
    artifact_kind: str
    sha256: str

    def __post_init__(self) -> None:
        """Require a controlled evidence role and immutable content fingerprint."""
        _code(self.reference)
        _digest(self.sha256)
        if not _member(self.artifact_kind, _ARTIFACT_KINDS):
            _fail("Capacity attribution evidence role is not registered")


def _artifacts(values: object, *, complete: bool) -> tuple[CapacityEvidenceArtifact, ...]:
    items = tuple(_concrete(item, CapacityEvidenceArtifact) for item in _tuple(values))
    kinds = {item.artifact_kind for item in items}
    if len(kinds) != len(items) or len({item.reference for item in items}) != len(items):
        _fail("Capacity attribution evidence references and roles must be unique")
    if complete and frozenset(kinds) != _ARTIFACT_KINDS:
        _fail("Capacity claim requires all explicit evaluation evidence roles")
    return tuple(sorted(items, key=lambda item: item.artifact_kind))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityAttributionClaim(_Contract):
    """An externally supported claimed subset of the same measured destination work."""

    claim_id: str
    version: str
    evidence_digest: str
    cohort: RedeploymentCohort
    method_code: str
    method_version: str
    claimed_attributed_redeployment_minutes: int
    unit: str
    artifacts: tuple[CapacityEvidenceArtifact, ...]
    claim_kind: str = "attributed_observed_redeployment"

    def __post_init__(self) -> None:
        """Pin units and external evidence without asserting causal truth."""
        for name in ("claim_id", "version", "method_code", "method_version"):
            _code(getattr(self, name), 80)
        _digest(self.evidence_digest)
        _count(self.claimed_attributed_redeployment_minutes)
        if self.unit != "minutes" or self.claim_kind != "attributed_observed_redeployment":
            _fail("Capacity claim requires explicit same-population observed minute units")
        object.__setattr__(self, "cohort", _concrete(self.cohort, RedeploymentCohort))
        object.__setattr__(self, "artifacts", _artifacts(self.artifacts, complete=True))


def capacity_claim_digest(claim: CapacityAttributionClaim) -> str:
    """Bind the exact protected claim, including its artifact provenance."""
    return _hash(_concrete(claim, CapacityAttributionClaim))


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedCapacityEvidenceManifest(_Contract):
    """Adapter-supplied actual artifact hashes; this object does not resolve or authenticate."""

    artifacts: tuple[CapacityEvidenceArtifact, ...]

    def __post_init__(self) -> None:
        """Detach actual resolution records; incomplete resolution stays incomplete."""
        object.__setattr__(self, "artifacts", _artifacts(self.artifacts, complete=False))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityReviewerContext(_Contract):
    """Role/actor resolved at an authenticated service boundary, not by this function."""

    reviewer_reference: str
    reviewer_role: str

    def __post_init__(self) -> None:
        """Reject unsupported review roles and narrative identifiers."""
        _code(self.reviewer_reference)
        if not _member(self.reviewer_role, frozenset({"process_owner", "assurance_reviewer"})):
            _fail("Capacity assessment requires a trusted owner or assurance reviewer")


_DECISIONS = frozenset({"accepted_for_evaluation_record", "rejected", "needs_more_evidence"})


@dataclass(frozen=True, slots=True, kw_only=True)
class CapacityAttributionAssessment(_Contract):
    """Protected external judgment only; never a causal verification certificate."""

    evidence_digest: str
    claim_digest: str
    resolved_manifest_digest: str
    reviewer: CapacityReviewerContext
    decided_at_utc: datetime
    decision: str
    scope: str = "external_judgment_only"

    def __post_init__(self) -> None:
        """Bind a disposition to immutable current evidence without operational authority."""
        for name in ("evidence_digest", "claim_digest", "resolved_manifest_digest"):
            _digest(getattr(self, name))
        object.__setattr__(self, "reviewer", _concrete(self.reviewer, CapacityReviewerContext))
        object.__setattr__(self, "decided_at_utc", _instant(self.decided_at_utc))
        if not _member(self.decision, _DECISIONS) or self.scope != "external_judgment_only":
            _fail("Capacity assessment cannot grant causal or operational authority")


def _claim_problem(
    record: CapacityEvidenceRecord,
    bundle: CapacityEvidenceBundle,
    claim: CapacityAttributionClaim,
) -> str | None:
    if record.suppressed:
        return "constituent_suppressed"
    if claim.evidence_digest != record.evidence_digest or claim.cohort != bundle.expected_cohort:
        return "claim_evidence_binding_mismatch"
    if record.unavailable_reason is not None:
        return record.unavailable_reason
    if (
        record.redeployment.metrics is None
        or claim.claimed_attributed_redeployment_minutes
        > record.redeployment.metrics.observed_higher_value_minutes
    ):
        return "claim_exceeds_same_measured_redeployment"
    return None


def assess_capacity_claim(  # noqa: PLR0913 - explicit protected evidence and reviewer boundary
    bundle: CapacityEvidenceBundle,
    claim: CapacityAttributionClaim,
    *,
    scope: CapacityReportScope,
    policy: CapacityReportPolicy,
    reviewer_context: CapacityReviewerContext,
    resolved_evidence_manifest: ResolvedCapacityEvidenceManifest,
    disposition: str,
    decided_at_utc: datetime,
) -> CapacityAttributionAssessment:
    """Record an authenticated adapter's judgment; do not authenticate client assertions."""
    value = _concrete(bundle, CapacityEvidenceBundle)
    supplied = _concrete(claim, CapacityAttributionClaim)
    record = build_capacity_evidence(value, scope=scope, policy=policy)
    manifest = _concrete(resolved_evidence_manifest, ResolvedCapacityEvidenceManifest)
    if _claim_problem(record, value, supplied) is not None:
        _fail("Capacity claim lacks compatible complete current measurement evidence")
    if disposition == "accepted_for_evaluation_record" and manifest.artifacts != supplied.artifacts:
        _fail("Capacity acceptance requires matching resolved evaluation artifact hashes")
    instant = _instant(decided_at_utc)
    if instant < value.expected_cohort.end_utc:
        _fail("Capacity assessment cannot precede its measured window end")
    return CapacityAttributionAssessment(
        evidence_digest=record.evidence_digest,
        claim_digest=capacity_claim_digest(supplied),
        resolved_manifest_digest=_hash(manifest),
        reviewer=_concrete(reviewer_context, CapacityReviewerContext),
        decided_at_utc=instant,
        decision=disposition,
    )


@dataclass(frozen=True, slots=True)
class ProtectedCapacitySummary:
    """Protected claim/judgment summary; NEVER a public aggregate release contract."""

    suppressed: bool
    redeployment: RedeploymentMetrics | None = None
    effort: EffortComparison | None = None
    claim_status: str | None = None
    claimed_attributed_redeployment_minutes: int | None = None
    unavailable_reason: str | None = None


def summarize_capacity_evidence(  # noqa: PLR0913 - separate protected claim/review inputs
    bundle: CapacityEvidenceBundle,
    *,
    scope: CapacityReportScope,
    policy: CapacityReportPolicy,
    claim: CapacityAttributionClaim | None = None,
    assessment: CapacityAttributionAssessment | None = None,
    resolved_evidence_manifest: ResolvedCapacityEvidenceManifest | None = None,
) -> ProtectedCapacitySummary:
    """Build a protected operational summary; authenticate access in the service adapter."""
    value = _concrete(bundle, CapacityEvidenceBundle)
    record = build_capacity_evidence(value, scope=scope, policy=policy)
    if record.suppressed:
        return ProtectedCapacitySummary(suppressed=True)
    status, amount, reason = "no_claim", None, record.unavailable_reason
    if claim is None and assessment is not None:
        _fail("Capacity assessment requires its retained claim")
    if claim is not None:
        supplied = _concrete(claim, CapacityAttributionClaim)
        reason = _claim_problem(record, value, supplied)
        status = "unavailable" if reason else "unverified"
        if reason is None:
            amount = supplied.claimed_attributed_redeployment_minutes
            if assessment is not None:
                reviewed = _concrete(assessment, CapacityAttributionAssessment)
                manifest = (
                    _concrete(resolved_evidence_manifest, ResolvedCapacityEvidenceManifest)
                    if resolved_evidence_manifest is not None
                    else None
                )
                if (
                    reviewed.evidence_digest != record.evidence_digest
                    or reviewed.claim_digest != capacity_claim_digest(supplied)
                    or reviewed.decided_at_utc < value.expected_cohort.end_utc
                    or manifest is None
                    or reviewed.resolved_manifest_digest != _hash(manifest)
                ):
                    reason = "stale_or_unresolved_assessment"
                elif (
                    reviewed.decision == "accepted_for_evaluation_record"
                    and manifest.artifacts != supplied.artifacts
                ):
                    reason = "assessment_artifact_binding_mismatch"
                else:
                    status = {
                        "accepted_for_evaluation_record": "human_assessed_external_judgment",
                        "rejected": "rejected",
                        "needs_more_evidence": "needs_more_evidence",
                    }[reviewed.decision]
    return ProtectedCapacitySummary(
        suppressed=False,
        redeployment=record.redeployment.metrics,
        effort=record.effort,
        claim_status=status,
        claimed_attributed_redeployment_minutes=amount,
        unavailable_reason=reason,
    )


@dataclass(frozen=True, slots=True)
class CapacityReport:
    """Public measurements only; contains no attributed subset or review disclosure."""

    suppressed: bool
    redeployment: RedeploymentMetrics | None = None
    effort: EffortComparison | None = None
    unavailable_reason: str | None = None


def report_capacity_evidence(
    bundle: CapacityEvidenceBundle,
    *,
    scope: CapacityReportScope,
    policy: CapacityReportPolicy,
) -> CapacityReport:
    """Release privacy-checked measurements without any protected claim/review input."""
    record = build_capacity_evidence(bundle, scope=scope, policy=policy)
    if record.suppressed:
        return CapacityReport(suppressed=True)
    return CapacityReport(
        suppressed=False,
        redeployment=record.redeployment.metrics,
        effort=record.effort,
        unavailable_reason=record.unavailable_reason,
    )


type CapacityWireRecord = (
    RedeploymentActivityDefinition
    | RedeploymentSnapshot
    | CapacityAttributionClaim
    | CapacityAttributionAssessment
    | ResolvedCapacityEvidenceManifest
)
_WIRE_TYPES: dict[str, type[_Contract]] = {
    "redeployment_activity_definition": RedeploymentActivityDefinition,
    "redeployment_snapshot": RedeploymentSnapshot,
    "capacity_attribution_claim": CapacityAttributionClaim,
    "capacity_attribution_assessment": CapacityAttributionAssessment,
    "resolved_capacity_evidence_manifest": ResolvedCapacityEvidenceManifest,
}


def capacity_record_payload(record: CapacityWireRecord) -> dict[str, object]:
    """Export a protected strict record; never treat these provenance fields as public metrics."""
    for kind, expected in _WIRE_TYPES.items():
        if isinstance(record, expected):
            value = _concrete(record, expected)
            return {"kind": kind, **cast("dict[str,object]", _wire(value))}
    _fail("Unsupported capacity wire record")


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _fail("Capacity wire object must be a mapping")
    return cast("Mapping[str,object]", value)


def _map(value: object, expected: type[_Contract]) -> dict[str, object]:
    supplied = _mapping(value)
    if frozenset(supplied) != frozenset(field.name for field in fields(expected)):
        _fail("Capacity wire fields do not match exact contract")
    return dict(supplied)


def _array(value: object) -> tuple[object, ...]:
    if not isinstance(value, list):
        _fail("Capacity wire collections must be arrays")
    return tuple(cast("list[object]", value))


def _wire_instant(value: object) -> datetime:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        _fail("Capacity wire timestamp must be aware RFC3339")
    try:
        instant = datetime.fromisoformat(value.replace("z", "+00:00"))
    except ValueError:
        _fail("Capacity wire timestamp is invalid")
    return _instant(instant)


def _decode[T: _Contract](payload: object, expected: type[T]) -> T:
    data = _map(payload, expected)
    if expected is RedeploymentActivityDefinition:
        data["activities"] = tuple(
            _decode(item, RedeploymentActivityRule) for item in _array(data["activities"])
        )
    elif expected is RedeploymentSnapshot:
        data["cohort"] = _decode(data["cohort"], RedeploymentCohort)
        data["activities"] = tuple(
            _decode(item, RedeploymentActivityCount) for item in _array(data["activities"])
        )
        data["joint_groups"] = tuple(
            _decode(item, JointParticipationGroup) for item in _array(data["joint_groups"])
        )
    elif expected is JointParticipationGroup:
        codes = tuple(_code(item) for item in _array(data["activity_codes"]))
        if len(set(codes)) != len(codes):
            _fail("Capacity wire joint membership cannot repeat activity codes")
        data["activity_codes"] = frozenset(codes)
    elif expected is RedeploymentCohort:
        data["start_utc"] = _wire_instant(data["start_utc"])
        data["end_utc"] = _wire_instant(data["end_utc"])
    elif expected is CapacityAttributionClaim:
        data["cohort"] = _decode(data["cohort"], RedeploymentCohort)
        data["artifacts"] = tuple(
            _decode(item, CapacityEvidenceArtifact) for item in _array(data["artifacts"])
        )
    elif expected is ResolvedCapacityEvidenceManifest:
        data["artifacts"] = tuple(
            _decode(item, CapacityEvidenceArtifact) for item in _array(data["artifacts"])
        )
    elif expected is CapacityAttributionAssessment:
        data["reviewer"] = _decode(data["reviewer"], CapacityReviewerContext)
        data["decided_at_utc"] = _wire_instant(data["decided_at_utc"])
    return expected(**data)  # type: ignore[arg-type]


def parse_capacity_record(payload: Mapping[str, object]) -> CapacityWireRecord:
    """Strict protected-wire ingestion; authentication must precede trusted service use."""
    supplied = _mapping(payload)
    kind = supplied.get("kind")
    if not isinstance(kind, str) or kind not in _WIRE_TYPES:
        _fail("Unknown capacity wire record kind")
    data = {key: value for key, value in supplied.items() if key != "kind"}
    return cast("CapacityWireRecord", _decode(data, _WIRE_TYPES[kind]))
