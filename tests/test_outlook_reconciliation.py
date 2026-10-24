# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic frozen-folder, page-ledger and destination reconciliation checks."""

from copy import deepcopy
from typing import Any, cast

import pytest

from careops_process.backfill_evidence import close_reconciled_run, validate_bound_evidence
from careops_process.outlook_reconciliation import (
    collect_folder_inventory,
    reconcile_outlook_evidence,
)

ROOT = "folder_" + "1" * 64
CHILD = "folder_" + "2" * 64
EXCLUDED = "folder_" + "3" * 64
FACT = {
    "id": "mail_" + "4" * 64,
    "activity": "email_received",
    "timestamp_utc": "2026-01-01T00:00:00Z",
    "source_system": "outlook",
    "object_ids": ["conversation_" + "5" * 64],
    "folder_id": CHILD,
    "has_attachments": False,
    "importance": "normal",
}


def inputs() -> dict[str, Any]:
    """Return independently authored source/destination fixtures, not live evidence."""
    return {
        "inventory": [
            {
                "folder_id": ROOT,
                "parent_folder_id": None,
                "disposition": "included",
                "reason": None,
                "children_enumerated": True,
                "source_record_count": 0,
            },
            {
                "folder_id": CHILD,
                "parent_folder_id": ROOT,
                "disposition": "included",
                "reason": None,
                "children_enumerated": True,
                "source_record_count": 1,
            },
            {
                "folder_id": EXCLUDED,
                "parent_folder_id": ROOT,
                "disposition": "excluded",
                "reason": "owner-excluded-system-folder",
                "children_enumerated": True,
                "source_record_count": None,
            },
        ],
        "collector_facts": [deepcopy(FACT)],
        "pages": [
            {
                "folder_id": ROOT,
                "page_number": 1,
                "candidate_count": 0,
                "acquired_count": 0,
                "duplicate_count": 0,
                "rejected_count": 0,
                "fact_ids": [],
                "next_link_exhausted": True,
            },
            {
                "folder_id": CHILD,
                "page_number": 1,
                "candidate_count": 1,
                "acquired_count": 1,
                "duplicate_count": 0,
                "rejected_count": 0,
                "fact_ids": [FACT["id"]],
                "next_link_exhausted": False,
            },
            {
                "folder_id": CHILD,
                "page_number": 2,
                "candidate_count": 1,
                "acquired_count": 0,
                "duplicate_count": 1,
                "rejected_count": 0,
                "fact_ids": [],
                "next_link_exhausted": True,
            },
        ],
        "destination_facts": [
            {
                "id": FACT["id"],
                "activity": "email_received",
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "source_system": "outlook",
                "object_ids": FACT["object_ids"],
            }
        ],
    }


def test_nested_empty_excluded_folders_and_destination_reconcile() -> None:
    """Measured nested pages and a supplied destination produce bound partitions."""
    fixture = inputs()
    result = reconcile_outlook_evidence(**fixture)
    assert result["status"] == "reconciled"
    assert result["destination_reconciled"] is True
    assert result["dataverse_reconciled"] is False
    assert (result["folder_count"], result["page_count"], result["candidate_count"]) == (2, 3, 2)
    assert result["facts"] == fixture["destination_facts"]
    assert result["partitions"][1]["duplicate_count"] == 1
    assert result["partitions"][0]["emitted_count"] == 0
    assert result["excluded_folder_count"] == 1
    assert result["idempotency_replay_verified"] is False
    assert result["full_mailbox_verified"] is False


def test_missing_destination_is_pending_and_never_synthesized() -> None:
    """Local source evidence cannot stand in for destination writes."""
    fixture = inputs()
    fixture["destination_facts"] = None
    result = reconcile_outlook_evidence(**fixture)
    assert result["status"] == "destination_pending"
    assert result["destination_reconciled"] is False
    assert result["dataverse_reconciled"] is False


