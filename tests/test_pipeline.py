"""End-to-end synthetic pipeline tests."""

from datetime import UTC, datetime

from careops_process.pipeline import run_pipeline

EVENT_COUNT = 2


def test_pipeline_connects_ingestion_discovery_conformance_and_projection() -> None:
    """The bounded pipeline returns each governed output without raw content."""
    facts: list[dict[str, object]] = [
        {
            "id": "source-1",
            "activity": "request_received",
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "source_system": "dataverse",
            "object_ids": ["request-1"],
        },
        {
            "id": "source-2",
            "activity": "approval_decided",
            "timestamp_utc": "2026-01-02T00:00:00Z",
            "source_system": "teams",
            "object_ids": ["request-1"],
        },
    ]
    test_secret = "pipeline-test-key"  # noqa: S105
    result = run_pipeline(
        facts,
        log_id="pipeline-test",
        schema_version="1.0.0",
        pseudonym_secret=test_secret,
        generated_at_utc=datetime(2026, 1, 3, tzinfo=UTC),
        reference=["request_received", "approval_decided"],
        minimum_cohort_size=1,
    )
    assert len(result.log.events) == EVENT_COUNT
    assert result.families
    assert result.conformance is not None
    assert result.conformance.fitness == 1.0
    assert result.projection["quality"]["event_count"] == EVENT_COUNT  # type: ignore[index]
