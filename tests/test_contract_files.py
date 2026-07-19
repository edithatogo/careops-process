"""Contract artifact integrity tests."""

import json
from pathlib import Path


def test_connector_contract_is_strict_and_minimized() -> None:
    """The connector contract forbids arbitrary and raw-content fields."""
    contract = json.loads(Path("contracts/m365-fact-projection.json").read_text(encoding="utf-8"))
    fact = contract["properties"]["facts"]["items"]
    assert fact["additionalProperties"] is False
    assert "body" not in fact["properties"]
    assert "subject" not in fact["properties"]
    assert contract["properties"]["contract_version"]["const"] == "1.0.0"


def test_checkpoint_mapping_has_no_payload_columns() -> None:
    """The Dataverse mapping contains state, not source message payloads."""
    mapping = json.loads(
        Path("contracts/dataverse-checkpoint.mapping.json").read_text(encoding="utf-8")
    )
    assert all("body" not in column.lower() for column in mapping["columns"])
    assert mapping["privacy"]["raw_message_content"] == "prohibited"


def test_corpus_coverage_contract_preserves_unknown_tenant_denominator() -> None:
    """Coverage artifacts cannot claim a tenant-wide percentage."""
    contract = json.loads(
        Path("contracts/m365-corpus-coverage.schema.json").read_text(encoding="utf-8")
    )
    assert contract["additionalProperties"] is False
    assert contract["properties"]["tenant_wide_coverage"]["type"] == "null"
    partition = contract["properties"]["partitions"]["items"]
    assert partition["additionalProperties"] is False
    assert set(partition["required"]) >= {
        "candidate_count",
        "acquired_count",
        "permission_state",
        "provenance",
        "limitation",
    }


def test_corpus_coverage_contract_separates_evidence_classes() -> None:
    """Synthetic, smoke-test, and live-corpus outputs stay distinguishable."""
    contract = json.loads(
        Path("contracts/m365-corpus-coverage.schema.json").read_text(encoding="utf-8")
    )
    classes = contract["properties"]["evidence_class"]["enum"]
    assert classes == ["synthetic", "smoke_test", "live_corpus"]
