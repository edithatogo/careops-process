"""Deterministic reference evidence and explicit credentialing reporting boundaries.

This disconnected pack requires trusted callers to supply authorised case IDs.
It never resolves practitioner identity, certifies policy compliance or writes
to a source workflow. Persist the ledger's tombstones with its projection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Literal

from pydantic import Field

if TYPE_CHECKING:
    from datetime import datetime

    from careops_process.credentialing import CredentialingFact

from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingModel,
    CredentialingProjection,
    merge_credentialing_projections,
    summarise_credentialing_projection,
    validate_credentialing_projection,
)
from careops_process.reliability import DeadLetter

RENEWAL_STAGES = (
    "request_received",
    "request_classified",
    "application_ready",
    "committee_scheduled",
    "committee_considered",
    "recommendation_recorded",
    "decision_routed_to_delegate",
    "delegated_decision_recorded",
    "decision_communicated",
    "register_activation_requested",
    "register_activated",
    "case_completed",
    "renewal_reminder_issued",
)
_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FAILURE_REASONS = frozenset({"schema", "conflicting_replay", "throttled", "timeout", "transient"})
_MINIMUM_REPORT_CASES = 2


class InferenceRun(CredentialingModel):
    """Bounded processing-run references; raw prompts and outputs are excluded."""

    run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    provider: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    model: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    agent_version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(slots=True)
class CredentialingLedger:
    """Replay state with unbounded deletion memory, requiring durable storage.

    Unlike the generic bounded checkpoint, deletions are never evicted. Tombstone
    identifiers are retained until an explicitly approved retention migration.
    """

    projection: CredentialingProjection
    tombstoned_event_ids: set[str] = field(default_factory=set[str])
    dead_letters: list[DeadLetter] = field(default_factory=list[DeadLetter])
    inference_provenance: dict[str, InferenceRun] = field(default_factory=dict[str, InferenceRun])

    def __post_init__(self) -> None:
        """Apply restored deletion memory before exposing a projection."""
        self.projection = validate_credentialing_projection(self.projection)
        self.tombstoned_event_ids = set(self.tombstoned_event_ids)
        self.dead_letters = list(self.dead_letters)
        self.inference_provenance = dict(self.inference_provenance)
        for event_id in tuple(self.tombstoned_event_ids):
            self.tombstone(event_id)
        self._require_provenance(self.projection)
        self.inference_provenance = {
            event_id: InferenceRun.model_validate(run.model_dump(mode="python"))
            for event_id, run in self.inference_provenance.items()
        }

    def _require_provenance(self, projection: CredentialingProjection) -> None:
        for fact in projection.facts:
            if fact.observed_or_inferred == "inferred" and not isinstance(
                self.inference_provenance.get(fact.event_id),
                InferenceRun,
            ):
                message = "Inferred ledger events require processing-run provenance"
                raise CredentialingContractError(message)

    def tombstone(self, event_id: str) -> None:
        """Delete a fact and remember its identity permanently across replay."""
        if _SAFE_REFERENCE.fullmatch(event_id) is None:
            message = "Tombstone must use a safe event reference"
            raise CredentialingContractError(message)
        retained = [fact for fact in self.projection.facts if fact.event_id != event_id]
        replacement = self.projection
        if len(retained) != len(self.projection.facts):
            replacement = self.projection.model_copy(update={"facts": retained}, deep=True)
        self.tombstoned_event_ids.add(event_id)
        self.inference_provenance.pop(event_id, None)
        self.projection = replacement

    def merge(self, incoming: CredentialingProjection) -> None:
        """Merge compatible batches after excluding permanently deleted facts."""
        incoming = validate_credentialing_projection(incoming)
        filtered = incoming.model_copy(
            update={
                "facts": [
                    fact
                    for fact in incoming.facts
                    if fact.event_id not in self.tombstoned_event_ids
                ],
            },
            deep=True,
        )
        self._require_provenance(filtered)
        self.projection = merge_credentialing_projections(self.projection, filtered)

    def reject(self, event_id: str, reason: str, *, recorded_at_utc: datetime) -> None:
        """Retain only a safe identity and a controlled error classification."""
        if reason not in _FAILURE_REASONS:
            message = "Dead-letter reason must be a controlled classification"
            raise CredentialingContractError(message)
        if recorded_at_utc.tzinfo is None or recorded_at_utc.utcoffset() is None:
            message = "Dead-letter timestamp must be timezone-aware"
            raise CredentialingContractError(message)
        self.dead_letters.append(
            DeadLetter(
                fact_id=event_id if _SAFE_REFERENCE.fullmatch(event_id) else "unidentified",
                reason=reason,
                retryable=reason in {"throttled", "timeout", "transient"},
                recorded_at_utc=recorded_at_utc.astimezone(UTC),
            ),
        )


@dataclass(frozen=True, slots=True)
class RenewalAssessment:
    """Human-reviewable reference comparison, never a compliance certificate."""

    status: Literal["matches_reference", "review_required", "insufficient_evidence"]
    deviations: tuple[str, ...]
    excluded_inferred_count: int


def _stage_deviations(observed: list[CredentialingFact]) -> list[str]:
    deviations: list[str] = []
    previous: datetime | None = None
    for stage in RENEWAL_STAGES:
        matches = [fact for fact in observed if fact.activity == stage]
        if not matches:
            deviations.append(f"missing:{stage}")
            continue
        if len(matches) > 1:
            deviations.append(f"repeated:{stage}")
        timestamp = matches[0].timestamp_utc
        if previous is not None and timestamp <= previous:
            deviations.append(f"order:{stage}")
        previous = timestamp
    return deviations


def assess_routine_renewal(
    projection: CredentialingProjection,
    case_id: str,
    *,
    authority_version: str,
) -> RenewalAssessment:
    """Compare one explicitly linked case to the generic routine-renewal model.

    Every required stage needs observed evidence with the caller's current
    authority version. Professional/service review and fairness branches need
    separate local applicability mapping before this evidence is operational.
    Tied required-stage timestamps are ambiguous and require human review.
    """
    projection = validate_credentialing_projection(projection)
    linked = [fact for fact in projection.facts if case_id in fact.object_ids]
    observed = [fact for fact in linked if fact.observed_or_inferred == "observed"]
    excluded = len(linked) - len(observed)
    if not observed:
        return RenewalAssessment("insufficient_evidence", ("no_observed_evidence",), excluded)
    deviations: list[str] = []
    if not authority_version:
        deviations.append("authority_version_missing")
    for fact in observed:
        if fact.qualifiers.pathway_code != "routine-renewal":
            deviations.append("pathway_mismatch")
        if fact.qualifiers.authority_mapping_version != authority_version:
            deviations.append("authority_mismatch")
    deviations.extend(_stage_deviations(observed))
    deviations.extend(
        f"additional_activity:{fact.activity}"
        for fact in observed
        if fact.activity not in RENEWAL_STAGES
    )
    return RenewalAssessment(
        "review_required" if deviations else "matches_reference",
        tuple(sorted(set(deviations))),
        excluded,
    )


def project_credentialing_report(
    projection: CredentialingProjection,
    *,
    role: str,
    case_ids: set[str],
    minimum_cases: object,
) -> dict[str, object]:
    """Project facts granted by a trusted authorisation layer or suppress counts.

    The role and case grants must come from server-side access control, never
    end-user input. Broader reports contain no case IDs or timestamps. Whole
    report suppression prevents totals revealing suppressed activity cells.
    Counts refer only to facts linked to supplied case IDs, not practitioners.
    """
    if role not in {"case_analyst", "report_reader"}:
        message = "Unknown reporting role"
        raise CredentialingContractError(message)
    if (
        not isinstance(minimum_cases, int)
        or isinstance(minimum_cases, bool)
        or minimum_cases < _MINIMUM_REPORT_CASES
    ):
        message = "Reporting minimum must be at least two distinct cases"
        raise CredentialingContractError(message)
    projection = validate_credentialing_projection(projection)
    facts = [fact for fact in projection.facts if case_ids.intersection(fact.object_ids)]
    if role == "case_analyst":
        return {
            "facts": [
                {
                    "event_id": fact.event_id,
                    "activity": fact.activity,
                    "timestamp_utc": fact.timestamp_utc.isoformat(),
                    "object_ids": sorted(case_ids.intersection(fact.object_ids)),
                    "observed_or_inferred": fact.observed_or_inferred,
                    "confidence": fact.confidence,
                }
                for fact in facts
            ],
        }
    contributors: dict[str, set[str]] = {}
    for fact in facts:
        contributors.setdefault(fact.activity, set()).update(case_ids.intersection(fact.object_ids))
        contributors.setdefault(fact.observed_or_inferred, set()).update(
            case_ids.intersection(fact.object_ids),
        )
    if not facts or any(len(cases) < minimum_cases for cases in contributors.values()):
        return {"suppressed": True, "metrics": None}
    scoped = projection.model_copy(update={"facts": facts}, deep=True)
    metrics = summarise_credentialing_projection(scoped).model_dump()
    # Unclassified linked objects could represent people; do not release this count.
    metrics.pop("unique_object_count")
    return {"suppressed": False, "metrics": metrics}
