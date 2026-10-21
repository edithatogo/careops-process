# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic agenda refresh history, replay and current-minute boundaries."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest

from careops_process.hub_decisions import apply_decision_transition
from careops_process.hub_meetings import (
    BriefReferences,
    MeetingAgenda,
    add_agenda_entry,
    replace_agenda_entry,
)
from tests.test_hub_decisions import decision_matter
from tests.test_hub_domain import command
from tests.test_hub_meetings import NOW, brief, matter, meeting, record_minutes, rule, session

if TYPE_CHECKING:
    from careops_process.hub_domain import GovernanceMatter


def _agenda() -> MeetingAgenda:
    return add_agenda_entry(
        meeting(),
        matter(),
        brief(),
        actor_ref="synthetic-secretariat",
        expected_revision=0,
        now=NOW,
    )


def _changed_matter(revision: int = 5) -> GovernanceMatter:
    current, configured = decision_matter()
    for expected, state in enumerate(("provisionally_decided", "ratified"), start=4):
        if current.revision >= revision:
            break
        current = apply_decision_transition(
            current,
            command(
                event_id=f"refresh-event-{expected}",
                replay_key=f"refresh-replay-{expected}",
                expected_revision=expected,
                to_state=state,
            ),
            template=configured,
            rule=rule(),
            session=session(),
            now=NOW,
        )
    return current


def _refresh(agenda: MeetingAgenda, **changes: Any) -> MeetingAgenda:  # noqa: ANN401
    options: dict[str, Any] = {
        "replacement_id": "refresh-1",
        "actor_ref": "synthetic-secretariat",
        "expected_revision": agenda.revision,
        "now": NOW + timedelta(minutes=1),
    }
    options.update(changes)
    current = options.pop("matter", _changed_matter())
    sources = options.pop("brief", brief())
    return replace_agenda_entry(agenda, current, sources, **options)


def test_refresh_preserves_history_inputs_and_restores_exactly() -> None:
    """The active snapshot changes once while its original record remains intact."""
    original = _agenda()
    before = original.model_dump(mode="json")
    refreshed = _refresh(original)
    assert original.model_dump(mode="json") == before
    assert (original.revision, refreshed.revision) == (1, 2)
    assert refreshed.entries[0].matter_revision == _changed_matter().revision
    assert refreshed.replacements[0].previous_entry == original.entries[0]
    assert refreshed.replacements[0].next_entry == refreshed.entries[0]
    assert MeetingAgenda.model_validate_json(refreshed.model_dump_json()) == refreshed


def test_original_serialized_records_need_no_migration() -> None:
    """Missing replacement history means the original no-replacement representation."""
    payload = _agenda().model_dump()
    payload.pop("replacements", None)
    assert MeetingAgenda.model_validate(payload).replacements == ()


def test_exact_historical_replay_does_not_undo_later_replacement() -> None:
    """Original command identity, including time/revision, survives a later refresh."""
    first = _refresh(_agenda())
    later = _refresh(
        first,
        replacement_id="refresh-2",
        matter=_changed_matter(6),
        now=NOW + timedelta(minutes=2),
    )
    replay = _refresh(later, expected_revision=1)
    assert replay == later
    assert tuple(item.replacement_id for item in replay.replacements) == ("refresh-1", "refresh-2")


@pytest.mark.parametrize("changed", ["time", "actor", "revision", "matter", "brief"])
def test_replacement_identity_collision_rejected(changed: str) -> None:
    """Every original request field participates in exact replay identity."""
    first = _refresh(_agenda())
    options: dict[str, Any] = {"expected_revision": 1}
    if changed == "time":
        options["now"] = NOW + timedelta(minutes=2)
    elif changed == "actor":
        options["actor_ref"] = "synthetic-chair"
    elif changed == "revision":
        options["expected_revision"] = first.revision
    elif changed == "matter":
        options["matter"] = _changed_matter(6)
    else:
        options["brief"] = BriefReferences.model_validate(
            {
                **brief().model_dump(),
                "question_ref": "changed-question",
            }
        )
    with pytest.raises(ValueError, match=r"replay|collision"):
        _refresh(first, **options)


@pytest.mark.parametrize("revision", [True, False, -1, 0, 2])
def test_refresh_requires_strict_current_revision(revision: int) -> None:
    """Boolean or stale revision values cannot authorize a fresh event."""
    with pytest.raises(ValueError, match="revision"):
        _refresh(_agenda(), expected_revision=revision)


@pytest.mark.parametrize("gap", ["actor", "scope", "policy", "template", "unchanged", "naive"])
def test_refresh_rejects_invalid_fresh_binding(gap: str) -> None:
    """Refresh preserves pinned policy/template and cannot manufacture an event for no change."""
    options: dict[str, Any] = {}
    if gap == "actor":
        options["actor_ref"] = "synthetic-outsider"
    elif gap == "scope":
        options["matter"] = _changed_matter().model_copy(update={"scope_ref": "another-scope"})
    elif gap == "policy":
        options["brief"] = brief().model_copy(update={"decision_rule_digest": "0" * 64})
    elif gap == "template":
        options["matter"] = _changed_matter().model_copy(update={"template_digest": "0" * 64})
    elif gap == "unchanged":
        options["matter"] = matter()
    else:
        options["now"] = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match=r"actor|binding|replacement|timezone|snapshot"):
        _refresh(_agenda(), **options)


