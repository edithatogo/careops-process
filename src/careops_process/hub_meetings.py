"""Synthetic meeting records assembled from approved references, without protected content."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Self

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from careops_process.hub_capabilities import OpaqueReference  # noqa: TC001
from careops_process.hub_decisions import (
    DecisionRule,
    DecisionSession,
    decision_rule_digest,
    evaluate_decision,
)
from careops_process.hub_domain import (
    Digest,
    GovernanceMatter,
    MetadataRecord,
    Revision,
    Version,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


class BriefReferences(MetadataRecord):
    """Bind approved brief sources to one scope, matter, template and decision policy."""

    execution_mode: Literal["synthetic"] = "synthetic"
    matter_id: OpaqueReference
    scope_ref: OpaqueReference
    template_version: Version
    approval_ref: OpaqueReference
    decision_rule_digest: Digest
    question_ref: OpaqueReference
    recommendation_ref: OpaqueReference
    alternatives_ref: OpaqueReference
    risk_ref: OpaqueReference
    authority_ref: OpaqueReference
    conflicts_ref: OpaqueReference
    consultations_ref: OpaqueReference
    proposed_actions_ref: OpaqueReference


class AgendaEntry(MetadataRecord):
    """Preserve an agenda snapshot and protected-source references without replacing the matter."""

    matter_id: OpaqueReference
    matter_revision: Revision
    review_cycle: Revision
    decision_refs: tuple[OpaqueReference, ...]
    added_at: AwareDatetime
    template_digest: Digest
    brief: BriefReferences
    chair_exception_ref: OpaqueReference | None = None


class MinuteDecision(MetadataRecord):
    """Record evaluated meeting outcome; a minute is not a canonical lifecycle mutation."""

    matter_id: OpaqueReference
    meeting_id: OpaqueReference
    matter_revision: Revision
    review_cycle: Revision
    template_version: Version
    template_digest: Digest
    decision_id: OpaqueReference
    session_id: OpaqueReference
    authority_ref: OpaqueReference
    policy_digest: Digest
    response_digest: Digest
    recorded_at: AwareDatetime
    minute_ref: OpaqueReference
    chair_confirmation_ref: OpaqueReference
    collective_confirmed: StrictBool
    gaps: tuple[str, ...]


class AgendaReplacement(MetadataRecord):
    """Retain the full synthetic refresh request and both immutable agenda snapshots."""

    replacement_id: OpaqueReference
    meeting_id: OpaqueReference
    scope_ref: OpaqueReference
    meeting_context_digest: Digest
    actor_ref: OpaqueReference
    expected_revision: Revision
    request_matter: GovernanceMatter
    previous_entry: AgendaEntry
    next_entry: AgendaEntry
    command_digest: Digest

    @model_validator(mode="after")
    def validate_replacement(self) -> Self:
        """Bind retained request identity to the exact refreshed canonical snapshot."""
        previous, following = self.previous_entry, self.next_entry
        _brief_binding(self.request_matter, following.brief, following.brief.scope_ref)
        expected = _agenda_snapshot(
            self.request_matter,
            following.brief,
            following.added_at,
            following.chair_exception_ref,
        )
        if (
            following != expected
            or previous.matter_id != following.matter_id
            or previous.brief.scope_ref != following.brief.scope_ref
            or following.matter_revision < previous.matter_revision
            or following.review_cycle < previous.review_cycle
            or following.added_at < previous.added_at
            or following.template_digest != previous.template_digest
            or following.brief.template_version != previous.brief.template_version
            or following.brief.decision_rule_digest != previous.brief.decision_rule_digest
            or _same_snapshot(previous, following)
        ):
            message = "replacement snapshot, policy, template or chronology is inconsistent"
            raise ValueError(message)
        if self.command_digest != _command_digest(
            self.model_dump(mode="json", exclude={"command_digest"}),
        ):
            message = "replacement command digest differs from retained request"
            raise ValueError(message)
        return self


class MeetingAgenda(MetadataRecord):
    """Keep immutable agenda and minute snapshots inside an explicit synthetic operating context."""

    execution_mode: Literal["synthetic"] = "synthetic"
    meeting_id: OpaqueReference
    scope_ref: OpaqueReference
    chair_ref: OpaqueReference
    secretariat_refs: tuple[OpaqueReference, ...]
    participant_refs: tuple[OpaqueReference, ...]
    scheduled_at: AwareDatetime
    agenda_deadline: AwareDatetime
    authority_ref: OpaqueReference
    cadence_policy_ref: OpaqueReference
    revision: Revision = 0
    entries: tuple[AgendaEntry, ...] = ()
    decisions: tuple[MinuteDecision, ...] = ()
    replacements: tuple[AgendaReplacement, ...] = ()

    @model_validator(mode="after")
    def validate_meeting_record(self) -> Self:
        """Reject impossible times, duplicated snapshots and contradictory record revisions."""
        if self.agenda_deadline > self.scheduled_at:
            message = "agenda deadline must not follow the meeting"
            raise ValueError(message)
        if self.revision != len(self.entries) + len(self.decisions) + len(self.replacements):
            message = "meeting revision must match recorded events"
            raise ValueError(message)
        if (
            len({entry.matter_id for entry in self.entries}) != len(self.entries)
            or len({decision.session_id for decision in self.decisions}) != len(self.decisions)
            or len(set(self.participant_refs)) != len(self.participant_refs)
            or not self.secretariat_refs
        ):
            message = "meeting requires distinct entries, sessions and participants"
            raise ValueError(message)
        for entry in self.entries:
            if entry.brief.scope_ref != self.scope_ref or entry.brief.matter_id != entry.matter_id:
                message = "agenda entry binding differs from meeting scope or matter"
                raise ValueError(message)
        _validate_replacement_history(self)
        previous_time = self.scheduled_at
        for decision in self.decisions:
            entry = next(
                (item for item in self.entries if item.matter_id == decision.matter_id), None
            )
            if (
                entry is None
                or decision.meeting_id != self.meeting_id
                or decision.decision_id not in entry.decision_refs
                or decision.review_cycle != entry.review_cycle
                or decision.matter_revision != entry.matter_revision
                or decision.template_version != entry.brief.template_version
                or decision.template_digest != entry.template_digest
                or decision.authority_ref != self.authority_ref
                or decision.policy_digest != entry.brief.decision_rule_digest
                or decision.recorded_at < previous_time
                or decision.recorded_at < entry.added_at
                or decision.collective_confirmed != (not decision.gaps)
            ):
                message = "inconsistent minute binding, chronology or confirmation"
                raise ValueError(message)
            previous_time = decision.recorded_at
        return self


def _check_actor(meeting: MeetingAgenda, actor_ref: str, now: datetime) -> None:
    if actor_ref not in {*meeting.secretariat_refs, meeting.chair_ref}:
        message = "meeting actor is outside configured secretariat and chair"
        raise ValueError(message)
    _require_aware(now)


def _require_aware(value: object) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        message = "meeting event requires timezone-aware time"
        raise ValueError(message)


def _strict_revision(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        message = "meeting expected revision must be a strict nonnegative integer"
        raise ValueError(message)


def _chronology(meeting: MeetingAgenda, now: datetime) -> None:
    times = [entry.added_at for entry in meeting.entries]
    times.extend(decision.recorded_at for decision in meeting.decisions)
    if times and now < max(times):
        message = "meeting chronology cannot precede retained events"
        raise ValueError(message)


def _command_digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()


def _meeting_context_digest(meeting: MeetingAgenda) -> str:
    return _command_digest(
        meeting.model_dump(
            mode="json",
            exclude={"entries", "decisions", "replacements", "revision"},
        )
    )


def _same_snapshot(previous: AgendaEntry, following: AgendaEntry) -> bool:
    excluded = {"added_at", "chair_exception_ref"}
    return previous.model_dump(exclude=excluded) == following.model_dump(exclude=excluded)


def _agenda_snapshot(
    matter: GovernanceMatter,
    brief: BriefReferences,
    now: datetime,
    chair_exception_ref: str | None,
) -> AgendaEntry:
    return AgendaEntry(
        matter_id=matter.matter_id,
        matter_revision=matter.revision,
        review_cycle=matter.review_cycle,
        decision_refs=tuple(
            item.decision_id
            for item in matter.decisions
            if item.review_cycle == matter.review_cycle
        ),
        added_at=now.astimezone(UTC),
        template_digest=matter.template_digest,
        brief=brief,
        chair_exception_ref=chair_exception_ref,
    )


def _original_agenda_entries(meeting: MeetingAgenda) -> dict[str, AgendaEntry]:
    originals = {entry.matter_id: entry for entry in meeting.entries}
    for event in reversed(meeting.replacements):
        if originals.get(event.next_entry.matter_id) != event.next_entry:
            message = "replacement history does not chain to the active snapshot"
            raise ValueError(message)
        originals[event.previous_entry.matter_id] = event.previous_entry
        _check_actor(meeting, event.actor_ref, event.next_entry.added_at)
        if (
            event.meeting_id != meeting.meeting_id
            or event.scope_ref != meeting.scope_ref
            or event.meeting_context_digest != _meeting_context_digest(meeting)
            or event.previous_entry.brief.scope_ref != meeting.scope_ref
            or event.next_entry.added_at >= meeting.scheduled_at
            or (
                event.next_entry.added_at > meeting.agenda_deadline
                and event.next_entry.chair_exception_ref is None
            )
        ):
            message = "replacement history violates scope, deadline or meeting cutoff"
            raise ValueError(message)
    return originals


def _validate_replacement_history(meeting: MeetingAgenda) -> None:
    if not meeting.replacements:
        return
    events = {event.expected_revision + 1: event for event in meeting.replacements}
    if (
        len(events) != len(meeting.replacements)
        or len({event.replacement_id for event in meeting.replacements})
        != len(meeting.replacements)
        or tuple(events) != tuple(sorted(events))
    ):
        message = "replacement history has duplicate or out-of-order identities or revisions"
        raise ValueError(message)
    originals = _original_agenda_entries(meeting)
    additions = iter(originals[entry.matter_id] for entry in meeting.entries)
    current: dict[str, AgendaEntry] = {}
    previous_time = None
    for revision in range(1, len(meeting.entries) + len(meeting.replacements) + 1):
        event = events.get(revision)
        if event is None:
            entry = next(additions, None)
            if entry is None:
                message = "replacement history claims an impossible meeting revision"
                raise ValueError(message)
        else:
            if current.get(event.previous_entry.matter_id) != event.previous_entry:
                message = "replacement expected revision precedes its original snapshot"
                raise ValueError(message)
            entry = event.next_entry
        if previous_time is not None and entry.added_at < previous_time:
            message = "agenda history chronology is not monotonic"
            raise ValueError(message)
        previous_time = entry.added_at
        current[entry.matter_id] = entry
    if current != {entry.matter_id: entry for entry in meeting.entries}:
        message = "restored agenda entries differ from replacement history"
        raise ValueError(message)


def _brief_binding(matter: GovernanceMatter, brief: BriefReferences, scope_ref: str) -> None:
    if (
        matter.scope_ref != scope_ref
        or brief.scope_ref != scope_ref
        or matter.matter_id != brief.matter_id
        or matter.template_version != brief.template_version
        or matter.classification != "low_sensitivity_metadata"
    ):
        message = "brief binding or classification differs from authorised matter"
        raise ValueError(message)


def add_agenda_entry(  # noqa: PLR0913
    meeting: MeetingAgenda,
    matter: GovernanceMatter,
    brief: BriefReferences,
    *,
    actor_ref: str,
    expected_revision: int,
    now: datetime,
    chair_exception_ref: str | None = None,
) -> MeetingAgenda:
    """Append an approved-reference agenda entry with explicit deadline and revision controls."""
    meeting = MeetingAgenda.model_validate(meeting.model_dump())
    matter = GovernanceMatter.model_validate(matter.model_dump())
    brief = BriefReferences.model_validate(brief.model_dump())
    _strict_revision(expected_revision)
    _check_actor(meeting, actor_ref, now)
    _brief_binding(matter, brief, meeting.scope_ref)
    entry = _agenda_snapshot(matter, brief, now, chair_exception_ref)
    existing = next((item for item in meeting.entries if item.matter_id == matter.matter_id), None)
    if existing is not None:
        if existing != entry.model_copy(update={"added_at": existing.added_at}):
            message = "duplicate agenda entry has a changed canonical snapshot"
            raise ValueError(message)
        return meeting
    if expected_revision != meeting.revision:
        message = "stale meeting revision"
        raise ValueError(message)
    _chronology(meeting, now)
    if now > meeting.agenda_deadline and chair_exception_ref is None:
        message = "agenda deadline requires explicit chair exception"
        raise ValueError(message)
    return MeetingAgenda.model_validate(
        {
            **meeting.model_dump(),
            "entries": (*meeting.entries, entry),
            "revision": meeting.revision + 1,
        }
    )


def replace_agenda_entry(  # noqa: PLR0913 - explicit synthetic command and revision boundary
    meeting: MeetingAgenda,
    matter: GovernanceMatter,
    brief: BriefReferences,
    *,
    replacement_id: str,
    actor_ref: str,
    expected_revision: int,
    now: datetime,
    chair_exception_ref: str | None = None,
) -> MeetingAgenda:
    """Refresh an unminuted pre-meeting snapshot, retaining verifiable request history.

    Exact historical command replay returns the current state, never the earlier
    snapshot. Unchanged snapshot requests are rejected without consuming an ID.
    Policy/template rebinding requires a separate governed operation.
    """
    meeting = MeetingAgenda.model_validate(meeting.model_dump())
    matter = GovernanceMatter.model_validate(matter.model_dump())
    brief = BriefReferences.model_validate(brief.model_dump())
    _strict_revision(expected_revision)
    _check_actor(meeting, actor_ref, now)
    _brief_binding(matter, brief, meeting.scope_ref)
    existing = next(
        (event for event in meeting.replacements if event.replacement_id == replacement_id),
        None,
    )
    previous = (
        existing.previous_entry
        if existing is not None
        else next(
            (entry for entry in meeting.entries if entry.matter_id == matter.matter_id),
            None,
        )
    )
    if previous is None:
        message = "replacement requires an existing agenda entry"
        raise ValueError(message)
    following = _agenda_snapshot(matter, brief, now, chair_exception_ref)
    request: dict[str, object] = {
        "replacement_id": replacement_id,
        "meeting_id": meeting.meeting_id,
        "scope_ref": meeting.scope_ref,
        "meeting_context_digest": _meeting_context_digest(meeting),
        "actor_ref": actor_ref,
        "expected_revision": expected_revision,
        "request_matter": matter.model_dump(mode="json"),
        "previous_entry": previous.model_dump(mode="json"),
        "next_entry": following.model_dump(mode="json"),
    }
    digest = _command_digest(request)
    if existing is not None:
        if digest != existing.command_digest:
            message = "replacement replay collision differs from the original command"
            raise ValueError(message)
        return meeting
    if expected_revision != meeting.revision:
        message = "stale meeting revision"
        raise ValueError(message)
    if any(decision.matter_id == matter.matter_id for decision in meeting.decisions):
        message = "replacement cannot rewrite a minuted matter"
        raise ValueError(message)
    _chronology(meeting, now)
    if now >= meeting.scheduled_at:
        message = "replacement must precede the scheduled meeting"
        raise ValueError(message)
    if now > meeting.agenda_deadline and chair_exception_ref is None:
        message = "agenda deadline requires explicit chair exception"
        raise ValueError(message)
    event = AgendaReplacement.model_validate({**request, "command_digest": digest})
    return MeetingAgenda.model_validate(
        {
            **meeting.model_dump(),
            "entries": tuple(
                following if entry.matter_id == matter.matter_id else entry
                for entry in meeting.entries
            ),
            "replacements": (*meeting.replacements, event),
            "revision": meeting.revision + 1,
        }
    )


def _session_digest(session: DecisionSession) -> str:
    normalized = session.model_copy(
        update={
            "responses": tuple(
                response.model_copy(update={"recorded_at": response.recorded_at.astimezone(UTC)})
                for response in session.responses
            ),
            "expires_at": session.expires_at.astimezone(UTC)
            if session.expires_at is not None
            else None,
        }
    )
    return hashlib.sha256(normalized.model_dump_json().encode()).hexdigest()


def record_minutes(  # noqa: PLR0913
    meeting: MeetingAgenda,
    rule: DecisionRule,
    session: DecisionSession,
    *,
    matter: GovernanceMatter,
    actor_ref: str,
    expected_revision: int,
    minute_ref: str,
    chair_confirmation_ref: str,
    now: datetime,
) -> MeetingAgenda:
    """Assemble a minuted outcome from a scoped collective session without canonical writes."""
    meeting = MeetingAgenda.model_validate(meeting.model_dump())
    _strict_revision(expected_revision)
    _check_actor(meeting, actor_ref, now)
    entry = next((item for item in meeting.entries if item.matter_id == session.matter_id), None)
    canonical_decision = next(
        (item for item in matter.decisions if item.decision_id == session.decision_id), None
    )
    if (
        entry is None
        or canonical_decision is None
        or matter.matter_id != session.matter_id
        or matter.scope_ref != meeting.scope_ref
        or matter.classification != "low_sensitivity_metadata"
        or matter.revision != entry.matter_revision
        or matter.template_digest != entry.template_digest
        or matter.review_cycle != session.review_cycle
        or canonical_decision.review_cycle != session.review_cycle
        or canonical_decision.template_version != session.template_version
        or canonical_decision.authority.authority_source_ref != rule.authority_source_ref
        or canonical_decision.outcome != rule.decision_outcome
        or canonical_decision.recorded_at > now
    ):
        message = "canonical decision binding, cycle or current matter differs from agenda"
        raise ValueError(message)
    if (
        session.meeting_ref != meeting.meeting_id
        or session.scope_ref != meeting.scope_ref
        or rule.scope_ref != meeting.scope_ref
        or rule.authority_source_ref != meeting.authority_ref
        or session.authority_source_ref != meeting.authority_ref
        or rule.chair_ref != meeting.chair_ref
        or session.chair_confirmation_actor_ref != meeting.chair_ref
        or session.chair_confirmation_ref != chair_confirmation_ref
        or session.minute_ref != minute_ref
        or session.template_version != entry.brief.template_version
        or decision_rule_digest(rule) != entry.brief.decision_rule_digest
        or not {response.actor_ref for response in session.responses}
        <= set(meeting.participant_refs)
    ):
        message = "minute binding differs from agenda, authority, participants or chair evidence"
        raise ValueError(message)
    response_digest = _session_digest(session)
    existing = next(
        (item for item in meeting.decisions if item.session_id == session.session_id), None
    )
    if existing is not None:
        if existing.response_digest != response_digest or existing.minute_ref != minute_ref:
            message = "minute session replay differs from recorded evidence"
            raise ValueError(message)
        return meeting
    if expected_revision != meeting.revision or now < meeting.scheduled_at:
        message = "stale revision or meeting has not been held"
        raise ValueError(message)
    _chronology(meeting, now)
    if meeting.decisions and now < meeting.decisions[-1].recorded_at:
        message = "minute chronology cannot precede earlier records"
        raise ValueError(message)
    evaluation = evaluate_decision(rule, session, now=now)
    decision = MinuteDecision(
        matter_id=session.matter_id,
        meeting_id=meeting.meeting_id,
        matter_revision=matter.revision,
        review_cycle=matter.review_cycle,
        template_version=matter.template_version,
        template_digest=matter.template_digest,
        decision_id=session.decision_id,
        session_id=session.session_id,
        authority_ref=meeting.authority_ref,
        policy_digest=decision_rule_digest(rule),
        response_digest=response_digest,
        recorded_at=now,
        minute_ref=minute_ref,
        chair_confirmation_ref=chair_confirmation_ref,
        collective_confirmed=evaluation.collective_confirmed,
        gaps=evaluation.gaps,
    )
    return MeetingAgenda.model_validate(
        {
            **meeting.model_dump(),
            "decisions": (*meeting.decisions, decision),
            "revision": meeting.revision + 1,
        }
    )


def render_reference_brief(
    matter: GovernanceMatter, brief: BriefReferences, *, actor_scope_ref: str
) -> str:
    """Render approved reference fields without retrieving or copying their protected contents."""
    _brief_binding(matter, brief, actor_scope_ref)
    fields = (
        ("Question", brief.question_ref),
        ("Recommendation", brief.recommendation_ref),
        ("Alternatives", brief.alternatives_ref),
        ("Risks", brief.risk_ref),
        ("Authority", brief.authority_ref),
        ("Conflicts", brief.conflicts_ref),
        ("Consultations", brief.consultations_ref),
        ("Proposed actions", brief.proposed_actions_ref),
    )
    rows = "\n".join(f"| {label} | {reference} |" for label, reference in fields)
    return (
        f"# Decision brief — {matter.matter_id}\n\n"
        f"| Field | Protected record reference |\n| --- | --- |\n{rows}\n"
    )


class UrgentDecisionLedger(MetadataRecord):
    """Keep urgency, decision expiry and later ratification distinct and explicit."""

    execution_mode: Literal["synthetic"] = "synthetic"
    matter_id: OpaqueReference
    scope_ref: OpaqueReference
    decision_id: OpaqueReference
    decision_session_id: OpaqueReference
    policy_ref: OpaqueReference
    urgency_evidence_ref: OpaqueReference
    authority_ref: OpaqueReference
    template_version: Version
    review_cycle: Revision
    approved_ratification_policy_digest: Digest
    original_response_refs: tuple[OpaqueReference, ...] = Field(min_length=1)
    provisionally_decided_at: AwareDatetime
    expires_at: AwareDatetime
    ratification_required: StrictBool
    ratification_ref: OpaqueReference | None = None
    ratification_rule: DecisionRule | None = None
    ratification_session: DecisionSession | None = None

    @model_validator(mode="after")
    def validate_expiry(self) -> Self:
        """Reject a decision opportunity that expired before its provisional decision."""
        if self.expires_at <= self.provisionally_decided_at:
            message = "urgent decision expiry must follow provisional decision"
            raise ValueError(message)
        return self


def urgent_decision_status(ledger: UrgentDecisionLedger, *, now: datetime) -> str:
    """Preserve an expired gap until a later scoped ratification session satisfies its rule."""
    if now.tzinfo is None or now.utcoffset() is None or now < ledger.provisionally_decided_at:
        message = "urgent ledger evaluation time is ambiguous or predates decision"
        raise ValueError(message)
    if ledger.ratification_ref is not None:
        session = ledger.ratification_session
        rule = ledger.ratification_rule
        if (
            session is not None
            and rule is not None
            and session.matter_id == ledger.matter_id
            and session.scope_ref == ledger.scope_ref
            and session.decision_id == ledger.decision_id
            and session.authority_source_ref == ledger.authority_ref
            and rule.authority_source_ref == ledger.authority_ref
            and session.template_version == ledger.template_version
            and rule.template_version == ledger.template_version
            and session.review_cycle == ledger.review_cycle
            and decision_rule_digest(rule) == ledger.approved_ratification_policy_digest
            and session.session_id != ledger.decision_session_id
            and session.ratification_ref == ledger.ratification_ref
            and rule.decision_outcome == "ratification"
            and all(
                response.recorded_at > ledger.provisionally_decided_at
                for response in session.responses
            )
            and not set(ledger.original_response_refs)
            & {response.response_record_ref for response in session.responses}
            and evaluate_decision(rule, session, now=now).collective_confirmed
        ):
            return "ratified"
        return "ratification_evidence_missing"
    if not ledger.ratification_required:
        return "expired" if now >= ledger.expires_at else "provisional"
    return (
        "expired_pending_ratification"
        if now >= ledger.expires_at
        else "provisional_pending_ratification"
    )
