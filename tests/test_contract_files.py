# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

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
