# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Replay-safe ingestion checkpoints, tombstones, and dead-letter records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

RETRYABLE_ERRORS: Final = frozenset({"throttled", "timeout", "transient"})


@dataclass(frozen=True, slots=True)
class DeadLetter:
    """A minimized failure record with no source payload."""

    fact_id: str
    reason: str
    retryable: bool
    recorded_at_utc: datetime


@dataclass(slots=True)
class IngestionCheckpoint:
    """Mutable checkpoint model with bounded replay and tombstone identities."""

    watermark_utc: datetime | None = None
    accepted_fact_ids: set[str] = field(default_factory=set[str])
    tombstoned_fact_ids: set[str] = field(default_factory=set[str])
    dead_letters: list[DeadLetter] = field(default_factory=list[DeadLetter])
    max_tracked_ids: int = 10_000
    _accepted_order: list[str] = field(default_factory=list[str], repr=False)
    _tombstoned_order: list[str] = field(default_factory=list[str], repr=False)

    def __post_init__(self) -> None:
        """Validate the bounded checkpoint policy."""
        if self.max_tracked_ids < 1:
            message = "max_tracked_ids must be positive"
            raise ValueError(message)

    def _trim(self, values: set[str], order: list[str]) -> None:
        while len(order) > self.max_tracked_ids:
            values.discard(order.pop(0))

    def accept(self, fact_id: str, observed_at_utc: datetime) -> bool:
        """Accept a new fact once and advance the watermark monotonically."""
        if fact_id in self.accepted_fact_ids or fact_id in self.tombstoned_fact_ids:
            return False
        if observed_at_utc.tzinfo is None:
            message = "observed_at_utc must be timezone-aware"
            raise ValueError(message)
        self.accepted_fact_ids.add(fact_id)
        self._accepted_order.append(fact_id)
        self._trim(self.accepted_fact_ids, self._accepted_order)
        normalized = observed_at_utc.astimezone(UTC)
        if self.watermark_utc is None or normalized > self.watermark_utc:
            self.watermark_utc = normalized
        return True

    def tombstone(self, fact_id: str) -> None:
        """Record a source deletion without retaining the deleted payload."""
        self.tombstoned_fact_ids.add(fact_id)
        self._tombstoned_order.append(fact_id)
        self._trim(self.tombstoned_fact_ids, self._tombstoned_order)
        self.accepted_fact_ids.discard(fact_id)

    def dead_letter(self, fact_id: str, reason: str, *, recorded_at_utc: datetime) -> None:
        """Record a minimized failure and classify whether it is retryable."""
        if recorded_at_utc.tzinfo is None:
            message = "recorded_at_utc must be timezone-aware"
            raise ValueError(message)
        self.dead_letters.append(
            DeadLetter(
                fact_id=fact_id,
                reason=reason,
                retryable=reason.lower() in RETRYABLE_ERRORS,
                recorded_at_utc=recorded_at_utc.astimezone(UTC),
            )
        )
