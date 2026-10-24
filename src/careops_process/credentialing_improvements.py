# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Evidence-bound investigation hypotheses and measurement-only human review."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never

from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)
from careops_process.credentialing_measurements import (
    STAGE_INTERVALS,
    StageTimeReport,
    report_stage_times,
    validate_measurement_scope,
)

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet

_MAX_HOURS = 1_000_000_000
_RULE_VERSION = "stage-p95-v1"
_INVESTIGATION = "investigate_stage_delay"
_ALTERNATIVES = ("source_coverage_gap", "legitimate_variant", "clock_quality", "case_mix")
_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_INTERVALS = frozenset(f"{start}__{finish}" for start, finish in STAGE_INTERVALS)


def _fail(message: str) -> Never:
    raise CredentialingContractError(message) from None


def _code(value: object) -> None:
    if not isinstance(value, str) or _CODE.fullmatch(value) is None:
        _fail("Review policy and actor references must be bounded opaque codes")


def _digest(value: object) -> None:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        _fail("Review requires a canonical evidence fingerprint")


def _hours(value: object) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value <= 0
        or value > _MAX_HOURS
    ):
        _fail("Review thresholds must be bounded positive hours")
    result = float(value)
    if not math.isfinite(result):
        _fail("Review thresholds must be finite hours")
    return result


