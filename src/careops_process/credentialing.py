"""Privacy-minimised credentialing event contracts and deterministic assurance."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ContractVersion = Literal["0.1.0"]
OntologyVersion = Literal["0.1.0"]
ProjectionSource = Literal[
    "careops-approve",
    "careops-decisions",
    "dataverse",
    "sharepoint",
    "power-automate",
    "authoritative-register",
]
DerivationKind = Literal["observed", "inferred"]
Activity = Literal[
    "request_received",
    "request_classified",
    "duplicate_detected",
    "validation_failed",
    "correction_requested",
    "correction_received",
    "application_ready",
    "professional_review_requested",
    "professional_review_completed",
    "service_capability_attested",
    "fairness_notice_issued",
    "fairness_response_received",
    "committee_scheduled",
    "committee_deferred",
    "committee_considered",
    "recommendation_recorded",
    "decision_routed_to_delegate",
    "delegated_decision_recorded",
    "decision_communicated",
    "condition_applied",
    "supervision_plan_started",
    "temporary_approval_started",
    "temporary_approval_expired",
    "register_activation_requested",
    "register_activated",
    "register_reconciliation_failed",
    "renewal_reminder_issued",
    "review_commenced",
    "appeal_lodged",
    "review_or_appeal_decided",
    "case_completed",
    "case_withdrawn",
    "case_superseded",
]
DurationBucket = Literal[
    "under_1_day",
    "1_to_3_days",
    "4_to_7_days",
    "8_to_14_days",
    "15_to_30_days",
    "over_30_days",
    "not_applicable",
]

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "body",
        "body_preview",
        "decisionreason",
        "decision_reason",
        "displayname",
        "display_name",
        "email",
        "emailaddress",
        "email_address",
        "name",
        "patientdata",
        "patient_data",
        "qualification",
        "rawpayload",
        "raw_payload",
        "registrationnumber",
        "registration_number",
        "scopetext",
        "scope_text",
        "subject",
    }
)
_REWORK_ACTIVITIES = frozenset(
    {
        "duplicate_detected",
        "validation_failed",
        "correction_requested",
        "correction_received",
        "committee_deferred",
        "register_reconciliation_failed",
    }
)
_EXCEPTION_ACTIVITIES = frozenset(
    {
        "validation_failed",
        "committee_deferred",
        "register_reconciliation_failed",
    }
)


class CredentialingContractError(ValueError):
    """Raised when credentialing process data violates the safety contract."""


class CredentialingModel(BaseModel):
    """Base model that rejects unrecognised fields and strips safe text values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CredentialingQualifiers(CredentialingModel):
    """Non-identifying dimensions permitted on a credentialing event."""

    pathway_code: str | None = Field(default=None, max_length=80)
    professional_stream: str | None = Field(default=None, max_length=80)
    facility_or_service_type: str | None = Field(default=None, max_length=80)
    exception_code: str | None = Field(default=None, max_length=120)
    feature_pack_version: str | None = Field(
        default=None,
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
    )
    authority_mapping_version: str | None = Field(default=None, max_length=80)
    duration_bucket: DurationBucket | None = None


class CredentialingFact(CredentialingModel):
    """One privacy-minimised observed or inferred credentialing event."""

    event_id: str = Field(min_length=1, max_length=128)
    activity: Activity
    timestamp_utc: datetime
    source_system: str = Field(min_length=1, max_length=80)
    object_ids: list[str] = Field(min_length=1)
    observed_or_inferred: DerivationKind
    confidence: float = Field(ge=0.0, le=1.0)
    qualifiers: CredentialingQualifiers = Field(default_factory=CredentialingQualifiers)

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        """Require a bounded identifier that cannot carry free-text content."""
        if _SAFE_ID.fullmatch(value) is None:
            message = "event_id must be a safe, non-sensitive identifier"
            raise ValueError(message)
        return value

    @field_validator("object_ids")
    @classmethod
    def validate_object_ids(cls, values: list[str]) -> list[str]:
        """Require unique, bounded, non-sensitive object references."""
        if any(_SAFE_ID.fullmatch(value) is None for value in values):
            message = "object_ids must contain only safe, non-sensitive identifiers"
            raise ValueError(message)
        if len(values) != len(set(values)):
            message = "object_ids must be unique within an event"
            raise ValueError(message)
        return values

    @field_validator("timestamp_utc")
    @classmethod
    def normalise_timestamp(cls, value: datetime) -> datetime:
        """Require an explicit timezone and normalise the timestamp to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            message = "timestamp_utc must include an explicit timezone"
            raise ValueError(message)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_observation_confidence(self) -> Self:
        """Require observed events to carry deterministic confidence of one."""
        if self.observed_or_inferred == "observed" and self.confidence != 1.0:
            message = "observed credentialing events must have confidence 1"
            raise ValueError(message)
        return self


class CredentialingProjection(CredentialingModel):
    """Versioned envelope for a batch of credentialing process facts."""

    contract_version: ContractVersion = "0.1.0"
    ontology_version: OntologyVersion = "0.1.0"
    source: ProjectionSource
    watermark_utc: datetime | None = None
    facts: list[CredentialingFact]

    @field_validator("watermark_utc")
    @classmethod
    def normalise_watermark(cls, value: datetime | None) -> datetime | None:
        """Require an explicit timezone for a non-null source watermark."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            message = "watermark_utc must include an explicit timezone"
            raise ValueError(message)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_batch(self) -> Self:
        """Reject duplicate identities and order facts deterministically."""
        event_ids = [fact.event_id for fact in self.facts]
        if len(event_ids) != len(set(event_ids)):
            message = "event_id must be unique within a projection"
            raise ValueError(message)
        self.facts.sort(key=lambda fact: (fact.timestamp_utc, fact.event_id))
        return self


