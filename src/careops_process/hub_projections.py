# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Bounded synthetic projections; no persistence, provider calls or canonical writes.

Approval responses are provisional input to the canonical collective evaluator.
Planner completion is an observation, never authority to close a matter or action.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Literal, Self

from pydantic import AwareDatetime, StrictBool, model_validator  # Runtime schema.

from careops_process.hub_capabilities import OpaqueReference  # noqa: TC001 # Runtime schema.
from careops_process.hub_domain import (
    ActionRecord,
    AuthorityRecord,
    MetadataRecord,
    Outcome,
    Revision,
    Version,
)

if TYPE_CHECKING:
    from datetime import datetime


ErrorCode = Literal[
    "replay_conflict",
    "stale_workflow",
    "identity_mismatch",
    "stale_revision",
    "invalid_time",
    "user_unavailable",
    "connection_unavailable",
    "request_terminal",
    "response_invalid",
    "reassignment_invalid",
    "timeout_not_due",
    "action_not_assigned",
    "projection_mismatch",
    "task_missing",
    "task_deleted",
    "task_duplicate",
    "task_inaccessible",
]


class ProjectionError(ValueError):
    """Fixed safe codes with no provider exception body or sensitive payload."""

    def __init__(self, code: ErrorCode) -> None:
        """Expose a bounded manual recovery route."""
        self.code = code
        self.recovery: Literal["manual_reconcile"] = "manual_reconcile"
        super().__init__(code)


class ApprovalEvent(MetadataRecord):
    """Preserve response identity and protected response reference without comments."""

    execution_mode: Literal["synthetic"] = "synthetic"
    event_ref: OpaqueReference
    replay_ref: OpaqueReference
    request_ref: OpaqueReference
    matter_ref: OpaqueReference
    authority: AuthorityRecord
    kind: Literal["response", "cancel", "timeout", "reassign"]
    actor_ref: OpaqueReference
    workflow_version: Version
    expected_revision: Revision
    occurred_at: AwareDatetime
    response_ref: OpaqueReference | None = None
    outcome: Outcome | None = None
    replacement_ref: OpaqueReference | None = None


class ApprovalEnvelope(MetadataRecord):
    """Immutable orchestration state independent of canonical decision/ratification."""

    execution_mode: Literal["synthetic"] = "synthetic"
    request_ref: OpaqueReference
    matter_ref: OpaqueReference
    assignee_ref: OpaqueReference
    initial_assignee_ref: OpaqueReference
    authority: AuthorityRecord
    workflow_version: Version
    expires_at: AwareDatetime
    revision: Revision = 0
    status: Literal["pending", "responded", "rejected", "cancelled", "timed_out"] = "pending"
    provisional_response: ApprovalEvent | None = None
    collective_decision: Literal[False] = False
    history: tuple[ApprovalEvent, ...] = ()

    @model_validator(mode="after")
    def validate_history(self) -> Self:
        """Reconstruct state from contiguous, context-bound history on every load."""
        status = "pending"
        assignee = self.initial_assignee_ref
        response = None
        ids: set[str] = set()
        replays: set[str] = set()
        previous = None
        valid = self.revision == len(self.history)
        for revision, event in enumerate(self.history):
            valid = valid and (
                status == "pending"
                and event.expected_revision == revision
                and event.event_ref not in ids
                and event.replay_ref not in replays
                and event.request_ref == self.request_ref
                and event.matter_ref == self.matter_ref
                and event.authority == self.authority
                and event.workflow_version == self.workflow_version
                and (previous is None or event.occurred_at >= previous)
                and event.actor_ref
                == (assignee if event.kind == "response" else self.authority.decision_owner_ref)
            )
            ids.add(event.event_ref)
            replays.add(event.replay_ref)
            previous = event.occurred_at
            if event.kind == "response":
                valid = valid and (
                    event.outcome is not None
                    and event.response_ref is not None
                    and event.replacement_ref is None
                    and event.occurred_at < self.expires_at
                )
                status = "rejected" if event.outcome == "decline" else "responded"
                response = event
            else:
                valid = valid and event.outcome is None and event.response_ref is None
                if event.kind == "reassign":
                    valid = (
                        valid
                        and event.replacement_ref is not None
                        and event.replacement_ref != assignee
                    )
                    if event.replacement_ref is not None:
                        assignee = event.replacement_ref
                else:
                    valid = valid and event.replacement_ref is None
                    if event.kind == "timeout":
                        valid = valid and event.occurred_at >= self.expires_at
                        status = "timed_out"
                    else:
                        status = "cancelled"
        if not (
            valid
            and status == self.status
            and assignee == self.assignee_ref
            and response == self.provisional_response
        ):
            message = "inconsistent_approval_history"
            raise ValueError(message)
        return self


