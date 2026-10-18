# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Transform sanitized Dataverse approval metadata into pilot facts."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


REQUIRED_APPROVAL_FIELDS = frozenset({"id", "createdon", "source"})
FORBIDDEN_APPROVAL_FIELDS = frozenset(
    {
        "title",
        "details",
        "description",
        "body",
        "comments",
        "email",
        "emailaddress",
        "owner",
        "requester",
        "approver",
    }
)


def approval_metadata_to_facts(
    records: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Convert safe approval metadata into minimized ingestion facts.

    This boundary intentionally accepts no human-readable approval content or
    identity fields. Each approval produces a creation event and, when present,
    a decision event linked only by its opaque source identifier.
    """
    facts: list[dict[str, object]] = []
    for record in records:
        forbidden = FORBIDDEN_APPROVAL_FIELDS.intersection(record)
        if forbidden:
            message = f"Approval payload fields are prohibited: {', '.join(sorted(forbidden))}"
            raise ValueError(message)
        missing = REQUIRED_APPROVAL_FIELDS.difference(record)
        if missing:
            message = f"Approval metadata fields are missing: {', '.join(sorted(missing))}"
            raise ValueError(message)
        approval_id = record["id"]
        created = record["createdon"]
        source = record["source"]
        if not all(isinstance(value, str) for value in (approval_id, created, source)):
            message = "id, createdon, and source must be strings"
            raise TypeError(message)
        object_ids = [f"approval:{approval_id}"]
        facts.append(
            {
                "id": f"{approval_id}:created",
                "activity": "approval_created",
                "timestamp_utc": created,
                "source_system": cast("str", source),
                "object_ids": object_ids,
            }
        )
        completed = record.get("completedon")
        if completed is not None:
            if not isinstance(completed, str):
                message = "completedon must be a string when present"
                raise TypeError(message)
            facts.append(
                {
                    "id": f"{approval_id}:decided",
                    "activity": "approval_decided",
                    "timestamp_utc": completed,
                    "source_system": cast("str", source),
                    "object_ids": object_ids,
                }
            )
    if not facts:
        message = "approval metadata must contain at least one record"
        raise ValueError(message)
    return facts
