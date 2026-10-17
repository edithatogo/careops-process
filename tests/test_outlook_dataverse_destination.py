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


class MemoryRecords:
    """Model independently committed rows and a lost acknowledgement."""

    def __init__(self, *, lose_ack: bool = False) -> None:
        """Initialize isolated synthetic storage."""
        self.rows: dict[str, dict[str, str]] = {}
        self.creates = 0
        self.lose_ack = lose_ack

    def retrieve(self, table: str, record_id: str, *, select: list[str]) -> dict[str, str] | None:
        """Return an SDK-shaped selected record."""
        assert table == "cop_processevent"
        assert d.PRIMARY_KEY in select
        return self.rows.get(record_id)

    def create(self, table: str, data: dict[str, str]) -> object:
        """Commit before optionally losing the response."""
        assert table == "cop_processevent"
        self.creates += 1
        self.rows[data[d.PRIMARY_KEY]] = {**data, "_organizationid_value": ORG}
        if self.lose_ack:
            message = "synthetic private provider response"
            raise TimeoutError(message)
        return data[d.PRIMARY_KEY]


def test_create_and_replay_never_create_twice() -> None:
    """A repeated run uses the same primary key."""
    records = MemoryRecords()
    assert d.ensure_synthetic_fact(records, ORG, RUN, fact()) == "created"
    assert d.ensure_synthetic_fact(records, ORG, RUN, fact()) == "existing"
    assert records.creates == 1


def test_ambiguous_create_reconciles_without_resend() -> None:
    """A lost acknowledgement is resolved by actual same-key readback."""
    records = MemoryRecords(lose_ack=True)
    assert d.ensure_synthetic_fact(records, ORG, RUN, fact()) == "reconciled"
    assert records.creates == 1


def test_changed_existing_content_never_overwrites() -> None:
    """Conflicting content fails with a fixed diagnostic."""
    records = MemoryRecords()
    d.ensure_synthetic_fact(records, ORG, RUN, fact())
    records.rows[d.row_id(ORG, RUN, FACT_ID)]["cop_timestamputc"] = "2025-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="destination_write_unconfirmed"):
        d.ensure_synthetic_fact(records, ORG, RUN, fact())
    assert records.creates == 1


def test_partial_readback_cannot_confirm_write() -> None:
    """An existing incomplete row is neither absent nor confirmed."""
    records = MemoryRecords()
    d.ensure_synthetic_fact(records, ORG, RUN, fact())
    del records.rows[d.row_id(ORG, RUN, FACT_ID)]["cop_objectids"]
    with pytest.raises(ValueError, match="destination_write_unconfirmed"):
        d.ensure_synthetic_fact(records, ORG, RUN, fact())
    assert records.creates == 1


def test_failed_create_without_row_is_not_retried() -> None:
    """Absence after a timeout cannot become an automatic resend."""

    class FailedCreate(MemoryRecords):
        def create(self, table: str, data: dict[str, str]) -> object:
            del table, data
            self.creates += 1
            message = "synthetic private provider response"
            raise TimeoutError(message)

    records = FailedCreate()
    with pytest.raises(ValueError, match=r"^destination_write_unconfirmed$"):
        d.ensure_synthetic_fact(records, ORG, RUN, fact())
    assert records.creates == 1
    assert not records.rows


def test_read_failure_cannot_be_interpreted_as_absence() -> None:
    """A forbidden or unavailable read cannot authorize a create."""

    class FailedRead(MemoryRecords):
        def retrieve(
            self, table: str, record_id: str, *, select: list[str]
        ) -> dict[str, str] | None:
            del table, record_id, select
            message = "synthetic forbidden private response"
            raise PermissionError(message)

    records = FailedRead()
    with pytest.raises(ValueError, match=r"^destination_write_unconfirmed$"):
        d.ensure_synthetic_fact(records, ORG, RUN, fact())
    assert records.creates == 0


@pytest.mark.parametrize(
    "timestamp",
    ["2026-01-01T00:00:00.0000001Z", "2026-01-01T00:00:00+00:00:00.5"],
)
@pytest.mark.parametrize("boundary", ["serialize", "readback"])
def test_unsupported_timestamp_precision_is_not_silently_lost(
    timestamp: str, boundary: str
) -> None:
    """Python datetime parsing must not truncate an unsupported source instant."""
    mutated = fact().model_copy(update={"timestamp_utc": timestamp})
    row = d.serialize_fact(fact())
    row["cop_timestamputc"] = timestamp
    if boundary == "serialize":
        with pytest.raises(ValueError, match="invalid_destination_fact"):
            d.serialize_fact(mutated)
    else:
        with pytest.raises(ValueError, match="invalid_destination_fact"):
            d.parse_readback(row)


def test_zero_fraction_and_minute_offset_preserve_exact_instant() -> None:
    """Explicit zero fractions are whole seconds; minute offsets normalize exactly."""
    value = fact().model_copy(update={"timestamp_utc": "2026-01-01T10:30:00.0000000+10:30"})
    assert d.serialize_fact(value)["cop_timestamputc"] == "2026-01-01T00:00:00Z"


@pytest.mark.parametrize(
    "timestamp",
    ["2026-01-01T00:00:00.0000001Z", "2026-01-01T00:00:00+00:00:00.5"],
)
def test_replay_rejects_lossy_timestamp_readback(timestamp: str) -> None:
    """Changed stored instants cannot be normalized into an unchanged replay."""
    records = MemoryRecords()
    expected = fact()
    if "+00:00:00.5" in timestamp:
        expected = fact().model_copy(update={"timestamp_utc": "2025-12-31T23:59:59Z"})
    d.ensure_synthetic_fact(records, ORG, RUN, expected)
    records.rows[d.row_id(ORG, RUN, FACT_ID)]["cop_timestamputc"] = timestamp
    with pytest.raises(ValueError, match="destination_write_unconfirmed"):
        d.ensure_synthetic_fact(records, ORG, RUN, expected)
    assert records.creates == 1
