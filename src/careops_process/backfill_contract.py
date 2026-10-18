# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Validation for the cloud-only historical Outlook backfill contract."""

from typing import Any, cast


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_backfill_contract(contract: dict[str, Any]) -> None:
    """Fail closed unless completeness and privacy invariants are present."""
    route = cast("dict[str, Any]", contract.get("route") or {})
    if route.get("platform") != "Power Automate":
        _fail("backfill must use Power Automate")
    completeness = cast("dict[str, Any]", contract.get("completeness_contract") or {})
    required = {
        "folder_inventory_required",
        "include_nested_folders",
        "follow_next_link_until_exhausted",
        "exhaustion_required_per_folder",
    }
    if not all(completeness.get(key) is True for key in required):
        _fail("backfill completeness controls are incomplete")
    if completeness.get("date_filter") is not None:
        _fail("historical backfill must not apply a date filter")
    projection = cast("dict[str, Any]", contract.get("projection") or {})
    forbidden = set(cast("list[str]", projection.get("forbidden_persistent_fields") or []))
    raw_fields = {
        "body",
        "bodyPreview",
        "subject",
        "from",
        "sender",
        "to",
        "cc",
        "bcc",
        "attachments",
        "displayName",
        "phone",
    }
    if raw_fields - forbidden:
        _fail("raw email fields are not forbidden")
    pseudonyms = set(cast("list[str]", projection.get("pseudonymise") or []))
    if {"id", "internetMessageId", "conversationId", "folder_id"} - pseudonyms:
        _fail("source identity pseudonymisation is incomplete")
    source_metadata = set(cast("list[str]", projection.get("allowed_source_metadata") or []))
    allowed_metadata = {
        "id",
        "internetMessageId",
        "receivedDateTime",
        "conversationId",
        "hasAttachments",
        "importance",
        "parentFolderId",
    }
    if not source_metadata or source_metadata - allowed_metadata:
        _fail("source metadata is outside the minimized allowlist")
    operation = cast("dict[str, Any]", contract.get("operation") or {})
    if operation.get("never_store_raw_payload") is not True:
        _fail("raw payload storage must be disabled")
    if operation.get("never_advance_checkpoint_on_failure") is not True:
        _fail("checkpoint must not advance on failure")
    complete_when = cast("list[str]", completeness.get("run_is_complete_only_when") or [])
    if "rerun produces zero new identities for unchanged input" not in complete_when:
        _fail("idempotency completion gate is missing")