class CredentialingMetrics(CredentialingModel):
    """Aggregate, non-identifying assurance measures for one projection."""

    event_count: int = Field(ge=0)
    unique_object_count: int = Field(ge=0)
    observed_event_count: int = Field(ge=0)
    inferred_event_count: int = Field(ge=0)
    completed_case_event_count: int = Field(ge=0)
    committee_deferral_count: int = Field(ge=0)
    register_reconciliation_failure_count: int = Field(ge=0)
    exception_event_count: int = Field(ge=0)
    rework_event_count: int = Field(ge=0)
    activity_counts: dict[str, int]


def _normalise_key(value: object) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(value).strip().lower())


def _find_forbidden_key(value: object, *, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = _normalise_key(raw_key)
            if key in _FORBIDDEN_KEYS:
                return f"{path}.{raw_key}"
            nested = _find_forbidden_key(child, path=f"{path}.{raw_key}")
            if nested is not None:
                return nested
        return None
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, child in enumerate(value):
            nested = _find_forbidden_key(child, path=f"{path}[{index}]")
            if nested is not None:
                return nested
    return None


def validate_credentialing_projection(
    payload: Mapping[str, object] | CredentialingProjection,
) -> CredentialingProjection:
    """Validate a projection and reject sensitive or uncontrolled fields.

    Args:
        payload: Candidate projection or an already parsed projection.

    Returns:
        A deterministic, validated projection.

    Raises:
        CredentialingContractError: If a prohibited field occurs anywhere in the
            untrusted payload.
        pydantic.ValidationError: If the versioned contract is invalid.

    """
    if isinstance(payload, CredentialingProjection):
        return payload
    forbidden_path = _find_forbidden_key(payload)
    if forbidden_path is not None:
        message = f"Prohibited credentialing content field: {forbidden_path}"
        raise CredentialingContractError(message)
    return CredentialingProjection.model_validate(payload)


def _canonical_fact(fact: CredentialingFact) -> str:
    return json.dumps(
        fact.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def merge_credentialing_projections(
    existing: CredentialingProjection,
    incoming: CredentialingProjection,
) -> CredentialingProjection:
    """Merge replayed event batches without silently accepting changed events.

    Exact replay is idempotent. Reuse of an existing event identifier with
    different content fails closed because it would corrupt process history.

    Args:
        existing: Previously accepted projection.
        incoming: Later or replayed projection from the same source contract.

    Returns:
        A new deterministic projection containing the union of exact events.

    Raises:
        CredentialingContractError: If versions or sources differ, or an event ID
            is reused with different content.

    """
    if (
        existing.contract_version != incoming.contract_version
        or existing.ontology_version != incoming.ontology_version
        or existing.source != incoming.source
    ):
        message = "Projection version and source must match before replay merge"
        raise CredentialingContractError(message)

    facts_by_id = {fact.event_id: fact for fact in existing.facts}
    for fact in incoming.facts:
        previous = facts_by_id.get(fact.event_id)
        if previous is None:
            facts_by_id[fact.event_id] = fact
            continue
        if _canonical_fact(previous) != _canonical_fact(fact):
            message = f"Conflicting replay for event_id {fact.event_id}"
            raise CredentialingContractError(message)

    watermarks = [
        value
        for value in (existing.watermark_utc, incoming.watermark_utc)
        if value is not None
    ]
    return CredentialingProjection(
        contract_version=existing.contract_version,
        ontology_version=existing.ontology_version,
        source=existing.source,
        watermark_utc=max(watermarks) if watermarks else None,
        facts=list(facts_by_id.values()),
    )


def summarise_credentialing_projection(
    projection: CredentialingProjection,
) -> CredentialingMetrics:
    """Calculate privacy-safe aggregate measures from validated facts.

    Args:
        projection: Validated credentialing projection.

    Returns:
        Aggregate counts suitable for a minimum assurance dashboard.

    """
    activity_counts = Counter(fact.activity for fact in projection.facts)
    object_ids = {
        object_id
        for fact in projection.facts
        for object_id in fact.object_ids
    }
    return CredentialingMetrics(
        event_count=len(projection.facts),
        unique_object_count=len(object_ids),
        observed_event_count=sum(
            fact.observed_or_inferred == "observed" for fact in projection.facts
        ),
        inferred_event_count=sum(
            fact.observed_or_inferred == "inferred" for fact in projection.facts
        ),
        completed_case_event_count=activity_counts["case_completed"],
        committee_deferral_count=activity_counts["committee_deferred"],
        register_reconciliation_failure_count=activity_counts[
            "register_reconciliation_failed"
        ],
        exception_event_count=sum(
            activity_counts[activity] for activity in _EXCEPTION_ACTIVITIES
        ),
        rework_event_count=sum(
            activity_counts[activity] for activity in _REWORK_ACTIVITIES
        ),
        activity_counts=dict(sorted(activity_counts.items())),
    )
