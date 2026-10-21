# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic rule-based triage, secretariat queues and quiet executive digests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from careops_process.hub_domain import GovernanceMatter
from careops_process.hub_views import (
    AttentionContext,
    DigestPolicy,
    RoutingPolicy,
    build_digest,
    build_portfolio,
    build_secretariat_queue,
    render_decision_brief,
    triage,
)
from tests.test_hub_domain import (
    advance,
    canonical_records,
    complete_template,
    completed_matter,
    matter,
    template,
)

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def policy() -> RoutingPolicy:
    """Use explicit synthetic priorities; these do not prescribe IHG escalation rules."""
    return RoutingPolicy.model_validate(
        {
            "scope_ref": "synthetic-scope",
            "policy_ref": "synthetic-routing",
            "rules": [
                {
                    "trigger": "district_threshold",
                    "route": "district",
                    "owner_role": "synthetic-district",
                    "authority_ref": "synthetic-district-policy",
                },
                {
                    "trigger": "urgent_criteria_met",
                    "route": "urgent_out_of_session",
                    "owner_role": "synthetic-chair",
                    "authority_ref": "synthetic-urgency-policy",
                },
                {
                    "trigger": "executive_decision_required",
                    "route": "scheduled_agenda",
                    "owner_role": "synthetic-secretariat",
                    "authority_ref": "synthetic-agenda-policy",
                },
                {
                    "trigger": "assurance_only",
                    "route": "assurance",
                    "owner_role": "synthetic-assurance",
                    "authority_ref": "synthetic-assurance-policy",
                },
                {
                    "trigger": "operational_delegation",
                    "route": "operational",
                    "owner_role": "synthetic-operational",
                    "authority_ref": "synthetic-delegation-policy",
                },
            ],
        }
    )


@pytest.mark.parametrize(
    ("trigger", "route"),
    [
        ("district_threshold", "district"),
        ("urgent_criteria_met", "urgent_out_of_session"),
        ("executive_decision_required", "scheduled_agenda"),
        ("assurance_only", "assurance"),
        ("operational_delegation", "operational"),
    ],
)
def test_routes_require_explicit_trigger_and_authority(trigger: str, route: str) -> None:
    """Triage uses selected configured rules rather than hard-coded clinical authority."""
    context = AttentionContext.model_validate({trigger: True})
    assert triage(matter(), context, policy()).route == route
    assert triage(matter(), AttentionContext(), policy()).route == "hold_for_triage"


def test_routing_scope_classification_and_priority_are_closed() -> None:
    """Conflicting contexts use explicit policy order, while wrong scope stays inaccessible."""
    context = AttentionContext(district_threshold=True, urgent_criteria_met=True)
    assert triage(matter(), context, policy()).route == "district"
    unknown = GovernanceMatter.model_validate(
        {**matter().model_dump(), "classification": "unconfirmed"}
    )
    assert triage(unknown, context, policy()).route == "hold_for_triage"
    wrong_scope = RoutingPolicy.model_validate(
        {**policy().model_dump(), "scope_ref": "another-scope"}
    )
    with pytest.raises(ValueError, match="scope"):
        triage(matter(), context, wrong_scope)


def test_exception_portfolio_excludes_routine_and_inaccessible_matters() -> None:
    """Executives receive material exceptions and overdue actions, not all routine changes."""
    material = GovernanceMatter.model_validate({**matter().model_dump(), "risk": "material"})
    records = [
        material,
        GovernanceMatter.model_validate({**matter().model_dump(), "matter_id": "routine"}),
    ]
    result = build_portfolio(records, actor_scope_ref="synthetic-scope", now=NOW)
    assert len(result) == 1
    assert result[0].reasons == ("material_risk",)
    hidden = GovernanceMatter.model_validate(
        {**material.model_dump(), "scope_ref": "another-scope"}
    )
    protected = GovernanceMatter.model_validate(
        {**material.model_dump(), "classification": "protected"}
    )
    assert build_portfolio([hidden, protected], actor_scope_ref="synthetic-scope", now=NOW) == ()


def test_overdue_dependencies_and_assurance_are_actionable_portfolio_flags() -> None:
    """Combine attention reasons without copying canonical actions or evidence."""
    value = GovernanceMatter.model_validate(
        {
            **matter().model_dump(),
            "actions": [
                {
                    "action_id": "synthetic-action",
                    "owner_ref": "synthetic-owner",
                    "due_at": NOW - timedelta(days=1),
                }
            ],
            "linked_matters": [
                {
                    "matter_id": "synthetic-dependency",
                    "relation": "depends_on",
                    "provenance_ref": "synthetic-link",
                }
            ],
            "risk": "higher",
        }
    )
    result = build_portfolio([value], actor_scope_ref="synthetic-scope", now=NOW)
    assert {"overdue_actions", "dependencies", "higher_risk"} <= set(result[0].reasons)
    assert "synthetic-owner" not in result[0].model_dump_json()


def test_digest_has_configured_frequency_cap_and_duplicate_suppression() -> None:
    """The same reporting interval cannot repeatedly notify the same snapshot."""
    value = GovernanceMatter.model_validate({**matter().model_dump(), "risk": "material"})
    records = [
        value,
        GovernanceMatter.model_validate({**value.model_dump(), "matter_id": "synthetic-matter-2"}),
    ]
    configured = DigestPolicy(enabled=True, maximum_items=1, interval_days=7)
    digest = build_digest(records, actor_scope_ref="synthetic-scope", policy=configured, now=NOW)
    assert digest is not None
    assert len(digest.items) == 1
    assert digest.omitted_count == 1
    assert (
        build_digest(
            records,
            actor_scope_ref="synthetic-scope",
            policy=configured,
            now=NOW,
            previous_digest_key=digest.digest_key,
        )
        is None
    )
    assert (
        build_digest(
            records,
            actor_scope_ref="synthetic-scope",
            policy=DigestPolicy(enabled=False, maximum_items=1, interval_days=7),
            now=NOW,
        )
        is None
    )
    assert (
        build_digest([matter()], actor_scope_ref="synthetic-scope", policy=configured, now=NOW)
        is None
    )