def test_deadline_exception_and_meeting_cutoff_are_distinct() -> None:
    """Chair exceptions permit a late pre-meeting refresh, never an in-meeting rewrite."""
    original = _agenda()
    late = original.agenda_deadline + timedelta(minutes=1)
    with pytest.raises(ValueError, match="deadline"):
        _refresh(original, now=late)
    refreshed = _refresh(original, now=late, chair_exception_ref="synthetic-exception")
    assert refreshed.replacements
    with pytest.raises(ValueError, match="meeting"):
        _refresh(original, now=original.scheduled_at, chair_exception_ref="synthetic-exception")


def test_minutes_require_current_replaced_snapshot_and_do_not_permit_backdated_refresh() -> None:
    """Stale snapshots cannot confirm minutes, and recorded minutes cannot be rewritten."""
    refreshed = _refresh(_agenda())
    kwargs: dict[str, Any] = {
        "actor_ref": "synthetic-secretariat",
        "expected_revision": refreshed.revision,
        "minute_ref": "synthetic-minute",
        "chair_confirmation_ref": "synthetic-chair-evidence",
        "now": NOW + timedelta(days=1),
    }
    with pytest.raises(ValueError, match="canonical"):
        record_minutes(refreshed, rule(), session(), **kwargs)
    minuted = record_minutes(
        refreshed,
        rule(),
        session(),
        current_matter=_changed_matter(),
        **kwargs,
    )
    with pytest.raises(ValueError, match=r"minute|chronology"):
        _refresh(minuted, replacement_id="backdated", now=NOW + timedelta(minutes=2))


@pytest.mark.parametrize(
    "gap", ["chain", "active", "revision", "digest", "duplicate", "actor", "time"]
)
def test_restoration_rejects_tampered_history(gap: str) -> None:
    """Serialized history is validated rather than trusted as a receipt boolean."""
    payload = _refresh(_agenda()).model_dump(mode="json")
    event = payload["replacements"][0]
    if gap == "chain":
        event["previous_entry"]["matter_revision"] += 1
    elif gap == "active":
        payload["entries"][0]["matter_revision"] += 1
    elif gap == "revision":
        event["expected_revision"] = 0
    elif gap == "digest":
        event["command_digest"] = "0" * 64
    elif gap == "duplicate":
        payload["replacements"].append(dict(event))
        payload["revision"] += 1
    elif gap == "actor":
        event["actor_ref"] = "synthetic-outsider"
    else:
        event["next_entry"]["added_at"] = (NOW - timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError, match=r"replacement|revision|history|snapshot"):
        MeetingAgenda.model_validate(payload)


def test_interleaved_additions_and_replacements_restore_and_preserve_chronology() -> None:
    """Meeting revisions sequence additions and replacements without losing entry order."""
    first = _refresh(_agenda())
    second_matter = matter().model_copy(update={"matter_id": "synthetic-matter-2"})
    second_brief = brief().model_copy(update={"matter_id": second_matter.matter_id})
    with pytest.raises(ValueError, match="chronology"):
        add_agenda_entry(
            first,
            second_matter,
            second_brief,
            actor_ref="synthetic-secretariat",
            expected_revision=first.revision,
            now=NOW,
        )
    added = add_agenda_entry(
        first,
        second_matter,
        second_brief,
        actor_ref="synthetic-secretariat",
        expected_revision=first.revision,
        now=NOW + timedelta(minutes=2),
    )
    refreshed = _refresh(
        added,
        replacement_id="refresh-2",
        matter=_changed_matter(6),
        now=NOW + timedelta(minutes=3),
    )
    assert (len(refreshed.entries), len(refreshed.replacements), refreshed.revision) == (2, 2, 4)
    assert MeetingAgenda.model_validate_json(refreshed.model_dump_json()) == refreshed
    assert refreshed.entries[1] == added.entries[1]


def test_recomputed_receipt_digest_cannot_hide_a_broken_snapshot_chain() -> None:
    """History validation checks structure even when an importer recomputes its hash."""
    first = _refresh(_agenda())
    later = _refresh(
        first,
        replacement_id="refresh-2",
        matter=_changed_matter(6),
        now=NOW + timedelta(minutes=2),
    )
    payload = later.model_dump(mode="json")
    event = payload["replacements"][1]
    event["previous_entry"]["brief"]["question_ref"] = "forged-question"
    body = {key: value for key, value in event.items() if key != "command_digest"}
    event["command_digest"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    with pytest.raises(ValueError, match="chain"):
        MeetingAgenda.model_validate(payload)


def test_receipt_cannot_move_to_another_meeting_context() -> None:
    """Matching snapshots and counts do not authorize cross-meeting history reuse."""
    refreshed = _refresh(_agenda())
    payload = refreshed.model_dump(mode="json")
    payload["meeting_id"] = "different-meeting"
    with pytest.raises(ValueError, match="scope"):
        MeetingAgenda.model_validate(payload)


def test_historical_replay_after_minutes_is_not_a_new_mutation() -> None:
    """A retained accepted command can replay after the cutoff without rewriting minutes."""
    refreshed = _refresh(_agenda())
    minuted = record_minutes(
        refreshed,
        rule(),
        session(),
        current_matter=_changed_matter(),
        actor_ref="synthetic-secretariat",
        expected_revision=refreshed.revision,
        minute_ref="synthetic-minute",
        chair_confirmation_ref="synthetic-chair-evidence",
        now=NOW + timedelta(days=1),
    )
    assert _refresh(minuted, expected_revision=1) == minuted


def test_forced_mutation_of_input_history_is_revalidated_before_refresh() -> None:
    """Frozen-model bypass cannot discard retained events to reuse revisions."""
    retained = _refresh(_agenda())
    object.__setattr__(retained, "replacements", ())
    with pytest.raises(ValueError, match="revision"):
        _refresh(retained, replacement_id="another-refresh")
