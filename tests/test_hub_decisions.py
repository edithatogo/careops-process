# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic configured collective-decision and ratification tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from careops_process.hub_decisions import (
    DecisionRule,
    DecisionSession,
    apply_decision_transition,
    decision_rule_digest,
    evaluate_decision,
)
from careops_process.hub_domain import (
    GovernanceMatter,
    WorkflowTemplate,
    apply_transition,
    create_matter,
)
from tests.test_hub_domain import advance, canonical_records, command, complete_template

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def rule(**changes: Any) -> DecisionRule:  # noqa: ANN401
    """Configure a synthetic two-of-three policy, never an IHG quorum default."""
    value: dict[str, Any] = {
        "rule_id": "synthetic-rule",
        "scope_ref": "synthetic-scope",
        "authority_source_ref": "synthetic-terms",
        "approved_policy_ref": "synthetic-policy",
        "eligible_principals": ["synthetic-a", "synthetic-b", "synthetic-c"],
        "minimum_participants": 2,
        "method": "quorum",
        "majority_denominator": "eligible",
        "decision_outcome": "approval",
        "chair_ref": "synthetic-chair",
        "conflict_policy": "exclude_from_quorum",
        "ratification_required": True,
        "template_version": "1.0.0",
    }
    value.update(changes)
    return DecisionRule.model_validate(value)


def session(**changes: Any) -> DecisionSession:  # noqa: ANN401
    """Record synthetic participation with distinct chair and ratification evidence."""
    value: dict[str, Any] = {
        "session_id": "synthetic-session",
        "scope_ref": "synthetic-scope",
        "rule_id": "synthetic-rule",
        "authority_source_ref": "synthetic-terms",
        "matter_id": "synthetic-matter-1",
        "decision_id": "synthetic-decision",
        "template_version": "1.0.0",
        "review_cycle": 0,
        "responses": [
            {
                "actor_ref": actor,
                "principal_ref": actor,
                "outcome": "approval",
                "recorded_at": NOW,
                "response_record_ref": "synthetic-response",
            }
            for actor in ("synthetic-a", "synthetic-b")
        ],
        "chair_confirmation_actor_ref": "synthetic-chair",
        "chair_confirmation_ref": "synthetic-chair-evidence",
        "minute_ref": "synthetic-minute",
        "ratification_ref": "synthetic-ratification",
    }
    value.update(changes)
    return DecisionSession.model_validate(value)


def test_one_individual_approval_cannot_be_a_collective_decision() -> None:
    """An individual card response cannot satisfy a configured collective rule."""
    value = session(responses=session().responses[:1])
    result = evaluate_decision(rule(), value, now=NOW)
    assert result.collective_confirmed is False
    assert "quorum_not_met" in result.gaps


def test_quorum_chair_minutes_and_ratification_all_required() -> None:
    """Technical approval responses remain provisional until every configured gate passes."""
    assert evaluate_decision(rule(), session(), now=NOW).collective_confirmed is True
    for field, code in (
        ("chair_confirmation_ref", "chair_confirmation_missing"),
        ("minute_ref", "minute_reference_missing"),
        ("ratification_ref", "ratification_missing"),
    ):
        result = evaluate_decision(rule(), session(**{field: None}), now=NOW)
        assert result.collective_confirmed is False
        assert code in result.gaps


@pytest.mark.parametrize(
    "outcome", ["consultation", "recommendation", "noting", "decline", "return_for_further_work"]
)
def test_advisory_or_different_outcomes_do_not_count_as_approval(outcome: str) -> None:
    """Consultation, noting and recommendations retain their own semantics."""
    responses = [{**response.model_dump(), "outcome": outcome} for response in session().responses]
    result = evaluate_decision(rule(), session(responses=responses), now=NOW)
    assert result.collective_confirmed is False


