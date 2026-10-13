"""Synthetic approved-reference briefs, agendas, minutes and urgent-decision ledgers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from careops_process.hub_decisions import DecisionRule, DecisionSession, decision_rule_digest
from careops_process.hub_domain import GovernanceMatter
from careops_process.hub_meetings import (
    BriefReferences,
    MeetingAgenda,
    UrgentDecisionLedger,
    add_agenda_entry,
    render_reference_brief,
    urgent_decision_status,
)
from careops_process.hub_meetings import (
    record_minutes as record_minutes_impl,
)
from tests.test_hub_decisions import decision_matter, rule
from tests.test_hub_decisions import session as base_session

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def matter() -> GovernanceMatter:
    """Return the actual synthetic decision-required matter for the agenda snapshot."""
    return decision_matter()[0]


def session(**changes: Any) -> DecisionSession:  # noqa: ANN401
    """Bind synthetic voting evidence to its exact meeting."""
    changes.setdefault("meeting_ref", "synthetic-meeting")
    return base_session(**changes)


def record_minutes(  # noqa: PLR0913
    agenda: MeetingAgenda,
    configured: DecisionRule,
    voted: DecisionSession,
    *,
    actor_ref: str,
    expected_revision: int,
    minute_ref: str,
    chair_confirmation_ref: str,
    now: datetime,
    current_matter: GovernanceMatter | None = None,
) -> MeetingAgenda:
    """Supply the controlled current-matter fixture to the real minute-recording API."""
    return record_minutes_impl(
        agenda,
        configured,
        voted,
        matter=current_matter or matter(),
        actor_ref=actor_ref,
        expected_revision=expected_revision,
        minute_ref=minute_ref,
        chair_confirmation_ref=chair_confirmation_ref,
        now=now,
    )


def brief() -> BriefReferences:
    """Provide synthetic controlled-record references, without their protected contents."""
    return BriefReferences(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        template_version="1.0.0",
        approval_ref="synthetic-brief-approval",
        question_ref="synthetic-question",
        recommendation_ref="synthetic-recommendation",
        alternatives_ref="synthetic-options",
        risk_ref="synthetic-risk",
        authority_ref="synthetic-terms",
        conflicts_ref="synthetic-conflicts",
        consultations_ref="synthetic-consultations",
        proposed_actions_ref="synthetic-actions",
        decision_rule_digest=decision_rule_digest(rule()),
    )


def meeting() -> MeetingAgenda:
    """Create an explicitly scoped synthetic meeting and secretariat membership."""
    return MeetingAgenda(
        meeting_id="synthetic-meeting",
        scope_ref="synthetic-scope",
        chair_ref="synthetic-chair",
        secretariat_refs=("synthetic-secretariat",),
        participant_refs=("synthetic-a", "synthetic-b", "synthetic-c"),
        scheduled_at=NOW + timedelta(days=1),
        agenda_deadline=NOW + timedelta(hours=1),
        authority_ref="synthetic-terms",
        cadence_policy_ref="synthetic-meeting-policy",
    )


def test_approved_brief_references_generate_bounded_agenda_and_rendered_brief() -> None:
    """Only approved metadata references populate a scoped agenda and brief."""
    agenda = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )
    assert agenda.revision == 1
    assert agenda.entries[0].matter_id == matter().matter_id
    assert meeting().entries == ()
    rendered = render_reference_brief(matter(), brief(), actor_scope_ref="synthetic-scope")
    assert "synthetic-question" in rendered
    assert "Question" in rendered
    assert "synthetic-brief-approval" not in rendered


def test_wrong_scope_policy_version_actor_and_revision_fail_closed() -> None:
    """Agenda writes require consistent scope, authorised secretariat and exact revision."""
    for actor_ref, revision in (("synthetic-outsider", 0), ("synthetic-secretariat", 1)):
        with pytest.raises(ValueError, match=r"actor|revision"):
            add_agenda_entry(
                meeting(),
                matter(),
                brief(),
                now=NOW,
                actor_ref=actor_ref,
                expected_revision=revision,
            )
    for changes in (
        {"scope_ref": "other-scope"},
        {"matter_id": "other-matter"},
        {"template_version": "2.0.0"},
    ):
        changed = BriefReferences.model_validate({**brief().model_dump(), **changes})
        with pytest.raises(ValueError, match="binding"):
            add_agenda_entry(
                meeting(),
                matter(),
                changed,
                actor_ref="synthetic-secretariat",
                expected_revision=0,
                now=NOW,
            )


def test_agenda_deadline_requires_explicit_chair_exception() -> None:
    """Late agenda additions require an explicit exception record, not an inferred urgent label."""
    with pytest.raises(ValueError, match="deadline"):
        add_agenda_entry(
            meeting(),
            matter(),
            brief(),
            actor_ref="synthetic-secretariat",
            expected_revision=0,
            now=NOW + timedelta(hours=2),
        )
    agenda = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW + timedelta(hours=2),
        chair_exception_ref="synthetic-chair-exception",
    )
    assert agenda.entries[0].chair_exception_ref == "synthetic-chair-exception"


def test_duplicate_agenda_entry_is_idempotent_but_changed_snapshot_rejected() -> None:
    """Keep identical entry retry harmless and reject silent changes to the brief."""
    initial = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )
    assert (
        add_agenda_entry(
            initial,
            matter(),
            brief(),
            actor_ref="synthetic-secretariat",
            expected_revision=0,
            now=NOW,
        )
        == initial
    )
    changed = BriefReferences.model_validate(
        {**brief().model_dump(), "question_ref": "synthetic-other-question"}
    )
    with pytest.raises(ValueError, match="duplicate"):
        add_agenda_entry(
            initial,
            matter(),
            changed,
            actor_ref="synthetic-secretariat",
            expected_revision=1,
            now=NOW,
        )


def test_minutes_use_collective_rules_and_keep_individual_vote_provisional() -> None:
    """Minute assembly cannot convert an individual response into a collective decision."""
    agenda = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )
    recorded = record_minutes(
        agenda,
        rule(),
        session(),
        actor_ref="synthetic-secretariat",
        expected_revision=1,
        minute_ref="synthetic-minute",
        chair_confirmation_ref="synthetic-chair-evidence",
        now=NOW + timedelta(days=1),
    )
    assert recorded.decisions[0].collective_confirmed is True
    one_vote = session(responses=session().responses[:1])
    provisional = record_minutes(
        agenda,
        rule(),
        one_vote,
        actor_ref="synthetic-secretariat",
        expected_revision=1,
        minute_ref="synthetic-minute",
        chair_confirmation_ref="synthetic-chair-evidence",
        now=NOW + timedelta(days=1),
    )
    assert provisional.decisions[0].collective_confirmed is False


def test_minute_scope_authority_membership_chair_and_reference_binding() -> None:
    """A meeting cannot minute responses from another matter, body, participant set or record."""
    agenda = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )
    for changes in (
        {"matter_id": "other-matter"},
        {"scope_ref": "other-scope"},
        {"chair_confirmation_actor_ref": "other-chair"},
        {"minute_ref": "other-minute"},
    ):
        with pytest.raises(ValueError, match="binding"):
            record_minutes(
                agenda,
                rule(),
                session(**changes),
                actor_ref="synthetic-secretariat",
                expected_revision=1,
                minute_ref="synthetic-minute",
                chair_confirmation_ref="synthetic-chair-evidence",
                now=NOW + timedelta(days=1),
            )


def test_urgent_ledger_distinguishes_expiry_from_later_ratification() -> None:
    """Keep an expired provisional urgent decision open until later ratification evidence exists."""
    ledger = UrgentDecisionLedger(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        decision_id="synthetic-decision",
        decision_session_id="synthetic-session",
        policy_ref="synthetic-urgency-policy",
        authority_ref="synthetic-terms",
        template_version="1.0.0",
        review_cycle=0,
        approved_ratification_policy_digest=decision_rule_digest(
            rule(decision_outcome="ratification")
        ),
        original_response_refs=("synthetic-response",),
        urgency_evidence_ref="synthetic-urgency",
        provisionally_decided_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        ratification_required=True,
    )
    assert urgent_decision_status(ledger, now=NOW) == "provisional_pending_ratification"
    assert (
        urgent_decision_status(ledger, now=NOW + timedelta(hours=2))
        == "expired_pending_ratification"
    )
    ratified = UrgentDecisionLedger.model_validate(
        {
            **ledger.model_dump(),
            "ratification_ref": "synthetic-later-ratification",
            "ratification_rule": rule(decision_outcome="ratification"),
            "ratification_session": session(
                session_id="synthetic-later-session",
                ratification_ref="synthetic-later-ratification",
                responses=[
                    {
                        **response.model_dump(),
                        "outcome": "ratification",
                        "recorded_at": NOW + timedelta(hours=2),
                        "response_record_ref": "synthetic-later-response-" + response.actor_ref,
                    }
                    for response in session().responses
                ],
            ),
        }
    )
    assert urgent_decision_status(ratified, now=NOW + timedelta(hours=2)) == "ratified"


def test_sensitive_brief_fields_and_invalid_meeting_times_rejected() -> None:
    """No narrative/comment payload enters briefs or meeting metadata."""
    with pytest.raises(ValidationError):
        BriefReferences.model_validate(
            {**brief().model_dump(), "clinical_narrative": "synthetic-sensitive"}
        )
    with pytest.raises(ValidationError):
        MeetingAgenda.model_validate(
            {**meeting().model_dump(), "agenda_deadline": NOW + timedelta(days=2)}
        )


def test_later_ratification_cannot_be_inferred_from_original_approval_or_unbound_reference() -> (
    None
):
    """Only a distinct, bound ratification session can close an urgent ratification gap."""
    ledger = UrgentDecisionLedger(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        decision_id="synthetic-decision",
        decision_session_id="synthetic-session",
        policy_ref="synthetic-urgency-policy",
        authority_ref="synthetic-terms",
        template_version="1.0.0",
        review_cycle=0,
        approved_ratification_policy_digest=decision_rule_digest(
            rule(decision_outcome="ratification")
        ),
        original_response_refs=("synthetic-response",),
        urgency_evidence_ref="synthetic-urgency",
        provisionally_decided_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        ratification_required=True,
        ratification_ref="synthetic-ratification",
        ratification_rule=rule(),
        ratification_session=session(),
    )
    assert urgent_decision_status(ledger, now=NOW + timedelta(hours=2)) != "ratified"


def test_minute_idempotence_and_monotonic_record_times() -> None:
    """Exact minute replay is harmless; a changed or backdated session is rejected."""
    agenda = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )
    minute_time = NOW + timedelta(days=1, hours=2)

    def record(value: MeetingAgenda) -> MeetingAgenda:
        return record_minutes(
            value,
            rule(),
            session(),
            actor_ref="synthetic-secretariat",
            expected_revision=1,
            minute_ref="synthetic-minute",
            chair_confirmation_ref="synthetic-chair-evidence",
            now=minute_time,
        )

    recorded = record(agenda)
    assert record(recorded) == recorded
    with pytest.raises(ValueError, match="chronology"):
        record_minutes(
            recorded,
            rule(),
            session(session_id="synthetic-second-session"),
            actor_ref="synthetic-secretariat",
            expected_revision=2,
            minute_ref="synthetic-minute",
            chair_confirmation_ref="synthetic-chair-evidence",
            now=NOW + timedelta(days=1, hours=1),
        )


def prepared_minutes() -> tuple[MeetingAgenda, MeetingAgenda]:
    """Build a synthetic agenda and its first minute record."""
    agenda = add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )
    recorded = record_minutes(
        agenda,
        rule(),
        session(),
        actor_ref="synthetic-secretariat",
        expected_revision=1,
        minute_ref="synthetic-minute",
        chair_confirmation_ref="synthetic-chair-evidence",
        now=NOW + timedelta(days=1),
    )
    return agenda, recorded


def test_minutes_reject_unknown_canonical_decision_or_review_cycle() -> None:
    """A correctly shaped vote cannot minute a nonexistent decision or a different review cycle."""
    agenda, _ = prepared_minutes()
    for changes in ({"decision_id": "synthetic-nonexistent"}, {"review_cycle": 99}):
        with pytest.raises(ValueError, match="canonical"):
            record_minutes(
                agenda,
                rule(),
                session(**changes),
                actor_ref="synthetic-secretariat",
                expected_revision=1,
                minute_ref="synthetic-minute",
                chair_confirmation_ref="synthetic-chair-evidence",
                now=NOW + timedelta(days=1),
            )


def test_voting_session_cannot_confirm_two_different_meetings() -> None:
    """Meeting-specific session provenance cannot be transplanted to another agenda."""
    another = MeetingAgenda.model_validate(
        {**meeting().model_dump(), "meeting_id": "synthetic-other-meeting"}
    )
    agenda = add_agenda_entry(
        another, matter(), brief(), actor_ref="synthetic-secretariat", expected_revision=0, now=NOW
    )
    with pytest.raises(ValueError, match="binding"):
        record_minutes(
            agenda,
            rule(),
            session(),
            actor_ref="synthetic-secretariat",
            expected_revision=1,
            minute_ref="synthetic-minute",
            chair_confirmation_ref="synthetic-chair-evidence",
            now=NOW + timedelta(days=1),
        )


def test_imported_minutes_reject_off_agenda_authority_chronology_and_confirmation_changes() -> None:
    """Loaded minutes must retain the same binding and confirmation/gap invariants as recording."""
    _, recorded = prepared_minutes()
    for changes in (
        {"matter_id": "synthetic-off-agenda"},
        {"authority_ref": "synthetic-wrong-authority"},
        {"recorded_at": NOW},
        {"collective_confirmed": True, "gaps": ["quorum_not_met"]},
    ):
        with pytest.raises(ValidationError):
            MeetingAgenda.model_validate(
                {
                    **recorded.model_dump(),
                    "decisions": [{**recorded.decisions[0].model_dump(), **changes}],
                }
            )


def test_urgent_ratification_rejects_changed_authority_version_cycle_and_quorum() -> None:
    """Ratification must use the approved pinned policy and canonical decision context."""
    foreign = rule(
        decision_outcome="ratification",
        authority_source_ref="synthetic-other-authority",
        template_version="9.0.0",
        minimum_participants=1,
    )
    voted = session(
        session_id="synthetic-later-session",
        authority_source_ref="synthetic-other-authority",
        template_version="9.0.0",
        review_cycle=99,
        responses=[
            {
                **session().responses[0].model_dump(),
                "outcome": "ratification",
                "recorded_at": NOW + timedelta(hours=2),
                "response_record_ref": "synthetic-later-response",
            }
        ],
    )
    ledger = UrgentDecisionLedger(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        decision_id="synthetic-decision",
        decision_session_id="synthetic-session",
        policy_ref="synthetic-urgency-policy",
        authority_ref="synthetic-terms",
        template_version="1.0.0",
        review_cycle=0,
        approved_ratification_policy_digest=decision_rule_digest(
            rule(decision_outcome="ratification")
        ),
        original_response_refs=("synthetic-response",),
        urgency_evidence_ref="synthetic-urgency",
        provisionally_decided_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        ratification_required=True,
        ratification_ref="synthetic-ratification",
        ratification_rule=foreign,
        ratification_session=voted,
    )
    assert urgent_decision_status(ledger, now=NOW + timedelta(hours=2)) != "ratified"


def test_equivalent_timestamp_spellings_replay_the_same_minute_session() -> None:
    """The same instants in UTC and local time do not create different session fingerprints."""
    _, recorded = prepared_minutes()
    offset = timezone(timedelta(hours=10))
    replay = session(
        responses=[
            {**response.model_dump(), "recorded_at": response.recorded_at.astimezone(offset)}
            for response in session().responses
        ]
    )
    assert (
        record_minutes(
            recorded,
            rule(),
            replay,
            actor_ref="synthetic-secretariat",
            expected_revision=1,
            minute_ref="synthetic-minute",
            chair_confirmation_ref="synthetic-chair-evidence",
            now=NOW + timedelta(days=1),
        )
        == recorded
    )


def test_current_classification_rechecked_before_minute_confirmation() -> None:
    """Reject current protected matters despite stale low-sensitivity agenda snapshots."""
    agenda, _ = prepared_minutes()
    protected = GovernanceMatter.model_validate(
        {**matter().model_dump(), "classification": "protected"}
    )
    with pytest.raises(ValueError, match="canonical"):
        record_minutes(
            agenda,
            rule(),
            session(),
            actor_ref="synthetic-secretariat",
            expected_revision=1,
            minute_ref="synthetic-minute",
            chair_confirmation_ref="synthetic-chair-evidence",
            now=NOW + timedelta(days=1),
            current_matter=protected,
        )


def test_identical_agenda_replay_preserves_original_timestamp_after_deadline() -> None:
    """A retry never appends another entry or changes its original event time."""
    agenda, _ = prepared_minutes()
    assert (
        add_agenda_entry(
            agenda,
            matter(),
            brief(),
            actor_ref="synthetic-secretariat",
            expected_revision=0,
            now=NOW + timedelta(days=2),
        )
        == agenda
    )
