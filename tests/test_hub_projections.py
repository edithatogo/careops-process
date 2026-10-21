# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic approval and action projection boundaries."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from careops_process.hub_domain import ActionRecord, AuthorityRecord
from careops_process.hub_projections import (
    ApprovalEnvelope,
    ApprovalEvent,
    ProjectionError,
    apply_approval_event,
    create_planner_projection,
    reconcile_planner_projection,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def envelope() -> ApprovalEnvelope:
    """Build a controlled synthetic approval request."""
    return ApprovalEnvelope(
        request_ref="request",
        matter_ref="matter",
        assignee_ref="user",
        initial_assignee_ref="user",
        authority=AuthorityRecord(authority_source_ref="policy", decision_owner_ref="owner"),
        workflow_version="1.0.0",
        expires_at=NOW + timedelta(days=1),
    )


def event(**changes: object) -> ApprovalEvent:
    """Build a typed event without narrative."""
    data: dict[str, object] = {
        "event_ref": "event",
        "replay_ref": "event",
        "request_ref": "request",
        "matter_ref": "matter",
        "authority": envelope().authority,
        "kind": "response",
        "actor_ref": "user",
        "workflow_version": "1.0.0",
        "expected_revision": 0,
        "occurred_at": NOW,
        "response_ref": "response",
        "outcome": "approval",
    }
    data.update(changes)
    if "event_ref" in changes and "replay_ref" not in changes:
        data["replay_ref"] = changes["event_ref"]
    return ApprovalEvent.model_validate(data)


def test_provisional_and_replay() -> None:
    """Individual responses retain provenance and cannot ratify."""
    before = envelope()
    command = event()
    after = apply_approval_event(before, command, now=NOW)
    assert after.provisional_response == command
    assert after.collective_decision is False
    assert after.authority == before.authority
    assert apply_approval_event(after, command, now=NOW) is after
    assert before.revision == 0
    with pytest.raises(ProjectionError, match="replay_conflict"):
        apply_approval_event(after, event(outcome="decline"), now=NOW)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"workflow_version": "2.0.0"}, "stale_workflow"),
        ({"actor_ref": "other"}, "identity_mismatch"),
        ({"expected_revision": 1}, "stale_revision"),
    ],
)
def test_approval_guards(changes: dict[str, object], code: str) -> None:
    """Reject stale and unauthorised responses."""
    with pytest.raises(ProjectionError, match=code):
        apply_approval_event(envelope(), event(**changes), now=NOW)


@pytest.mark.parametrize(
    ("kind", "status"),
    [
        ("cancel", "cancelled"),
        ("timeout", "timed_out"),
        ("reassign", "pending"),
        ("response", "rejected"),
    ],
)
def test_approval_lifecycle(kind: str, status: str) -> None:
    """Handle lifecycle events without canonical mutations."""
    command = event(
        kind=kind,
        outcome="decline" if kind == "response" else None,
        response_ref="response" if kind == "response" else None,
        replacement_ref="replacement" if kind == "reassign" else None,
        actor_ref="owner" if kind != "response" else "user",
        occurred_at=NOW + timedelta(days=1) if kind == "timeout" else NOW,
    )
    result = apply_approval_event(envelope(), command, now=command.occurred_at)
    assert result.status == status
    if kind == "reassign":
        assert result.assignee_ref == "replacement"


@pytest.mark.parametrize(
    ("flag", "code"),
    [("user_available", "user_unavailable"), ("connection_available", "connection_unavailable")],
)
def test_availability(flag: str, code: str) -> None:
    """Unavailable resources produce safe recovery metadata."""
    with pytest.raises(ProjectionError, match=code) as error:
        apply_approval_event(envelope(), event(), now=NOW, **{flag: False})
    assert error.value.recovery == "manual_reconcile"


def action(**changes: object) -> ActionRecord:
    """Build a canonical action fixture."""
    data: dict[str, object] = {"action_id": "action", "owner_ref": "owner", "due_at": NOW}
    data.update(changes)
    return ActionRecord.model_validate(data)


