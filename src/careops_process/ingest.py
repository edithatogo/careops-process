"""Low-privilege ingestion boundary for minimized M365 and Dataverse facts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from .ocel import OcelEvent, OcelLog, OcelObject, pseudonymize, validate_ocel

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

REQUIRED_FACT_FIELDS = frozenset({"id", "activity", "timestamp_utc", "source_system", "object_ids"})
FORBIDDEN_FACT_FIELDS = frozenset(
    {"body", "body_preview", "subject", "sender", "recipients", "email_address"}
)


class IngestionError(ValueError):
    """Raised when a source fact cannot safely enter the canonical log."""


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        message = "timestamp_utc must be an ISO-8601 string"
        raise IngestionError(message)
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        message = "timestamp_utc is not valid ISO-8601"
        raise IngestionError(message) from error
    if timestamp.tzinfo is None:
        message = "timestamp_utc must include an explicit timezone"
        raise IngestionError(message)
    return timestamp.astimezone(UTC)


def facts_to_ocel(
    facts: Sequence[Mapping[str, object]],
    *,
    log_id: str,
    schema_version: str,
    pseudonym_secret: str,
    after: datetime | None = None,
) -> OcelLog:
    """Convert minimized source facts to a validated OCEL log.

    The adapter accepts no raw email fields. ``after`` is an exclusive
    watermark, allowing incremental polling without mailbox export.
    """
    events: list[OcelEvent] = []
    objects: dict[str, OcelObject] = {}
    for fact in facts:
        forbidden = FORBIDDEN_FACT_FIELDS.intersection(fact)
        if forbidden:
            message = f"Raw content fields are prohibited: {', '.join(sorted(forbidden))}"
            raise IngestionError(message)
        missing = REQUIRED_FACT_FIELDS.difference(fact)
        if missing:
            message = f"Missing source fact fields: {', '.join(sorted(missing))}"
            raise IngestionError(message)
        timestamp = _parse_timestamp(fact["timestamp_utc"])
        if after is not None and timestamp <= after:
            continue
        raw_fact_id, raw_activity, raw_source = fact["id"], fact["activity"], fact["source_system"]
        raw_object_ids = fact["object_ids"]
        if not all(isinstance(value, str) for value in (raw_fact_id, raw_activity, raw_source)):
            message = "id, activity, and source_system must be strings"
            raise IngestionError(message)
        if not isinstance(raw_object_ids, list):
            message = "object_ids must be a list of strings"
            raise IngestionError(message)
        candidate_object_ids = cast("list[object]", raw_object_ids)
        if not all(isinstance(value, str) for value in candidate_object_ids):
            message = "object_ids must be a list of strings"
            raise IngestionError(message)
        fact_id = cast("str", raw_fact_id)
        activity = cast("str", raw_activity)
        source = cast("str", raw_source)
        object_values = cast("list[str]", raw_object_ids)
        event_id = pseudonymize(f"event:{fact_id}", secret=pseudonym_secret)
        object_ids = [
            pseudonymize(f"object:{value}", secret=pseudonym_secret) for value in object_values
        ]
        for object_id in object_ids:
            objects.setdefault(
                object_id, OcelObject(object_id=object_id, object_type="source_object")
            )
        events.append(
            OcelEvent(
                event_id=event_id,
                event_type=activity,
                timestamp_utc=timestamp,
                source_system=source,
                observed_or_inferred="observed",
                confidence=1.0,
                object_ids=object_ids,
            )
        )
    if not events:
        message = "No facts remain after watermark filtering"
        raise IngestionError(message)
    return validate_ocel(
        OcelLog(
            log_id=log_id,
            schema_version=schema_version,
            lineage="minimized M365/Dataverse fact projection",
            objects=list(objects.values()),
            events=events,
        )
    )
