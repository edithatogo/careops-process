"""Synthetic canonical governance lifecycle and versioned-policy contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from careops_process.hub_domain import (
    ActionRecord,
    GovernanceMatter,
    TransitionCommand,
    WorkflowTemplate,
    apply_transition,
    collaboration_projection,
    create_matter,
    draft_templates,
    template_digest,
    validate_template_upgrade,
)

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def template(version: str = "1.0.0") -> WorkflowTemplate:
    """Return explicit synthetic rules; these are not IHG authority decisions."""
    return WorkflowTemplate.model_validate(
        {
            "template_id": "executive_decision",
            "version": version,
            "schema_version": 1,
            "authority_source_ref": "synthetic-terms",
            "approval_ref": "synthetic-approval",
            "roles": ["synthetic-secretariat"],
            "notification_policy": "digest",
            "records_policy_ref": "synthetic-records",
            "closure_requires_evidence": True,
            "rules": [
                {
                    "from_state": "draft",
                    "to_state": "submitted",
                    "allowed_roles": ["synthetic-secretariat"],
                },
                {
                    "from_state": "submitted",
                    "to_state": "triaged",
                    "allowed_roles": ["synthetic-secretariat"],
                },
                {
                    "from_state": "triaged",
                    "to_state": "under_review",
                    "allowed_roles": ["synthetic-secretariat"],
                },
                {
                    "from_state": "under_review",
                    "to_state": "decision_required",
                    "allowed_roles": ["synthetic-secretariat"],
                },
                {
                    "from_state": "submitted",
                    "to_state": "withdrawn",
                    "allowed_roles": ["synthetic-secretariat"],
                },
                {
                    "from_state": "draft",
                    "to_state": "superseded",
                    "allowed_roles": ["synthetic-secretariat"],
                },
                {
                    "from_state": "draft",
                    "to_state": "consolidated",
                    "allowed_roles": ["synthetic-secretariat"],
                },
            ],
        }
    )


def matter() -> GovernanceMatter:
    """Create a synthetic matter pinned to the approved synthetic template."""
    return create_matter(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        classification="low_sensitivity_metadata",
        source_ref="synthetic-source",
        template=template(),
    )


def command(**changes: Any) -> TransitionCommand:  # noqa: ANN401
    """Construct a scoped event with a compare-and-swap revision and replay key."""
    value: dict[str, Any] = {
        "event_id": "synthetic-event-1",
        "replay_key": "synthetic-replay-1",
        "expected_revision": 0,
        "to_state": "submitted",
        "occurred_at": NOW,
        "actor_ref": "synthetic-actor",
        "actor_role": "synthetic-secretariat",
        "actor_scope_ref": "synthetic-scope",
        "evidence_ref": "synthetic-evidence",
    }
    value.update(changes)
    return TransitionCommand.model_validate(value)


def test_create_pins_version_and_digest_without_activating_live_policy() -> None:
    """New matters retain the exact template and version that govern them."""
    value = matter()
    assert value.state == "draft"
    assert value.revision == 0
    assert value.template_version == "1.0.0"
    assert value.template_digest == template_digest(template())
    assert value.execution_mode == "synthetic"


def test_valid_transition_records_identity_authority_and_provenance() -> None:
    """Canonical transition history retains who, when, authority and version."""
    initial = matter()
    changed = apply_transition(initial, command(), template=template(), now=NOW)
    assert changed.state == "submitted"
    assert changed.revision == 1
    assert initial.state == "draft"
    assert changed.history[0].actor_ref == "synthetic-actor"
    assert changed.history[0].authority_source_ref == "synthetic-terms"
    assert changed.history[0].template_version == "1.0.0"


def test_replay_is_idempotent_after_later_events_and_collisions_rejected() -> None:
    """A replay preserves the latest state but reuse for another payload is rejected."""
    first = apply_transition(matter(), command(), template=template(), now=NOW)
    second_command = command(
        event_id="synthetic-event-2",
        replay_key="synthetic-replay-2",
        expected_revision=1,
        to_state="triaged",
    )
    second = apply_transition(first, second_command, template=template(), now=NOW)
    assert apply_transition(second, command(), template=template(), now=NOW) == second
    with pytest.raises(ValueError, match="replay key collision"):
        apply_transition(second, command(to_state="withdrawn"), template=template(), now=NOW)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"expected_revision": 1}, "revision"),
        ({"actor_scope_ref": "another-scope"}, "scope"),
        ({"actor_role": "unauthorised-role"}, "role"),
        ({"to_state": "archived"}, "transition"),
        ({"occurred_at": NOW + timedelta(seconds=1)}, "future"),
    ],
)
def test_invalid_commands_do_not_mutate_canonical_record(
    changes: dict[str, Any], reason: str
) -> None:
    """Invalid sequence, access, authority and timestamp inputs fail before mutation."""
    original = matter()
    with pytest.raises(ValueError, match=reason):
        apply_transition(original, command(**changes), template=template(), now=NOW)
    assert original.history == ()


def test_out_of_order_events_and_event_id_reuse_rejected() -> None:
    """No late event or reused event identity silently rewrites the history."""
    first = apply_transition(matter(), command(), template=template(), now=NOW)
    for changes, reason in [
        (
            {"event_id": "synthetic-event-2", "occurred_at": NOW - timedelta(seconds=1)},
            "out-of-order",
        ),
        ({"event_id": "synthetic-event-1"}, "event ID"),
    ]:
        value = command(
            replay_key="synthetic-replay-2", expected_revision=1, to_state="triaged", **changes
        )
        with pytest.raises(ValueError, match=reason):
            apply_transition(first, value, template=template(), now=NOW)


def test_active_matter_rejects_silent_version_or_rule_changes() -> None:
    """The same name/version cannot hide a change in its governing rules."""
    for changed in (
        template("1.0.1"),
        WorkflowTemplate.model_validate({**template().model_dump(), "notification_policy": "none"}),
    ):
        with pytest.raises(ValueError, match="pinned template"):
            apply_transition(matter(), command(), template=changed, now=NOW)


def test_unapproved_and_empty_templates_cannot_govern_a_matter() -> None:
    """Draft pathway names convey no actual delegation or routing authority."""
    drafts = draft_templates()
    assert len(drafts) == 7  # noqa: PLR2004
    assert {item.template_id for item in drafts} >= {"pra_pitstop", "research_governance"}
    for draft in drafts:
        assert draft.approval_ref is None
        assert draft.rules == ()
        with pytest.raises(ValueError, match="approved configured template"):
            create_matter(
                matter_id="synthetic-matter-2",
                scope_ref="synthetic-scope",
                classification="low_sensitivity_metadata",
                source_ref="synthetic-source",
                template=draft,
            )


def test_live_execution_is_not_implied_by_synthetic_contract() -> None:
    """Local schemas cannot create a live deployment or operating-model approval."""
    value = matter().model_dump()
    value["execution_mode"] = "live"
    with pytest.raises(ValidationError):
        GovernanceMatter.model_validate(value)


def test_sensitive_fields_and_unsupported_classification_rejected() -> None:
    """Canonical metadata and events do not accept narrative or patient identifiers."""
    for field in ("patient_id", "clinical_narrative", "approval_comments"):
        value = matter().model_dump()
        value[field] = "synthetic-sensitive-payload"
        with pytest.raises(ValidationError):
            GovernanceMatter.model_validate(value)
    with pytest.raises(ValidationError):
        command(expected_revision=True)


def test_projection_is_minimal_and_checks_authorized_scope() -> None:
    """Protected evidence and histories never reach a collaboration projection."""
    value = apply_transition(matter(), command(), template=template(), now=NOW)
    rendered = collaboration_projection(value, actor_scope_ref="synthetic-scope")
    assert set(rendered) == {"matter_id", "state", "revision"}
    assert "synthetic-evidence" not in str(rendered)
    with pytest.raises(ValueError, match="scope"):
        collaboration_projection(value, actor_scope_ref="another-scope")
    protected = GovernanceMatter.model_validate(
        {**value.model_dump(), "classification": "protected"}
    )
    with pytest.raises(ValueError, match="classification"):
        collaboration_projection(protected, actor_scope_ref="synthetic-scope")


def test_template_upgrade_requires_compatible_schema_and_explicit_migration() -> None:
    """Active matters cannot move version without a separately reviewed migration."""
    assert (
        validate_template_upgrade(
            template(), template("1.1.0"), migration_ref="synthetic-migration"
        )
        is None
    )
    with pytest.raises(ValueError, match="migration"):
        validate_template_upgrade(template(), template("1.1.0"), migration_ref=None)
    with pytest.raises(ValueError, match="version"):
        validate_template_upgrade(
            template("1.1.0"), template(), migration_ref="synthetic-migration"
        )


def test_invalid_edges_and_evidence_free_closure_policy_cannot_activate() -> None:
    """Reject invalid configured lifecycle edges and weakened records controls."""
    for changes in (
        {
            "rules": [
                {
                    "from_state": "draft",
                    "to_state": "archived",
                    "allowed_roles": ["synthetic-secretariat"],
                }
            ]
        },
        {"closure_requires_evidence": False},
    ):
        with pytest.raises(ValidationError):
            WorkflowTemplate.model_validate({**template().model_dump(), **changes})


def test_completed_action_requires_canonical_closure_evidence() -> None:
    """A task completion flag alone cannot count as completed governed action."""
    with pytest.raises(ValidationError):
        ActionRecord(
            action_id="synthetic-action", owner_ref="synthetic-owner", due_at=NOW, state="completed"
        )


def test_supersession_retains_explicit_destination_and_rejects_missing_destination() -> None:
    """Supersession preserves its direction and provenance rather than a loose relation."""
    for to_state in ("superseded", "consolidated"):
        with pytest.raises(ValueError, match="destination"):
            apply_transition(matter(), command(to_state=to_state), template=template(), now=NOW)
    updated = apply_transition(
        matter(),
        command(to_state="superseded", destination_matter_ref="synthetic-matter-2"),
        template=template(),
        now=NOW,
    )
    assert updated.linked_matters[0].relation == "superseded_by"


def test_replay_digest_does_not_depend_on_timezone_spelling() -> None:
    """Equivalent instants represent the same replay rather than a payload collision."""
    first_command = command(occurred_at="2026-10-14T00:00:00Z")
    first = apply_transition(matter(), first_command, template=template(), now=NOW)
    replay = command(occurred_at="2026-10-14T10:00:00+10:00")
    assert apply_transition(first, replay, template=template(), now=NOW) == first


def complete_template() -> WorkflowTemplate:
    """Configure the specification's lifecycle using synthetic role and policy references."""
    states = (
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
    )
    rules = [
        {"from_state": before, "to_state": after, "allowed_roles": ["synthetic-secretariat"]}
        for before, after in pairwise(states)
    ]
    rules.extend(
        [
            {
                "from_state": "closed",
                "to_state": "under_review",
                "allowed_roles": ["synthetic-secretariat"],
            },
            {
                "from_state": "submitted",
                "to_state": "returned",
                "allowed_roles": ["synthetic-secretariat"],
            },
            {
                "from_state": "returned",
                "to_state": "submitted",
                "allowed_roles": ["synthetic-secretariat"],
            },
            {
                "from_state": "submitted",
                "to_state": "rejected",
                "allowed_roles": ["synthetic-secretariat"],
            },
            {
                "from_state": "rejected",
                "to_state": "under_review",
                "allowed_roles": ["synthetic-secretariat"],
            },
        ]
    )
    return WorkflowTemplate.model_validate(
        {**template().model_dump(), "rules": rules, "outcomes": ["approval", "noting"]}
    )