def test_conflict_recusal_and_unauthorized_participants_excluded() -> None:
    """An ineligible, conflicted or recused participant cannot manufacture quorum."""
    for changes in (
        {"conflicted": True},
        {"recused": True},
        {"principal_ref": "synthetic-outsider", "actor_ref": "synthetic-outsider"},
    ):
        responses = [
            session().responses[0].model_dump(),
            {**session().responses[1].model_dump(), **changes},
        ]
        result = evaluate_decision(rule(), session(responses=responses), now=NOW)
        assert result.collective_confirmed is False


def test_delegate_requires_authority_and_cannot_vote_twice() -> None:
    """Delegates represent one principal and must not add a second quorum vote."""
    responses = [
        session().responses[0].model_dump(),
        {
            **session().responses[1].model_dump(),
            "actor_ref": "synthetic-delegate",
            "delegation_ref": "synthetic-delegation",
        },
    ]
    assert (
        evaluate_decision(rule(), session(responses=responses), now=NOW).collective_confirmed
        is True
    )
    responses[1]["delegation_ref"] = None
    assert (
        evaluate_decision(rule(), session(responses=responses), now=NOW).collective_confirmed
        is False
    )
    duplicates = [session().responses[0].model_dump(), session().responses[0].model_dump()]
    with pytest.raises(ValidationError):
        session(responses=duplicates)


def test_same_delegate_cannot_occupy_multiple_principal_seats() -> None:
    """One person cannot fill two distinct quorum seats through delegation."""
    responses = [
        {
            **response.model_dump(),
            "actor_ref": "synthetic-delegate",
            "delegation_ref": "synthetic-delegation",
        }
        for response in session().responses
    ]
    with pytest.raises(ValidationError):
        session(responses=responses)


def test_expired_out_of_session_and_future_responses_fail_closed() -> None:
    """Expiry and chronology gates prevent stale or future decisions being confirmed."""
    result = evaluate_decision(rule(), session(expires_at=NOW - timedelta(seconds=1)), now=NOW)
    assert "out_of_session_expired" in result.gaps
    responses = [
        {**response.model_dump(), "recorded_at": NOW + timedelta(seconds=1)}
        for response in session().responses
    ]
    assert (
        evaluate_decision(rule(), session(responses=responses), now=NOW).collective_confirmed
        is False
    )


def test_majority_and_unanimous_semantics_are_explicit_configuration() -> None:
    """Voting rules use their configured denominator rather than a guessed meeting convention."""
    assert (
        evaluate_decision(rule(method="majority"), session(), now=NOW).collective_confirmed is True
    )
    assert (
        evaluate_decision(rule(method="unanimous"), session(), now=NOW).collective_confirmed
        is False
    )
    assert (
        evaluate_decision(
            rule(ratification_required=False), session(ratification_ref=None), now=NOW
        ).collective_confirmed
        is True
    )
    assert (
        evaluate_decision(
            rule(conflict_policy="hold_decision"), session(), now=NOW
        ).collective_confirmed
        is True
    )


def test_scope_rule_authority_and_chair_mismatch_are_closed() -> None:
    """A valid response set cannot be reused under a different body or authority."""
    for changes in (
        {"scope_ref": "different-scope"},
        {"rule_id": "different-rule"},
        {"authority_source_ref": "different-authority"},
        {"chair_confirmation_actor_ref": "different-chair"},
    ):
        assert evaluate_decision(rule(), session(**changes), now=NOW).collective_confirmed is False


def test_invalid_quorum_and_sensitive_response_fields_rejected() -> None:
    """Reject impossible quorum and free-text comments before evaluation."""
    for quorum in (0, 4, True):
        with pytest.raises(ValidationError):
            rule(minimum_participants=quorum)
    responses = [{**session().responses[0].model_dump(), "comments": "synthetic-sensitive"}]
    with pytest.raises(ValidationError):
        session(responses=responses)


