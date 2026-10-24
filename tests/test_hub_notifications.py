# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic notification admission, history and delivery uncertainty contracts."""

from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from careops_process import hub_notifications as n
from careops_process.hub_domain import GovernanceMatter
from careops_process.hub_views import DigestPolicy, ExecutiveDigest, PortfolioItem, build_digest
from tests.test_hub_domain import matter

LIMIT = 2
THREE_RESERVATIONS = 3
START = datetime(2026, 10, 1, tzinfo=UTC)


def ledger() -> n.NotificationLedger:
    """Provide a new adapter-provisioned recipient/channel history origin."""
    return n.NotificationLedger(
        tenant_ref="tenant",
        recipient_ref="recipient",
        channel_ref="teams",
        scope_ref="scope",
        history_origin=START,
    )


def candidate() -> ExecutiveDigest:
    """Provide a build_digest-compatible synthetic metadata candidate."""
    return ExecutiveDigest(
        digest_key="digest-1",
        omitted_count=0,
        items=(
            PortfolioItem(
                matter_id="matter",
                state="decision_required",
                template_id="executive_decision",
                reasons=("decision_required",),
                overdue_action_count=0,
            ),
        ),
    )


def reserve(index: int = 0, *, revision: int = 0) -> n.ReserveCommand:
    """Bind an admission to one recipient, intent, candidate and pinned window."""
    return n.ReserveCommand(
        command_ref=f"reserve-{index}",
        expected_revision=revision,
        now=START,
        tenant_ref="tenant",
        recipient_ref="recipient",
        channel_ref="teams",
        scope_ref="scope",
        message_ref=f"message-{index}",
        reservation_ref=f"reservation-{index}",
        provider_intent_ref=f"intent-{index}",
        policy_ref="policy-v1",
        enabled=True,
        window=n.NotificationWindow(start=START, end=START + timedelta(days=1), limit=2),
        candidate=candidate(),
    )


def reconcile(
    value: n.NotificationLedger,
    *,
    outcome: str = "delivery_unknown",
    index: int = 0,
) -> n.ReconcileCommand:
    """Provide a trusted-adapter evidence declaration, not live delivery proof."""
    return n.ReconcileCommand(
        command_ref=f"reconcile-{index}",
        expected_revision=value.revision,
        now=START,
        reservation_ref="reservation-0",
        evidence=n.DeliveryEvidence(
            evidence_ref=f"evidence-{index}",
            provider_intent_ref="intent-0",
            outcome=outcome,
            observed_at=START,
            complete_attempts=outcome == "confirmed_not_delivered",
        ),
    )


def test_quota_and_policy_change_do_not_reset_capacity() -> None:
    """A new policy or digest key cannot enlarge an existing pinned window."""
    first = n.reserve_notification(ledger(), reserve())
    second = n.reserve_notification(first.ledger, reserve(1, revision=1))
    rejected = n.reserve_notification(
        second.ledger,
        replace(
            reserve(2, revision=2),
            policy_ref="policy-v2",
            candidate=replace_candidate("digest-2"),
        ),
    )
    assert rejected.receipt.decision == "capacity"
    assert not rejected.attempt_permitted
    with pytest.raises(n.NotificationContractError, match="pinned"):
        n.reserve_notification(
            second.ledger,
            replace(
                reserve(2, revision=2),
                window=replace(reserve().window, limit=3),
            ),
        )


def replace_candidate(key: str) -> ExecutiveDigest:
    """Change a builder key without changing quota identity."""
    return ExecutiveDigest.model_validate({**candidate().model_dump(), "digest_key": key})


def test_replay_returns_original_receipt_without_rollback_or_dispatch() -> None:
    """A command replay preserves the latest ledger and never schedules a resend."""
    first = n.reserve_notification(ledger(), reserve())
    latest = n.reserve_notification(first.ledger, reserve(1, revision=1))
    replay = n.reserve_notification(latest.ledger, reserve())
    assert replay.ledger == latest.ledger
    assert replay.receipt == first.receipt
    assert replay.replayed
    assert not replay.attempt_permitted
    with pytest.raises(n.NotificationContractError, match="collision"):
        n.reserve_notification(latest.ledger, replace(reserve(), policy_ref="policy-v2"))