def canonical_records() -> dict[str, Any]:
    """Build synthetic decision and ratification references for lifecycle tests."""
    return {
        "authority": {
            "authority_source_ref": "synthetic-terms",
            "decision_owner_ref": "synthetic-owner",
        },
        "decisions": [
            {
                "decision_id": "synthetic-decision",
                "outcome": "approval",
                "authority": {
                    "authority_source_ref": "synthetic-terms",
                    "decision_owner_ref": "synthetic-owner",
                },
                "participant_refs": ["synthetic-a", "synthetic-b"],
                "conflict_record_ref": "synthetic-conflicts",
                "response_ref": "synthetic-response",
                "recorded_at": NOW,
                "template_version": "1.0.0",
            }
        ],
        "ratification": {
            "decision_id": "synthetic-decision",
            "ratification_record_ref": "synthetic-ratification",
            "quorum_evidence_ref": "synthetic-quorum",
            "chair_confirmation_ref": "synthetic-chair-evidence",
            "minute_or_out_of_session_ref": "synthetic-minute",
            "recorded_at": NOW,
        },
        "closure_evidence_ref": "synthetic-closure",
        "archive_record_ref": "synthetic-archive",
    }


def advance(
    record: GovernanceMatter, to_state: str, configured: WorkflowTemplate
) -> GovernanceMatter:
    """Advance with a fresh event and exact expected revision."""
    value = command(
        event_id=f"synthetic-event-{record.revision + 1}",
        replay_key=f"synthetic-replay-{record.revision + 1}",
        expected_revision=record.revision,
        to_state=to_state,
    )
    return apply_transition(record, value, template=configured, now=NOW)


