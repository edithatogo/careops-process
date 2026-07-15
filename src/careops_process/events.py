"""Fail-closed validation for minimized object-centric event facts."""

from __future__ import annotations

import polars as pl

REQUIRED_COLUMNS = {
    "event_id": pl.String,
    "event_type": pl.String,
    "timestamp_utc": pl.Datetime(time_zone="UTC"),
    "source_system": pl.String,
    "observed_or_inferred": pl.String,
    "confidence": pl.Float64,
}

PROHIBITED_COLUMNS = frozenset(
    {"body", "body_preview", "email_address", "sender_email", "recipient_email", "subject"}
)


class EventFrameError(ValueError):
    """Raised when an event frame violates the canonical privacy contract."""


def validate_events(frame: pl.DataFrame) -> pl.DataFrame:
    """Validate and deterministically order a minimized event frame.

    Args:
        frame: Candidate canonical event facts.

    Returns:
        A deterministically sorted clone suitable for downstream processing.

    Raises:
        EventFrameError: If schema, privacy, identity, or confidence checks fail.

    """
    prohibited = sorted(PROHIBITED_COLUMNS.intersection(frame.columns))
    if prohibited:
        msg = f"Prohibited content columns: {', '.join(prohibited)}"
        raise EventFrameError(msg)

    missing = sorted(set(REQUIRED_COLUMNS).difference(frame.columns))
    if missing:
        msg = f"Missing required columns: {', '.join(missing)}"
        raise EventFrameError(msg)

    if frame.select(pl.col("event_id").is_null().any()).item():
        message = "event_id must not be null"
        raise EventFrameError(message)
    if frame.select(pl.col("event_id").is_duplicated().any()).item():
        message = "event_id must be unique"
        raise EventFrameError(message)
    if frame.select((~pl.col("observed_or_inferred").is_in(["observed", "inferred"])).any()).item():
        message = "observed_or_inferred must be observed or inferred"
        raise EventFrameError(message)
    if frame.select((~pl.col("confidence").is_between(0.0, 1.0, closed="both")).any()).item():
        message = "confidence must be between 0 and 1"
        raise EventFrameError(message)

    return frame.sort(["timestamp_utc", "event_id"])
