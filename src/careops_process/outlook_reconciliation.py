# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Offline reconciliation of supplied Outlook folder/page and destination evidence."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from .backfill_evidence import evidence_digest

if TYPE_CHECKING:
    from collections.abc import Callable

MINIMUM_KEY_BYTES = 32

FolderReference = Annotated[str, Field(pattern=r"^folder_[a-f0-9]{64}$")]
MailReference = Annotated[str, Field(pattern=r"^mail_[a-f0-9]{64}$")]
ConversationReference = Annotated[str, Field(pattern=r"^conversation_[a-f0-9]{64}$")]
Count = Annotated[int, Field(ge=0)]


class EvidenceModel(BaseModel):
    """Strict minimized evidence boundary with no implicit coercion or extras."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class FolderEntry(EvidenceModel):
    """One supplied inventory entry; no raw folder names or source identifiers."""

    folder_id: FolderReference
    parent_folder_id: FolderReference | None
    disposition: Literal["included", "excluded", "inaccessible"]
    reason: (
        Literal["owner-excluded-system-folder", "owner-excluded-scope", "source-inaccessible"]
        | None
    )
    children_enumerated: bool
    source_record_count: Count | None


class CanonicalMailFact(EvidenceModel):
    """Exact five-field input accepted by the closed-run report consumer."""

    id: MailReference
    activity: Literal["email_received"]
    timestamp_utc: str
    source_system: Literal["outlook"]
    object_ids: list[ConversationReference]


class CollectorMailFact(CanonicalMailFact):
    """Acquired collector record before its explicit canonical mapping."""

    folder_id: FolderReference
    has_attachments: bool
    importance: Literal["low", "normal", "high"]


class FolderPage(EvidenceModel):
    """Measured page accounting supplied by the folder-scoped acquisition lane."""

    folder_id: FolderReference
    page_number: Annotated[int, Field(ge=1)]
    candidate_count: Count
    acquired_count: Count
    duplicate_count: Count
    rejected_count: Count
    fact_ids: list[MailReference]
    next_link_exhausted: bool


def collect_folder_inventory(
    fetch_page: Callable[[str | None, str | None, bool], dict[str, Any]],
    *,
    pseudonym_key: bytes,
    mailbox_ref: str,
    excluded_folder_refs: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Traverse supplied source pages without storing protected folder identity."""
    try:
        _require(len(pseudonym_key) >= MINIMUM_KEY_BYTES, "strong pseudonym key required")
        _require(
            re.fullmatch(r"mailbox_[a-f0-9]{64}", mailbox_ref) is not None,
            "mailbox pseudonym required",
        )
        excluded = excluded_folder_refs or set()
        queue: list[tuple[str | None, str | None, bool, int | None]] = [(None, None, False, None)]
        seen_ids: set[str] = set()
        result: list[dict[str, Any]] = []
        include_hidden = True
        for parent, parent_ref, inherited_exclusion, expected_children in queue:
            cursor: str | None = None
            seen_cursors: set[str] = set()
            observed_children = 0
            while True:
                if cursor is not None:
                    _require(cursor not in seen_cursors, "folder pagination cycle")
                    seen_cursors.add(cursor)
                # The connection adapter owns approved credentials, retries and
                # cursor destination checks. Always request hidden folders too.
                page = _source_page(fetch_page(parent, cursor, include_hidden))
                _require(isinstance(page.get("value"), list), "folder page required")
                for raw in page["value"]:
                    _require(isinstance(raw, dict), "folder record required")
                    identifier = raw.get("id")
                    child_count = raw.get("childFolderCount")
                    source_count = raw.get("totalItemCount")
                    _require(
                        isinstance(identifier, str) and bool(identifier.strip()),
                        "folder identity required",
                    )
                    _require(identifier not in seen_ids, "repeated source folder")
                    _require(
                        type(child_count) is int and child_count >= 0, "child denominator required"
                    )
                    _require(
                        type(source_count) is int and source_count >= 0,
                        "source denominator required",
                    )
                    _require(
                        parent is None or raw.get("parentFolderId") == parent, "wrong source parent"
                    )
                    seen_ids.add(identifier)
                    payload = json.dumps(
                        ["folder", mailbox_ref, identifier],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    folder_ref = (
                        "folder_"
                        + hmac.new(pseudonym_key, payload.encode(), hashlib.sha256).hexdigest()
                    )
                    is_excluded = inherited_exclusion or folder_ref in excluded
                    result.append(
                        {
                            "folder_id": folder_ref,
                            "parent_folder_id": parent_ref,
                            "disposition": "excluded" if is_excluded else "included",
                            "reason": "owner-excluded-scope" if is_excluded else None,
                            "children_enumerated": True,
                            "source_record_count": None if is_excluded else source_count,
                        }
                    )
                    queue.append((identifier, folder_ref, is_excluded, child_count))
                    observed_children += 1
                next_cursor = page.get("@odata.nextLink")
                _require(
                    next_cursor is None or (isinstance(next_cursor, str) and bool(next_cursor)),
                    "invalid folder cursor",
                )
                if next_cursor is None:
                    break
                cursor = next_cursor
            _require(
                expected_children is None or observed_children == expected_children,
                "source child inventory drift",
            )
        _require(
            excluded.issubset({item["folder_id"] for item in result}),
            "excluded folder absent from inventory",
        )
        _require(bool(result), "source folder inventory empty")
    except ValueError, RuntimeError, OSError, TypeError, KeyError:
        message = (
            "Outlook inventory collection failed; source scope or traversal remains unverified"
        )
        raise ValueError(message) from None
    return result


def _require(condition: bool, message: str) -> None:  # noqa: FBT001
    if not condition:
        raise ValueError(message)


def _source_page(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        message = "folder envelope required"
        raise TypeError(message)
    return cast("dict[str, Any]", value)


def _inventory(entries: list[FolderEntry]) -> list[str]:
    by_id = {entry.folder_id: entry for entry in entries}
    _require(bool(entries) and len(by_id) == len(entries), "inventory requires unique folders")
    for entry in entries:
        _require(entry.children_enumerated, "nested folder enumeration is incomplete")
        _require(entry.disposition != "inaccessible", "inaccessible population remains unknown")
        if entry.disposition == "included":
            _require(entry.reason is None, "included folder cannot carry an exclusion reason")
            _require(entry.source_record_count is not None, "source denominator required")
        else:
            _require(
                entry.reason in {"owner-excluded-system-folder", "owner-excluded-scope"},
                "excluded folder requires an owner exclusion, not an unknown population",
            )
        visited: set[str] = set()
        current: str | None = entry.folder_id
        while current is not None:
            _require(current in by_id, "folder parent absent from inventory")
            _require(current not in visited, "folder ancestry cycle")
            _require(
                entry.disposition != "included" or by_id[current].disposition == "included",
                "included folder descends from an excluded ancestor",
            )
            visited.add(current)
            current = by_id[current].parent_folder_id
    admitted = [entry.folder_id for entry in entries if entry.disposition == "included"]
    _require(bool(admitted), "no admitted folders")
    return admitted


def _canonical(facts: list[CollectorMailFact]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fact in facts:
        _require(fact.id not in seen, "duplicate collector fact")
        seen.add(fact.id)
        _require(
            bool(fact.object_ids) and len(set(fact.object_ids)) == len(fact.object_ids),
            "invalid object references",
        )
        _require(
            datetime.fromisoformat(fact.timestamp_utc).utcoffset() is not None,
            "timestamp needs timezone",
        )
        result.append(fact.model_dump(exclude={"folder_id", "has_attachments", "importance"}))
    return result


def _partition(
    folder: FolderEntry, pages: list[FolderPage], facts: list[CollectorMailFact]
) -> dict[str, Any]:
    ledger = [page for page in pages if page.folder_id == folder.folder_id]
    _require(bool(ledger), "folder page evidence missing")
    _require(
        [page.page_number for page in ledger] == list(range(1, len(ledger) + 1)),
        "page sequence gap or repeat",
    )
    _require(
        ledger[-1].next_link_exhausted
        and not any(page.next_link_exhausted for page in ledger[:-1]),
        "folder exhaustion inconsistent",
    )
    identifiers: list[str] = []
    for page in ledger:
        _require(
            page.candidate_count
            == page.acquired_count + page.duplicate_count + page.rejected_count,
            "page counts differ",
        )
        _require(page.rejected_count == 0, "unresolved rejected source records")
        _require(page.acquired_count == len(page.fact_ids), "page fact membership differs")
        identifiers.extend(page.fact_ids)
    selected = [fact for fact in facts if fact.folder_id == folder.folder_id]
    _require(len(set(identifiers)) == len(identifiers), "fact assigned to repeated pages")
    _require(set(identifiers) == {fact.id for fact in selected}, "folder fact membership differs")
    candidate_count = sum(page.candidate_count for page in ledger)
    # Page candidates include repeated records; the frozen source denominator
    # counts distinct source records, not duplicate acquisition attempts.
    acquired_count = sum(page.acquired_count for page in ledger)
    _require(acquired_count == folder.source_record_count, "frozen source denominator differs")
    return {
        "partition_id": folder.folder_id,
        "source_system": "outlook",
        "pages_read": len(ledger),
        "candidate_count": candidate_count,
        "acquired_count": acquired_count,
        "duplicate_count": sum(page.duplicate_count for page in ledger),
        "rejected_count": 0,
        "filtered_count": 0,
        "emitted_count": len(selected),
        "fact_ids": [fact.id for fact in selected],
        "content_hash": evidence_digest(_canonical(selected)),
        "next_link_exhausted": True,
    }


def reconcile_outlook_evidence(
    inventory: list[dict[str, Any]],
    collector_facts: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    destination_facts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Validate supplied evidence without manufacturing source or destination facts."""
    try:
        folders = [FolderEntry.model_validate(item) for item in inventory]
        admitted = _inventory(folders)
        facts = [CollectorMailFact.model_validate(item) for item in collector_facts]
        canonical = _canonical(facts)
        ledger = [FolderPage.model_validate(item) for item in pages]
        _require(all(page.folder_id in admitted for page in ledger), "page outside admitted scope")
        _require(all(fact.folder_id in admitted for fact in facts), "fact outside admitted scope")
        partitions = [
            _partition(folder, ledger, facts) for folder in folders if folder.folder_id in admitted
        ]
        if destination_facts is not None:
            destination = [
                CanonicalMailFact.model_validate(item).model_dump() for item in destination_facts
            ]
            _require(
                len({fact["id"] for fact in destination}) == len(destination),
                "duplicate destination identity",
            )
            _require(
                {fact["id"]: fact for fact in destination}
                == {fact["id"]: fact for fact in canonical},
                "destination content differs",
            )
        return {
            "status": "reconciled" if destination_facts is not None else "destination_pending",
            "facts": canonical,
            "content_hash": evidence_digest(canonical),
            "inventory_hash": evidence_digest(inventory),
            "page_ledger_hash": evidence_digest(pages),
            "partitions": partitions,
            "folder_count": len(admitted),
            "excluded_folder_count": len(folders) - len(admitted),
            "page_count": len(ledger),
            "candidate_count": sum(page.candidate_count for page in ledger),
            "destination_reconciled": destination_facts is not None,
            "dataverse_reconciled": False,
            "idempotency_replay_verified": False,
            "full_mailbox_verified": False,
        }
    except ValueError:
        # Pydantic and datetime diagnostics may echo supplied protected values.
        message = "Outlook evidence failed privacy, inventory, page or destination validation"
        raise ValueError(message) from None
