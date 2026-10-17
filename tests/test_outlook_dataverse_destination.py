"""Synthetic destination identity and serialization contract checks."""

from uuid import UUID, uuid5

import pytest

from careops_process import outlook_dataverse_destination as d
from careops_process.outlook_reconciliation import CanonicalMailFact

ORG = "00000000-0000-0000-0000-000000000001"
RUN = "00000000-0000-0000-0000-000000000002"
FACT_ID = "mail_" + "a" * 64


def test_row_identity_pins_version_organization_run_and_fact() -> None:
    """The run-scoped primary key follows an independently specified formula."""
    name = '["careops-outlook-destination-v1","' + ORG + '","' + FACT_ID + '"]'
    expected = str(uuid5(UUID(RUN), name))
    assert d.row_id(ORG, RUN, FACT_ID) == expected
    assert d.row_id(RUN, RUN, FACT_ID) != expected
    assert d.row_id(ORG, ORG, FACT_ID) != expected
    assert d.row_id(ORG, RUN, "mail_" + "b" * 64) != expected


@pytest.mark.parametrize("value", ["bad", "00000000-0000-0000-0000-000000000000", RUN + "\n"])
def test_bad_run_ids_fail_without_input_echo(value: str) -> None:
    """Invalid run IDs cannot become a fresh implicit scope."""
    with pytest.raises(ValueError, match="invalid_destination_identity"):
        d.row_id(ORG, value, FACT_ID)


def test_fact_id_requires_full_match() -> None:
    """A trailing newline cannot select an alternate row."""
    with pytest.raises(ValueError, match="invalid_destination_identity"):
        d.row_id(ORG, RUN, FACT_ID + "\n")


def fact() -> CanonicalMailFact:
    """Return an explicitly synthetic minimized fact."""
    return CanonicalMailFact(
        id=FACT_ID,
        activity="email_received",
        timestamp_utc="2026-01-01T10:00:00+10:00",
        source_system="outlook",
        object_ids=["conversation_" + "b" * 64],
    )


def test_serialization_uses_exact_five_fields_and_utc() -> None:
    """A TimeZoneIndependent value is explicitly written as UTC."""
    result = d.serialize_fact(fact())
    assert result == {
        "cop_eventkey": FACT_ID,
        "cop_activity": "email_received",
        "cop_timestamputc": "2026-01-01T00:00:00Z",
        "cop_sourcesystem": "outlook",
        "cop_objectids": '["conversation_' + "b" * 64 + '"]',
    }
    restored = d.parse_readback(result)
    assert restored.timestamp_utc == "2026-01-01T00:00:00Z"
    assert restored.id == FACT_ID


@pytest.mark.parametrize("timestamp", ["2026-01-01T00:00:00", "2026-01-01T00:00:00.123Z"])
def test_timestamp_loss_or_ambiguity_rejected(timestamp: str) -> None:
    """No precision truncation or implicit timezone is permitted."""
    with pytest.raises(ValueError, match="invalid_destination_fact"):
        d.serialize_fact(fact().model_copy(update={"timestamp_utc": timestamp}))


def test_mutated_object_list_is_revalidated() -> None:
    """Frozen models still contain mutable collections."""
    value = fact()
    value.object_ids.append(value.object_ids[0])
    with pytest.raises(ValueError, match="invalid_destination_fact"):
        d.serialize_fact(value)


def test_readback_unexpected_fields_are_rejected() -> None:
    """Readback selects must not silently accept extra content."""
    value = d.serialize_fact(fact())
    value["subject"] = "synthetic unexpected content"
    with pytest.raises(ValueError, match="invalid_destination_fact"):
        d.parse_readback(value)
