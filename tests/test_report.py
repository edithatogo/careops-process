"""Closed-run report tests."""

from datetime import UTC, datetime
from typing import Any

from careops_process.report import build_authorised_closed_run_report, build_closed_run_report
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
PILOT_ENTRY: dict[str, Any] = {
    "source_owner_approved": True,
    "ig_approved": True,
    "configuration_frozen": True,
    "rollback_retention_approved": True,
    "authorised_source_partitions": ["outlook-authorised-mailbox"],
    "evidence_reference": "approved-ref",
}
PILOT_ENTRY["configuration_hash"] = EVIDENCE["configuration_hash"]


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


def test_authorised_report_requires_pilot_entry() -> None:
    """The report path enforces pilot approvals."""
    report = build_authorised_closed_run_report(
        FACTS,
        EVIDENCE,
        PILOT_ENTRY,
        pseudonym_secret="test-secret",  # noqa: S106
    )
    assert report["run_id"] == "run-1"


def test_report_preserves_measured_partition_manifest() -> None:
    """Executive lineage retains the validated source population and frozen controls."""
    evidence = sealed_evidence(FACTS)
    report = build_closed_run_report(FACTS, evidence, pseudonym_secret="test-secret")  # noqa: S106
    assert report["evidence"]["content_hash"] == evidence["content_hash"]
    assert report["evidence"]["partitions"] == evidence["partitions"]
    assert report["evidence"]["configuration_hash"] == evidence["configuration_hash"]
    assert report["evidence"]["configuration"] == evidence["configuration"]
    assert report["report_version"] == "2.0.0"


def test_report_coverage_and_quality_share_the_closed_run() -> None:
    """Population, quality and discovery summaries use one manifest and preserve uncertainty."""
    evidence = sealed_evidence(FACTS)
    report = build_closed_run_report(FACTS, evidence, pseudonym_secret="test-secret")  # noqa: S106
    assert report["coverage_ledger"]["run_id"] == report["run_id"]
    assert report["coverage_ledger"]["source_candidate_count"] == evidence["candidate_count"]
    assert report["coverage_ledger"]["included_event_count"] == len(FACTS)
    assert report["coverage_ledger"]["tenant_wide_coverage"] is None
    assert report["coverage_ledger"]["owner_validation_status"] == "pending"
    assert report["corpus_quality"]["event_count"] == len(report["ocel"]["events"])
    assert report["coverage_ledger"]["evidence_class"] == "synthetic"
    assert report["operational_patterns"]


def test_same_closed_run_and_generation_time_produce_identical_report() -> None:
    """All artifacts and lineage rebuild deterministically from the frozen run."""
    evidence = sealed_evidence(FACTS)
    generated = datetime(2026, 1, 2, tzinfo=UTC)
    first = build_closed_run_report(
        FACTS,
        evidence,
        pseudonym_secret="test-secret",  # noqa: S106
        generated_at_utc=generated,
    )
    second = build_closed_run_report(
        FACTS,
        evidence,
        pseudonym_secret="test-secret",  # noqa: S106
        generated_at_utc=generated,
    )
    assert first == second


def test_report_and_projection_share_one_freshness_timestamp() -> None:
    """A single generated instant describes every artifact in this report."""
    report = build_closed_run_report(FACTS, sealed_evidence(FACTS), pseudonym_secret="test-secret")  # noqa: S106
    assert report["generated_at_utc"] == report["semantic_projection"]["generated_at_utc"]
