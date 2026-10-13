"""Connector-neutral, synthetic-only governance metadata and lifecycle contracts.

This local engine demonstrates version pinning, access boundaries and replay
safety. It does not authenticate people, persist records or activate IHG rules.
Live operating-model and platform approval remain external prerequisites.
"""

from __future__ import annotations

import hashlib
from datetime import UTC
from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from careops_process.hub_capabilities import (
    OpaqueReference,  # noqa: TC001 # Pydantic runtime schema.
)

if TYPE_CHECKING:
    from datetime import datetime

    from careops_process.hub_decisions import DecisionRule, DecisionSession

State = Literal[
    "draft",
    "submitted",
    "triaged",
    "under_review",
    "decision_required",
    "provisionally_decided",
    "ratified",
    "actions_open",
    "assurance_review",
    "closed",
    "archived",
    "withdrawn",
    "rejected",
    "returned",
    "cancelled",
    "superseded",
    "consolidated",
]
TemplateId = Literal[
    "pra_pitstop",
    "research_governance",
    "clinical_risk",
    "executive_decision",
    "policy_endorsement",
    "operational_exception",
    "review_action",
]
Classification = Literal["unconfirmed", "low_sensitivity_metadata", "protected"]
Outcome = Literal[
    "consultation",
    "recommendation",
    "endorsement",
    "approval",
    "noting",
    "ratification",
    "decline",
    "return_for_further_work",
]
Version = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")]
Revision = Annotated[int, Field(strict=True, ge=0)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
TEMPLATE_IDS: tuple[TemplateId, ...] = (
    "pra_pitstop",
    "research_governance",
    "clinical_risk",
    "executive_decision",
    "policy_endorsement",
    "operational_exception",
    "review_action",
)
PRIMARY_EDGES = frozenset(
    zip(
        (
            "draft",
            "submitted",
            "triaged",
            "under_review",
            "decision_required",
            "provisionally_decided",
            "ratified",
            "actions_open",
            "assurance_review",
            "closed",
        ),
        (
            "submitted",
            "triaged",
            "under_review",
            "decision_required",
            "provisionally_decided",
            "ratified",
            "actions_open",
            "assurance_review",
            "closed",
            "archived",
        ),
        strict=True,
    )
)
TERMINAL = frozenset(
    {"archived", "withdrawn", "rejected", "cancelled", "superseded", "consolidated"}
)


class MetadataRecord(BaseModel):
    """Reject arbitrary payloads; use immutable typed records and opaque references."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityRecord(MetadataRecord):
    """Reference an existing authority and its accountable owner or decision body."""

    authority_source_ref: OpaqueReference
    decision_owner_ref: OpaqueReference
    decision_body_ref: OpaqueReference | None = None
    delegate_ref: OpaqueReference | None = None
    acting_arrangement_ref: OpaqueReference | None = None


class ConsultationRecord(MetadataRecord):
    """Preserve adviser input without converting consultation into a decision."""

    consultation_id: OpaqueReference
    adviser_ref: OpaqueReference
    evidence_ref: OpaqueReference
    recorded_at: AwareDatetime


class DecisionRecord(MetadataRecord):
    """Preserve a provisional decision, authority and protected response reference."""

    decision_id: OpaqueReference
    outcome: Outcome
    authority: AuthorityRecord
    participant_refs: tuple[OpaqueReference, ...]
    conflict_record_ref: OpaqueReference
    response_ref: OpaqueReference
    recorded_at: AwareDatetime
    template_version: Version
    review_cycle: Revision = 0


class MeetingRecord(MetadataRecord):
    """Reference agenda, participant, conflict, chair and minute records separately."""

    meeting_id: OpaqueReference
    agenda_ref: OpaqueReference
    scheduled_at: AwareDatetime
    participant_refs: tuple[OpaqueReference, ...]
    conflicts_ref: OpaqueReference
    chair_confirmation_ref: OpaqueReference | None = None
    minute_ref: OpaqueReference | None = None


class RatificationRecord(MetadataRecord):
    """Link ratification evidence to a specific canonical decision."""

    decision_id: OpaqueReference
    ratification_record_ref: OpaqueReference
    quorum_evidence_ref: OpaqueReference
    chair_confirmation_ref: OpaqueReference
    minute_or_out_of_session_ref: OpaqueReference
    recorded_at: AwareDatetime
    review_cycle: Revision = 0


class ActionRecord(MetadataRecord):
    """Retain canonical action accountability; Planner is only an optional projection."""

    action_id: OpaqueReference
    owner_ref: OpaqueReference
    due_at: AwareDatetime
    state: Literal["assigned", "in_progress", "completed", "cancelled"] = "assigned"
    closure_evidence_ref: OpaqueReference | None = None
    planner_projection_ref: OpaqueReference | None = None

    @model_validator(mode="after")
    def require_completion_evidence(self) -> Self:
        """Require governed closure evidence for completed actions."""
        if self.state == "completed" and self.closure_evidence_ref is None:
            message = "completed action requires closure evidence"
            raise ValueError(message)
        return self


class LinkedMatter(MetadataRecord):
    """Preserve provenance for related, dependent and superseding matters."""

    matter_id: OpaqueReference
    relation: Literal["related", "depends_on", "supersedes", "superseded_by", "duplicate_of"]
    provenance_ref: OpaqueReference


class TransitionRule(MetadataRecord):
    """Configure roles for a lifecycle edge without inventing a delegation."""

    from_state: State
    to_state: State
    allowed_roles: tuple[OpaqueReference, ...]


class EscalationRule(MetadataRecord):
    """Configure a named trigger and an authorised role using approved policy evidence."""

    trigger: Literal[
        "higher_risk", "material", "contested", "cross_service", "overdue", "safety_signal"
    ]
    target_role: OpaqueReference
    threshold_policy_ref: OpaqueReference


class WorkflowTemplate(MetadataRecord):
    """Version pathway rules, authority, escalation, notifications and records controls."""

    schema_version: Literal[1] = 1
    template_id: TemplateId
    version: Version
    authority_source_ref: OpaqueReference | None = None
    approval_ref: OpaqueReference | None = None
    roles: tuple[OpaqueReference, ...] = ()
    rules: tuple[TransitionRule, ...] = ()
    escalation_rules: tuple[EscalationRule, ...] = ()
    outcomes: tuple[Outcome, ...] = ()
    decision_rule_ref: OpaqueReference | None = None
    decision_rule_digest: Digest | None = None
    notification_policy: Literal["none", "digest", "exceptions_only"] = "none"
    records_policy_ref: OpaqueReference | None = None
    closure_requires_evidence: Literal[True] = True

    @model_validator(mode="after")
    def validate_configured_roles(self) -> Self:
        """Reject duplicate edges and rule roles absent from the template."""
        if bool(self.decision_rule_ref) != bool(self.decision_rule_digest):
            message = "collective rule reference and fingerprint must be configured together"
            raise ValueError(message)
        edges = [(rule.from_state, rule.to_state) for rule in self.rules]
        if len(set(edges)) != len(edges):
            message = "duplicate template transition"
            raise ValueError(message)
        for rule in self.rules:
            if not rule.allowed_roles or not set(rule.allowed_roles) <= set(self.roles):
                message = "transition role must be configured in template"
                raise ValueError(message)
            if not _valid_edge(rule.from_state, rule.to_state):
                message = "invalid configured lifecycle transition"
                raise ValueError(message)
        for rule in self.escalation_rules:
            if rule.target_role not in self.roles:
                message = "escalation role must be configured in template"
                raise ValueError(message)
        return self


class TransitionCommand(MetadataRecord):
    """Supply explicit identity context, compare-and-swap revision and replay key."""

    event_id: OpaqueReference
    replay_key: OpaqueReference
    expected_revision: Revision
    to_state: State
    occurred_at: AwareDatetime
    actor_ref: OpaqueReference
    actor_role: OpaqueReference
    actor_scope_ref: OpaqueReference
    evidence_ref: OpaqueReference
    destination_matter_ref: OpaqueReference | None = None


class TransitionAudit(MetadataRecord):
    """Retain immutable transition provenance without narrative or approval comments."""

    event_id: OpaqueReference
    replay_key: OpaqueReference
    command_digest: Digest
    from_state: State
    to_state: State
    revision: Revision
    occurred_at: AwareDatetime
    actor_ref: OpaqueReference
    authority_source_ref: OpaqueReference
    evidence_ref: OpaqueReference
    template_version: Version
    review_cycle: Revision = 0


class GovernanceMatter(MetadataRecord):
    """Canonical synthetic matter; no collaboration projection is authoritative."""

    schema_version: Literal[1] = 1
    execution_mode: Literal["synthetic"] = "synthetic"
    matter_id: OpaqueReference
    scope_ref: OpaqueReference
    classification: Classification
    source_ref: OpaqueReference
    sponsor_ref: OpaqueReference | None = None
    risk: Literal["unconfirmed", "routine", "higher", "material"] = "unconfirmed"
    template_id: TemplateId
    template_version: Version
    template_digest: Digest
    state: State = "draft"
    revision: Revision = 0
    review_cycle: Revision = 0
    authority: AuthorityRecord | None = None
    consultations: tuple[ConsultationRecord, ...] = ()
    decisions: tuple[DecisionRecord, ...] = ()
    meeting: MeetingRecord | None = None
    ratification: RatificationRecord | None = None
    past_ratifications: tuple[RatificationRecord, ...] = ()
    actions: tuple[ActionRecord, ...] = ()
    evidence_refs: tuple[OpaqueReference, ...] = ()
    linked_matters: tuple[LinkedMatter, ...] = ()
    closure_evidence_ref: OpaqueReference | None = None
    assurance_evidence_ref: OpaqueReference | None = None
    archive_record_ref: OpaqueReference | None = None
    history: tuple[TransitionAudit, ...] = ()

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:  # Validate persisted audit boundaries.
        """Reject contradictory history, self-links and silently changed decision versions."""
        if self.revision != len(self.history):
            message = "revision must match canonical history"
            raise ValueError(message)
        expected_state: State = "draft"
        expected_cycle = 0
        event_ids: set[str] = set()
        replay_keys: set[str] = set()
        previous_time = None
        for revision, event in enumerate(self.history, start=1):
            if event.from_state in TERMINAL | {"closed"} and event.to_state == "under_review":
                expected_cycle += 1
            if (
                event.revision != revision
                or event.from_state != expected_state
                or event.template_version != self.template_version
                or event.review_cycle != expected_cycle
                or not _valid_edge(event.from_state, event.to_state)
                or event.event_id in event_ids
                or event.replay_key in replay_keys
                or (previous_time is not None and event.occurred_at < previous_time)
            ):
                message = "inconsistent canonical history"
                raise ValueError(message)
            event_ids.add(event.event_id)
            replay_keys.add(event.replay_key)
            previous_time = event.occurred_at
            expected_state = event.to_state
        if self.state != expected_state or self.review_cycle != expected_cycle:
            message = "state must match canonical history"
            raise ValueError(message)
        if any(link.matter_id == self.matter_id for link in self.linked_matters):
            message = "matter cannot link to itself"
            raise ValueError(message)
        if any(decision.template_version != self.template_version for decision in self.decisions):
            message = "decision version must match pinned template"
            raise ValueError(message)
        return self


def template_digest(template: WorkflowTemplate) -> str:
    """Fingerprint complete validated rules, including their authority and records policy."""
    return hashlib.sha256(template.model_dump_json().encode()).hexdigest()


def _require_approved(template: WorkflowTemplate) -> str:
    if not (
        template.approval_ref
        and template.authority_source_ref
        and template.records_policy_ref
        and template.roles
        and template.rules
    ):
        message = "matter requires an approved configured template"
        raise ValueError(message)
    return str(template.authority_source_ref)


def create_matter(
    *,
    matter_id: str,
    scope_ref: str,
    classification: Classification,
    source_ref: str,
    template: WorkflowTemplate,
) -> GovernanceMatter:
    """Create a synthetic matter pinned to an explicitly supplied approved test policy."""
    _require_approved(template)
    return GovernanceMatter(
        matter_id=matter_id,
        scope_ref=scope_ref,
        classification=classification,
        source_ref=source_ref,
        template_id=template.template_id,
        template_version=template.version,
        template_digest=template_digest(template),
    )


def _valid_edge(before: State, after: State) -> bool:
    if (before, after) in PRIMARY_EDGES:
        return True
    if before == "archived":
        return False
    if after in {"superseded", "consolidated"}:
        return before not in TERMINAL
    if before in TERMINAL or before == "closed":
        return after == "under_review"
    if before == "returned":
        return after == "submitted"
    return after in {"withdrawn", "rejected", "returned", "cancelled"}


def _record_requirements(matter: GovernanceMatter, command: TransitionCommand) -> None:
    if command.to_state == "provisionally_decided" and not any(
        decision.review_cycle == matter.review_cycle for decision in matter.decisions
    ):
        message = "decision record required"
        raise ValueError(message)
    if command.to_state == "ratified":
        ratification = matter.ratification
        if (
            ratification is None
            or ratification.review_cycle != matter.review_cycle
            or ratification.decision_id
            not in {
                decision.decision_id
                for decision in matter.decisions
                if decision.review_cycle == matter.review_cycle
            }
        ):
            message = "ratification evidence for canonical decision required"
            raise ValueError(message)
    if command.to_state in {"closed", "archived"} and (
        not matter.closure_evidence_ref
        or any(action.state not in {"completed", "cancelled"} for action in matter.actions)
    ):
        message = "closure requires evidence and resolved actions"
        raise ValueError(message)
    if command.to_state == "archived" and not matter.archive_record_ref:
        message = "archive record required"
        raise ValueError(message)
    if command.to_state in {"superseded", "consolidated"} and (
        not command.destination_matter_ref or command.destination_matter_ref == matter.matter_id
    ):
        message = "distinct destination matter required"
        raise ValueError(message)


def apply_transition(  # noqa: C901, PLR0912, PLR0913, PLR0915 # Check boundaries before atomic update.
    matter: GovernanceMatter,
    command: TransitionCommand,
    *,
    template: WorkflowTemplate,
    now: datetime,
    dependency_states: dict[str, State] | None = None,
    rule: DecisionRule | None = None,
    session: DecisionSession | None = None,
) -> GovernanceMatter:
    """Apply an authorised synthetic transition or return the current record on identical replay."""
    authority_ref = _require_approved(template)
    if (
        matter.template_id != template.template_id
        or matter.template_version != template.version
        or matter.template_digest != template_digest(template)
    ):
        message = "transition differs from pinned template"
        raise ValueError(message)
    for recorded in matter.history:
        configured = next(
            (
                item
                for item in template.rules
                if (item.from_state == recorded.from_state and item.to_state == recorded.to_state)
            ),
            None,
        )
        if configured is None or recorded.authority_source_ref != authority_ref:
            message = "canonical history differs from pinned template authority or transitions"
            raise ValueError(message)
    if command.actor_scope_ref != matter.scope_ref:
        message = "actor scope does not permit this matter"
        raise ValueError(message)
    canonical_command = command.model_copy(
        update={"occurred_at": command.occurred_at.astimezone(UTC)}
    )
    digest = hashlib.sha256(canonical_command.model_dump_json().encode()).hexdigest()
    for event in matter.history:
        if event.replay_key == command.replay_key:
            if event.command_digest != digest:
                message = "replay key collision"
                raise ValueError(message)
            return matter
        if event.event_id == command.event_id:
            message = "event ID reused with a new replay key"
            raise ValueError(message)
    if command.expected_revision != matter.revision:
        message = "stale or out-of-order expected revision"
        raise ValueError(message)
    if now.tzinfo is None or now.utcoffset() is None or command.occurred_at > now:
        message = "ambiguous or future event time"
        raise ValueError(message)
    if matter.history and command.occurred_at < matter.history[-1].occurred_at:
        message = "out-of-order event time"
        raise ValueError(message)
    transition_rule = next(
        (
            item
            for item in template.rules
            if (item.from_state == matter.state and item.to_state == command.to_state)
        ),
        None,
    )
    if transition_rule is None or not _valid_edge(matter.state, command.to_state):
        message = "unconfigured or invalid lifecycle transition"
        raise ValueError(message)
    if command.actor_role not in transition_rule.allowed_roles:
        message = "actor role does not hold configured transition authority"
        raise ValueError(message)
    if command.to_state in {"decision_required", "provisionally_decided", "closed"}:
        known = dependency_states or {}
        if any(
            link.relation == "depends_on"
            and known.get(link.matter_id) not in {"closed", "archived"}
            for link in matter.linked_matters
        ):
            message = "unresolved linked-matter dependency"
            raise ValueError(message)
    _record_requirements(matter, command)
    if template.decision_rule_ref and command.to_state in {"provisionally_decided", "ratified"}:
        if rule is None or session is None:
            message = "collective decision requires configured policy and session evidence"
            raise ValueError(message)
        # Keep the shared boundary authoritative while avoiding a model-definition import cycle.
        from careops_process.hub_decisions import validate_collective_transition  # noqa: PLC0415

        validate_collective_transition(
            matter, command, template=template, rule=rule, session=session, now=now
        )
    reopening = matter.state in TERMINAL | {"closed"} and command.to_state == "under_review"
    review_cycle = matter.review_cycle + int(reopening)
    audit = TransitionAudit(
        event_id=command.event_id,
        replay_key=command.replay_key,
        command_digest=digest,
        from_state=matter.state,
        to_state=command.to_state,
        revision=matter.revision + 1,
        occurred_at=command.occurred_at,
        actor_ref=command.actor_ref,
        authority_source_ref=authority_ref,
        evidence_ref=command.evidence_ref,
        template_version=template.version,
        review_cycle=review_cycle,
    )
    links = matter.linked_matters
    if command.destination_matter_ref:
        links += (
            LinkedMatter(
                matter_id=command.destination_matter_ref,
                relation="duplicate_of" if command.to_state == "consolidated" else "superseded_by",
                provenance_ref=command.evidence_ref,
            ),
        )
    value = matter.model_dump()
    value.update(
        state=command.to_state,
        revision=matter.revision + 1,
        review_cycle=review_cycle,
        history=(*matter.history, audit),
        linked_matters=links,
    )
    if reopening:
        value.update(
            past_ratifications=(*matter.past_ratifications, matter.ratification)
            if matter.ratification
            else matter.past_ratifications,
            ratification=None,
            closure_evidence_ref=None,
            assurance_evidence_ref=None,
            archive_record_ref=None,
        )
    return GovernanceMatter.model_validate(value)


def collaboration_projection(
    matter: GovernanceMatter, *, actor_scope_ref: str
) -> dict[str, str | int]:
    """Expose only actionable low-sensitivity identifiers to the authorised scope."""
    if actor_scope_ref != matter.scope_ref:
        message = "projection requires authorised scope"
        raise ValueError(message)
    if matter.classification != "low_sensitivity_metadata":
        message = "projection classification is not approved low-sensitivity metadata"
        raise ValueError(message)
    return {"matter_id": matter.matter_id, "state": matter.state, "revision": matter.revision}


def draft_templates() -> tuple[WorkflowTemplate, ...]:
    """Define seven pathway identifiers without invented clinical or executive rules."""
    return tuple(WorkflowTemplate(template_id=name, version="0.1.0") for name in TEMPLATE_IDS)


def validate_template_upgrade(
    current: WorkflowTemplate,
    replacement: WorkflowTemplate,
    *,
    migration_ref: str | None,
) -> None:
    """Require an explicit reviewed migration and a forward compatible template version."""
    _require_approved(replacement)
    if not migration_ref:
        message = "explicit migration reference required"
        raise ValueError(message)
    if (
        current.template_id != replacement.template_id
        or current.schema_version != replacement.schema_version
        or tuple(map(int, replacement.version.split(".")))
        <= tuple(map(int, current.version.split(".")))
    ):
        message = "template identity, schema or version is incompatible"
        raise ValueError(message)