@pytest.mark.parametrize(
    "defect",
    [
        "cycle",
        "orphan",
        "duplicate_folder",
        "unvisited_children",
        "inaccessible",
        "missing_reason",
        "missing_page",
        "page_gap",
        "premature_exhaustion",
        "unexhausted",
        "count_mismatch",
        "source_count_drift",
        "missing_membership",
        "wrong_folder",
        "rejected",
        "destination_missing",
        "destination_changed",
        "destination_duplicate",
        "raw_fact",
        "raw_folder",
        "duplicate_fact",
        "unknown_source_count",
        "boolean_count",
        "timestamp_without_timezone",
        "empty_objects",
        "duplicated_objects",
        "foreign_page",
        "repeated_page_fact",
        "empty_inventory",
        "raw_diagnostics",
    ],
)
def test_invalid_evidence_cannot_be_reconciled(defect: str) -> None:  # noqa: C901, PLR0912, PLR0915
    """Each source, destination or privacy inconsistency fails closed."""
    fixture = inputs()
    inventory = fixture["inventory"]
    pages = fixture["pages"]
    facts = fixture["collector_facts"]
    destination = fixture["destination_facts"]
    if defect == "cycle":
        inventory[0]["parent_folder_id"] = CHILD
    elif defect == "orphan":
        inventory[1]["parent_folder_id"] = "folder_" + "9" * 64
    elif defect == "duplicate_folder":
        inventory.append(deepcopy(inventory[0]))
    elif defect == "unvisited_children":
        inventory[0]["children_enumerated"] = False
    elif defect == "inaccessible":
        inventory[2]["disposition"] = "inaccessible"
    elif defect == "missing_reason":
        inventory[2]["reason"] = None
    elif defect == "missing_page":
        pages.pop(0)
    elif defect == "page_gap":
        pages[2]["page_number"] = 3
    elif defect == "premature_exhaustion":
        pages[1]["next_link_exhausted"] = True
    elif defect == "unexhausted":
        pages[2]["next_link_exhausted"] = False
    elif defect == "count_mismatch":
        pages[1]["candidate_count"] = 4
    elif defect == "source_count_drift":
        inventory[1]["source_record_count"] = 4
    elif defect == "missing_membership":
        pages[1]["fact_ids"] = []
    elif defect == "wrong_folder":
        facts[0]["folder_id"] = EXCLUDED
    elif defect == "rejected":
        pages[2]["duplicate_count"] = 0
        pages[2]["rejected_count"] = 1
    elif defect == "destination_missing":
        destination.clear()
    elif defect == "destination_changed":
        destination[0]["activity"] = "something_else"
    elif defect == "destination_duplicate":
        destination.append(deepcopy(destination[0]))
    elif defect == "raw_fact":
        facts[0]["subject"] = "synthetic forbidden narrative"
    elif defect == "raw_folder":
        inventory[0]["folder_id"] = "raw-folder-id"
    elif defect == "duplicate_fact":
        facts.append(deepcopy(facts[0]))
    elif defect == "unknown_source_count":
        inventory[1]["source_record_count"] = None
    elif defect == "boolean_count":
        pages[0]["candidate_count"] = False
    elif defect == "timestamp_without_timezone":
        facts[0]["timestamp_utc"] = "2026-01-01T00:00:00"
    elif defect == "empty_objects":
        facts[0]["object_ids"] = []
    elif defect == "duplicated_objects":
        facts[0]["object_ids"] *= 2
    elif defect == "foreign_page":
        pages[0]["folder_id"] = EXCLUDED
    elif defect == "repeated_page_fact":
        pages[2].update(acquired_count=1, duplicate_count=0, fact_ids=[FACT["id"]])
    elif defect == "empty_inventory":
        inventory.clear()
    elif defect == "raw_diagnostics":
        facts[0]["id"] = "PROTECTED-INPUT-MUST-NOT-BE-LOGGED"
    with pytest.raises(ValueError, match="Outlook evidence failed"):
        reconcile_outlook_evidence(**fixture)


def test_reconciliation_is_deterministic_without_reordering_input() -> None:
    """Repeated evidence gives identical hashes and leaves inputs untouched."""
    fixture = inputs()
    before = deepcopy(fixture)
    assert reconcile_outlook_evidence(**fixture) == reconcile_outlook_evidence(**fixture)
    assert fixture == before


def test_partition_mapping_is_accepted_by_bound_consumer() -> None:
    """Supplied synthetic evidence maps to the strict M365 partition/hash interface."""
    result = reconcile_outlook_evidence(**inputs())
    configuration = {
        "authorised_source_partitions": [ROOT, CHILD],
        "observation_start": "2026-01-01T00:00:00Z",
        "observation_end": "2026-01-02T00:00:00Z",
        "destination_reference": "synthetic-store",
        "retention_policy_version": "synthetic-v1",
        "mapping_version": "2.0.0",
        "inventory_hash": result["inventory_hash"],
    }
    replay = reconcile_outlook_evidence(**inputs())
    evidence = close_reconciled_run(
        result, replay, configuration, run_id="synthetic-only", evidence_class="synthetic"
    )
    lineage = validate_bound_evidence(result["facts"], evidence)
    assert lineage.startswith("closed-run:synthetic-only|facts:")
    assert result["status"] == "reconciled"


def test_bad_input_is_not_echoed_in_validation_diagnostics() -> None:
    """Schema diagnostics cannot echo an accidentally supplied protected identifier."""
    fixture = inputs()
    fixture["collector_facts"][0]["id"] = "PROTECTED-INPUT-MUST-NOT-BE-LOGGED"
    with pytest.raises(ValueError, match="Outlook evidence failed") as error:
        reconcile_outlook_evidence(**fixture)
    assert "PROTECTED-INPUT" not in str(error.value)


