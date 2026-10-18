# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic ingestion boundary tests."""

from datetime import UTC, datetime

import pytest

from careops_process.ingest import IngestionError, facts_to_ocel


def source_facts() -> list[dict[str, object]]:
    """Return minimized synthetic facts resembling a connector projection."""
    return [
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


def test_incremental_projection_applies_watermark() -> None:
    """Only facts after the exclusive watermark are emitted."""
    test_secret = "contract-test-key"  # noqa: S105
    log = facts_to_ocel(
        source_facts(),
        log_id="log-1",
        schema_version="1.0.0",
        pseudonym_secret=test_secret,
        after=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert len(log.events) == 1
    assert log.events[0].event_type == "approval_decided"


def test_raw_content_is_rejected() -> None:
    """The connector boundary rejects raw mailbox content."""
    test_secret = "contract-test-key"  # noqa: S105
    with pytest.raises(IngestionError, match="Raw content"):
        facts_to_ocel(
            [{**source_facts()[0], "body_preview": "redacted"}],
            log_id="log-1",
            schema_version="1.0.0",
            pseudonym_secret=test_secret,
        )


def test_empty_increment_is_rejected() -> None:
    """A poll with no new facts cannot create a misleading empty log."""
    test_secret = "contract-test-key"  # noqa: S105
    with pytest.raises(IngestionError, match="No facts"):
        facts_to_ocel(
            source_facts(),
            log_id="log-1",
            schema_version="1.0.0",
            pseudonym_secret=test_secret,
            after=datetime(2026, 2, 1, tzinfo=UTC),
        )


def test_invalid_timestamp_and_missing_fields_fail_closed() -> None:
    """Malformed connector facts are rejected before pseudonymization."""
    test_secret = "contract-test-key"  # noqa: S105
    with pytest.raises(IngestionError, match="ISO-8601"):
        facts_to_ocel(
            [{**source_facts()[0], "timestamp_utc": "not-a-date"}],
            log_id="log-1",
            schema_version="1.0.0",
            pseudonym_secret=test_secret,
        )
    with pytest.raises(IngestionError, match="Missing"):
        facts_to_ocel(
            [{key: value for key, value in source_facts()[0].items() if key != "activity"}],
            log_id="log-1",
            schema_version="1.0.0",
            pseudonym_secret=test_secret,
        )


def test_invalid_types_fail_closed() -> None:
    """Connector type drift is rejected rather than coerced silently."""
    test_secret = "contract-test-key"  # noqa: S105
    with pytest.raises(IngestionError, match="must be strings"):
        facts_to_ocel(
            [{**source_facts()[0], "id": 7}],
            log_id="log-1",
            schema_version="1.0.0",
            pseudonym_secret=test_secret,
        )
    with pytest.raises(IngestionError, match="list of strings"):
        facts_to_ocel(
            [{**source_facts()[0], "object_ids": "request-1"}],
            log_id="log-1",
            schema_version="1.0.0",
            pseudonym_secret=test_secret,
        )
