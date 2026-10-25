# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Power Automate flow contract tests."""

import json
from pathlib import Path
from typing import cast

import pytest

from careops_process.flow_contract import validate_flow_contract


def load_contract() -> dict[str, object]:
    """Load the repository-owned flow contract."""
    return json.loads(Path("contracts/power-automate-tesl-flow.json").read_text(encoding="utf-8"))


def test_flow_contract_is_privacy_safe_and_ordered() -> None:
    """The shipped TESL flow contract passes all safety invariants."""
    validate_flow_contract(load_contract())


def test_flow_contract_rejects_dataverse_and_premium_http() -> None:
    """The selected ingestion contract cannot regress to premium destinations."""
    for connector in ("Microsoft Dataverse", "HTTP with Microsoft Entra ID"):
        contract = load_contract()
        actions = cast("list[dict[str, object]]", contract["actions"])
        actions[0]["connector"] = connector
        with pytest.raises(ValueError, match="premium connector"):
            validate_flow_contract(contract)


def test_flow_contract_requires_keyed_sharepoint_checkpoint_lookup() -> None:
    """Checkpoint lookup uses the documented filter action and detects duplicates."""
    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    checkpoint = next(action for action in actions if action["id"] == "read_checkpoint")
    checkpoint["operation"] = "Get item"
    with pytest.raises(ValueError, match="Get items and fail closed"):
        validate_flow_contract(contract)

    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    checkpoint = next(action for action in actions if action["id"] == "read_checkpoint")
    checkpoint["on_multiple"] = "select_first"
    with pytest.raises(ValueError, match="Get items and fail closed"):
        validate_flow_contract(contract)


def test_flow_contract_requires_keyed_identity_and_transient_raw_ids() -> None:
    """Plain hashes or persisted source identifiers cannot replace keyed pseudonyms."""
    contract = load_contract()
    identity = cast("dict[str, object]", contract["identity_projection"])
    identity["algorithm"] = "sha256 without key"
    with pytest.raises(ValueError, match="keyed pseudonyms"):
        validate_flow_contract(contract)


def test_flow_contract_rejects_raw_source_ids_in_persistent_stores() -> None:
    """Raw identifiers may never leak into Lists, event files or dead letters."""
    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    projection = next(action for action in actions if action["id"] == "write_projection")
    cast("list[str]", projection["stores"]).append("internetMessageId")
    with pytest.raises(ValueError, match="raw fields cannot be persisted"):
        validate_flow_contract(contract)


def test_flow_contract_rejects_non_string_persistent_fields() -> None:
    """Persistence field names must be strings before applying privacy rules."""
    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    projection = next(action for action in actions if action["id"] == "write_projection")
    cast("list[object]", projection["stores"]).append({"field": "fact_id"})
    with pytest.raises(TypeError, match="stores must be a list"):
        validate_flow_contract(contract)


def test_flow_contract_rejects_checkpoint_before_write() -> None:
    """Checkpoint advancement cannot precede projection persistence."""
    contract = load_contract()
    actions = contract["actions"]
    assert isinstance(actions, list)
    actions[3], actions[5] = actions[5], actions[3]
    with pytest.raises(ValueError, match="after projection"):
        validate_flow_contract(contract)


def test_flow_contract_rejects_raw_content_and_unsafe_failure_policy() -> None:
    """Raw fields and unsafe failure behavior are fail-closed."""
    contract = load_contract()
    actions = contract["actions"]
    assert isinstance(actions, list)
    action = cast("dict[str, object]", actions[1])
    forbidden_inputs = cast("list[str]", action["forbidden_inputs"])
    forbidden_inputs.append("displayName")
    with pytest.raises(ValueError, match="unrecognized raw"):
        validate_flow_contract(contract)
    contract = load_contract()
    policy = cast("dict[str, object]", contract["failure_policy"])
    policy["never_store_raw_payload"] = False
    with pytest.raises(ValueError, match="raw payload"):
        validate_flow_contract(contract)


@pytest.mark.parametrize(("first", "second"), [(0, 1), (1, 2), (2, 3)])
def test_flow_contract_rejects_required_action_reordering(first: int, second: int) -> None:
    """Checkpoint reads, projection and watermark validation precede persistence."""
    contract = load_contract()
    actions = contract["actions"]
    assert isinstance(actions, list)
    actions[first], actions[second] = actions[second], actions[first]
    with pytest.raises(ValueError, match="order"):
        validate_flow_contract(contract)


def test_flow_contract_rejects_duplicate_action_identifiers() -> None:
    """An ambiguous repeated action cannot establish safe checkpoint ordering."""
    contract = load_contract()
    actions = cast("list[object]", contract["actions"])
    actions.append(actions[0])
    with pytest.raises(ValueError, match="unique"):
        validate_flow_contract(contract)


def test_flow_contract_requires_verified_publication_and_closed_dead_letter_branch() -> None:
    """A failed publication cannot be hidden by advancing the source checkpoint."""
    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    actions[4], actions[5] = actions[5], actions[4]
    with pytest.raises(ValueError, match="checkpoint-safe order"):
        validate_flow_contract(contract)

    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    dead_letter = next(action for action in actions if action["id"] == "dead_letter")
    dead_letter["never_advance_checkpoint"] = False
    with pytest.raises(ValueError, match="dead-letter branch"):
        validate_flow_contract(contract)


@pytest.mark.parametrize(
    ("actions", "error", "exception"),
    [
        (None, "actions must be a list", TypeError),
        ([None], "each action must be an object", TypeError),
        ([{"id": 1}], "string id", TypeError),
        ([], "required flow actions", ValueError),
    ],
)
def test_flow_contract_rejects_invalid_action_structure(
    actions: object, error: str, exception: type[Exception]
) -> None:
    """Malformed flow definitions cannot establish a safe execution sequence."""
    contract = load_contract()
    contract["actions"] = actions
    with pytest.raises(exception, match=error):
        validate_flow_contract(contract)


def test_flow_contract_rejects_non_list_privacy_fields() -> None:
    """Privacy exclusions must have the declared collection shape."""
    contract = load_contract()
    actions = cast("list[dict[str, object]]", contract["actions"])
    actions[0]["forbidden_inputs"] = "body"
    with pytest.raises(TypeError, match="forbidden_inputs must be a list"):
        validate_flow_contract(contract)


@pytest.mark.parametrize("policy", [None, {}, {"never_advance_checkpoint_on_failure": False}])
def test_flow_contract_requires_checkpoint_failure_protection(policy: object) -> None:
    """Missing or disabled recovery protection is rejected before execution."""
    contract = load_contract()
    contract["failure_policy"] = policy
    with pytest.raises((TypeError, ValueError), match=r"failure_policy|checkpoint advancement"):
        validate_flow_contract(contract)