def test_planner_reconcile_is_signal_only() -> None:
    """Completion stays a projection signal until canonical closure evidence exists."""
    original = action()
    projection = create_planner_projection("matter", original, canonical_revision=0, now=NOW)
    assert projection.title == "matter / action"
    assert (
        create_planner_projection(
            "matter", original, canonical_revision=0, now=NOW, existing=projection
        )
        is projection
    )
    changed = action(owner_ref="newowner", due_at=NOW + timedelta(days=2))
    updated = reconcile_planner_projection(
        projection,
        changed,
        matter_ref="matter",
        canonical_revision=1,
        observed_at=NOW + timedelta(hours=1),
        now=NOW + timedelta(hours=1),
        task_state="present",
        task_completed=True,
    )
    assert updated.owner_ref == "newowner"
    assert updated.completion_signal is True
    assert updated.canonical_completed is False
    assert original.state == "assigned"
    completed = action(state="completed", closure_evidence_ref="closure")
    assert reconcile_planner_projection(
        updated,
        completed,
        matter_ref="matter",
        canonical_revision=2,
        observed_at=NOW + timedelta(hours=2),
        now=NOW + timedelta(hours=2),
        task_state="present",
        task_completed=True,
    ).canonical_completed


@pytest.mark.parametrize("state", ["missing", "deleted", "duplicate", "inaccessible"])
def test_planner_resource_failures(state: str) -> None:
    """Resource failures require explicit reconciliation."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ProjectionError, match="task_" + state):
        reconcile_planner_projection(
            projection,
            action(),
            matter_ref="matter",
            canonical_revision=1,
            observed_at=NOW,
            now=NOW,
            task_state=state,
            task_completed=False,
        )


def test_planner_guards_and_privacy() -> None:
    """Reject unassigned creation, stale writes and arbitrary payloads."""
    with pytest.raises(ProjectionError, match="action_not_assigned"):
        create_planner_projection(
            "matter", action(state="in_progress"), canonical_revision=0, now=NOW
        )
    projection = create_planner_projection("matter", action(), canonical_revision=2, now=NOW)
    with pytest.raises(ProjectionError, match="stale_revision"):
        reconcile_planner_projection(
            projection,
            action(),
            matter_ref="matter",
            canonical_revision=1,
            observed_at=NOW,
            now=NOW,
            task_state="present",
            task_completed=False,
        )
    with pytest.raises(ProjectionError, match="invalid_time"):
        reconcile_planner_projection(
            projection,
            action(),
            matter_ref="matter",
            canonical_revision=3,
            observed_at=NOW - timedelta(hours=1),
            now=NOW,
            task_state="present",
            task_completed=False,
        )
    with pytest.raises(ValidationError):
        ApprovalEnvelope.model_validate({**envelope().model_dump(), "comments": "patient"})
    with pytest.raises(ValidationError):
        ApprovalEnvelope.model_validate({**envelope().model_dump(), "execution_mode": "live"})


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"response_ref": None}, "response_invalid"),
        ({"outcome": None}, "response_invalid"),
        ({"occurred_at": NOW + timedelta(days=2)}, "invalid_time"),
    ],
)
def test_invalid_response(changes: dict[str, object], code: str) -> None:
    """Reject incomplete or future response records."""
    with pytest.raises(ProjectionError, match=code):
        apply_approval_event(envelope(), event(**changes), now=NOW)


def test_terminal_and_reassignment_authority() -> None:
    """A new response cannot replace a terminal response or bypass reassignment authority."""
    responded = apply_approval_event(envelope(), event(), now=NOW)
    with pytest.raises(ProjectionError, match="request_terminal"):
        apply_approval_event(responded, event(event_ref="next", expected_revision=1), now=NOW)
    reassigned = apply_approval_event(
        envelope(),
        event(
            kind="reassign",
            actor_ref="owner",
            outcome=None,
            response_ref=None,
            replacement_ref="replacement",
        ),
        now=NOW,
    )
    with pytest.raises(ProjectionError, match="identity_mismatch"):
        apply_approval_event(reassigned, event(event_ref="next", expected_revision=1), now=NOW)
    with pytest.raises(ProjectionError, match="timeout_not_due"):
        apply_approval_event(
            envelope(),
            event(kind="timeout", actor_ref="owner", outcome=None, response_ref=None),
            now=NOW,
        )


def test_opaque_refs_and_frozen_records() -> None:
    """Reject narrative identifiers and mutation at all schema boundaries."""
    with pytest.raises(ValidationError):
        ApprovalEvent.model_validate({**event().model_dump(), "actor_ref": "Patient narrative"})
    with pytest.raises(ValidationError):
        envelope().assignee_ref = "other"
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ValidationError):
        type(projection).model_validate({**projection.model_dump(), "description": "private"})


def test_equal_time_conflicting_planner_signal() -> None:
    """Equal timestamps cannot replace a previously reconciled observation."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ProjectionError, match="replay_conflict"):
        reconcile_planner_projection(
            projection,
            action(),
            matter_ref="matter",
            canonical_revision=0,
            observed_at=NOW,
            now=NOW,
            task_state="present",
            task_completed=True,
        )


