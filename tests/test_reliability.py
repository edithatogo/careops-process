# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic replay and failure-state tests."""

from datetime import UTC, datetime, timedelta

import pytest

from careops_process.reliability import IngestionCheckpoint


def test_checkpoint_is_idempotent_and_monotonic() -> None:
    """Replays are ignored and older observations cannot move the watermark back."""
    checkpoint = IngestionCheckpoint()
    newest = datetime(2026, 1, 2, tzinfo=UTC)
    assert checkpoint.accept("fact-1", newest)
    assert not checkpoint.accept("fact-1", newest + timedelta(days=1))
    assert checkpoint.accept("fact-2", datetime(2026, 1, 1, tzinfo=UTC))
    assert checkpoint.watermark_utc == newest


def test_tombstone_blocks_late_replay() -> None:
    """A deleted source fact cannot be resurrected by a later replay."""
    checkpoint = IngestionCheckpoint()
    checkpoint.tombstone("fact-1")
    assert not checkpoint.accept("fact-1", datetime(2026, 1, 1, tzinfo=UTC))


def test_dead_letters_are_minimized_and_classified() -> None:
    """Dead letters retain reason and retryability, never payload content."""
    checkpoint = IngestionCheckpoint()
    checkpoint.dead_letter("fact-1", "throttled", recorded_at_utc=datetime(2026, 1, 1, tzinfo=UTC))
    checkpoint.dead_letter("fact-2", "schema", recorded_at_utc=datetime(2026, 1, 1, tzinfo=UTC))
    assert [item.retryable for item in checkpoint.dead_letters] == [True, False]
    assert not hasattr(checkpoint.dead_letters[0], "payload")


def test_naive_times_fail_closed() -> None:
    """Checkpoint timestamps require explicit timezone information."""
    checkpoint = IngestionCheckpoint()
    with pytest.raises(ValueError, match="timezone"):
        checkpoint.accept("fact-1", datetime(2026, 1, 1))  # noqa: DTZ001
    with pytest.raises(ValueError, match="timezone"):
        checkpoint.dead_letter("fact-1", "schema", recorded_at_utc=datetime(2026, 1, 1))  # noqa: DTZ001


def test_checkpoint_identifier_sets_are_bounded() -> None:
    """Checkpoint state stays within the configured Dataverse storage bound."""
    checkpoint = IngestionCheckpoint(max_tracked_ids=2)
    for index in range(3):
        checkpoint.accept(f"fact-{index}", datetime(2026, 1, index + 1, tzinfo=UTC))
    assert checkpoint.accepted_fact_ids == {"fact-1", "fact-2"}


def test_checkpoint_rejects_invalid_bound() -> None:
    """A zero-sized checkpoint is invalid rather than silently lossy."""
    with pytest.raises(ValueError, match="positive"):
        IngestionCheckpoint(max_tracked_ids=0)
