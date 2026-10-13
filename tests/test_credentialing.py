"""Credentialing process-assurance tests use synthetic facts only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    merge_credentialing_projections,
    summarise_credentialing_projection,
    validate_credentialing_projection,
)

INFERRED_CONFIDENCE = 0.4
EXPECTED_EVENT_COUNT = 4
EXPECTED_UNIQUE_OBJECT_COUNT = 3
EXPECTED_OBSERVED_EVENT_COUNT = 3
EXPECTED_EXCEPTION_EVENT_COUNT = 2


def synthetic_payload() -> dict[str, Any]:
    """Return a small, valid and deliberately unordered synthetic projection."""
    return {
        "contract_version": "0.1.0",
        "ontology_version": "0.1.0",
        "source": "careops-approve",
        "watermark_utc": "2026-09-10T10:00:00+10:00",
        "facts": [
            {
                "event_id": "evt-002",
                "activity": "case_completed",
                "timestamp_utc": "2026-09-10T09:30:00+10:00",
                "source_system": "synthetic",
                "object_ids": ["case-001"],
                "observed_or_inferred": "observed",
                "confidence": 1.0,
                "qualifiers": {
                    "pathway_code": "routine-renewal",
                    "professional_stream": "medical-and-dental",
                    "duration_bucket": "1_to_3_days",
                    "feature_pack_version": "0.1.0",
                },
            },
            {
                "event_id": "evt-001",
                "activity": "request_received",
                "timestamp_utc": "2026-09-09T23:00:00Z",
                "source_system": "synthetic",
                "object_ids": ["case-001", "request-001"],
                "observed_or_inferred": "inferred",
                "confidence": 0.8,
                "qualifiers": {
                    "pathway_code": "routine-renewal",
                    "authority_mapping_version": "authority-v1",
                },
            },
        ],
    }


def test_valid_projection_is_normalised_and_sorted() -> None:
    """Validated facts and the watermark are normalised to UTC and sorted."""
    projection = validate_credentialing_projection(synthetic_payload())

    assert [fact.event_id for fact in projection.facts] == ["evt-001", "evt-002"]
    assert projection.watermark_utc == datetime(2026, 9, 10, tzinfo=UTC)
    assert projection.facts[1].timestamp_utc == datetime(
        2026,
        9,
        9,
        23,
        30,
        tzinfo=UTC,
    )


def test_parsed_projection_is_returned_without_reinterpretation() -> None:
    """An already validated projection remains the same object."""
    projection = CredentialingProjection.model_validate(synthetic_payload())
    assert validate_credentialing_projection(projection) is projection


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "name",
        "emailAddress",
        "registrationNumber",
        "qualification",
        "scopeText",
        "decisionReason",
        "patientData",
        "rawPayload",
    ],
)
def test_sensitive_fields_fail_closed_at_any_depth(forbidden_key: str) -> None:
    """Direct identity, source content and decision text never enter events."""
    payload = synthetic_payload()
    payload["facts"][0]["qualifiers"][forbidden_key] = "not permitted"

    with pytest.raises(CredentialingContractError, match="Prohibited"):
        validate_credentialing_projection(payload)


def test_sensitive_field_in_nested_list_fails_closed() -> None:
    """The raw boundary scan descends into lists before model parsing."""
    payload = synthetic_payload()
    payload["unexpected"] = [{"patient_data": "not permitted"}]

    with pytest.raises(CredentialingContractError, match="patient_data"):
        validate_credentialing_projection(payload)


def test_unrecognised_non_sensitive_field_is_rejected() -> None:
    """The versioned model does not silently accept contract drift."""
    payload = synthetic_payload()
    payload["unexpected"] = "contract drift"

    with pytest.raises(ValidationError, match="extra_forbidden"):
        validate_credentialing_projection(payload)


def test_observed_event_requires_confidence_one() -> None:
    """Observed facts cannot carry probabilistic provenance."""
    payload = synthetic_payload()
    payload["facts"][0]["confidence"] = 0.9

    with pytest.raises(ValidationError, match="must have confidence 1"):
        validate_credentialing_projection(payload)


def test_inferred_event_may_have_bounded_confidence() -> None:
    """Inferred facts retain an explicit bounded confidence value."""
    payload = synthetic_payload()
    payload["facts"][1]["confidence"] = INFERRED_CONFIDENCE

    projection = validate_credentialing_projection(payload)
    assert projection.facts[0].confidence == INFERRED_CONFIDENCE


def test_duplicate_event_identifiers_fail_closed() -> None:
    """Duplicate event identity cannot distort path or throughput measures."""
    payload = synthetic_payload()
    payload["facts"][1]["event_id"] = "evt-002"

    with pytest.raises(ValidationError, match="unique within a projection"):
        validate_credentialing_projection(payload)


def test_unsafe_and_duplicate_object_references_fail_closed() -> None:
    """Object references are bounded, safe and unique within each event."""
    payload = synthetic_payload()
    payload["facts"][0]["object_ids"] = ["unsafe object"]
    with pytest.raises(ValidationError, match="safe, non-sensitive"):
        validate_credentialing_projection(payload)

    payload = synthetic_payload()
    payload["facts"][0]["object_ids"] = ["case-001", "case-001"]
    with pytest.raises(ValidationError, match="unique within an event"):
        validate_credentialing_projection(payload)


def test_timestamps_require_explicit_timezones() -> None:
    """Naive event and watermark timestamps cannot enter the canonical log."""
    payload = synthetic_payload()
    payload["facts"][0]["timestamp_utc"] = "2026-09-10T09:30:00"
    with pytest.raises(ValidationError, match="explicit timezone"):
        validate_credentialing_projection(payload)

    payload = synthetic_payload()
    payload["watermark_utc"] = "2026-09-10T10:00:00"
    with pytest.raises(ValidationError, match="watermark_utc"):
        validate_credentialing_projection(payload)


def test_exact_replay_is_idempotent() -> None:
    """An exact replay does not create duplicate facts."""
    existing = validate_credentialing_projection(synthetic_payload())
    replay = validate_credentialing_projection(synthetic_payload())

    merged = merge_credentialing_projections(existing, replay)
    assert [fact.event_id for fact in merged.facts] == ["evt-001", "evt-002"]


def test_new_event_and_later_watermark_merge_deterministically() -> None:
    """A later batch adds new events and advances the source watermark."""
    existing = validate_credentialing_projection(synthetic_payload())
    incoming_payload = synthetic_payload()
    incoming_payload["watermark_utc"] = "2026-09-11T00:00:00Z"
    incoming_payload["facts"] = [
        {
            "event_id": "evt-003",
            "activity": "register_reconciliation_failed",
            "timestamp_utc": "2026-09-10T12:00:00Z",
            "source_system": "synthetic",
            "object_ids": ["case-001"],
            "observed_or_inferred": "observed",
            "confidence": 1.0,
            "qualifiers": {"exception_code": "synthetic-mismatch"},
        }
    ]
    incoming = validate_credentialing_projection(incoming_payload)

    merged = merge_credentialing_projections(existing, incoming)
    assert [fact.event_id for fact in merged.facts] == [
        "evt-001",
        "evt-002",
        "evt-003",
    ]
    assert merged.watermark_utc == datetime(2026, 9, 11, tzinfo=UTC)


def test_changed_replay_and_mismatched_source_fail_closed() -> None:
    """History cannot be rewritten and unlike source streams cannot be merged."""
    existing = validate_credentialing_projection(synthetic_payload())
    changed_payload = synthetic_payload()
    changed_payload["facts"][0]["activity"] = "case_withdrawn"
    changed = validate_credentialing_projection(changed_payload)
    with pytest.raises(CredentialingContractError, match="Conflicting replay"):
        merge_credentialing_projections(existing, changed)

    other_payload = synthetic_payload()
    other_payload["source"] = "careops-decisions"
    other = validate_credentialing_projection(other_payload)
    with pytest.raises(CredentialingContractError, match="source must match"):
        merge_credentialing_projections(existing, other)


def test_empty_watermarks_remain_empty_after_merge() -> None:
    """Two unwatermarked batches remain explicitly unwatermarked."""
    first_payload = synthetic_payload()
    second_payload = synthetic_payload()
    first_payload["watermark_utc"] = None
    second_payload["watermark_utc"] = None
    second_payload["facts"] = []

    merged = merge_credentialing_projections(
        validate_credentialing_projection(first_payload),
        validate_credentialing_projection(second_payload),
    )
    assert merged.watermark_utc is None


def test_metrics_are_aggregate_and_deterministic() -> None:
    """Minimum assurance measures contain counts rather than case content."""
    payload = synthetic_payload()
    payload["facts"].extend(
        [
            {
                "event_id": "evt-003",
                "activity": "committee_deferred",
                "timestamp_utc": "2026-09-10T12:00:00Z",
                "source_system": "synthetic",
                "object_ids": ["case-002"],
                "observed_or_inferred": "observed",
                "confidence": 1.0,
                "qualifiers": {"exception_code": "quorum"},
            },
            {
                "event_id": "evt-004",
                "activity": "register_reconciliation_failed",
                "timestamp_utc": "2026-09-10T13:00:00Z",
                "source_system": "synthetic",
                "object_ids": ["case-002"],
                "observed_or_inferred": "observed",
                "confidence": 1.0,
                "qualifiers": {"exception_code": "mismatch"},
            },
        ]
    )
    metrics = summarise_credentialing_projection(validate_credentialing_projection(payload))

    assert metrics.event_count == EXPECTED_EVENT_COUNT
    assert metrics.unique_object_count == EXPECTED_UNIQUE_OBJECT_COUNT
    assert metrics.observed_event_count == EXPECTED_OBSERVED_EVENT_COUNT
    assert metrics.inferred_event_count == 1
    assert metrics.completed_case_event_count == 1
    assert metrics.committee_deferral_count == 1
    assert metrics.register_reconciliation_failure_count == 1
    assert metrics.exception_event_count == EXPECTED_EXCEPTION_EVENT_COUNT
    assert metrics.rework_event_count == EXPECTED_EXCEPTION_EVENT_COUNT
    assert list(metrics.activity_counts) == sorted(metrics.activity_counts)


def test_timezone_normalisation_handles_non_whole_hour_offset() -> None:
    """UTC normalisation does not assume whole-hour local offsets."""
    payload = synthetic_payload()
    offset = timezone(timedelta(hours=5, minutes=30))
    payload["facts"][0]["timestamp_utc"] = datetime(
        2026,
        9,
        10,
        1,
        tzinfo=offset,
    )

    projection = validate_credentialing_projection(payload)
    assert projection.facts[1].timestamp_utc.tzinfo is UTC
