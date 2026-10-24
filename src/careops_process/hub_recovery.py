# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic bounded recovery metadata; no dispatcher, provider or persistence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from careops_process.hub_capabilities import OpaqueReference
from careops_process.hub_domain import (
    Digest,
    GovernanceMatter,
    MetadataRecord,
    Revision,
    TemplateId,
    TransitionCommand,
    Version,
)


class RecoveryPolicy(MetadataRecord):
    """Configure explicit synthetic owners and bounded recovery attempts."""

    execution_mode: Literal["synthetic"] = "synthetic"
    policy_ref: OpaqueReference
    scope_ref: OpaqueReference
    owner_refs: tuple[OpaqueReference, ...] = Field(min_length=1, max_length=32)
    maximum_attempts: Annotated[int, Field(strict=True, ge=1, le=10)]
    retry_delay_seconds: Annotated[int, Field(strict=True, ge=1, le=86400)]

    @model_validator(mode="after")
    def unique_owners(self) -> Self:
        """Reject ambiguous duplicate owner configuration."""
        if len(set(self.owner_refs)) != len(self.owner_refs):
            message = "duplicate recovery owner"
            raise ValueError(message)
        return self


class RecoveryRecord(MetadataRecord):
    """Retain opaque pointers and fixed metadata without the failed payload."""

    execution_mode: Literal["synthetic"] = "synthetic"
    matter_id: OpaqueReference
    scope_ref: OpaqueReference
    event_id: OpaqueReference
    replay_key: OpaqueReference
    template_id: TemplateId
    template_version: Version
    template_digest: Digest
    failed_command_digest: Digest
    command_record_ref: OpaqueReference
    policy_ref: OpaqueReference
    policy_digest: Digest
    error_code: Literal["transition_rejected"] = "transition_rejected"
    maximum_attempts: Annotated[int, Field(strict=True, ge=1, le=10)]
    retry_delay_seconds: Annotated[int, Field(strict=True, ge=1, le=86400)]
    attempt_count: Annotated[int, Field(strict=True, ge=0, le=10)] = 0
    revision: Revision = 0
    status: Literal["pending", "queued", "recovered"] = "pending"
    captured_at: AwareDatetime
    updated_at: AwareDatetime
    not_before: AwareDatetime | None = None
    recovered_at: AwareDatetime | None = None
    receipt_ref: OpaqueReference | None = None
    receipt_digest: Digest | None = None

    @model_validator(mode="after")
    def consistent_metadata(self) -> Self:
        """Reject contradictory imported bounds, chronology and receipt state."""
        valid = (
            self.attempt_count <= self.maximum_attempts
            and self.revision == self.attempt_count + int(self.status == "recovered")
            and self.updated_at >= self.captured_at
        )
        if self.status == "pending":
            valid = valid and self.attempt_count == 0 and self.not_before is None
        else:
            valid = valid and self.attempt_count > 0 and self.not_before is not None
        if self.not_before is not None:
            valid = valid and self.not_before >= self.captured_at + timedelta(
                seconds=self.retry_delay_seconds
            )
        receipt = bool(self.receipt_ref and self.receipt_digest and self.recovered_at)
        if self.status == "recovered":
            valid = (
                valid
                and receipt
                and self.recovered_at == self.updated_at
                and self.not_before is not None
                and self.updated_at >= self.not_before
            )
        else:
            valid = valid and all(
                item is None for item in (self.receipt_ref, self.receipt_digest, self.recovered_at)
            )
            if self.status == "queued":
                valid = valid and self.not_before == self.updated_at + timedelta(
                    seconds=self.retry_delay_seconds
                )
        if not valid:
            message = "inconsistent recovery metadata"
            raise ValueError(message)
        return self


def _digest(value: MetadataRecord) -> str:
    return hashlib.sha256(value.model_dump_json().encode()).hexdigest()


def _time(now: datetime) -> datetime:
    return TypeAdapter[datetime](AwareDatetime).validate_python(now).astimezone(UTC)


