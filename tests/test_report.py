"""Closed-run report tests."""

from datetime import UTC, datetime
from typing import Any

from careops_process.report import build_closed_run_report

FACTS: list[dict[str, Any]] = [
    {
        "id": "fact-1",
        "activity": "request_received",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "source_system": "outlook",
        "object_ids": ["request-1"],
    }
]
EVIDENCE: dict[str, Any] = {
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


def test_closed_run_report_retains_lineage_and_safe_outputs() -> None:
    """A report contains the run lineage and no raw email fields."""
    report = build_closed_run_report(
        FACTS,
        EVIDENCE,
        pseudonym_secret="test-secret",  # noqa: S106
        generated_at_utc=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert report["run_id"] == "run-1"
    assert report["lineage"]
    assert report["evidence"]["reconciled"] is True
    assert "subject" not in str(report).lower()