def decision_matter() -> tuple[GovernanceMatter, WorkflowTemplate]:
    """Bind a synthetic matter to the exact collective decision rule."""
    configured = WorkflowTemplate.model_validate(
        {
            **complete_template().model_dump(),
            "decision_rule_ref": "synthetic-rule",
            "decision_rule_digest": decision_rule_digest(rule()),
        }
    )
    value = create_matter(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        classification="low_sensitivity_metadata",
        source_ref="synthetic-source",
        template=configured,
    )
    value = GovernanceMatter.model_validate({**value.model_dump(), **canonical_records()})
    for state in ("submitted", "triaged", "under_review", "decision_required"):
        value = advance(value, state, configured)
    return value, configured


def test_collective_workflow_binds_rule_matter_cycle_version_and_response_outcome() -> None:
    """A different matter, review cycle or workflow version cannot reuse approval responses."""
    value, configured = decision_matter()
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    for changes in (
        {"matter_id": "another-matter"},
        {"review_cycle": 1},
        {"template_version": "2.0.0"},
        {"decision_id": "another-decision"},
    ):
        with pytest.raises(ValueError, match="decision binding"):
            apply_decision_transition(
                value, event, template=configured, rule=rule(), session=session(**changes), now=NOW
            )
    result = apply_decision_transition(
        value, event, template=configured, rule=rule(), session=session(), now=NOW
    )
    assert result.state == "provisionally_decided"
    ratify = command(
        event_id="synthetic-event-6",
        replay_key="synthetic-replay-6",
        expected_revision=5,
        to_state="ratified",
    )
    with pytest.raises(ValueError, match="collective decision"):
        apply_decision_transition(
            result,
            ratify,
            template=configured,
            rule=rule(),
            session=session(responses=session().responses[:1]),
            now=NOW,
        )
    assert (
        apply_decision_transition(
            result, ratify, template=configured, rule=rule(), session=session(), now=NOW
        ).state
        == "ratified"
    )


def test_voting_may_be_provisional_until_ratification_but_not_final() -> None:
    """A satisfied voting rule can create a provisional record while finalization stays gated."""
    value, configured = decision_matter()
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    provisional = apply_decision_transition(
        value,
        event,
        template=configured,
        rule=rule(),
        session=session(ratification_ref=None),
        now=NOW,
    )
    event = command(
        event_id="synthetic-event-6",
        replay_key="synthetic-replay-6",
        expected_revision=5,
        to_state="ratified",
    )
    with pytest.raises(ValueError, match="collective decision"):
        apply_decision_transition(
            provisional,
            event,
            template=configured,
            rule=rule(),
            session=session(ratification_ref=None),
            now=NOW,
        )


def test_common_transition_boundary_cannot_bypass_collective_controls() -> None:
    """Calling the general lifecycle API cannot avoid the configured voting controls."""
    value, configured = decision_matter()
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    with pytest.raises(ValueError, match="collective"):
        apply_transition(value, event, template=configured, now=NOW)


def test_same_rule_id_cannot_hide_changed_quorum_or_participants() -> None:
    """The whole collective rule must match the template fingerprint, not only its ID."""
    value, configured = decision_matter()
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    with pytest.raises(ValueError, match="fingerprint"):
        apply_decision_transition(
            value,
            event,
            template=configured,
            rule=rule(minimum_participants=1),
            session=session(responses=session().responses[:1]),
            now=NOW,
        )


def test_ratification_and_vote_must_reference_same_decision_and_evidence() -> None:
    """An evaluated vote cannot ratify a different canonical decision or minute."""
    value, configured = decision_matter()
    first = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    provisional = apply_decision_transition(
        value, first, template=configured, rule=rule(), session=session(), now=NOW
    )
    event = command(
        event_id="synthetic-event-6",
        replay_key="synthetic-replay-6",
        expected_revision=5,
        to_state="ratified",
    )
    for field in (
        "decision_id",
        "minute_or_out_of_session_ref",
        "chair_confirmation_ref",
        "ratification_record_ref",
    ):
        ratification = provisional.ratification
        assert ratification is not None
        broken_value = {
            **provisional.model_dump(),
            "ratification": {**ratification.model_dump(), field: "synthetic-wrong-record"},
        }
        if field == "decision_id":
            broken_value["decisions"] = [
                *provisional.decisions,
                provisional.decisions[0].model_copy(
                    update={"decision_id": "synthetic-wrong-record"}
                ),
            ]
        broken = GovernanceMatter.model_validate(broken_value)
        with pytest.raises(ValueError, match="ratification binding"):
            apply_decision_transition(
                broken, event, template=configured, rule=rule(), session=session(), now=NOW
            )


