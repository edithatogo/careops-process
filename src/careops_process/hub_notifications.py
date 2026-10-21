# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Pure synthetic notification admission proposals; adapters own auth, CAS and delivery."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from careops_process.hub_views import ExecutiveDigest, PortfolioItem

Status = Literal["reserved", "delivery_unknown", "delivered", "confirmed_not_delivered"]
Decision = Literal["reserved", "retry", "terminal", "capacity", "disabled", "empty", "reconciled"]
_MAX_INTEGER = 1_000_000_000
_TERMINAL = {"delivered", "confirmed_not_delivered"}
_REASONS = {
    "material_risk",
    "higher_risk",
    "decision_required",
    "ratification_gap",
    "assurance_review",
    "overdue_actions",
    "dependencies",
}


class NotificationContractError(ValueError):
    """Reject an invalid admission contract without proposing a state change."""


def _require(condition: bool, message: str) -> None:  # noqa: FBT001 - contract predicate
    if not condition:
        raise NotificationContractError(message)


def _exact(value: object, expected: type[object]) -> None:
    _require(type(value) is expected, "unsupported concrete notification contract")


def _code(value: object) -> None:
    _require(
        type(value) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", str(value)) is not None,
        "notification metadata requires bounded opaque codes",
    )


def _integer(value: object, *, minimum: int = 0) -> None:
    _require(
        type(value) is int and minimum <= value <= _MAX_INTEGER,
        "notification integer outside strict bounds",
    )


def _time(value: datetime) -> datetime:
    _exact(value, datetime)
    _require(
        value.tzinfo is not None and value.utcoffset() is not None,
        "notification time must be timezone aware",
    )
    return value.astimezone(UTC)


def _hash(value: str) -> None:
    _require(
        type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None,
        "notification fingerprint invalid",
    )


def _default(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    message = "unsupported notification fingerprint value"
    raise NotificationContractError(message)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=_default).encode()
    ).hexdigest()


