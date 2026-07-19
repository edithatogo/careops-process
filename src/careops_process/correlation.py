"""Cross-source object-centric corpus reconstruction."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from careops_process.ocel import OcelEvent, OcelLog, OcelObject, OcelRelation, validate_ocel


@dataclass(frozen=True, slots=True)
class CorrelationHypothesis:
    """An explainable inferred object link awaiting human confirmation."""

    source_object_id: str
    target_object_id: str
    relation_type: str
    confidence: float
    rule_version: str

    def __post_init__(self) -> None:
        """Keep hypotheses uncertain, versioned, and non-reflexive."""
        if not 0.0 < self.confidence < 1.0:
            message = "hypothesis confidence must be greater than 0 and less than 1"
            raise ValueError(message)
        if self.source_object_id == self.target_object_id:
            message = "hypothesis cannot self-reference"
            raise ValueError(message)
        if not self.rule_version.strip():
            message = "hypothesis rule version is required"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class CorpusQualityReport:
    """Inspectable corpus integrity and lifecycle gaps."""

    event_count: int
    object_count: int
    single_event_objects: tuple[str, ...]
    incomplete_lifecycle_objects: tuple[str, ...]
    out_of_order_objects: tuple[str, ...]
    source_event_counts: tuple[tuple[str, int], ...]


def _object_type(object_id: str) -> str:
    prefix, separator, _ = object_id.partition(":")
    if not separator or not prefix:
        message = f"object identifier has no type prefix: {object_id}"
        raise ValueError(message)
    return prefix


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    message = "fact timestamp_utc must be a datetime or ISO string"
    raise TypeError(message)


def build_ocel_from_facts(
    facts: list[dict[str, object]],
    *,
    log_id: str,
    lineage: str,
    schema_version: str = "1.0.0",
) -> OcelLog:
    """Reconstruct a deterministic OCEL log from minimized source facts."""
    object_types: dict[str, str] = {}
    events: list[OcelEvent] = []
    for fact in facts:
        raw_object_ids = fact.get("object_ids")
        if not isinstance(raw_object_ids, list) or not raw_object_ids:
            message = "fact object_ids must be a non-empty list"
            raise ValueError(message)
        object_ids = cast("list[object]", raw_object_ids)
        if not all(isinstance(item, str) for item in object_ids):
            message = "fact object_ids must contain strings"
            raise TypeError(message)
        typed_ids = cast("list[str]", object_ids)
        raw_overrides = fact.get("object_types", {})
        if not isinstance(raw_overrides, dict):
            message = "object_types must be a mapping"
            raise TypeError(message)
        overrides = cast("dict[object, object]", raw_overrides)
        for object_id in typed_ids:
            inferred_type = _object_type(object_id)
            raw_override = overrides.get(object_id, inferred_type)
            if not isinstance(raw_override, str):
                message = "object type override must be a string"
                raise TypeError(message)
            existing = object_types.get(object_id)
            if existing is not None and existing != raw_override:
                message = f"conflicting object type for {object_id}"
                raise ValueError(message)
            if raw_override != inferred_type:
                message = f"conflicting object type for {object_id}"
                raise ValueError(message)
            object_types[object_id] = raw_override
        events.append(
            OcelEvent(
                event_id=str(fact["id"]),
                event_type=str(fact["activity"]),
                timestamp_utc=_timestamp(fact["timestamp_utc"]),
                source_system=str(fact["source_system"]),
                observed_or_inferred="observed",
                confidence=1.0,
                object_ids=typed_ids,
            )
        )
    objects = [
        OcelObject(object_id=object_id, object_type=object_type)
        for object_id, object_type in sorted(object_types.items())
    ]
    events.sort(key=lambda event: (event.timestamp_utc, event.event_id))
    return validate_ocel(
        OcelLog(
            log_id=log_id,
            objects=objects,
            events=events,
            lineage=lineage,
            schema_version=schema_version,
        )
    )


def hypothesis_relation(hypothesis: CorrelationHypothesis) -> OcelRelation:
    """Convert a versioned hypothesis to an inferred OCEL relation."""
    identity = (
        f"{hypothesis.source_object_id}|{hypothesis.target_object_id}|"
        f"{hypothesis.relation_type}|{hypothesis.rule_version}"
    )
    relation_id = "hyp_" + hashlib.sha256(identity.encode()).hexdigest()[:24]
    return OcelRelation(
        relation_id=relation_id,
        relation_type=hypothesis.relation_type,
        source_object_id=hypothesis.source_object_id,
        target_object_id=hypothesis.target_object_id,
        observed_or_inferred="inferred",
        confidence=hypothesis.confidence,
    )


def corpus_fingerprint(log: OcelLog) -> str:
    """Hash a canonical OCEL representation for rebuild comparison."""
    payload = log.model_dump_json(exclude_none=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def evaluate_corpus_quality(log: OcelLog) -> CorpusQualityReport:
    """Report source balance, sparse objects, and missing lifecycle closure."""
    object_events: dict[str, list[str]] = defaultdict(list)
    object_timed_events: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    source_counts: Counter[str] = Counter()
    for event in log.events:
        source_counts[event.source_system] += 1
        for object_id in event.object_ids:
            object_events[object_id].append(event.event_type)
            object_timed_events[object_id].append((event.timestamp_utc, event.event_type))
    single_event = tuple(sorted(key for key, values in object_events.items() if len(values) == 1))
    incomplete = tuple(
        sorted(
            key
            for key, values in object_events.items()
            if any(value.endswith("_created") for value in values)
            and not any(value.endswith(("_completed", "_decided", "_closed")) for value in values)
        )
    )
    out_of_order = tuple(
        sorted(
            key
            for key, values in object_timed_events.items()
            if any(event_type.endswith("_created") for _, event_type in values)
            and any(
                event_type.endswith(("_completed", "_decided", "_closed"))
                for _, event_type in values
            )
            and min(
                timestamp for timestamp, event_type in values if event_type.endswith("_created")
            )
            > min(
                timestamp
                for timestamp, event_type in values
                if event_type.endswith(("_completed", "_decided", "_closed"))
            )
        )
    )
    return CorpusQualityReport(
        event_count=len(log.events),
        object_count=len(log.objects),
        single_event_objects=single_event,
        incomplete_lifecycle_objects=incomplete,
        out_of_order_objects=out_of_order,
        source_event_counts=tuple(sorted(source_counts.items())),
    )
