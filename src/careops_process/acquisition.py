# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Connector-neutral complete-population acquisition primitives."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

REQUIRED_FACT_FIELDS = frozenset({"id", "activity", "timestamp_utc", "source_system", "object_ids"})
PROHIBITED_FIELDS = frozenset(
    {
        "body",
        "bodyPreview",
        "subject",
        "from",
        "to",
        "cc",
        "bcc",
        "title",
        "description",
        "comments",
        "email",
        "attachments",
    }
)


@dataclass(frozen=True, slots=True)
class AcquisitionPage:
    """One source page plus its opaque continuation cursor."""

    records: tuple[Mapping[str, object], ...]
    next_cursor: str | None


class TransientSourceError(RuntimeError):
    """A bounded-retry source failure such as throttling or timeout."""


@dataclass(frozen=True, slots=True)
class DeadLetter:
    """Minimized malformed-record evidence without source payload."""

    fact_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class AcquisitionManifest:
    """Reconciliation evidence for one source partition."""

    source: str
    container: str
    pages_read: int
    candidate_count: int
    acquired_count: int
    duplicate_count: int
    rejected_count: int
    filtered_count: int
    retry_count: int
    exhausted: bool
    withdrawn: bool
    content_hash: str


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    """Minimized facts and their reconciliation evidence."""

    facts: tuple[dict[str, object], ...]
    dead_letters: tuple[DeadLetter, ...]
    manifest: AcquisitionManifest


def _content_hash(facts: tuple[dict[str, object], ...]) -> str:
    payload = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _normalize_fact(record: Mapping[str, object]) -> dict[str, object] | None:
    prohibited = PROHIBITED_FIELDS.intersection(record)
    if prohibited:
        fields = ", ".join(sorted(prohibited))
        message = f"prohibited raw fields at acquisition boundary: {fields}"
        raise ValueError(message)
    if not REQUIRED_FACT_FIELDS.issubset(record):
        return None
    identifier = record["id"]
    activity = record["activity"]
    timestamp = record["timestamp_utc"]
    source_system = record["source_system"]
    object_ids = record["object_ids"]
    scalar_values = (identifier, activity, timestamp, source_system)
    if not all(isinstance(value, str) for value in scalar_values):
        return None
    if not isinstance(object_ids, list):
        return None
    raw_object_ids = cast("list[object]", object_ids)
    if not all(isinstance(value, str) for value in raw_object_ids):
        return None
    return {
        "id": identifier,
        "activity": activity,
        "timestamp_utc": timestamp,
        "source_system": source_system,
        "object_ids": list(raw_object_ids),
    }


def acquire_partition(  # noqa: C901, PLR0912, PLR0913, PLR0915
    source: str,
    container: str,
    fetch_page: Callable[[str | None], AcquisitionPage],
    *,
    withdrawn: bool = False,
    watermark_utc: str | None = None,
    max_retries: int = 0,
    retry_backoff_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> AcquisitionResult:
    """Acquire a partition to exhaustion with deterministic reconciliation."""
    if withdrawn:
        facts: tuple[dict[str, object], ...] = ()
        return AcquisitionResult(
            facts=facts,
            dead_letters=(),
            manifest=AcquisitionManifest(
                source=source,
                container=container,
                pages_read=0,
                candidate_count=0,
                acquired_count=0,
                duplicate_count=0,
                rejected_count=0,
                filtered_count=0,
                retry_count=0,
                exhausted=False,
                withdrawn=True,
                content_hash=_content_hash(facts),
            ),
        )
    if max_retries < 0:
        message = "max_retries must not be negative"
        raise ValueError(message)
    if retry_backoff_seconds < 0:
        message = "retry_backoff_seconds must not be negative"
        raise ValueError(message)

    cursor: str | None = None
    seen_cursors: set[str] = set()
    seen_ids: set[str] = set()
    facts_list: list[dict[str, object]] = []
    dead_letters: list[DeadLetter] = []
    pages_read = 0
    candidate_count = 0
    duplicate_count = 0
    filtered_count = 0
    retry_count = 0

    while True:
        if cursor is not None:
            if cursor in seen_cursors:
                message = f"cursor loop detected for {source}/{container}"
                raise ValueError(message)
            seen_cursors.add(cursor)
        page_attempts = 0
        while True:
            try:
                page = fetch_page(cursor)
                break
            except TransientSourceError:
                if page_attempts >= max_retries:
                    raise
                sleep(retry_backoff_seconds * (2**page_attempts))
                page_attempts += 1
                retry_count += 1
        pages_read += 1
        for record in page.records:
            candidate_count += 1
            normalized = _normalize_fact(record)
            if normalized is None:
                raw_id = record.get("id")
                fact_id = raw_id if isinstance(raw_id, str) else "unknown"
                dead_letters.append(DeadLetter(fact_id=fact_id, reason="missing_required_fields"))
                continue
            identifier = str(normalized["id"])
            timestamp = str(normalized["timestamp_utc"])
            if watermark_utc is not None and timestamp <= watermark_utc:
                filtered_count += 1
                continue
            if identifier in seen_ids:
                duplicate_count += 1
                continue
            seen_ids.add(identifier)
            facts_list.append(normalized)
        cursor = page.next_cursor
        if cursor is None:
            break

    facts = tuple(facts_list)
    return AcquisitionResult(
        facts=facts,
        dead_letters=tuple(dead_letters),
        manifest=AcquisitionManifest(
            source=source,
            container=container,
            pages_read=pages_read,
            candidate_count=candidate_count,
            acquired_count=len(facts),
            duplicate_count=duplicate_count,
            rejected_count=len(dead_letters),
            filtered_count=filtered_count,
            retry_count=retry_count,
            exhausted=True,
            withdrawn=False,
            content_hash=_content_hash(facts),
        ),
    )
