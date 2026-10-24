# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Canonical event-contract tests use synthetic facts only."""

from datetime import UTC, datetime

import polars as pl
import pytest

from careops_process.events import EventFrameError, validate_events


def synthetic_events() -> pl.DataFrame:
    """Return a minimal synthetic event frame."""
    return pl.DataFrame(
        {
            "event_id": ["evt-2", "evt-1"],
            "event_type": ["approval_decided", "request_received"],
            "timestamp_utc": [
                datetime(2026, 1, 2, tzinfo=UTC),
                datetime(2026, 1, 1, tzinfo=UTC),
            ],
            "source_system": ["synthetic", "synthetic"],
            "observed_or_inferred": ["observed", "inferred"],
            "confidence": [1.0, 0.75],
        },
        schema_overrides={"timestamp_utc": pl.Datetime(time_zone="UTC")},
    )


def test_valid_events_are_deterministically_sorted() -> None:
    """Valid input is sorted by timestamp then identity."""
    result = validate_events(synthetic_events())
    assert result["event_id"].to_list() == ["evt-1", "evt-2"]


@pytest.mark.parametrize("column", ["body", "subject", "email_address"])
def test_sensitive_columns_fail_closed(column: str) -> None:
    """Mailbox content and direct identity fields are rejected."""
    with pytest.raises(EventFrameError, match="Prohibited content"):
        validate_events(synthetic_events().with_columns(pl.lit("secret").alias(column)))


def test_duplicate_identity_fails_closed() -> None:
    """Duplicate event identities cannot silently distort process paths."""
    frame = synthetic_events().with_columns(pl.lit("same").alias("event_id"))
    with pytest.raises(EventFrameError, match="unique"):
        validate_events(frame)


def test_invalid_confidence_fails_closed() -> None:
    """Confidence outside the probability interval is rejected."""
    frame = synthetic_events().with_columns(pl.lit(1.1).alias("confidence"))
    with pytest.raises(EventFrameError, match="between 0 and 1"):
        validate_events(frame)


def test_missing_required_column_fails_closed() -> None:
    """Incomplete canonical schemas are rejected."""
    with pytest.raises(EventFrameError, match="Missing required columns"):
        validate_events(synthetic_events().drop("source_system"))


def test_null_identity_fails_closed() -> None:
    """Null event identities cannot enter the canonical log."""
    frame = synthetic_events().with_columns(
        pl.when(pl.col("event_id") == "evt-1")
        .then(pl.lit(None, dtype=pl.String))
        .otherwise(pl.col("event_id"))
        .alias("event_id")
    )
    with pytest.raises(EventFrameError, match="must not be null"):
        validate_events(frame)


def test_invalid_derivation_kind_fails_closed() -> None:
    """Only explicit observed or inferred provenance is accepted."""
    frame = synthetic_events().with_columns(pl.lit("unknown").alias("observed_or_inferred"))
    with pytest.raises(EventFrameError, match="observed or inferred"):
        validate_events(frame)