def completed_matter() -> GovernanceMatter:
    """Walk the independently specified happy path up to evidence-backed closure."""
    configured = complete_template()
    value = create_matter(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        classification="low_sensitivity_metadata",
        source_ref="synthetic-source",
        template=configured,
    )
    value = GovernanceMatter.model_validate({**value.model_dump(), **canonical_records()})
    for state in (
        "submitted",
        "triaged",
        "under_review",
        "decision_required",
        "provisionally_decided",
        "ratified",
        "actions_open",
        "assurance_review",
        "closed",
    ):
        value = advance(value, state, configured)
    return value


def test_complete_synthetic_lifecycle_and_archive_require_canonical_records() -> None:
    """Every happy-path transition is auditable and archive preserves the canonical record."""
    value = completed_matter()
    archived = advance(value, "archived", complete_template())
    assert archived.state == "archived"
    assert len(archived.history) == 10  # noqa: PLR2004
    assert archived.decisions == value.decisions
    missing_archive = GovernanceMatter.model_validate(
        {**value.model_dump(), "archive_record_ref": None}
    )
    with pytest.raises(ValueError, match="archive record"):
        advance(missing_archive, "archived", complete_template())


def test_reopening_requires_new_cycle_decision_and_ratification() -> None:
    """A previous decision and closure proof cannot finalize a reopened review."""
    value = advance(completed_matter(), "under_review", complete_template())
    assert value.review_cycle == 1
    assert value.ratification is None
    assert value.closure_evidence_ref is None
    assert value.archive_record_ref is None
    assert len(value.past_ratifications) == 1
    value = advance(value, "decision_required", complete_template())
    with pytest.raises(ValueError, match="decision"):
        advance(value, "provisionally_decided", complete_template())


