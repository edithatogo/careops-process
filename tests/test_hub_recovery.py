# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic recoverable dead letters without failed command or sensitive error payloads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from careops_process.hub_domain import apply_transition
from careops_process.hub_recovery import (
    RecoveryPolicy,
    capture_transition_failure,
    record_recovery,
    schedule_retry,
)
from tests.test_hub_domain import command, matter, template

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def policy() -> RecoveryPolicy:
    """Declare an explicit synthetic recovery owner and bounded retry policy."""
    return RecoveryPolicy(
        policy_ref="synthetic-recovery-policy",
        scope_ref="synthetic-scope",
        owner_refs=("synthetic-maintainer",),
        maximum_attempts=2,
        retry_delay_seconds=60,
    )


def test_dead_letter_contains_only_opaque_references_and_fixed_error_code() -> None:
    """A failed private error and command body never enter the recoverable record."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    rendered = failed.model_dump_json()
    assert failed.status == "pending"
    assert failed.error_code == "transition_rejected"
    assert "actor_ref" not in rendered
    assert "evidence_ref" not in rendered
    assert "synthetic-command-record" in rendered
    assert failed.failed_command_digest


def test_retry_requires_scope_owner_revision_and_delay() -> None:
    """Only an authorised recovery owner can schedule the exact letter's bounded retry."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    for actor_ref, revision in (("synthetic-outsider", 0), ("synthetic-maintainer", 1)):
        with pytest.raises(ValueError, match=r"owner|revision"):
            schedule_retry(
                failed, policy=policy(), actor_ref=actor_ref, expected_revision=revision, now=NOW
            )
    queued = schedule_retry(
        failed, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=0, now=NOW
    )
    assert queued.attempt_count == 1
    assert queued.not_before == NOW + timedelta(seconds=60)
    assert failed.status == "pending"


def test_recovery_needs_actual_canonical_applied_event_not_success_boolean() -> None:
    """A provider success signal cannot mark an unapplied governance transition recovered."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    queued = schedule_retry(
        failed, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=0, now=NOW
    )
    with pytest.raises(ValueError, match="canonical"):
        record_recovery(
            queued,
            matter(),
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=1,
            receipt_ref="synthetic-receipt",
            now=NOW + timedelta(minutes=1),
        )
    applied = apply_transition(matter(), command(), template=template(), now=NOW)
    recovered = record_recovery(
        queued,
        applied,
        policy=policy(),
        actor_ref="synthetic-maintainer",
        expected_revision=1,
        receipt_ref="synthetic-receipt",
        now=NOW + timedelta(minutes=1),
    )
    assert recovered.status == "recovered"
    assert applied.state == "submitted"


def test_before_delay_and_cross_scope_recovery_fail_closed() -> None:
    """Recovery cannot run early or use a canonical event belonging to another matter."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    queued = schedule_retry(
        failed, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=0, now=NOW
    )
    applied = apply_transition(matter(), command(), template=template(), now=NOW)
    with pytest.raises(ValueError, match="delay"):
        record_recovery(
            queued,
            applied,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=1,
            receipt_ref="synthetic-receipt",
            now=NOW,
        )
    changed = applied.model_copy(update={"matter_id": "synthetic-another-matter"})
    with pytest.raises(ValueError, match="canonical"):
        record_recovery(
            queued,
            changed,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=1,
            receipt_ref="synthetic-receipt",
            now=NOW + timedelta(minutes=1),
        )


def test_recovered_letter_cannot_schedule_another_attempt() -> None:
    """A terminal recovered letter cannot repeat the canonical side effect."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    queued = schedule_retry(
        failed, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=0, now=NOW
    )
    applied = apply_transition(matter(), command(), template=template(), now=NOW)
    recovered = record_recovery(
        queued,
        applied,
        policy=policy(),
        actor_ref="synthetic-maintainer",
        expected_revision=1,
        receipt_ref="synthetic-receipt",
        now=NOW + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="terminal"):
        schedule_retry(
            recovered,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=2,
            now=NOW + timedelta(minutes=2),
        )


def test_recovery_models_reject_private_diagnostics_and_invalid_retry_bounds() -> None:
    """No free-text error, token or command payload can be stored in a dead letter."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    with pytest.raises(ValidationError):
        type(failed).model_validate(
            {**failed.model_dump(), "error_message": "synthetic-private-diagnostic"}
        )
    with pytest.raises(ValidationError):
        RecoveryPolicy.model_validate({**policy().model_dump(), "maximum_attempts": 0})


