"""Closed backfill execution boundary tests."""

from datetime import UTC, datetime

import pytest

from careops_process.backfill_run import run_closed_backfill

FACTS = [
    {
        "id": "fact-1",
        "activity": "request_received",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "source_system": "outlook",
        "object_ids": ["request-1"],
    }
]
EVIDENCE = {
    "run_id": "run-1",
    "status": "closed",
    "folder_count": 1,
    "page_count": 1,
    "candidate_count": 1,
    "pagination_exhausted": True,
    "reconciled": True,
    "idempotency_replay_verified": True,
    "no_raw_content_stored": True,
}


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