def test_unknown_retry_stays_charged_and_can_be_delivered() -> None:
    """Ambiguous attempts reuse the same charged provider idempotency binding."""
    first = n.reserve_notification(ledger(), reserve())
    unknown = n.reconcile_notification(first.ledger, reconcile(first.ledger))
    retry = n.reserve_notification(
        unknown.ledger,
        replace(
            reserve(),
            command_ref="retry",
            expected_revision=2,
        ),
    )
    assert retry.receipt.decision == "retry"
    assert retry.ledger.reservations == unknown.ledger.reservations
    delivered = n.reconcile_notification(
        retry.ledger,
        reconcile(
            retry.ledger,
            outcome="delivered",
            index=1,
        ),
    )
    assert delivered.ledger.reservations[0].status == "delivered"
    with pytest.raises(n.NotificationContractError, match="terminal"):
        n.reconcile_notification(
            delivered.ledger,
            reconcile(
                delivered.ledger,
                outcome="confirmed_not_delivered",
                index=2,
            ),
        )


def test_confirmed_non_delivery_releases_once_and_message_is_terminal() -> None:
    """Released reservations never authorize an uncharged retry of that message."""
    first = n.reserve_notification(ledger(), reserve())
    command = reconcile(first.ledger, outcome="confirmed_not_delivered")
    with pytest.raises(n.NotificationContractError, match="complete"):
        n.reconcile_notification(
            first.ledger,
            replace(
                command,
                evidence=replace(command.evidence, complete_attempts=False),
            ),
        )
    released = n.reconcile_notification(first.ledger, command)
    terminal = n.reserve_notification(
        released.ledger,
        replace(
            reserve(),
            command_ref="retry",
            expected_revision=2,
        ),
    )
    assert terminal.receipt.decision == "terminal"
    assert not terminal.attempt_permitted
    second = n.reserve_notification(terminal.ledger, reserve(1, revision=3))
    third = n.reserve_notification(second.ledger, reserve(2, revision=4))
    assert third.attempt_permitted
    assert len(third.ledger.reservations) == THREE_RESERVATIONS


def test_window_history_is_adjacent_pinned_and_global() -> None:
    """Boundary rollover retains old identities and rejects gaps and overlaps."""
    first = n.reserve_notification(ledger(), reserve())
    next_window = n.NotificationWindow(
        start=START + timedelta(days=1),
        end=START + timedelta(days=2),
        limit=1,
    )
    command = replace(reserve(1, revision=1), now=next_window.start, window=next_window)
    second = n.reserve_notification(first.ledger, command)
    assert len(second.ledger.windows) == LIMIT
    retry = n.reserve_notification(
        second.ledger,
        replace(
            reserve(),
            command_ref="late-retry",
            expected_revision=2,
            now=next_window.start,
        ),
    )
    assert retry.receipt.decision == "retry"
    assert retry.ledger.reservations[0].window_start == START
    for delta in (-1, 1):
        with pytest.raises(n.NotificationContractError, match="adjacent"):
            n.reserve_notification(
                first.ledger,
                replace(
                    command,
                    window=replace(next_window, start=next_window.start + timedelta(seconds=delta)),
                ),
            )


def test_revision_collision_and_recipient_binding_are_strict() -> None:
    """Pure proposal competition still requires adapter atomic compare-and-swap."""
    first = n.reserve_notification(ledger(), reserve())
    with pytest.raises(n.NotificationContractError, match="revision"):
        n.reserve_notification(first.ledger, reserve(1))
    for field in ("recipient_ref", "channel_ref", "tenant_ref", "scope_ref"):
        with pytest.raises(n.NotificationContractError, match="binding"):
            n.reserve_notification(ledger(), replace(reserve(), **{field: "other"}))
    for field in ("message_ref", "reservation_ref", "provider_intent_ref"):
        with pytest.raises(n.NotificationContractError, match="collision"):
            n.reserve_notification(
                first.ledger,
                replace(
                    reserve(1, revision=1),
                    **{field: getattr(reserve(), field)},
                ),
            )


@given(st.lists(st.booleans(), min_size=1, max_size=20))
def test_generated_admission_sequences_never_exceed_pinned_limit(release: list[bool]) -> None:
    """Independent charged-cell accounting remains bounded under repeated release attempts."""
    value = ledger()
    charged = 0
    for index, free in enumerate(release):
        result = n.reserve_notification(value, reserve(index, revision=value.revision))
        value = result.ledger
        if charged == LIMIT:
            assert result.receipt.decision == "capacity"
        else:
            assert result.attempt_permitted
            charged += 1
            if free:
                evidence = n.DeliveryEvidence(
                    evidence_ref=f"evidence-{index}",
                    provider_intent_ref=f"intent-{index}",
                    outcome="confirmed_not_delivered",
                    observed_at=START,
                    complete_attempts=True,
                )
                value = n.reconcile_notification(
                    value,
                    n.ReconcileCommand(
                        command_ref=f"reconcile-{index}",
                        expected_revision=value.revision,
                        now=START,
                        reservation_ref=f"reservation-{index}",
                        evidence=evidence,
                    ),
                ).ledger
                charged -= 1
        actual = sum(item.status != "confirmed_not_delivered" for item in value.reservations)
        assert actual == charged <= LIMIT
        assert value.revision == len(value.receipts)


