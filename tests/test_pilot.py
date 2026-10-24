# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Sanitized Dataverse pilot adapter tests."""

import pytest

from careops_process.pilot import approval_metadata_to_facts


def test_approval_metadata_adapter_emits_minimized_lifecycle() -> None:
    """Only opaque IDs and lifecycle timestamps enter the fact boundary."""
    facts = approval_metadata_to_facts(
        [
            {
                "id": "approval-1",
                "createdon": "2026-01-01T00:00:00Z",
                "completedon": "2026-01-01T00:01:00Z",
                "source": "dataverse_approvals",
            }
        ]
    )
    assert [fact["activity"] for fact in facts] == ["approval_created", "approval_decided"]
    assert all(
        set(fact) == {"id", "activity", "timestamp_utc", "source_system", "object_ids"}
        for fact in facts
    )


def test_approval_metadata_adapter_rejects_content_and_identity() -> None:
    """The adapter fails closed when raw content or identities appear."""
    with pytest.raises(ValueError, match="prohibited"):
        approval_metadata_to_facts(
            [
                {
                    "id": "approval-1",
                    "createdon": "2026-01-01T00:00:00Z",
                    "source": "dataverse_approvals",
                    "details": "do not ingest",
                }
            ]
        )


@pytest.mark.parametrize(
    "record",
    [
        {"createdon": "2026-01-01T00:00:00Z", "source": "dataverse_approvals"},
        {"id": "approval-1", "source": "dataverse_approvals"},
        {"id": "approval-1", "createdon": "2026-01-01T00:00:00Z"},
    ],
)
def test_approval_metadata_adapter_rejects_missing_fields(record: dict[str, object]) -> None:
    """Incomplete metadata cannot create an event log."""
    with pytest.raises(ValueError, match="missing"):
        approval_metadata_to_facts([record])


def test_approval_metadata_adapter_rejects_invalid_types() -> None:
    """Metadata types are not coerced silently."""
    with pytest.raises(TypeError, match="must be strings"):
        approval_metadata_to_facts(
            [{"id": 1, "createdon": "2026-01-01T00:00:00Z", "source": "dataverse_approvals"}]
        )
    with pytest.raises(TypeError, match="completedon"):
        approval_metadata_to_facts(
            [
                {
                    "id": "approval-1",
                    "createdon": "2026-01-01T00:00:00Z",
                    "completedon": 1,
                    "source": "dataverse_approvals",
                }
            ]
        )


def test_approval_metadata_adapter_requires_records() -> None:
    """An empty pilot cannot masquerade as a successful event log."""
    with pytest.raises(ValueError, match="at least one"):
        approval_metadata_to_facts([])
