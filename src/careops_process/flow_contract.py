# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

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
    "publish_analytics_file",
    "advance_checkpoint",
)
ALLOWED_CONNECTORS = frozenset(
    {
        "Office 365 Outlook",
        "Planner",
        "SharePoint",
        "Compose",
        "Condition",
        "Microsoft Teams Approvals",
    }
)
PROHIBITED_PERSISTED_FIELDS = FORBIDDEN_FIELDS | frozenset(
    {"internetMessageId", "conversationId", "parentFolderId", "raw_source_id", "rawMessageId"}
)
CHECKPOINT_LOOKUP_TOP_COUNT = 2


def validate_flow_contract(contract: Mapping[str, object]) -> None:  # noqa: C901, PLR0912, PLR0915
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
    by_id: dict[str, Mapping[str, object]] = {}
    for raw_action in raw_actions:
        # Every action was checked before evaluating the execution sequence.
        action = cast("Mapping[str, object]", raw_action)
        by_id[cast("str", action["id"])] = action
        forbidden_inputs = cast("list[str]", action.get("forbidden_inputs", []))
        if not isinstance(action.get("forbidden_inputs", []), list):
            message = "forbidden_inputs must be a list"
            raise TypeError(message)
        unsafe = set(forbidden_inputs) - FORBIDDEN_FIELDS
        if unsafe:
            message = f"unrecognized raw fields in flow contract: {', '.join(sorted(unsafe))}"
            raise ValueError(message)
        stores = action.get("stores", [])
        if not isinstance(stores, list):
            message = "stores must be a list of minimized persistent fields"
            raise TypeError(message)
        store_fields = cast("list[object]", stores)
        if any(not isinstance(field, str) for field in store_fields):
            message = "stores must be a list of minimized persistent fields"
            raise TypeError(message)
        persisted_unsafe = set(cast("list[str]", store_fields)) & PROHIBITED_PERSISTED_FIELDS
        if persisted_unsafe:
            message = f"raw fields cannot be persisted: {', '.join(sorted(persisted_unsafe))}"
            raise ValueError(message)
        connector = action.get("connector")
        if connector not in ALLOWED_CONNECTORS:
            message = f"unsupported or premium connector in ingestion contract: {connector}"
            raise ValueError(message)
    if (
        by_id["read_checkpoint"].get("connector") != "SharePoint"
        or by_id["read_checkpoint"].get("operation") != "Get items"
        or by_id["read_checkpoint"].get("filter_query") != "source_key eq '<source_key>'"
        or by_id["read_checkpoint"].get("top_count") != CHECKPOINT_LOOKUP_TOP_COUNT
        or by_id["read_checkpoint"].get("on_empty")
        != "create_initial_checkpoint_with_empty_watermark_and_revision_zero"
        or by_id["read_checkpoint"].get("on_one")
        != "read_checkpoint_and_use_returned_ID_for_Update_item"
        or by_id["read_checkpoint"].get("on_multiple") != "stop_and_reconcile; never_select_first"
    ):
        message = "checkpoint lookup must filter uniquely with SharePoint Get items and fail closed"
        raise ValueError(message)
    if (
        by_id["write_projection"].get("connector") != "SharePoint"
        or by_id["write_projection"].get("unique_key") != "fact_id"
    ):
        message = "projection persistence must use SharePoint with a unique fact_id"
        raise ValueError(message)
    if (
        by_id["publish_analytics_file"].get("connector") != "SharePoint"
        or by_id["publish_analytics_file"].get("after") != "write_projection"
    ):
        message = "portable event file must publish after the SharePoint queue write"
        raise ValueError(message)
    if by_id["advance_checkpoint"].get("after") != "publish_analytics_file":
        message = "checkpoint must advance only after event file publication"
        raise ValueError(message)
    if by_id["dead_letter"].get("never_advance_checkpoint") is not True:
        message = "dead-letter branch must not advance the checkpoint"
        raise ValueError(message)
    identity_projection = contract.get("identity_projection")
    if not isinstance(identity_projection, Mapping):
        message = "flow contract must define keyed identity projection"
        raise TypeError(message)
    raw_source_policy = cast("object", identity_projection.get("raw_source_ids"))
    if (
        identity_projection.get("algorithm")
        != "existing hmac-sha256-json-array-v1 with approved key reference"
        or not isinstance(raw_source_policy, str)
        or "never persist" not in raw_source_policy
    ):
        message = (
            "flow contract must use approved keyed pseudonyms and prohibit "
            "persisted raw identifiers"
        )
        raise ValueError(message)
    concurrency = contract.get("concurrency")
    if not isinstance(concurrency, Mapping) or concurrency.get("flow_runs") != 1:
        message = "SharePoint checkpoint flow must serialize runs"
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
