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
    """The retained Dataverse map is historical and contains no source payloads."""
    mapping = json.loads(
        Path("contracts/dataverse-checkpoint.mapping.json").read_text(encoding="utf-8")
    )
    assert all("body" not in column.lower() for column in mapping["columns"])
    assert mapping["privacy"]["raw_message_content"] == "prohibited"


def test_sharepoint_ingestion_binding_is_standard_and_minimized() -> None:
    """The selected route uses standard Lists and keeps native bindings unverified."""
    contract = json.loads(
        Path("contracts/sharepoint-m365-ingestion.json").read_text(encoding="utf-8")
    )
    assert contract["status"] == "source-design-only-native-binding-unverified"
    assert all(item["tier"] == "standard" for item in contract["connectors"].values())
    assert contract["flow_safety"]["max_concurrent_runs"] == 1
    assert "Get items" in contract["connectors"]["sharepoint"]["operations"]
    assert "Get item" not in contract["connectors"]["sharepoint"]["operations"]
    assert "Top Count 2" in contract["lists"][0]["lookup"]
    assert "body" in contract["flow_safety"]["prohibited_persistent_fields"]
    selected_connectors = {item["name"] for item in contract["connectors"].values()}
    assert "Microsoft Dataverse" not in selected_connectors
    assert "HTTP with Microsoft Entra ID" not in selected_connectors
