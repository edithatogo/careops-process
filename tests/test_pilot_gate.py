# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Corpus-scale pilot entry gate tests."""

import json
from pathlib import Path
from typing import Any

import pytest

from careops_process.pilot_gate import validate_pilot_entry


def entry() -> dict[str, Any]:
    """Return a fully populated but unapproved pilot entry."""
    return {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": ["outlook-authorised-mailbox"],
        "evidence_reference": "approved-ref",
    }


def test_approved_entry_passes() -> None:
    """All gates and one source partition permit pilot entry."""
    validate_pilot_entry(entry())


def test_repository_template_is_structurally_pending() -> None:
    """The checked-in template remains sanitized and non-authorising."""
    template = json.loads(Path("config/pilot-entry.example.json").read_text())
    assert template["source_owner_approved"] is False
    assert template["ig_approved"] is False
    assert template["authorised_source_partitions"] == []


def test_missing_approval_fails_closed() -> None:
    """A missing approval cannot be inferred from other controls."""
    value = entry()
    value["ig_approved"] = False
    with pytest.raises(ValueError, match="approval"):
        validate_pilot_entry(value)


def test_empty_partition_scope_fails_closed() -> None:
    """A pilot cannot run without an explicit source partition."""
    value = entry()
    value["authorised_source_partitions"] = []
    with pytest.raises(ValueError, match="source partition"):
        validate_pilot_entry(value)


def test_blank_partition_label_fails_closed() -> None:
    """A blank partition label cannot define an authorised scope."""
    value = entry()
    value["authorised_source_partitions"] = [" "]
    with pytest.raises(ValueError, match="non-empty"):
        validate_pilot_entry(value)


def test_blank_evidence_reference_fails_closed() -> None:
    """An audit reference is required for pilot entry."""
    value = entry()
    value["evidence_reference"] = " "
    with pytest.raises(ValueError, match="evidence_reference"):
        validate_pilot_entry(value)