def test_corrupt_history_and_self_links_rejected() -> None:
    """External stores cannot deserialize contradictory revision/state/provenance metadata."""
    first = apply_transition(matter(), command(), template=template(), now=NOW)
    corruptions = [
        {"revision": 2},
        {"state": "draft"},
        {
            "linked_matters": [
                {
                    "matter_id": first.matter_id,
                    "relation": "related",
                    "provenance_ref": "synthetic-link",
                }
            ]
        },
        {"history": [{**first.history[0].model_dump(), "from_state": "triaged"}]},
        {"decisions": [{**canonical_records()["decisions"][0], "template_version": "2.0.0"}]},
    ]
    for changed in corruptions:
        with pytest.raises(ValidationError):
            GovernanceMatter.model_validate({**first.model_dump(), **changed})


def test_return_rejection_and_dependency_controls() -> None:
    """Returning information is reversible; unresolved dependencies hold decision routing."""
    configured = complete_template()
    value = create_matter(
        matter_id="synthetic-matter-1",
        scope_ref="synthetic-scope",
        classification="low_sensitivity_metadata",
        source_ref="synthetic-source",
        template=configured,
    )
    submitted = advance(value, "submitted", configured)
    returned = advance(submitted, "returned", configured)
    assert advance(returned, "submitted", configured).state == "submitted"
    rejected = advance(submitted, "rejected", configured)
    assert advance(rejected, "under_review", configured).review_cycle == 1
    reviewing = advance(advance(submitted, "triaged", configured), "under_review", configured)
    reviewing = GovernanceMatter.model_validate(
        {
            **reviewing.model_dump(),
            "linked_matters": [
                {
                    "matter_id": "synthetic-dependency",
                    "relation": "depends_on",
                    "provenance_ref": "synthetic-link",
                }
            ],
        }
    )
    with pytest.raises(ValueError, match="dependency"):
        advance(reviewing, "decision_required", configured)
    event = command(
        event_id="synthetic-event-4",
        replay_key="synthetic-replay-4",
        expected_revision=3,
        to_state="decision_required",
    )
    assert (
        apply_transition(
            reviewing,
            event,
            template=configured,
            now=NOW,
            dependency_states={"synthetic-dependency": "closed"},
        ).state
        == "decision_required"
    )