def _skip_validation(_self: object) -> None:
    pass


def _bypass(value: Any, **changes: Any) -> Any:  # noqa: ANN401 - adversarial runtime fixtures
    base = cast("type[Any]", type(value))
    subtype = type("Bypass", (base,), {"__post_init__": _skip_validation})
    if isinstance(value, ExecutiveDigest | PortfolioItem):
        return cast("Any", subtype).model_construct(**{**value.model_dump(), **changes})
    return subtype(**{**{f.name: getattr(value, f.name) for f in fields(value)}, **changes})


@pytest.mark.parametrize(
    "record",
    [
        "ledger",
        "command",
        "window",
        "candidate",
        "item",
        "reservation",
        "receipt",
        "evidence",
        "reconcile",
    ],
)
def test_subclass_bypasses_are_rejected_at_public_boundaries(record: str) -> None:
    """Concrete direct and deeply nested contracts cannot replace validation methods."""
    value = n.reserve_notification(ledger(), reserve()).ledger
    command = reserve(1, revision=1)
    reconciliation = reconcile(value)
    if record == "ledger":
        value = _bypass(value)
    elif record == "command":
        command = _bypass(command)
    elif record == "window":
        object.__setattr__(command, "window", _bypass(command.window))
    elif record == "candidate":
        object.__setattr__(command, "candidate", _bypass(command.candidate))
    elif record == "item":
        object.__setattr__(command.candidate, "items", (_bypass(candidate().items[0]),))
    elif record == "reservation":
        object.__setattr__(value, "reservations", (_bypass(value.reservations[0]),))
    elif record == "receipt":
        object.__setattr__(value, "receipts", (_bypass(value.receipts[0]),))
    elif record == "evidence":
        object.__setattr__(reconciliation, "evidence", _bypass(reconciliation.evidence))
    else:
        reconciliation = _bypass(reconciliation)
    operation = n.reconcile_notification if record in {"evidence", "reconcile"} else None
    if operation is not None:
        with pytest.raises(n.NotificationContractError, match="concrete"):
            operation(value, reconciliation)
    else:
        with pytest.raises(n.NotificationContractError, match="concrete"):
            n.reserve_notification(value, command)


@pytest.mark.parametrize("field", ["windows", "reservations", "receipts"])
def test_missing_retained_history_is_not_fresh_quota(field: str) -> None:
    """Dropping any retained history fails before another admission can be proposed."""
    value = n.reserve_notification(ledger(), reserve()).ledger
    object.__setattr__(value, field, ())
    with pytest.raises(n.NotificationContractError):
        n.reserve_notification(value, reserve(1, revision=1))


@pytest.mark.parametrize(
    ("field", "bad"),
    [("expected_revision", True), ("enabled", 1), ("message_ref", "private narrative / body")],
)
def test_forced_command_mutations_are_revalidated(field: str, bad: object) -> None:
    """Frozen records cannot become a trust shortcut after object-level mutation."""
    command = reserve()
    object.__setattr__(command, field, bad)
    with pytest.raises(n.NotificationContractError):
        n.reserve_notification(ledger(), command)