def test_exhaustion_policy_conflicts_and_chronology() -> None:
    """Attempts stay bounded and policy replacement cannot change retry authority."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    with pytest.raises(ValueError, match="chronology"):
        schedule_retry(
            failed,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=0,
            now=NOW - timedelta(seconds=1),
        )
    for field, value in (
        ("scope_ref", "other-scope"),
        ("policy_ref", "other-policy"),
        ("maximum_attempts", 3),
    ):
        changed = RecoveryPolicy.model_validate({**policy().model_dump(), field: value})
        with pytest.raises(ValueError, match="policy"):
            schedule_retry(
                failed,
                policy=changed,
                actor_ref="synthetic-maintainer",
                expected_revision=0,
                now=NOW,
            )
    queued = schedule_retry(
        failed, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=0, now=NOW
    )
    with pytest.raises(ValueError, match="delay"):
        schedule_retry(
            queued, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=1, now=NOW
        )
    second = schedule_retry(
        queued,
        policy=policy(),
        actor_ref="synthetic-maintainer",
        expected_revision=1,
        now=NOW + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="exhausted"):
        schedule_retry(
            second,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=2,
            now=NOW + timedelta(minutes=2),
        )


def test_receipt_replay_collision_and_digest_agreement() -> None:
    """Canonical normalization matches applied history and receipts replay exactly."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    applied = apply_transition(matter(), command(), template=template(), now=NOW)
    assert failed.failed_command_digest == applied.history[0].command_digest
    queued = schedule_retry(
        failed, policy=policy(), actor_ref="synthetic-maintainer", expected_revision=0, now=NOW
    )
    recovered = record_recovery(
        queued,
        applied,
        policy=policy(),
        actor_ref="synthetic-maintainer",
        expected_revision=1,
        receipt_ref="synthetic-receipt",
        now=NOW + timedelta(minutes=1),
    )
    assert (
        record_recovery(
            recovered,
            applied,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=1,
            receipt_ref="synthetic-receipt",
            now=NOW + timedelta(minutes=1),
        )
        is recovered
    )
    with pytest.raises(ValueError, match="collision"):
        record_recovery(
            recovered,
            applied,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=1,
            receipt_ref="different-receipt",
            now=NOW + timedelta(minutes=1),
        )
    different = apply_transition(
        matter(), command(evidence_ref="changed-evidence"), template=template(), now=NOW
    )
    with pytest.raises(ValueError, match="canonical"):
        record_recovery(
            queued,
            different,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=1,
            receipt_ref="synthetic-receipt",
            now=NOW + timedelta(minutes=1),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"attempt_count": 3},
        {"status": "recovered"},
        {"revision": 2},
        {"receipt_ref": "forged-receipt"},
        {"updated_at": NOW - timedelta(seconds=1)},
    ],
)
def test_imported_recovery_metadata_cannot_contradict_state(changes: dict[str, object]) -> None:
    """Imported records reject invalid chronology, counts and incomplete receipts."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    with pytest.raises(ValidationError):
        type(failed).model_validate({**failed.model_dump(), **changes})


def test_utc_normalization_and_capture_boundaries() -> None:
    """Equivalent time zones fingerprint the actual canonical command consistently."""
    changed_command = command(
        occurred_at=command().occurred_at.astimezone(timezone(timedelta(hours=10)))
    )
    failed = capture_transition_failure(
        matter(),
        changed_command,
        command_record_ref="synthetic-command-record",
        policy=policy(),
        now=NOW,
    )
    applied = apply_transition(matter(), changed_command, template=template(), now=NOW)
    assert failed.failed_command_digest == applied.history[0].command_digest
    with pytest.raises(ValueError, match="scope"):
        capture_transition_failure(
            matter(),
            command(actor_scope_ref="other-scope"),
            command_record_ref="synthetic-command-record",
            policy=policy(),
            now=NOW,
        )
    with pytest.raises(ValidationError):
        schedule_retry(
            failed,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=False,
            now=NOW,
        )
    with pytest.raises(ValidationError):
        schedule_retry(
            failed,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=0,
            now=NOW.replace(tzinfo=None),
        )


@pytest.mark.parametrize("changes", [{"maximum_attempts": 10}, {"retry_delay_seconds": 1}])
def test_imported_retry_limits_must_match_verified_policy(changes: dict[str, int]) -> None:
    """Imported retry metadata cannot weaken the fingerprinted policy limits."""
    failed = capture_transition_failure(
        matter(), command(), command_record_ref="synthetic-command-record", policy=policy(), now=NOW
    )
    imported = type(failed).model_validate({**failed.model_dump(), **changes})
    with pytest.raises(ValueError, match="policy"):
        schedule_retry(
            imported,
            policy=policy(),
            actor_ref="synthetic-maintainer",
            expected_revision=0,
            now=NOW,
        )