def _time(value: datetime, now: datetime, previous: datetime | None = None) -> None:
    if (
        now.tzinfo is None
        or now.utcoffset() is None
        or value > now
        or (previous is not None and value < previous)
    ):
        msg = "invalid_time"
        raise ProjectionError(msg)


def apply_approval_event(  # noqa: C901, PLR0912, PLR0915
    request: ApprovalEnvelope,
    event: ApprovalEvent,
    *,
    now: datetime,
    user_available: bool = True,
    connection_available: bool = True,
) -> ApprovalEnvelope:
    """Apply a synthetic event, preserving identical replay and authority provenance."""
    if (
        event.request_ref != request.request_ref
        or event.matter_ref != request.matter_ref
        or event.authority != request.authority
    ):
        code: ErrorCode = "projection_mismatch"
        raise ProjectionError(code)
    for recorded in request.history:
        if recorded.event_ref == event.event_ref or recorded.replay_ref == event.replay_ref:
            if recorded == event:
                return request
            msg = "replay_conflict"
            raise ProjectionError(msg)
    if event.workflow_version != request.workflow_version:
        msg = "stale_workflow"
        raise ProjectionError(msg)
    if event.expected_revision != request.revision:
        msg = "stale_revision"
        raise ProjectionError(msg)
    _time(event.occurred_at, now, request.history[-1].occurred_at if request.history else None)
    if not connection_available:
        msg = "connection_unavailable"
        raise ProjectionError(msg)
    if not user_available:
        msg = "user_unavailable"
        raise ProjectionError(msg)
    if request.status != "pending":
        msg = "request_terminal"
        raise ProjectionError(msg)
    expected_actor = (
        request.assignee_ref if event.kind == "response" else request.authority.decision_owner_ref
    )
    if event.actor_ref != expected_actor:
        msg = "identity_mismatch"
        raise ProjectionError(msg)
    status = request.status
    assignee = request.assignee_ref
    response = request.provisional_response
    if event.kind == "response":
        if event.outcome is None or event.response_ref is None or event.replacement_ref is not None:
            msg = "response_invalid"
            raise ProjectionError(msg)
        if event.occurred_at >= request.expires_at:
            msg = "request_terminal"
            raise ProjectionError(msg)
        status = "rejected" if event.outcome == "decline" else "responded"
        response = event
    elif event.response_ref is not None or event.outcome is not None:
        msg = "response_invalid"
        raise ProjectionError(msg)
    elif event.kind == "reassign":
        if not event.replacement_ref or event.replacement_ref == assignee:
            msg = "reassignment_invalid"
            raise ProjectionError(msg)
        assignee = event.replacement_ref
    elif event.kind == "timeout":
        if event.occurred_at < request.expires_at:
            msg = "timeout_not_due"
            raise ProjectionError(msg)
        status = "timed_out"
    else:
        status = "cancelled"
    return ApprovalEnvelope.model_validate(
        {
            **request.model_dump(),
            "status": status,
            "assignee_ref": assignee,
            "provisional_response": response,
            "revision": request.revision + 1,
            "history": (*request.history, event),
        }
    )