def test_brief_uses_references_and_minimised_labels_only() -> None:
    """Brief rendering provides the decision structure without retrieving sensitive evidence."""
    value = GovernanceMatter.model_validate({**matter().model_dump(), **canonical_records()})
    brief = render_decision_brief(value, actor_scope_ref="synthetic-scope")
    assert "Question" in brief
    assert "Recommendation" in brief
    assert "Authority" in brief
    assert "synthetic-response" not in brief
    assert "synthetic-quorum" not in brief
    with pytest.raises(ValueError, match="scope"):
        render_decision_brief(value, actor_scope_ref="another-scope")


def test_no_sensitive_free_text_or_inconsistent_policy_input() -> None:
    """No queue or policy payload accepts arbitrary narrative or zero notification limits."""
    with pytest.raises(ValidationError):
        AttentionContext.model_validate({"clinical_narrative": "synthetic-sensitive"})
    with pytest.raises(ValidationError):
        DigestPolicy(enabled=True, maximum_items=0, interval_days=7)


def test_routine_secretariat_work_does_not_fill_executive_digest() -> None:
    """Routine intake belongs to the secretariat; completed matters are not open exceptions."""
    submitted = advance(matter(), "submitted", template())
    assert build_portfolio([submitted], actor_scope_ref="synthetic-scope", now=NOW) == ()
    queue = build_secretariat_queue([submitted], actor_scope_ref="synthetic-scope")
    assert queue[0].reasons == ("intake_triage",)
    archived = advance(completed_matter(), "archived", complete_template())
    archived = GovernanceMatter.model_validate({**archived.model_dump(), "risk": "material"})
    assert build_portfolio([archived], actor_scope_ref="synthetic-scope", now=NOW) == ()


def test_duplicate_canonical_matters_cannot_create_duplicate_digest_rows() -> None:
    """Conflicting source snapshots must be reconciled before notification candidates are built."""
    material = GovernanceMatter.model_validate({**matter().model_dump(), "risk": "material"})
    with pytest.raises(ValueError, match="duplicate canonical"):
        build_portfolio([material, material], actor_scope_ref="synthetic-scope", now=NOW)


def test_duplicate_routing_rules_ambiguous_time_and_protected_brief_rejected() -> None:
    """Hold ambiguous rule order, timezone and classification boundaries closed."""
    with pytest.raises(ValidationError):
        RoutingPolicy.model_validate(
            {**policy().model_dump(), "rules": [policy().rules[0], policy().rules[0]]}
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        build_portfolio([], actor_scope_ref="synthetic-scope", now=datetime(2026, 10, 14))  # noqa: DTZ001
    protected = GovernanceMatter.model_validate(
        {**matter().model_dump(), "classification": "protected"}
    )
    with pytest.raises(ValueError, match="classification"):
        render_decision_brief(protected, actor_scope_ref="synthetic-scope")


def test_conflicting_snapshots_rejected_before_filtering() -> None:
    """Input order and stale classification cannot choose which canonical snapshot wins."""
    routine = matter()
    material = GovernanceMatter.model_validate({**routine.model_dump(), "risk": "material"})
    protected = GovernanceMatter.model_validate(
        {**material.model_dump(), "classification": "protected"}
    )
    submitted = advance(matter(), "submitted", template())
    for records in (
        [routine, material],
        [material, routine],
        [protected, material],
        [material, protected],
    ):
        with pytest.raises(ValueError, match="duplicate canonical"):
            build_portfolio(records, actor_scope_ref="synthetic-scope", now=NOW)
    with pytest.raises(ValueError, match="duplicate canonical"):
        build_secretariat_queue([submitted, submitted], actor_scope_ref="synthetic-scope")


def test_closed_dependencies_do_not_generate_routine_executive_noise() -> None:
    """Only unresolved or unknown dependencies warrant the executive exception reason."""
    parent = GovernanceMatter.model_validate(
        {
            **matter().model_dump(),
            "linked_matters": [
                {
                    "matter_id": "synthetic-dependency",
                    "relation": "depends_on",
                    "provenance_ref": "synthetic-link",
                }
            ],
        }
    )
    dependency = GovernanceMatter.model_validate(
        {**completed_matter().model_dump(), "matter_id": "synthetic-dependency"}
    )
    assert build_portfolio([parent, dependency], actor_scope_ref="synthetic-scope", now=NOW) == ()


def test_decision_ratification_and_assurance_portfolio_reasons() -> None:
    """Show distinct actionable stages without copying participants or protected records."""
    closed = completed_matter()
    for state, history_length, reason in (
        ("decision_required", 4, "decision_required"),
        ("provisionally_decided", 5, "ratification_gap"),
        ("assurance_review", 8, "assurance_review"),
    ):
        value = GovernanceMatter.model_validate(
            {
                **closed.model_dump(),
                "state": state,
                "history": closed.history[:history_length],
                "revision": history_length,
            }
        )
        assert (
            reason
            in build_portfolio([value], actor_scope_ref="synthetic-scope", now=NOW)[0].reasons
        )
