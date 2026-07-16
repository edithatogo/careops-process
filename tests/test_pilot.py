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