@pytest.mark.parametrize(
    "defect", ["included_below_excluded", "inaccessible_as_excluded", "included_reason"]
)
def test_inventory_disposition_cannot_hide_an_unknown_or_excluded_population(defect: str) -> None:
    """Supplied snapshots must preserve exclusion inheritance and reason semantics."""
    fixture = inputs()
    if defect == "included_below_excluded":
        fixture["inventory"].append(
            {
                "folder_id": "folder_" + "6" * 64,
                "parent_folder_id": EXCLUDED,
                "disposition": "included",
                "reason": None,
                "children_enumerated": True,
                "source_record_count": 0,
            }
        )
        fixture["pages"].append(
            {
                **deepcopy(fixture["pages"][0]),
                "folder_id": "folder_" + "6" * 64,
            }
        )
    elif defect == "inaccessible_as_excluded":
        fixture["inventory"][2]["reason"] = "source-inaccessible"
    else:
        fixture["inventory"][1]["reason"] = "owner-excluded-scope"
    with pytest.raises(ValueError, match="Outlook evidence failed"):
        reconcile_outlook_evidence(**fixture)


@pytest.mark.parametrize(
    "response",
    [None, list[object](), {"value": [None]}, {"value": [list[object]()]}],
)
def test_inventory_malformed_source_shapes_have_sanitized_failure(response: object) -> None:
    """Malformed source envelopes and rows fail at the protected adapter boundary."""

    def fetch(parent: str | None, cursor: str | None, include_hidden: bool) -> dict[str, Any]:  # noqa: FBT001, ARG001
        return cast("dict[str, Any]", response)

    with pytest.raises(ValueError, match="Outlook inventory collection failed"):
        collect_folder_inventory(
            fetch, pseudonym_key=bytes(range(32)), mailbox_ref="mailbox_" + "a" * 64
        )


def test_inventory_traverses_nested_and_paginated_hidden_folders() -> None:
    """A real traversal over a synthetic source never stores raw IDs or names."""
    calls: list[tuple[str | None, str | None, bool]] = []
    responses: dict[tuple[str | None, str | None], dict[str, Any]] = {
        (None, None): {
            "value": [
                {
                    "id": "RAW-ROOT",
                    "childFolderCount": 1,
                    "totalItemCount": 0,
                    "displayName": "RAW-NAME",
                }
            ],
            "@odata.nextLink": "opaque-next-page",
        },
        (None, "opaque-next-page"): {
            "value": [{"id": "RAW-OTHER", "childFolderCount": 0, "totalItemCount": 0}],
        },
        ("RAW-ROOT", None): {
            "value": [
                {
                    "id": "RAW-CHILD",
                    "parentFolderId": "RAW-ROOT",
                    "childFolderCount": 0,
                    "totalItemCount": 1,
                    "isHidden": True,
                }
            ],
        },
        ("RAW-OTHER", None): {"value": []},
        ("RAW-CHILD", None): {"value": []},
    }

    def fetch(parent: str | None, cursor: str | None, include_hidden: bool) -> dict[str, Any]:  # noqa: FBT001
        calls.append((parent, cursor, include_hidden))
        return responses[parent, cursor]

    inventory = collect_folder_inventory(
        fetch, pseudonym_key=bytes(range(32)), mailbox_ref="mailbox_" + "a" * 64
    )
    assert len(inventory) == len(responses) - 2
    assert all(include_hidden for _, _, include_hidden in calls)
    assert "RAW-" not in str(inventory)
    assert inventory[2]["parent_folder_id"] == inventory[0]["folder_id"]
    assert inventory[2]["source_record_count"] == 1
    excluded = collect_folder_inventory(
        fetch,
        pseudonym_key=bytes(range(32)),
        mailbox_ref="mailbox_" + "a" * 64,
        excluded_folder_refs={inventory[0]["folder_id"]},
    )
    assert [folder["disposition"] for folder in excluded] == ["excluded", "included", "excluded"]


@pytest.mark.parametrize(
    "defect", ["cursor_loop", "repeated_id", "wrong_parent", "child_count_drift", "source_failure"]
)
def test_inventory_collection_fails_closed(defect: str) -> None:
    """Traversal failures cannot yield a frozen inventory certificate."""

    def fetch(parent: str | None, cursor: str | None, include_hidden: bool) -> dict[str, Any]:  # noqa: FBT001, ARG001
        if defect == "source_failure":
            message = "PROTECTED-SOURCE-ERROR"
            raise RuntimeError(message)
        folder = {
            "id": "RAW-ID",
            "parentFolderId": "WRONG" if defect == "wrong_parent" else parent,
            "childFolderCount": 1,
            "totalItemCount": 0,
        }
        if defect == "cursor_loop":
            folder["id"] = "RAW-ID" + str(cursor)
            return {"value": [folder], "@odata.nextLink": "same-page"}
        if defect == "child_count_drift" and parent is not None:
            return {"value": []}
        return {"value": [folder]}

    with pytest.raises(ValueError, match="Outlook inventory collection failed") as error:
        collect_folder_inventory(
            fetch, pseudonym_key=bytes(range(32)), mailbox_ref="mailbox_" + "a" * 64
        )
    assert "PROTECTED" not in str(error.value)
