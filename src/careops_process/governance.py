"""Governance and Executive decision validation boundaries."""

from __future__ import annotations

from typing import Any, cast


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_executive_record(record: dict[str, Any]) -> None:  # noqa: C901
    """Fail closed unless a sanitized Executive decision record is valid."""
    required = (
        "run_id",
        "evidence_reference",
        "scope_approved",
        "ig_approved",
        "owner_validation",
        "executive_decision",
    )
    missing = [key for key in required if record.get(key) is None]
    if missing:
        _fail(f"missing governance fields: {', '.join(missing)}")
    if not isinstance(record["owner_validation"], dict):
        _fail("owner_validation must be an object")
    if not isinstance(record["scope_approved"], bool) or not isinstance(
        record["ig_approved"], bool
    ):
        _fail("approval fields must be boolean")
    if record["executive_decision"] not in {
        "pending",
        "fit-for-improvement",
        "expand-pilot",
        "pause",
        "close",
    }:
        _fail("unsupported Executive decision")
    owner = cast("dict[str, Any]", record["owner_validation"])
    if owner.get("status") not in {"pending", "complete"}:
        _fail("unsupported owner validation status")
    for count in ("validated_family_count", "unresolved_family_count"):
        if (
            not isinstance(owner.get(count), int)
            or isinstance(owner.get(count), bool)
            or owner[count] < 0
        ):
            _fail(f"{count} must be a non-negative integer")
    if record["executive_decision"] != "pending":
        if record["scope_approved"] is not True or record["ig_approved"] is not True:
            _fail("executive decision requires scope and IG approval")
        if owner.get("status") != "complete":
            _fail("executive decision requires owner validation")
