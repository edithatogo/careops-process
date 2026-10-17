"""Fail-closed validation for the Power Automate flow contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

FORBIDDEN_FIELDS = frozenset({"body", "bodyPreview", "subject", "from", "to", "cc", "bcc"})
REQUIRED_ACTIONS = (
    "read_checkpoint",
    "project_fact",
    "validate_watermark",
    "write_projection",
    "advance_checkpoint",
)


def validate_flow_contract(contract: Mapping[str, object]) -> None:  # noqa: C901, PLR0912
    """Validate ordering, privacy, and checkpoint safety invariants."""
    actions = contract.get("actions")
    if not isinstance(actions, list):
        message = "actions must be a list"
        raise TypeError(message)
    raw_actions = cast("list[object]", actions)
    action_ids: list[str] = []
    for raw_item in raw_actions:
        item = raw_item
        if not isinstance(item, Mapping):
            message = "each action must be an object"
            raise TypeError(message)
        action_id = cast("object", item.get("id"))
        if not isinstance(action_id, str):
            message = "each action must have a string id"
            raise TypeError(message)
        action_ids.append(action_id)
    if len(action_ids) != len(set(action_ids)):
        message = "flow action identifiers must be unique"
        raise ValueError(message)
    if not all(action in action_ids for action in REQUIRED_ACTIONS):
        message = "required flow actions are missing"
        raise ValueError(message)
    positions = {action: action_ids.index(action) for action in REQUIRED_ACTIONS}
    if positions["advance_checkpoint"] <= positions["write_projection"]:
        message = "checkpoint must advance after projection write"
        raise ValueError(message)
    ordered_positions = [positions[action] for action in REQUIRED_ACTIONS]
    if ordered_positions != sorted(ordered_positions):
        message = "required flow actions must follow checkpoint-safe order"
        raise ValueError(message)
    for raw_action in raw_actions:
        # Every action was checked before evaluating the execution sequence.
        action = cast("Mapping[str, object]", raw_action)
        forbidden_inputs = cast("list[str]", action.get("forbidden_inputs", []))
        if not isinstance(action.get("forbidden_inputs", []), list):
            message = "forbidden_inputs must be a list"
            raise TypeError(message)
        unsafe = set(forbidden_inputs) - FORBIDDEN_FIELDS
        if unsafe:
            message = f"unrecognized raw fields in flow contract: {', '.join(sorted(unsafe))}"
            raise ValueError(message)
    failure_policy = contract.get("failure_policy")
    if not isinstance(failure_policy, Mapping):
        message = "failure_policy is required"
        raise TypeError(message)
    if failure_policy.get("never_advance_checkpoint_on_failure") is not True:
        message = "failure policy must prevent checkpoint advancement"
        raise ValueError(message)
    if failure_policy.get("never_store_raw_payload") is not True:
        message = "failure policy must prevent raw payload storage"
        raise ValueError(message)
