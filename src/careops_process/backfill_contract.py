"""Validation for the cloud-only historical Outlook backfill contract."""

from typing import Any


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_backfill_contract(contract: dict[str, Any]) -> None:
    """Fail closed unless completeness and privacy invariants are present."""
    route = contract.get("route") or {}
    if route.get("platform") != "Power Automate":
        _fail("backfill must use Power Automate")
    completeness = contract.get("completeness_contract") or {}
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
    projection = contract.get("projection") or {}
    forbidden = set(projection.get("forbidden_persistent_fields", []))
    if {"body", "subject", "attachments"} - forbidden:
        _fail("raw email fields are not forbidden")
    operation = contract.get("operation") or {}
    if operation.get("never_store_raw_payload") is not True:
        _fail("raw payload storage must be disabled")
    if operation.get("never_advance_checkpoint_on_failure") is not True:
        _fail("checkpoint must not advance on failure")
    complete_when = completeness.get("run_is_complete_only_when") or []
    if "rerun produces zero new identities for unchanged input" not in complete_when:
        _fail("idempotency completion gate is missing")
