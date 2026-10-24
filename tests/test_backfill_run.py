# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Closed backfill execution boundary tests."""

from datetime import UTC, datetime
from typing import Any

import pytest

from careops_process.backfill_run import run_authorised_closed_backfill, run_closed_backfill
from tests.backfill_fixture import sealed_evidence

FACTS: list[dict[str, Any]] = [
    {
        "id": "fact-1",
        "activity": "request_received",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "source_system": "outlook",
        "object_ids": ["request-1"],
    }
]
EVIDENCE = sealed_evidence(FACTS)
PILOT_ENTRY = {
    "source_owner_approved": True,
    "ig_approved": True,
    "configuration_frozen": True,
    "rollback_retention_approved": True,
    "authorised_source_partitions": ["outlook-authorised-mailbox"],
    "evidence_reference": "approved-ref",
}
PILOT_ENTRY["configuration_hash"] = EVIDENCE["configuration_hash"]


def test_closed_backfill_runs_pipeline() -> None:
    """A closed, reconciled run produces a pipeline result."""
    result = run_closed_backfill(
        FACTS,
        EVIDENCE,
        pseudonym_secret="test-secret",  # noqa: S106
        generated_at_utc=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert result.log.log_id == "run-1"


def test_open_backfill_cannot_reach_discovery() -> None:
    """Open or incomplete runs are fail-closed."""
    evidence = {**EVIDENCE, "status": "running"}
    with pytest.raises(ValueError, match="closed backfill"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="test-secret")  # noqa: S106


def test_authorised_closed_backfill_requires_pilot_entry() -> None:
    """The authorised wrapper enforces the pilot gate before discovery."""
    result = run_authorised_closed_backfill(
        FACTS,
        EVIDENCE,
        PILOT_ENTRY,
        pseudonym_secret="test-secret",  # noqa: S106
    )
    assert result.log.log_id == "run-1"
    with pytest.raises(ValueError, match="approval"):
        run_authorised_closed_backfill(
            FACTS,
            EVIDENCE,
            {**PILOT_ENTRY, "ig_approved": False},
            pseudonym_secret="test-secret",  # noqa: S106
        )


@pytest.mark.parametrize("field", ["folder_count", "page_count", "candidate_count"])
@pytest.mark.parametrize("value", [-1, True, "1"])
def test_closed_backfill_rejects_invalid_counts(field: str, value: object) -> None:
    """Declared closure cannot admit negative, boolean or textual population counts."""
    evidence = {**EVIDENCE, field: value}
    with pytest.raises(ValueError, match="non-negative integer"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="test-secret")  # noqa: S106
