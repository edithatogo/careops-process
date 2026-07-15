"""Synthetic multi-object OCEL contract tests."""

from datetime import UTC, datetime

import pytest

from careops_process.ocel import (
    ContractError,
    OcelEvent,
    OcelLog,
    OcelObject,
    pseudonymize,
    validate_ocel,
)


def sample_log() -> OcelLog:
    """Return a valid synthetic approval request with two object types."""
    objects = [
        OcelObject(
            object_id="req-1",
            object_type="approval_request",
            attributes={"priority": "normal"},
        ),
        OcelObject(object_id="person-1", object_type="decision_subject"),
    ]
    events = [
        OcelEvent(
            event_id="evt-1",
            event_type="request_received",
            timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
            source_system="synthetic",
            observed_or_inferred="observed",
            confidence=1.0,
            object_ids=["req-1", "person-1"],
        )
    ]
    return validate_ocel(
        OcelLog(
            log_id="log-demo",
            schema_version="1.0.0",
            lineage="synthetic fixture",
            objects=objects,
            events=events,
        )
    )


def test_multi_object_log_is_valid() -> None:
    """A valid envelope declares the OCEL version."""
    assert sample_log().ocel_version == "2.0"


def test_unknown_reference_fails_closed() -> None:
    """Events cannot reference objects outside the envelope."""
    event = sample_log().events[0].model_copy(update={"object_ids": ["missing"]})
    log = sample_log().model_copy(update={"events": [event]})
    with pytest.raises(ContractError, match="Unknown object"):
        validate_ocel(log)


def test_direct_identity_attribute_fails_closed() -> None:
    """Direct identity fields are excluded from object attributes."""
    object_ = OcelObject(
        object_id="req-1",
        object_type="approval_request",
        attributes={"email": "redacted"},
    )
    log = sample_log().model_copy(update={"objects": [object_]})
    with pytest.raises(ContractError, match="Direct identity"):
        validate_ocel(log)


def test_direct_identity_qualifier_fails_closed() -> None:
    """Event qualifiers cannot reintroduce direct identity fields."""
    event = sample_log().events[0].model_copy(update={"qualifiers": {"email": "redacted"}})
    log = sample_log().model_copy(update={"events": [event]})
    with pytest.raises(ContractError, match="qualifiers"):
        validate_ocel(log)


def test_event_and_object_ids_are_safe() -> None:
    """Event and referenced object IDs share the safe-ID contract."""
    with pytest.raises(ValueError, match="event_id"):
        OcelEvent(
            event_id="unsafe id",
            event_type="received",
            timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
            source_system="synthetic",
            observed_or_inferred="observed",
            confidence=1.0,
            object_ids=["req-1"],
        )
    with pytest.raises(ValueError, match="object_id"):
        OcelEvent(
            event_id="evt-1",
            event_type="received",
            timestamp_utc=datetime(2026, 1, 1, tzinfo=UTC),
            source_system="synthetic",
            observed_or_inferred="observed",
            confidence=1.0,
            object_ids=["unsafe id"],
        )


def test_pseudonymization_is_deterministic_and_secret_required() -> None:
    """Pseudonyms are stable with a secret and reject empty secrets."""
    secret_key = "contract-test-key"  # noqa: S105
    first = pseudonymize("person@example.invalid", secret=secret_key)
    second = pseudonymize("person@example.invalid", secret=secret_key)
    assert first == second
    with pytest.raises(ContractError, match="secret"):
        pseudonymize("person", secret="")