class PlannerProjection(MetadataRecord):
    """Only minimised action metadata and synthetic task-observation state."""

    execution_mode: Literal["synthetic"] = "synthetic"
    projection_key: OpaqueReference
    matter_ref: OpaqueReference
    action_ref: OpaqueReference
    owner_ref: OpaqueReference
    due_at: AwareDatetime
    canonical_revision: Revision
    canonical_action: ActionRecord
    observed_at: AwareDatetime
    completion_signal: StrictBool = False
    canonical_completed: StrictBool = False

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        """Bind projected metadata and stable identity to its canonical snapshot."""
        key = (
            "planner_"
            + hashlib.sha256(
                f"{self.matter_ref}:{self.canonical_action.action_id}".encode()
            ).hexdigest()
        )
        if (
            self.projection_key != key
            or self.action_ref != self.canonical_action.action_id
            or self.owner_ref != self.canonical_action.owner_ref
            or self.due_at != self.canonical_action.due_at
            or self.canonical_completed
            != (
                self.canonical_action.state == "completed"
                and self.canonical_action.closure_evidence_ref is not None
            )
        ):
            message = "inconsistent_planner_snapshot"
            raise ValueError(message)
        return self

    @property
    def title(self) -> str:
        """Derive the title entirely from opaque canonical identifiers."""
        return f"{self.matter_ref} / {self.action_ref}"


def create_planner_projection(
    matter_ref: str,
    action: ActionRecord,
    *,
    canonical_revision: int,
    now: datetime,
    existing: PlannerProjection | None = None,
) -> PlannerProjection:
    """Create one stable projection intent only for an assigned canonical action."""
    if action.state != "assigned":
        msg = "action_not_assigned"
        raise ProjectionError(msg)
    _time(now, now)
    key = "planner_" + hashlib.sha256(f"{matter_ref}:{action.action_id}".encode()).hexdigest()
    if existing is not None:
        if (
            existing.projection_key != key
            or existing.matter_ref != matter_ref
            or existing.action_ref != action.action_id
        ):
            msg = "projection_mismatch"
            raise ProjectionError(msg)
        if existing.canonical_action != action or existing.canonical_revision != canonical_revision:
            code: ErrorCode = "replay_conflict"
            raise ProjectionError(code)
        return existing
    return PlannerProjection(
        projection_key=key,
        matter_ref=matter_ref,
        action_ref=action.action_id,
        owner_ref=action.owner_ref,
        due_at=action.due_at,
        canonical_revision=canonical_revision,
        canonical_action=action,
        observed_at=now,
    )


def reconcile_planner_projection(  # noqa: PLR0913
    projection: PlannerProjection,
    action: ActionRecord,
    *,
    matter_ref: str,
    canonical_revision: int,
    observed_at: datetime,
    now: datetime,
    task_state: str,
    task_completed: bool,
) -> PlannerProjection:
    """Reconcile owner/due and completion signals without returning canonical writes."""
    key = "planner_" + hashlib.sha256(f"{matter_ref}:{action.action_id}".encode()).hexdigest()
    if (
        matter_ref != projection.matter_ref
        or action.action_id != projection.action_ref
        or projection.projection_key != key
    ):
        msg = "projection_mismatch"
        raise ProjectionError(msg)
    if canonical_revision < projection.canonical_revision:
        msg = "stale_revision"
        raise ProjectionError(msg)
    _time(observed_at, now, projection.observed_at)
    if observed_at == projection.observed_at and task_completed != projection.completion_signal:
        code: ErrorCode = "replay_conflict"
        raise ProjectionError(code)
    errors: dict[str, ErrorCode] = {
        "missing": "task_missing",
        "deleted": "task_deleted",
        "duplicate": "task_duplicate",
        "inaccessible": "task_inaccessible",
    }
    if task_state != "present":
        raise ProjectionError(errors.get(task_state, "task_inaccessible"))
    if canonical_revision == projection.canonical_revision and (
        action != projection.canonical_action
    ):
        msg = "stale_revision"
        raise ProjectionError(msg)
    return PlannerProjection.model_validate(
        {
            **projection.model_dump(),
            "owner_ref": action.owner_ref,
            "due_at": action.due_at,
            "canonical_revision": canonical_revision,
            "canonical_action": action,
            "observed_at": observed_at,
            "completion_signal": task_completed,
            "canonical_completed": action.state == "completed"
            and action.closure_evidence_ref is not None,
        }
    )