def test_reconciliation_replay_evidence_binding_and_staleness() -> None:
    """Evidence is bound to one provider intent; stale or duplicate facts cannot change state."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    command = reconcile(first)
    wrong = replace(command, evidence=replace(command.evidence, provider_intent_ref="other"))
    with pytest.raises(n.NotificationContractError, match="binding"):
        n.reconcile_notification(first, wrong)
    unknown = n.reconcile_notification(first, command)
    replay = n.reconcile_notification(unknown.ledger, command)
    assert replay.replayed
    assert not replay.attempt_permitted
    assert replay.ledger == unknown.ledger
    with pytest.raises(n.NotificationContractError, match="collision"):
        n.reconcile_notification(
            unknown.ledger,
            replace(
                command,
                command_ref="repeat-evidence",
                expected_revision=2,
            ),
        )
    later = replace(
        reconcile(unknown.ledger, index=1),
        now=START + timedelta(hours=1),
        evidence=replace(
            command.evidence, evidence_ref="later", observed_at=START + timedelta(hours=1)
        ),
    )
    advanced = n.reconcile_notification(unknown.ledger, later).ledger
    stale = replace(reconcile(advanced, index=2), now=later.now)
    with pytest.raises(n.NotificationContractError, match="stale"):
        n.reconcile_notification(advanced, stale)


def test_disabled_and_empty_candidates_do_not_reserve_capacity() -> None:
    """Record deterministic rejection receipts without creating an outbound intent."""
    disabled = n.reserve_notification(ledger(), replace(reserve(), enabled=False))
    assert disabled.receipt.decision == "disabled"
    assert not disabled.ledger.reservations
    empty = ExecutiveDigest(digest_key="empty", items=(), omitted_count=0)
    result = n.reserve_notification(
        disabled.ledger,
        replace(
            reserve(1, revision=1),
            candidate=empty,
        ),
    )
    assert result.receipt.decision == "empty"
    assert not result.attempt_permitted
    assert not result.ledger.reservations


def test_exact_half_open_boundaries_and_strict_time() -> None:
    """A new message cannot use an expired window or a naive timestamp."""
    command = reserve()
    with pytest.raises(n.NotificationContractError, match="current window"):
        n.reserve_notification(ledger(), replace(command, now=command.window.end))
    with pytest.raises(n.NotificationContractError, match="timezone"):
        replace(command, now=START.replace(tzinfo=None))


def test_candidate_reasons_cannot_carry_free_text_or_invalid_shapes() -> None:
    """Approved metadata excludes arbitrary notification narrative."""
    command = reserve()
    object.__setattr__(command.candidate.items[0], "reasons", (["private"],))
    with pytest.raises(n.NotificationContractError, match="reason"):
        n.reserve_notification(ledger(), command)


def test_existing_digest_builder_integrates_without_policy_api_changes() -> None:
    """The existing capped metadata digest enters the separate recipient quota ledger."""
    value = GovernanceMatter.model_validate({**matter().model_dump(), "risk": "material"})
    digest = build_digest(
        [value],
        actor_scope_ref="synthetic-scope",
        now=START,
        policy=DigestPolicy(enabled=True, maximum_items=1, interval_days=7),
    )
    assert digest is not None
    result = n.reserve_notification(
        replace(ledger(), scope_ref="synthetic-scope"),
        replace(
            reserve(),
            scope_ref="synthetic-scope",
            candidate=digest,
        ),
    )
    assert result.attempt_permitted
    assert result.ledger.reservations[0].candidate_fingerprint
    assert "synthetic-matter" not in repr(result.ledger)


@pytest.mark.parametrize("outcome", ["delivered", "confirmed_not_delivered"])
def test_both_terminal_states_reject_late_evidence_and_uncharged_retry(outcome: str) -> None:
    """Only exact command replay is allowed after terminal reconciliation."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    command = reconcile(first, outcome=outcome)
    terminal = n.reconcile_notification(first, command).ledger
    replay = n.reconcile_notification(terminal, command)
    assert replay.replayed
    retry = n.reserve_notification(
        terminal,
        replace(
            reserve(),
            command_ref="retry",
            expected_revision=2,
        ),
    )
    assert retry.receipt.decision == "terminal"
    assert not retry.attempt_permitted
    with pytest.raises(n.NotificationContractError, match="terminal"):
        n.reconcile_notification(terminal, reconcile(terminal, outcome="delivered", index=1))


def test_independent_recipient_and_channel_ledgers_have_separate_capacity() -> None:
    """A matching trusted binding is required for each isolated history namespace."""
    for field in ("recipient_ref", "channel_ref"):
        first = n.reserve_notification(ledger(), reserve()).ledger
        full = n.reserve_notification(first, reserve(1, revision=1)).ledger
        assert n.reserve_notification(full, reserve(2, revision=2)).receipt.decision == "capacity"
        other = replace(ledger(), **{field: "other"})
        assert n.reserve_notification(
            other, replace(reserve(), **{field: "other"})
        ).attempt_permitted


def test_mutated_nested_ledger_evidence_cannot_free_capacity() -> None:
    """A forced false complete-attempt flag is rejected during nested ledger reconstruction."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    released = n.reconcile_notification(first, reconcile(first, outcome="confirmed_not_delivered"))
    object.__setattr__(released.ledger.reservations[0].evidence[0], "complete_attempts", False)
    with pytest.raises(n.NotificationContractError, match="complete"):
        n.reserve_notification(released.ledger, reserve(1, revision=2))


def test_candidate_content_and_provider_binding_cannot_change_on_retry() -> None:
    """Retained message identity binds full candidate content including builder key."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    command = replace(
        reserve(),
        command_ref="retry",
        expected_revision=1,
        candidate=replace_candidate("different"),
    )
    with pytest.raises(n.NotificationContractError, match="collision"):
        n.reserve_notification(first, command)