@pytest.mark.parametrize("field", ["request_ref", "matter_ref", "authority"])
def test_approval_event_cannot_cross_context(field: str) -> None:
    """A response is bound to its immutable request, matter and authority."""
    data = envelope().model_dump()
    data[field] = (
        "other"
        if field != "authority"
        else AuthorityRecord(authority_source_ref="otherpolicy", decision_owner_ref="owner")
    )
    other = ApprovalEnvelope.model_validate(data)
    with pytest.raises(ProjectionError, match="projection_mismatch"):
        apply_approval_event(other, event(), now=NOW)


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "pending", "provisional_response": None},
        {"revision": 100},
        {"assignee_ref": "other"},
        {"authority": {"authority_source_ref": "other", "decision_owner_ref": "owner"}},
    ],
)
def test_envelope_rejects_contradictory_deserialization(changes: dict[str, object]) -> None:
    """Persisted history binds all material approval state."""
    responded = apply_approval_event(envelope(), event(), now=NOW)
    with pytest.raises(ValidationError):
        ApprovalEnvelope.model_validate({**responded.model_dump(), **changes})


def test_planner_cannot_cross_matter_context() -> None:
    """Same action identifier in another matter cannot overwrite a task projection."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ProjectionError, match="projection_mismatch"):
        reconcile_planner_projection(
            projection,
            action(owner_ref="other"),
            matter_ref="other",
            canonical_revision=1,
            observed_at=NOW,
            now=NOW,
            task_state="present",
            task_completed=False,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"owner_ref": "other"},
        {"due_at": NOW + timedelta(days=1)},
        {"closure_evidence_ref": "evidence"},
        {"planner_projection_ref": "task"},
    ],
)
def test_planner_creation_replay_requires_exact_action(changes: dict[str, object]) -> None:
    """Stable identifiers do not turn changed canonical content into an exact replay."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ProjectionError, match="replay_conflict"):
        create_planner_projection(
            "matter", action(**changes), canonical_revision=0, now=NOW, existing=projection
        )


def test_planner_creation_replay_requires_exact_revision() -> None:
    """New canonical revisions use reconciliation explicitly."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ProjectionError, match="replay_conflict"):
        create_planner_projection(
            "matter", action(), canonical_revision=1, now=NOW, existing=projection
        )


@pytest.mark.parametrize("change", ["duplicate", "terminal", "version", "response", "initial"])
def test_approval_history_rejects_corruption(change: str) -> None:
    """Replay identities, terminality and material historical fields survive deserialization."""
    responded = apply_approval_event(envelope(), event(), now=NOW)
    data = responded.model_dump()
    if change in {"duplicate", "terminal"}:
        second = event(
            event_ref="event" if change == "duplicate" else "second", expected_revision=1
        )
        data.update(history=(*responded.history, second), revision=2)
    elif change == "version":
        data["workflow_version"] = "2.0.0"
    elif change == "response":
        data["provisional_response"] = None
    else:
        data["initial_assignee_ref"] = "other"
    with pytest.raises(ValidationError):
        ApprovalEnvelope.model_validate(data)


def test_planner_same_revision_full_content_guard_and_cancellation() -> None:
    """Same-revision evidence changes conflict and cancellation is preserved explicitly."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    with pytest.raises(ProjectionError, match="stale_revision"):
        reconcile_planner_projection(
            projection,
            action(closure_evidence_ref="new"),
            matter_ref="matter",
            canonical_revision=0,
            observed_at=NOW,
            now=NOW,
            task_state="present",
            task_completed=False,
        )
    cancelled = reconcile_planner_projection(
        projection,
        action(state="cancelled"),
        matter_ref="matter",
        canonical_revision=1,
        observed_at=NOW,
        now=NOW,
        task_state="present",
        task_completed=False,
    )
    assert cancelled.canonical_action.state == "cancelled"
    assert not cancelled.canonical_completed


def test_planner_deserialization_binds_snapshot_and_stable_key() -> None:
    """Projection fields cannot contradict the full canonical action snapshot."""
    projection = create_planner_projection("matter", action(), canonical_revision=0, now=NOW)
    for changes in (
        {"owner_ref": "other"},
        {"projection_key": "wrong"},
        {"canonical_completed": True},
        {"action_ref": "other"},
    ):
        with pytest.raises(ValidationError):
            type(projection).model_validate({**projection.model_dump(), **changes})