def test_decision_ratification_and_closure_gates() -> None:
    """Canonical evidence and unresolved actions control final lifecycle progression."""
    configured = complete_template()
    value = completed_matter()
    reviewing = advance(value, "under_review", configured)
    required = advance(reviewing, "decision_required", configured)
    decision = {
        **canonical_records()["decisions"][0],
        "decision_id": "synthetic-new-decision",
        "review_cycle": 1,
    }
    required = GovernanceMatter.model_validate(
        {**required.model_dump(), "decisions": [*required.decisions, decision]}
    )
    provisional = advance(required, "provisionally_decided", configured)
    with pytest.raises(ValueError, match="ratification"):
        advance(provisional, "ratified", configured)
    for updates in (
        {"closure_evidence_ref": None},
        {
            "actions": [
                {
                    "action_id": "synthetic-action",
                    "owner_ref": "synthetic-owner",
                    "due_at": NOW,
                    "state": "in_progress",
                }
            ]
        },
    ):
        earlier = GovernanceMatter.model_validate(
            {
                **value.model_dump(),
                "history": value.history[:-1],
                "revision": value.revision - 1,
                "state": "assurance_review",
                **updates,
            }
        )
        with pytest.raises(ValueError, match="closure"):
            advance(earlier, "closed", configured)


def test_template_rejects_duplicate_edges_undefined_roles_and_escalation_roles() -> None:
    """Activation validation cannot leave invalid role references in configured paths."""
    values = template().model_dump()
    change_cases: tuple[dict[str, object], ...] = (
        {"rules": [values["rules"][0], values["rules"][0]]},
        {"roles": []},
        {
            "escalation_rules": [
                {
                    "trigger": "material",
                    "target_role": "unknown-role",
                    "threshold_policy_ref": "synthetic-policy",
                }
            ]
        },
    )
    for changes in change_cases:
        with pytest.raises(ValidationError):
            WorkflowTemplate.model_validate({**values, **changes})


def test_loaded_history_rejects_impossible_edges_time_order_and_duplicate_ids() -> None:
    """Deserialization enforces the same audit invariants as applying new events."""
    first = apply_transition(matter(), command(), template=template(), now=NOW)
    second = advance(first, "triaged", template())
    histories = [
        [{**first.history[0].model_dump(), "to_state": "ratified"}],
        [
            first.history[0].model_dump(),
            {**second.history[1].model_dump(), "occurred_at": NOW - timedelta(seconds=1)},
        ],
        [
            first.history[0].model_dump(),
            {**second.history[1].model_dump(), "event_id": first.history[0].event_id},
        ],
        [
            first.history[0].model_dump(),
            {**second.history[1].model_dump(), "replay_key": first.history[0].replay_key},
        ],
    ]
    for history in histories:
        with pytest.raises(ValidationError):
            GovernanceMatter.model_validate(
                {
                    **second.model_dump(),
                    "history": history,
                    "revision": len(history),
                    "state": history[-1]["to_state"],
                }
            )


def test_published_matter_template_and_drafts_match_executable_models() -> None:
    """Keep exported canonical schemas and explicitly unconfigured drafts reproducible."""
    root = Path(__file__).parents[1] / "contracts"
    for name, model in (("hub-matter", GovernanceMatter), ("hub-template", WorkflowTemplate)):
        assert (
            json.loads((root / f"{name}.schema.json").read_text(encoding="utf-8"))
            == model.model_json_schema()
        )
    drafts = json.loads((root / "hub-template-drafts.json").read_text(encoding="utf-8"))
    assert drafts["evidence_kind"] == "synthetic_unconfigured_drafts"
    assert drafts["templates"] == [item.model_dump(mode="json") for item in draft_templates()]