def test_new_command_kind_cannot_reuse_reserved_command_reference() -> None:
    """One global command namespace fingerprints operation kind and all command fields."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    with pytest.raises(n.NotificationContractError, match="collision"):
        n.reconcile_notification(first, replace(reconcile(first), command_ref="reserve-0"))


@pytest.mark.parametrize("empty", [False, True])
def test_evaluated_idle_window_is_retained_before_next_interval(*, empty: bool) -> None:
    """Disabled and empty intervals pin their limits and preserve observed continuity."""
    command = reserve()
    if empty:
        command = replace(
            command,
            candidate=ExecutiveDigest(
                digest_key="empty",
                items=(),
                omitted_count=0,
            ),
        )
    else:
        command = replace(command, enabled=False)
    idle = n.reserve_notification(ledger(), command).ledger
    next_window = n.NotificationWindow(
        start=command.window.end, end=command.window.end + timedelta(days=1), limit=1
    )
    admitted = n.reserve_notification(
        idle,
        replace(
            reserve(1, revision=1),
            now=next_window.start,
            window=next_window,
        ),
    )
    assert admitted.attempt_permitted
    assert admitted.ledger.windows == (command.window, next_window)


def test_reservation_requires_retained_admission_receipt() -> None:
    """A receipt cannot lose its admission decision while leaving an orphan reservation."""
    value = n.reserve_notification(ledger(), reserve()).ledger
    changed = replace(
        value.receipts[0], decision="disabled", reservation_ref=None, reservation_fingerprint=None
    )
    object.__setattr__(value, "receipts", (changed,))
    with pytest.raises(n.NotificationContractError, match="history"):
        n.reserve_notification(value, reserve(1, revision=1))


def test_delivery_evidence_requires_retained_reconciliation_receipt() -> None:
    """Changing a reconciliation result cannot leave release evidence without its receipt."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    value = n.reconcile_notification(
        first, reconcile(first, outcome="confirmed_not_delivered")
    ).ledger
    changed = replace(
        value.receipts[-1], decision="retry", evidence_ref=None, evidence_fingerprint=None
    )
    object.__setattr__(value, "receipts", (value.receipts[0], changed))
    with pytest.raises(n.NotificationContractError, match="history"):
        n.reserve_notification(value, reserve(1, revision=2))


def test_restored_history_cannot_hide_an_earlier_over_capacity_admission() -> None:
    """Final released totals do not excuse an impossible earlier charged history."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    released = n.reconcile_notification(first, reconcile(first, outcome="confirmed_not_delivered"))
    second = n.reserve_notification(released.ledger, reserve(1, revision=2)).ledger
    third = n.reserve_notification(second, reserve(2, revision=3)).ledger
    receipts = third.receipts
    reordered = (
        receipts[0],
        replace(receipts[2], revision=2),
        replace(receipts[3], revision=3),
        replace(receipts[1], revision=4),
    )
    object.__setattr__(third, "receipts", reordered)
    with pytest.raises(n.NotificationContractError, match="capacity history"):
        n.reserve_notification(third, reserve(3, revision=4))


def test_pinned_window_and_evidence_effect_fingerprints_detect_inconsistent_restore() -> None:
    """Changing a retained effect alone cannot silently change its original receipt result."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    object.__setattr__(first.windows[0], "limit", 3)
    with pytest.raises(n.NotificationContractError, match="window history"):
        n.reserve_notification(first, reserve(1, revision=1))
    first = n.reserve_notification(ledger(), reserve()).ledger
    unknown = n.reconcile_notification(first, reconcile(first)).ledger
    evidence = unknown.reservations[0].evidence[0]
    object.__setattr__(evidence, "outcome", "confirmed_not_delivered")
    object.__setattr__(evidence, "complete_attempts", True)
    with pytest.raises(n.NotificationContractError, match="receipt history"):
        n.reserve_notification(unknown, reserve(1, revision=2))


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("message_ref", "other-message"),
        ("provider_intent_ref", "other-intent"),
        ("policy_ref", "policy-v2"),
        ("candidate_fingerprint", "a" * 64),
    ],
)
def test_immutable_reservation_effect_is_bound_to_its_admission_receipt(
    field: str,
    bad: str,
) -> None:
    """Valid-looking replacement identities cannot redefine a retained charged message."""
    first = n.reserve_notification(ledger(), reserve()).ledger
    object.__setattr__(first.reservations[0], field, bad)
    with pytest.raises(n.NotificationContractError, match="reservation history"):
        n.reserve_notification(first, reserve(1, revision=1))