def test_transition_cannot_predate_its_authorizing_responses() -> None:
    """A later evaluation time cannot make future-to-event votes authorize an earlier decision."""
    value, configured = decision_matter()
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    responses = [
        {**response.model_dump(), "recorded_at": NOW + timedelta(hours=1)}
        for response in session().responses
    ]
    with pytest.raises(ValueError, match="collective"):
        apply_decision_transition(
            value,
            event,
            template=configured,
            rule=rule(),
            session=session(responses=responses),
            now=NOW + timedelta(hours=2),
        )


def test_collective_replay_is_idempotent_after_expiry() -> None:
    """Return historical state on exact replay after session expiry."""
    value, configured = decision_matter()
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    scoped_session = session(expires_at=NOW + timedelta(minutes=1))
    applied = apply_decision_transition(
        value, event, template=configured, rule=rule(), session=scoped_session, now=NOW
    )
    assert (
        apply_decision_transition(
            applied,
            event,
            template=configured,
            rule=rule(),
            session=scoped_session,
            now=NOW + timedelta(hours=2),
        )
        == applied
    )


def test_collective_transition_accepts_resolved_dependency_evidence() -> None:
    """The collective wrapper preserves the general engine's dependency contract."""
    value, configured = decision_matter()
    value = GovernanceMatter.model_validate(
        {
            **value.model_dump(),
            "linked_matters": [
                {
                    "matter_id": "synthetic-dependency",
                    "relation": "depends_on",
                    "provenance_ref": "synthetic-link",
                }
            ],
        }
    )
    event = command(
        event_id="synthetic-event-5",
        replay_key="synthetic-replay-5",
        expected_revision=4,
        to_state="provisionally_decided",
    )
    assert (
        apply_decision_transition(
            value,
            event,
            template=configured,
            rule=rule(),
            session=session(),
            now=NOW,
            dependency_states={"synthetic-dependency": "closed"},
        ).state
        == "provisionally_decided"
    )


def test_conflict_hold_participating_majority_and_ambiguous_clock() -> None:
    """Apply the explicit conflict policy and denominator without inventing default rules."""
    conflicted = [{**response.model_dump(), "conflicted": True} for response in session().responses]
    evaluated = evaluate_decision(
        rule(conflict_policy="hold_decision"), session(responses=conflicted), now=NOW
    )
    assert "conflict_requires_resolution" in evaluated.gaps
    assert (
        evaluate_decision(
            rule(method="majority", majority_denominator="participating"), session(), now=NOW
        ).collective_confirmed
        is True
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_decision(rule(), session(), now=datetime(2026, 10, 14))  # noqa: DTZ001


def test_acting_arrangement_and_exported_decision_contracts() -> None:
    """Record explicit acting authority and keep the reusable decision schema aligned."""
    responses = [
        session().responses[0].model_dump(),
        {
            **session().responses[1].model_dump(),
            "actor_ref": "synthetic-acting",
            "acting_arrangement_ref": "synthetic-acting-record",
        },
    ]
    assert (
        evaluate_decision(rule(), session(responses=responses), now=NOW).collective_confirmed
        is True
    )
    root = Path(__file__).parents[1] / "contracts"
    for name, model in (
        ("hub-decision-rule", DecisionRule),
        ("hub-decision-session", DecisionSession),
    ):
        assert (
            json.loads((root / f"{name}.schema.json").read_text(encoding="utf-8"))
            == model.model_json_schema()
        )
