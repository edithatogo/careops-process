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


def test_flow_contract_rejects_checkpoint_before_write() -> None:
    """Checkpoint advancement cannot precede projection persistence."""
    contract = load_contract()
    actions = contract["actions"]
    assert isinstance(actions, list)
    actions[3], actions[4] = actions[4], actions[3]
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