def _candidate(value: ExecutiveDigest) -> ExecutiveDigest:
    _exact(value, ExecutiveDigest)
    _exact(value.items, tuple)
    _code(value.digest_key)
    _integer(value.omitted_count)
    _require(value.execution_mode == "synthetic", "only synthetic notification candidates")
    seen: set[str] = set()
    for item in value.items:
        _exact(item, PortfolioItem)
        _code(item.matter_id)
        _integer(item.overdue_action_count)
        _exact(item.reasons, tuple)
        _require(
            bool(item.reasons)
            and all(type(reason) is str for reason in item.reasons)
            and len(set(item.reasons)) == len(item.reasons)
            and all(reason in _REASONS for reason in item.reasons),
            "candidate requires approved metadata reason codes",
        )
        _require(item.matter_id not in seen, "duplicate notification candidate matter")
        seen.add(item.matter_id)
    # Validate enum fields again: model_copy/model_construct and forced mutations bypass Pydantic.
    return ExecutiveDigest.model_validate(value.model_dump(), strict=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class NotificationWindow:
    """Pin half-open UTC bounds and a recipient/channel delivery limit."""

    start: datetime
    end: datetime
    limit: int

    def __post_init__(self) -> None:
        """Normalize time and reject invalid or empty windows."""
        object.__setattr__(self, "start", _time(self.start))
        object.__setattr__(self, "end", _time(self.end))
        _require(self.start < self.end, "notification window must be nonempty")
        _integer(self.limit, minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class DeliveryEvidence:
    """Declare trusted-adapter outcome for one complete idempotent provider intent."""

    evidence_ref: str
    provider_intent_ref: str
    outcome: str
    observed_at: datetime
    complete_attempts: bool

    def __post_init__(self) -> None:
        """Keep ambiguity charged and require complete proof to release capacity."""
        _code(self.evidence_ref)
        _code(self.provider_intent_ref)
        _require(self.outcome in _TERMINAL | {"delivery_unknown"}, "unsupported delivery outcome")
        _exact(self.complete_attempts, bool)
        _require(
            self.outcome != "confirmed_not_delivered" or self.complete_attempts,
            "non-delivery requires complete attempt evidence",
        )
        object.__setattr__(self, "observed_at", _time(self.observed_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class Reservation:
    """Retain one logical message, frozen content and charged original window."""

    reservation_ref: str
    message_ref: str
    provider_intent_ref: str
    window_start: datetime
    candidate_fingerprint: str
    policy_ref: str
    created_at: datetime
    evidence: tuple[DeliveryEvidence, ...] = ()

    def __post_init__(self) -> None:
        """Detach nested records and reject contradictory terminal evidence."""
        for value in (
            self.reservation_ref,
            self.message_ref,
            self.provider_intent_ref,
            self.policy_ref,
        ):
            _code(value)
        _hash(self.candidate_fingerprint)
        object.__setattr__(self, "window_start", _time(self.window_start))
        object.__setattr__(self, "created_at", _time(self.created_at))
        _exact(self.evidence, tuple)
        detached: list[DeliveryEvidence] = []
        previous = self.created_at
        terminal = False
        for supplied in self.evidence:
            _exact(supplied, DeliveryEvidence)
            item = replace(supplied)
            _require(not terminal, "terminal delivery evidence cannot be extended")
            _require(
                item.provider_intent_ref == self.provider_intent_ref,
                "provider intent binding mismatch",
            )
            _require(item.observed_at >= previous, "stale delivery evidence")
            previous = item.observed_at
            terminal = item.outcome in _TERMINAL
            detached.append(item)
        object.__setattr__(self, "evidence", tuple(detached))

    @property
    def status(self) -> str:
        """Derive state from retained evidence without mutable duplicate state."""
        return self.evidence[-1].outcome if self.evidence else "reserved"


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandReceipt:
    """Keep the original result, never a stale ledger snapshot or send instruction."""

    command_ref: str
    fingerprint: str
    decision: Decision
    reservation_ref: str | None
    revision: int
    window_start: datetime
    window_fingerprint: str
    evidence_ref: str | None = None
    evidence_fingerprint: str | None = None
    reservation_fingerprint: str | None = None

    def __post_init__(self) -> None:
        """Validate retained replay identity and bounded result metadata."""
        _code(self.command_ref)
        _hash(self.fingerprint)
        _integer(self.revision, minimum=1)
        object.__setattr__(self, "window_start", _time(self.window_start))
        _hash(self.window_fingerprint)
        _require(
            self.decision
            in {"reserved", "retry", "terminal", "capacity", "disabled", "empty", "reconciled"},
            "invalid notification receipt",
        )
        if self.reservation_ref is not None:
            _code(self.reservation_ref)
        _require(
            (self.reservation_ref is not None)
            == (self.decision in {"reserved", "retry", "terminal", "reconciled"}),
            "receipt reservation binding invalid",
        )
        _require(
            (self.evidence_ref is not None) == (self.decision == "reconciled"),
            "receipt evidence history binding invalid",
        )
        _require(
            (self.evidence_fingerprint is not None) == (self.evidence_ref is not None),
            "receipt evidence fingerprint history invalid",
        )
        if self.evidence_ref is not None:
            _code(self.evidence_ref)
        if self.evidence_fingerprint is not None:
            _hash(self.evidence_fingerprint)
        _require(
            (self.reservation_fingerprint is not None) == (self.reservation_ref is not None),
            "receipt reservation history fingerprint invalid",
        )
        if self.reservation_fingerprint is not None:
            _hash(self.reservation_fingerprint)


@dataclass(frozen=True, slots=True, kw_only=True)
class NotificationLedger:
    """Retain recipient/channel windows and global identity history without pruning."""

    tenant_ref: str
    recipient_ref: str
    channel_ref: str
    scope_ref: str
    history_origin: datetime
    revision: int = 0
    windows: tuple[NotificationWindow, ...] = ()
    reservations: tuple[Reservation, ...] = ()
    receipts: tuple[CommandReceipt, ...] = ()
    evaluated_at: datetime | None = None

    def __post_init__(self) -> None:  # noqa: C901 - validate complete retained history
        """Revalidate all concrete nested history, continuity and capacity."""
        for value in (self.tenant_ref, self.recipient_ref, self.channel_ref, self.scope_ref):
            _code(value)
        _integer(self.revision)
        object.__setattr__(self, "history_origin", _time(self.history_origin))
        for value in (self.windows, self.reservations, self.receipts):
            _exact(value, tuple)
        windows: list[NotificationWindow] = []
        expected = self.history_origin
        for supplied_window in self.windows:
            _exact(supplied_window, NotificationWindow)
            window = replace(supplied_window)
            _require(window.start == expected, "history windows must be adjacent to origin")
            expected = window.end
            windows.append(window)
        object.__setattr__(self, "windows", tuple(windows))
        reservations: list[Reservation] = []
        for item in self.reservations:
            _exact(item, Reservation)
            reservations.append(replace(item))
        object.__setattr__(self, "reservations", tuple(reservations))
        for attribute in ("message_ref", "reservation_ref", "provider_intent_ref"):
            values = [getattr(item, attribute) for item in reservations]
            _require(len(set(values)) == len(values), "global reservation identity collision")
        evidence_refs = [e.evidence_ref for item in reservations for e in item.evidence]
        _require(len(set(evidence_refs)) == len(evidence_refs), "delivery evidence collision")
        for item in reservations:
            window = next((w for w in windows if w.start == item.window_start), None)
            _require(window is not None, "reservation missing window history")
            if window is not None:
                _require(
                    window.start <= item.created_at < window.end,
                    "reservation creation outside pinned window",
                )
        for window in windows:
            _require(
                sum(
                    r.window_start == window.start and r.status != "confirmed_not_delivered"
                    for r in reservations
                )
                <= window.limit,
                "pinned capacity exceeded",
            )
        receipts: list[CommandReceipt] = []
        for index, supplied_receipt in enumerate(self.receipts, 1):
            _exact(supplied_receipt, CommandReceipt)
            receipt = replace(supplied_receipt)
            _require(receipt.revision == index, "missing command revision history")
            _require(
                receipt.reservation_ref is None
                or any(r.reservation_ref == receipt.reservation_ref for r in reservations),
                "receipt missing reservation history",
            )
            receipts.append(receipt)
        _require(len({r.command_ref for r in receipts}) == len(receipts), "command collision")
        _require(len(receipts) == self.revision, "ledger revision/history mismatch")
        object.__setattr__(self, "receipts", tuple(receipts))
        _history_bindings(tuple(windows), tuple(reservations), tuple(receipts))
        _require(self.revision != 0 or not (windows or reservations), "missing admission history")
        _require((self.evaluated_at is None) == (self.revision == 0), "missing evaluation history")
        if self.evaluated_at is not None:
            object.__setattr__(self, "evaluated_at", _time(self.evaluated_at))
            _require(self.evaluated_at >= self.history_origin, "evaluation precedes history")
            _require(
                all(
                    self.evaluated_at
                    >= (r.evidence[-1].observed_at if r.evidence else r.created_at)
                    for r in reservations
                ),
                "evidence exceeds evaluation time",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReserveCommand:
    """Bind a complete command to approved scope, recipient and provider identity."""

    command_ref: str
    expected_revision: int
    now: datetime
    tenant_ref: str
    recipient_ref: str
    channel_ref: str
    scope_ref: str
    message_ref: str
    reservation_ref: str
    provider_intent_ref: str
    policy_ref: str
    enabled: bool
    window: NotificationWindow
    candidate: ExecutiveDigest

    def __post_init__(self) -> None:
        """Reconstruct concrete candidate/window contracts before hashing or admission."""
        for value in (
            self.command_ref,
            self.tenant_ref,
            self.recipient_ref,
            self.channel_ref,
            self.scope_ref,
            self.message_ref,
            self.reservation_ref,
            self.provider_intent_ref,
            self.policy_ref,
        ):
            _code(value)
        _integer(self.expected_revision)
        _exact(self.enabled, bool)
        object.__setattr__(self, "now", _time(self.now))
        _exact(self.window, NotificationWindow)
        object.__setattr__(self, "window", replace(self.window))
        object.__setattr__(self, "candidate", _candidate(self.candidate))


@dataclass(frozen=True, slots=True, kw_only=True)
class ReconcileCommand:
    """Attach trusted adapter evidence to an existing bound provider intent."""

    command_ref: str
    expected_revision: int
    now: datetime
    reservation_ref: str
    evidence: DeliveryEvidence

    def __post_init__(self) -> None:
        """Reject invalid nested records and evidence from the future."""
        _code(self.command_ref)
        _code(self.reservation_ref)
        _integer(self.expected_revision)
        object.__setattr__(self, "now", _time(self.now))
        _exact(self.evidence, DeliveryEvidence)
        object.__setattr__(self, "evidence", replace(self.evidence))
        _require(self.evidence.observed_at <= self.now, "future delivery evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class AdmissionResult:
    """Return a proposal; replay cannot roll back state or request another attempt."""

    ledger: NotificationLedger
    receipt: CommandReceipt
    replayed: bool = False

    @property
    def attempt_permitted(self) -> bool:
        """Expose local admission only; actual sends still require every adapter gate."""
        return not self.replayed and self.receipt.decision in {"reserved", "retry"}


def _reservation_fingerprint(value: Reservation) -> str:
    return _fingerprint(asdict(replace(value, evidence=())))


def _history_bindings(
    windows: tuple[NotificationWindow, ...],
    reservations: tuple[Reservation, ...],
    receipts: tuple[CommandReceipt, ...],
) -> None:
    by_window = {w.start: w for w in windows}
    by_reservation = {r.reservation_ref: r for r in reservations}
    observed_windows: set[datetime] = set()
    admitted: set[str] = set()
    evidence_counts: dict[str, int] = {}
    states: dict[str, str] = {}
    charged = dict.fromkeys(by_window, 0)
    for receipt in receipts:
        window = by_window.get(receipt.window_start)
        _require(
            window is not None and receipt.window_fingerprint == _fingerprint(asdict(window)),
            "receipt window history mismatch",
        )
        observed_windows.add(receipt.window_start)
        if receipt.reservation_ref is None:
            continue
        reference = receipt.reservation_ref
        reservation = by_reservation[reference]  # Existence checked by ledger reconstruction.
        _require(
            reservation.window_start == receipt.window_start
            and receipt.reservation_fingerprint == _reservation_fingerprint(reservation),
            "receipt reservation history mismatch",
        )
        if receipt.decision == "reserved":
            _require(reference not in admitted, "duplicate admission history")
            admitted.add(reference)
            states[reference] = "reserved"
            evidence_counts[reference] = 0
            charged[receipt.window_start] += 1
            _require(
                charged[receipt.window_start] <= by_window[receipt.window_start].limit,
                "pinned capacity history exceeded",
            )
            continue
        _require(reference in admitted, "receipt precedes admission history")
        if receipt.decision == "reconciled":
            index = evidence_counts[reference]
            _require(index < len(reservation.evidence), "missing delivery evidence history")
            evidence = reservation.evidence[index]
            _require(
                states[reference] not in _TERMINAL
                and evidence.evidence_ref == receipt.evidence_ref
                and receipt.evidence_fingerprint == _fingerprint(asdict(evidence)),
                "reconciliation receipt history mismatch",
            )
            evidence_counts[reference] += 1
            states[reference] = evidence.outcome
            if evidence.outcome == "confirmed_not_delivered":
                charged[receipt.window_start] -= 1
        else:
            _require(
                (receipt.decision == "terminal") == (states[reference] in _TERMINAL),
                "retry/terminal receipt history mismatch",
            )
    _require(observed_windows == set(by_window), "window missing receipt history")
    _require(admitted == set(by_reservation), "reservation missing admission receipt history")
    _require(
        all(evidence_counts[r.reservation_ref] == len(r.evidence) for r in reservations),
        "evidence missing reconciliation receipt history",
    )


def _begin(
    ledger: NotificationLedger,
    command: ReserveCommand | ReconcileCommand,
) -> tuple[str, AdmissionResult | None]:
    fingerprint = _fingerprint({"kind": type(command).__name__, "command": asdict(command)})
    for receipt in ledger.receipts:
        if receipt.command_ref == command.command_ref:
            _require(receipt.fingerprint == fingerprint, "command identity collision")
            return fingerprint, AdmissionResult(ledger=ledger, receipt=receipt, replayed=True)
    _require(command.expected_revision == ledger.revision, "stale notification revision")
    _require(
        command.now >= (ledger.evaluated_at or ledger.history_origin),
        "stale notification evaluation time",
    )
    return fingerprint, None


def _finish(
    ledger: NotificationLedger,
    command: ReserveCommand,
    fingerprint: str,
    decision: Decision,
    reservation_ref: str | None,
) -> AdmissionResult:
    window = command.window
    receipt = CommandReceipt(
        command_ref=command.command_ref,
        fingerprint=fingerprint,
        decision=decision,
        reservation_ref=reservation_ref,
        revision=ledger.revision + 1,
        window_start=window.start,
        window_fingerprint=_fingerprint(asdict(window)),
        reservation_fingerprint=None
        if reservation_ref is None
        else _reservation_fingerprint(
            next(r for r in ledger.reservations if r.reservation_ref == reservation_ref)
        ),
    )
    updated = replace(
        ledger,
        revision=receipt.revision,
        receipts=(*ledger.receipts, receipt),
        evaluated_at=command.now,
        windows=ledger.windows if window in ledger.windows else (*ledger.windows, window),
    )
    return AdmissionResult(ledger=updated, receipt=receipt)


def reserve_notification(
    ledger: NotificationLedger,
    command: ReserveCommand,
) -> AdmissionResult:
    """Propose one reservation or charged idempotent retry without sending anything."""
    _exact(ledger, NotificationLedger)
    ledger = replace(ledger)
    _exact(command, ReserveCommand)
    command = replace(command)
    fingerprint, replay = _begin(ledger, command)
    if replay is not None:
        return replay
    _require(
        all(
            getattr(ledger, field) == getattr(command, field)
            for field in ("tenant_ref", "recipient_ref", "channel_ref", "scope_ref")
        ),
        "notification recipient/scope binding mismatch",
    )
    content = _fingerprint(command.candidate.model_dump(mode="json"))
    matches = [
        r
        for r in ledger.reservations
        if r.message_ref == command.message_ref
        or r.reservation_ref == command.reservation_ref
        or r.provider_intent_ref == command.provider_intent_ref
    ]
    if matches:
        old = matches[0]
        _require(
            len(matches) == 1
            and (
                old.message_ref,
                old.reservation_ref,
                old.provider_intent_ref,
                old.window_start,
                old.candidate_fingerprint,
                old.policy_ref,
            )
            == (
                command.message_ref,
                command.reservation_ref,
                command.provider_intent_ref,
                command.window.start,
                content,
                command.policy_ref,
            ),
            "reservation identity collision",
        )
        _require(command.window in ledger.windows, "pinned retry window mismatch")
        decision: Decision = "terminal" if old.status in _TERMINAL else "retry"
        if not command.enabled and decision != "terminal":
            decision = "disabled"
        return _finish(
            ledger,
            command,
            fingerprint,
            decision,
            None if decision == "disabled" else old.reservation_ref,
        )
    window = next((w for w in ledger.windows if w.start == command.window.start), None)
    if window is not None:
        _require(window == command.window, "pinned window cannot change")
    else:
        expected = ledger.windows[-1].end if ledger.windows else ledger.history_origin
        _require(command.window.start == expected, "new window must be adjacent to history")
    _require(
        command.window.start <= command.now < command.window.end,
        "new reservation outside current window",
    )
    if not command.enabled:
        return _finish(ledger, command, fingerprint, "disabled", None)
    if not command.candidate.items:
        return _finish(ledger, command, fingerprint, "empty", None)
    consumed = sum(
        r.window_start == command.window.start and r.status != "confirmed_not_delivered"
        for r in ledger.reservations
    )
    if consumed >= command.window.limit:
        return _finish(ledger, command, fingerprint, "capacity", None)
    reservation = Reservation(
        reservation_ref=command.reservation_ref,
        message_ref=command.message_ref,
        provider_intent_ref=command.provider_intent_ref,
        window_start=command.window.start,
        candidate_fingerprint=content,
        policy_ref=command.policy_ref,
        created_at=command.now,
    )
    # Construct ledger and receipt together; no intermediate invalid history snapshot is exposed.
    receipt = CommandReceipt(
        command_ref=command.command_ref,
        fingerprint=fingerprint,
        decision="reserved",
        reservation_ref=reservation.reservation_ref,
        reservation_fingerprint=_reservation_fingerprint(reservation),
        revision=ledger.revision + 1,
        window_start=command.window.start,
        window_fingerprint=_fingerprint(asdict(command.window)),
    )
    updated = replace(
        ledger,
        windows=ledger.windows if window is not None else (*ledger.windows, command.window),
        reservations=(*ledger.reservations, reservation),
        revision=receipt.revision,
        receipts=(*ledger.receipts, receipt),
        evaluated_at=command.now,
    )
    return AdmissionResult(ledger=updated, receipt=receipt)


def reconcile_notification(
    ledger: NotificationLedger,
    command: ReconcileCommand,
) -> AdmissionResult:
    """Reconcile matching trusted evidence; ambiguity never releases quota."""
    _exact(ledger, NotificationLedger)
    ledger = replace(ledger)
    _exact(command, ReconcileCommand)
    command = replace(command)
    fingerprint, replay = _begin(ledger, command)
    if replay is not None:
        return replay
    old = next(
        (r for r in ledger.reservations if r.reservation_ref == command.reservation_ref), None
    )
    _require(old is not None, "unknown notification reservation")
    if old is None:  # Narrow for static checking; _require already raises.
        message = "unknown notification reservation"
        raise NotificationContractError(message)
    _require(old.status not in _TERMINAL, "terminal notification cannot be reconciled again")
    _require(
        not any(
            e.evidence_ref == command.evidence.evidence_ref
            for r in ledger.reservations
            for e in r.evidence
        ),
        "delivery evidence collision",
    )
    updated_reservation = replace(old, evidence=(*old.evidence, command.evidence))
    receipt = CommandReceipt(
        command_ref=command.command_ref,
        fingerprint=fingerprint,
        decision="reconciled",
        reservation_ref=old.reservation_ref,
        reservation_fingerprint=_reservation_fingerprint(old),
        revision=ledger.revision + 1,
        window_start=old.window_start,
        window_fingerprint=_fingerprint(
            asdict(next(w for w in ledger.windows if w.start == old.window_start))
        ),
        evidence_ref=command.evidence.evidence_ref,
        evidence_fingerprint=_fingerprint(asdict(command.evidence)),
    )
    updated = replace(
        ledger,
        reservations=tuple(
            updated_reservation if r.reservation_ref == old.reservation_ref else r
            for r in ledger.reservations
        ),
        revision=receipt.revision,
        receipts=(*ledger.receipts, receipt),
        evaluated_at=command.now,
    )
    return AdmissionResult(ledger=updated, receipt=receipt)