def _review_instant(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail("Review timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _fingerprint(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class HumanMeasurementReview:
    """A trusted reviewer's recorded measurement decision; no operational authority."""

    decision: str
    reviewer_reference: str
    reviewer_role: str
    decided_at_utc: datetime
    evidence_digest: str
    scope: str = "measurement_review_only"

    def __post_init__(self) -> None:
        """Reject unsafe roles, decision codes, scope and timestamps."""
        if self.decision not in ("accepted", "rejected", "needs_more_evidence"):
            _fail("Unsupported measurement-review decision")
        if self.reviewer_role not in ("process_owner", "assurance_reviewer"):
            _fail("Measurement review requires a trusted owner or assurance role")
        _code(self.reviewer_reference)
        _digest(self.evidence_digest)
        if self.scope != "measurement_review_only":
            _fail("Measurement review cannot grant operational authority")
        object.__setattr__(self, "decided_at_utc", _review_instant(self.decided_at_utc))


@dataclass(frozen=True, slots=True, kw_only=True)
class ImprovementProposal:
    """A deterministic p95 investigation candidate with pinned evidence and policy."""

    proposal_id: str
    rule_version: str
    evidence_digest: str
    interval_id: str
    measured_p95_hours: float
    threshold_hours: float
    threshold_version: str
    investigation_code: str = _INVESTIGATION
    alternative_explanation_codes: tuple[str, ...] = _ALTERNATIVES
    review: HumanMeasurementReview | None = None

    def __post_init__(self) -> None:
        """Check controlled semantics, genuine breach and identity consistency."""
        _digest(self.evidence_digest)
        _code(self.threshold_version)
        _hours(self.measured_p95_hours)
        _hours(self.threshold_hours)
        if (
            self.rule_version != _RULE_VERSION
            or self.interval_id not in _INTERVALS
            or self.investigation_code != _INVESTIGATION
            or self.alternative_explanation_codes != _ALTERNATIVES
            or self.measured_p95_hours <= self.threshold_hours
        ):
            _fail("Proposal does not match a supported investigation rule and breach")
        expected = _proposal_identity(
            self.evidence_digest,
            self.interval_id,
            self.measured_p95_hours,
            self.threshold_hours,
            self.threshold_version,
        )
        if self.proposal_id != expected:
            _fail("Proposal identity does not match its immutable evidence and rule")
        if self.review is not None:
            validated = replace(self.review)
            if validated.evidence_digest != self.evidence_digest:
                _fail("Review evidence does not match the proposal")
            object.__setattr__(self, "review", validated)


def _proposal_identity(
    evidence: str,
    interval: str,
    measured: float,
    threshold: float,
    version: str,
) -> str:
    return "proposal-" + _fingerprint(
        (
            _RULE_VERSION,
            evidence,
            interval,
            measured,
            threshold,
            version,
            _INVESTIGATION,
            _ALTERNATIVES,
        ),
    )


def _evidence_fingerprint(
    projection: CredentialingProjection,
    grants: frozenset[str],
    report: StageTimeReport,
    authority: str,
) -> str:
    facts: list[dict[str, object]] = []
    for fact in projection.facts:
        if fact.observed_or_inferred != "observed" or not grants.intersection(fact.object_ids):
            continue
        payload = fact.model_dump(mode="json")
        payload["object_ids"] = sorted(fact.object_ids)
        facts.append(payload)
    facts.sort(key=lambda row: json.dumps(row, sort_keys=True))
    return _fingerprint(
        {
            "source": projection.source,
            "contract_version": projection.contract_version,
            "ontology_version": projection.ontology_version,
            "authority_version": authority,
            "case_grants": sorted(grants),
            "observed_facts": facts,
            "report": asdict(report),
        }
    )


def propose_stage_improvements(  # noqa: PLR0913 - explicit trusted scope and versioned policy
    projection: CredentialingProjection,
    *,
    role: str,
    case_ids: AbstractSet[str],
    minimum_cases: object,
    authority_version: str,
    threshold_hours: object,
    threshold_version: str,
) -> tuple[ImprovementProposal, ...]:
    """Recompute released evidence and propose investigation for genuine p95 breaches.

    Args:
        projection: Current source projection, revalidated and detached here.
        role: Aggregate role supplied by a trusted authorization adapter.
        case_ids: Explicit case grants supplied by that adapter.
        minimum_cases: Controlled distinct-case privacy threshold.
        authority_version: Approved mapping version to measure against.
        threshold_hours: Finite positive controlled investigation threshold.
        threshold_version: Version of the approved measurement policy.

    Returns:
        Immutable hypotheses, empty when evidence is suppressed or no breach exists.

    Raises:
        CredentialingContractError: If scope, projection or measurement policy is invalid.

    """
    threshold = _hours(threshold_hours)
    _code(threshold_version)
    grants, minimum = validate_measurement_scope(
        role=role,
        case_ids=case_ids,
        minimum_cases=minimum_cases,
    )
    detached = validate_credentialing_projection(projection)
    report = report_stage_times(
        detached,
        role=role,
        case_ids=grants,
        minimum_cases=minimum,
        authority_version=authority_version,
    )
    if report.suppressed or report.measures is None:
        return ()
    digest = _fingerprint(
        {
            "observed_evidence": _evidence_fingerprint(detached, grants, report, authority_version),
            "threshold_hours": threshold,
            "threshold_version": threshold_version,
            "rule_version": _RULE_VERSION,
        }
    )
    return tuple(
        ImprovementProposal(
            proposal_id=_proposal_identity(
                digest,
                measure.interval_id,
                measure.p95_hours,
                threshold,
                threshold_version,
            ),
            rule_version=_RULE_VERSION,
            evidence_digest=digest,
            interval_id=measure.interval_id,
            measured_p95_hours=measure.p95_hours,
            threshold_hours=threshold,
            threshold_version=threshold_version,
        )
        for measure in report.measures
        if measure.p95_hours is not None and measure.p95_hours > threshold
    )


def review_proposal(  # noqa: PLR0913 - explicit trusted actor and current evidence boundary
    proposal: ImprovementProposal,
    *,
    decision: str,
    reviewer_reference: str,
    reviewer_role: str,
    decided_at_utc: datetime,
    current_evidence_digest: str,
) -> ImprovementProposal:
    """Record one human measurement decision against unchanged current evidence.

    Args:
        proposal: Retained hypothesis, revalidated before transition.
        decision: Accepted, rejected or needs_more_evidence measurement disposition.
        reviewer_reference: Opaque controlled reference resolved by the service.
        reviewer_role: Process owner or assurance reviewer from trusted authorization.
        decided_at_utc: Aware review-record timestamp.
        current_evidence_digest: Recomputed digest from the current authorized projection.

    Returns:
        A new reviewed proposal; the input is unchanged.

    Raises:
        CredentialingContractError: For stale evidence, invalid actors or repeat review.

    """
    validated = replace(proposal)
    _digest(current_evidence_digest)
    if validated.review is not None or validated.evidence_digest != current_evidence_digest:
        _fail("Review requires an unreviewed proposal and unchanged current evidence")
    review = HumanMeasurementReview(
        decision=decision,
        reviewer_reference=reviewer_reference,
        reviewer_role=reviewer_role,
        decided_at_utc=decided_at_utc,
        evidence_digest=current_evidence_digest,
    )
    return replace(validated, review=review)