def capture_transition_failure(
    matter: GovernanceMatter,
    command: TransitionCommand,
    *,
    command_record_ref: str,
    policy: RecoveryPolicy,
    now: datetime,
) -> RecoveryRecord:
    """Capture a rejected synthetic command without retaining its actor or evidence."""
    now = _time(now)
    if matter.scope_ref != policy.scope_ref or command.actor_scope_ref != matter.scope_ref:
        message = "recovery scope differs from configured policy"
        raise ValueError(message)
    if command.occurred_at > now:
        message = "recovery capture chronology is invalid"
        raise ValueError(message)
    canonical = command.model_copy(update={"occurred_at": command.occurred_at.astimezone(UTC)})
    return RecoveryRecord(
        matter_id=matter.matter_id,
        scope_ref=matter.scope_ref,
        event_id=command.event_id,
        replay_key=command.replay_key,
        template_id=matter.template_id,
        template_version=matter.template_version,
        template_digest=matter.template_digest,
        failed_command_digest=_digest(canonical),
        command_record_ref=command_record_ref,
        policy_ref=policy.policy_ref,
        policy_digest=_digest(policy),
        maximum_attempts=policy.maximum_attempts,
        retry_delay_seconds=policy.retry_delay_seconds,
        captured_at=now,
        updated_at=now,
    )


def _authorize(record: RecoveryRecord, policy: RecoveryPolicy, actor_ref: str) -> None:
    if (
        record.scope_ref != policy.scope_ref
        or record.policy_ref != policy.policy_ref
        or record.policy_digest != _digest(policy)
        or record.maximum_attempts != policy.maximum_attempts
        or record.retry_delay_seconds != policy.retry_delay_seconds
        or actor_ref not in policy.owner_refs
    ):
        message = "recovery requires configured scope policy and owner"
        raise ValueError(message)


def schedule_retry(
    record: RecoveryRecord,
    *,
    policy: RecoveryPolicy,
    actor_ref: str,
    expected_revision: int,
    now: datetime,
) -> RecoveryRecord:
    """Schedule metadata for a future attempt; execute no canonical side effect."""
    expected_revision = TypeAdapter[int](Revision).validate_python(expected_revision)
    _authorize(record, policy, actor_ref)
    now = _time(now)
    if record.status == "recovered":
        message = "recovery record is terminal"
        raise ValueError(message)
    if expected_revision != record.revision:
        message = "stale recovery expected revision"
        raise ValueError(message)
    if now < record.updated_at or (record.not_before and now < record.not_before):
        message = "retry delay or chronology is invalid"
        raise ValueError(message)
    if record.attempt_count >= record.maximum_attempts:
        message = "recovery maximum attempts exhausted"
        raise ValueError(message)
    return RecoveryRecord.model_validate(
        {
            **record.model_dump(),
            "status": "queued",
            "revision": record.revision + 1,
            "attempt_count": record.attempt_count + 1,
            "updated_at": now,
            "not_before": now + timedelta(seconds=record.retry_delay_seconds),
        }
    )


def record_recovery(  # noqa: PLR0913
    record: RecoveryRecord,
    canonical: GovernanceMatter,
    *,
    policy: RecoveryPolicy,
    actor_ref: str,
    expected_revision: int,
    receipt_ref: str,
    now: datetime,
) -> RecoveryRecord:
    """Require exact canonical applied history before recording a recovery receipt."""
    expected_revision = TypeAdapter[int](Revision).validate_python(expected_revision)
    _authorize(record, policy, actor_ref)
    now = _time(now)
    canonical = GovernanceMatter.model_validate(canonical.model_dump())
    if (
        canonical.matter_id != record.matter_id
        or canonical.scope_ref != record.scope_ref
        or canonical.template_id != record.template_id
        or canonical.template_version != record.template_version
        or canonical.template_digest != record.template_digest
        or not any(
            event.event_id == record.event_id
            and event.replay_key == record.replay_key
            and event.command_digest == record.failed_command_digest
            and event.occurred_at <= now
            for event in canonical.history
        )
    ):
        message = "recovery requires exact canonical applied event"
        raise ValueError(message)
    receipt_ref = TypeAdapter[str](OpaqueReference).validate_python(receipt_ref)
    receipt_digest = hashlib.sha256(
        repr((actor_ref, expected_revision, receipt_ref, now.isoformat())).encode()
    ).hexdigest()
    if record.status == "recovered":
        if record.receipt_digest == receipt_digest:
            return record
        message = "recovery receipt collision"
        raise ValueError(message)
    if expected_revision != record.revision:
        message = "stale recovery expected revision"
        raise ValueError(message)
    if record.status != "queued" or record.not_before is None or now < record.not_before:
        message = "recovery requires scheduled retry delay"
        raise ValueError(message)
    return RecoveryRecord.model_validate(
        {
            **record.model_dump(),
            "status": "recovered",
            "revision": record.revision + 1,
            "updated_at": now,
            "recovered_at": now,
            "receipt_ref": receipt_ref,
            "receipt_digest": receipt_digest,
        }
    )
