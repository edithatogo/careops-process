"""Synthetic collective-decision rules without hard-coded IHG meeting conventions.

References and participant context must come from a controlled authority record.
Evaluation is not authentication, approval of policy or permission to deploy.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from careops_process.hub_capabilities import (
    OpaqueReference,  # noqa: TC001 # Runtime Pydantic schema.
)
from careops_process.hub_domain import (  # Runtime Pydantic schema.
    GovernanceMatter,
    MetadataRecord,
    Outcome,
    Revision,
    State,
    TransitionCommand,
    Version,
    WorkflowTemplate,
    apply_transition,
)

if TYPE_CHECKING:
    from datetime import datetime


class DecisionRule(MetadataRecord):
    """Require explicit quorum, voting, authority, chair and ratification configuration."""

    execution_mode: Literal["synthetic"] = "synthetic"
    rule_id: OpaqueReference
    scope_ref: OpaqueReference
    authority_source_ref: OpaqueReference
    approved_policy_ref: OpaqueReference
    template_version: Version
    eligible_principals: tuple[OpaqueReference, ...]
    minimum_participants: Annotated[int, Field(strict=True, ge=1)]
    method: Literal["quorum", "majority", "unanimous"]
    majority_denominator: Literal["eligible", "participating"]
    decision_outcome: Literal["approval", "endorsement", "noting", "ratification"]
    chair_ref: OpaqueReference
    conflict_policy: Literal["exclude_from_quorum", "hold_decision"]
    ratification_required: StrictBool

    @model_validator(mode="after")
    def validate_participation(self) -> Self:
        """Reject duplicated seats and impossible quorum requirements."""
        if len(set(self.eligible_principals)) != len(
            self.eligible_principals
        ) or self.minimum_participants > len(self.eligible_principals):
            message = "quorum must fit distinct eligible participants"
            raise ValueError(message)
        return self


class ParticipantResponse(MetadataRecord):
    """Record one authenticated-context response, with comments kept in protected records."""

    actor_ref: OpaqueReference
    principal_ref: OpaqueReference
    outcome: Outcome
    recorded_at: AwareDatetime
    conflicted: StrictBool = False
    recused: StrictBool = False
    delegation_ref: OpaqueReference | None = None
    acting_arrangement_ref: OpaqueReference | None = None
    response_record_ref: OpaqueReference


class DecisionSession(MetadataRecord):
    """Bind response, chair, minute and ratification records to one rule and scope."""

    execution_mode: Literal["synthetic"] = "synthetic"
    session_id: OpaqueReference
    scope_ref: OpaqueReference
    rule_id: OpaqueReference
    authority_source_ref: OpaqueReference
    responses: tuple[ParticipantResponse, ...]
    matter_id: OpaqueReference
    decision_id: OpaqueReference
    template_version: Version
    review_cycle: Revision
    chair_confirmation_ref: OpaqueReference | None = None
    chair_confirmation_actor_ref: OpaqueReference | None = None
    minute_ref: OpaqueReference | None = None
    ratification_ref: OpaqueReference | None = None
    expires_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def require_distinct_voters_and_seats(self) -> Self:
        """Prevent duplicate responses or one person occupying multiple quorum seats."""
        actors = [response.actor_ref for response in self.responses]
        principals = [response.principal_ref for response in self.responses]
        if len(set(actors)) != len(actors) or len(set(principals)) != len(principals):
            message = "decision requires distinct actors and principal seats"
            raise ValueError(message)
        return self


class DecisionEvaluation(MetadataRecord):
    """Minimise decision evaluation output; never expose identity or response narratives."""

    execution_mode: Literal["synthetic"] = "synthetic"
    rule_satisfied: bool
    collective_confirmed: bool
    provisional: bool
    participation_count: int
    affirmative_count: int
    gaps: tuple[str, ...]


def decision_rule_digest(rule: DecisionRule) -> str:
    """Fingerprint the full collective policy, including membership and confirmation gates."""
    return hashlib.sha256(rule.model_dump_json().encode()).hexdigest()


def _count_participation(
    rule: DecisionRule,
    session: DecisionSession,
    now: datetime,
) -> tuple[int, int, int, set[str]]:
    eligible = set(rule.eligible_principals)
    participation = 0
    affirmative = 0
    gaps: set[str] = set()
    for response in session.responses:
        if response.principal_ref not in eligible:
            gaps.add("ineligible_participant")
            continue
        if response.conflicted or response.recused:
            eligible.discard(response.principal_ref)
            if rule.conflict_policy == "hold_decision":
                gaps.add("conflict_requires_resolution")
            continue
        if response.recorded_at > now:
            gaps.add("future_response")
            continue
        if response.actor_ref != response.principal_ref and not (
            response.delegation_ref or response.acting_arrangement_ref
        ):
            gaps.add("delegate_authority_missing")
            continue
        if response.outcome in {rule.decision_outcome, "decline", "return_for_further_work"}:
            participation += 1
        if response.outcome == rule.decision_outcome:
            affirmative += 1
    return participation, affirmative, len(eligible), gaps


def evaluate_decision(
    rule: DecisionRule,
    session: DecisionSession,
    *,
    now: datetime,
) -> DecisionEvaluation:
    """Evaluate configured collective semantics without adopting a live IHG operating model."""
    if now.tzinfo is None or now.utcoffset() is None:
        message = "decision evaluation requires timezone-aware time"
        raise ValueError(message)
    participation, affirmative, eligible_count, gaps = _count_participation(rule, session, now)
    if (
        session.scope_ref != rule.scope_ref
        or session.rule_id != rule.rule_id
        or session.authority_source_ref != rule.authority_source_ref
        or session.template_version != rule.template_version
    ):
        gaps.add("rule_scope_or_authority_mismatch")
    if session.expires_at is not None and now >= session.expires_at:
        gaps.add("out_of_session_expired")
    if participation < rule.minimum_participants:
        gaps.add("quorum_not_met")
    denominator = eligible_count if rule.majority_denominator == "eligible" else participation
    outcome_met = (
        (rule.method == "quorum" and affirmative >= rule.minimum_participants)
        or (rule.method == "majority" and affirmative * 2 > denominator)
        or (rule.method == "unanimous" and affirmative == eligible_count and eligible_count > 0)
    )
    if not outcome_met:
        gaps.add("decision_rule_not_met")
    rule_satisfied = not gaps
    if (
        session.chair_confirmation_ref is None
        or session.chair_confirmation_actor_ref != rule.chair_ref
    ):
        gaps.add("chair_confirmation_missing")
    if session.minute_ref is None:
        gaps.add("minute_reference_missing")
    if rule.ratification_required and session.ratification_ref is None:
        gaps.add("ratification_missing")
    confirmed = not gaps
    return DecisionEvaluation(
        rule_satisfied=rule_satisfied,
        collective_confirmed=confirmed,
        provisional=not confirmed,
        participation_count=participation,
        affirmative_count=affirmative,
        gaps=tuple(sorted(gaps)),
    )


def validate_collective_transition(  # noqa: PLR0913
    matter: GovernanceMatter,
    command: TransitionCommand,
    *,
    template: WorkflowTemplate,
    rule: DecisionRule,
    session: DecisionSession,
    now: datetime,
) -> None:
    """Check collective votes against the canonical matter, cycle, decision and authority."""
    if template.decision_rule_digest != decision_rule_digest(rule):
        message = "collective policy fingerprint differs from pinned template"
        raise ValueError(message)
    decision = next(
        (item for item in matter.decisions if item.decision_id == session.decision_id), None
    )
    if (
        template.decision_rule_ref != rule.rule_id
        or template.version != rule.template_version
        or template.authority_source_ref != rule.authority_source_ref
        or session.matter_id != matter.matter_id
        or session.scope_ref != matter.scope_ref
        or session.review_cycle != matter.review_cycle
        or session.template_version != matter.template_version
        or decision is None
        or decision.review_cycle != matter.review_cycle
        or decision.outcome != rule.decision_outcome
        or decision.authority.authority_source_ref != rule.authority_source_ref
    ):
        message = "collective decision binding does not match canonical matter and policy"
        raise ValueError(message)
    if decision.recorded_at > command.occurred_at or any(
        response.recorded_at > command.occurred_at for response in session.responses
    ):
        message = "collective decision evidence postdates transition"
        raise ValueError(message)
    evaluated = evaluate_decision(rule, session, now=now)
    if (
        command.to_state not in {"provisionally_decided", "ratified"}
        or not evaluated.rule_satisfied
        or (command.to_state == "ratified" and not evaluated.collective_confirmed)
    ):
        message = "collective decision requires satisfied voting and confirmation gates"
        raise ValueError(message)
    if command.to_state == "ratified":
        canonical = matter.ratification
        if (
            canonical is None
            or canonical.decision_id != session.decision_id
            or canonical.review_cycle != session.review_cycle
            or canonical.ratification_record_ref != session.ratification_ref
            or canonical.minute_or_out_of_session_ref != session.minute_ref
            or canonical.chair_confirmation_ref != session.chair_confirmation_ref
            or canonical.recorded_at > command.occurred_at
        ):
            message = "canonical ratification binding differs from evaluated decision and evidence"
            raise ValueError(message)


def apply_decision_transition(  # noqa: PLR0913
    matter: GovernanceMatter,
    command: TransitionCommand,
    *,
    template: WorkflowTemplate,
    rule: DecisionRule,
    session: DecisionSession,
    now: datetime,
    dependency_states: dict[str, State] | None = None,
) -> GovernanceMatter:
    """Apply a collective transition through the common lifecycle enforcement boundary."""
    return apply_transition(
        matter,
        command,
        template=template,
        now=now,
        dependency_states=dependency_states,
        rule=rule,
        session=session,
    )
