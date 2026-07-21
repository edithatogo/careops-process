"""Fail-closed entry controls for the authorised corpus-scale pilot."""

from __future__ import annotations

from typing import Any, cast


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_pilot_entry(record: dict[str, Any]) -> None:
    """Require explicit approvals and operational controls before extraction."""
    if not isinstance(record, dict):
        _fail("pilot entry record must be a dictionary")
    required = (
        "source_owner_approved",
        "ig_approved",
        "configuration_frozen",
        "rollback_retention_approved",
        "authorised_source_partitions",
        "evidence_reference",
    )
    missing = [key for key in required if record.get(key) is None]
    if missing:
        _fail(f"pilot entry fields missing: {', '.join(missing)}")
    evidence_ref = record["evidence_reference"]
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        _fail("evidence_reference must be a non-empty string")
    approval_fields = required[:4]
    if not all(record[field] is True for field in approval_fields):
        _fail("pilot entry requires all approval and freeze gates")
    partitions = cast("list[Any]", record["authorised_source_partitions"])
    if type(partitions) is not list or not partitions:
        _fail("pilot entry requires at least one authorised source partition")
    if any(type(partition) is not str or not partition.strip() for partition in partitions):
        _fail("authorised source partitions must be non-empty labels")
