"""Synthetic run-scoped Dataverse row identity; no authentication or service writes."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Never, cast
from uuid import UUID, uuid5

from careops_process.outlook_reconciliation import CanonicalMailFact

if TYPE_CHECKING:
    from collections.abc import Mapping

ENTITY_SET = "cop_processevents"
PRIMARY_KEY = "cop_processeventid"
FIELD_MAPPING = (
    ("id", "cop_eventkey"),
    ("activity", "cop_activity"),
    ("timestamp_utc", "cop_timestamputc"),
    ("source_system", "cop_sourcesystem"),
    ("object_ids", "cop_objectids"),
)
_OBJECT_LIMIT = 4000
_MAIL_ID = re.compile(r"mail_[a-f0-9]{64}")


def _guid(value: str) -> UUID:
    try:
        parsed = UUID(value)
        if type(value) is str and str(parsed) == value and parsed.int:
            return parsed
    except ValueError, TypeError, AttributeError:
        pass
    message = "invalid_destination_identity"
    raise ValueError(message)


def row_id(org_id: str, run_id: str, fact_id: str) -> str:
    """Derive a v1 primary key; this provides no server alternate-key guarantee."""
    organization = str(_guid(org_id))
    namespace = _guid(run_id)
    if type(fact_id) is not str or _MAIL_ID.fullmatch(fact_id) is None:
        message = "invalid_destination_identity"
        raise ValueError(message)
    name = json.dumps(
        ["careops-outlook-destination-v1", organization, fact_id],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return str(uuid5(namespace, name))


def _invalid() -> Never:
    message = "invalid_destination_fact"
    raise ValueError(message)


def serialize_fact(fact: CanonicalMailFact) -> dict[str, str]:
    """Validate a minimized fact against the verified Developer column constraints."""
    try:
        if type(fact) is not CanonicalMailFact:
            _invalid()
        checked = CanonicalMailFact.model_validate(fact.model_dump())
        instant = datetime.fromisoformat(checked.timestamp_utc)
        if instant.utcoffset() is None or instant.microsecond:
            _invalid()
        if not checked.object_ids or len(set(checked.object_ids)) != len(checked.object_ids):
            _invalid()
        for item in [checked.id, *checked.object_ids]:
            pattern = _MAIL_ID if item == checked.id else re.compile(r"conversation_[a-f0-9]{64}")
            if pattern.fullmatch(item) is None:
                _invalid()
        objects = json.dumps(sorted(checked.object_ids), separators=(",", ":"), ensure_ascii=True)
        if len(objects) > _OBJECT_LIMIT:
            _invalid()
        return {
            "cop_eventkey": checked.id,
            "cop_activity": checked.activity,
            "cop_timestamputc": instant.astimezone(UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            "cop_sourcesystem": checked.source_system,
            "cop_objectids": objects,
        }
    except ValueError, TypeError, AttributeError, OverflowError:
        message = "invalid_destination_fact"
        raise ValueError(message) from None


def parse_readback(row: Mapping[str, object]) -> CanonicalMailFact:
    """Decode an exact selected five-field response without trusting extra payloads."""
    try:
        if type(row) is not dict:
            _invalid()
        selected = cast("Mapping[str, object]", row)
        if set(selected) != {column for _, column in FIELD_MAPPING}:
            _invalid()
        if any(type(value) is not str for value in selected.values()):
            _invalid()
        values: dict[str, object] = {name: selected[column] for name, column in FIELD_MAPPING}
        values["object_ids"] = json.loads(cast("str", values["object_ids"]))
        fact = CanonicalMailFact.model_validate(values)
        normalized = serialize_fact(fact)
        return CanonicalMailFact(
            id=fact.id,
            activity=fact.activity,
            timestamp_utc=normalized["cop_timestamputc"],
            source_system=fact.source_system,
            object_ids=sorted(fact.object_ids),
        )
    except ValueError, TypeError, AttributeError, KeyError:
        message = "invalid_destination_fact"
        raise ValueError(message) from None
