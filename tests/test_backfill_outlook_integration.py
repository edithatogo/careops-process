# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic Outlook reconciliation-to-M365 closed-report integration."""

from copy import deepcopy
from typing import Any

import pytest

from careops_process.backfill_evidence import close_reconciled_run, evidence_digest
from careops_process.outlook_reconciliation import reconcile_outlook_evidence
from careops_process.report import build_authorised_closed_run_report
from tests.test_outlook_reconciliation import inputs


def configuration(reconciled: dict[str, Any]) -> dict[str, Any]:
    """Bind the independently supplied folder inventory into synthetic controls."""
    return {
        "authorised_source_partitions": [item["partition_id"] for item in reconciled["partitions"]],
        "observation_start": "2026-01-01T00:00:00Z",
        "observation_end": "2026-01-02T00:00:00Z",
        "destination_reference": "synthetic-store",
        "retention_policy_version": "synthetic-policy-v1",
        "mapping_version": "1.0.0",
        "inventory_hash": reconciled["inventory_hash"],
    }


@pytest.mark.parametrize("evidence_class", ["synthetic", "smoke_test"])
def test_reconciled_source_destination_and_replay_produce_bound_report(evidence_class: str) -> None:
    """Two synthetic reconciled snapshots bind empty folders, duplicates and destination data."""
    initial = reconcile_outlook_evidence(**inputs())
    replay = reconcile_outlook_evidence(**inputs())
    frozen = configuration(initial)
    evidence = close_reconciled_run(
        initial, replay, frozen, run_id="synthetic-run", evidence_class=evidence_class
    )
    entry = {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": frozen["authorised_source_partitions"],
        "configuration_hash": evidence_digest(frozen),
        "evidence_reference": "synthetic-approval-reference",
    }
    report = build_authorised_closed_run_report(
        initial["facts"],
        evidence,
        entry,
        pseudonym_secret="synthetic-key",  # noqa: S106
    )
    assert report["evidence"]["idempotency_replay_verified"] is True
    assert report["coverage_ledger"]["source_candidate_count"] == 2  # noqa: PLR2004
    assert report["coverage_ledger"]["source_acquired_count"] == 1
    assert len(report["evidence"]["partitions"]) == len(frozen["authorised_source_partitions"])
    assert report["coverage_ledger"]["owner_validation_status"] == "pending"


@pytest.mark.parametrize(
    "defect",
    ["destination_pending", "changed_replay", "changed_inventory", "unbound_configuration"],
)
def test_incomplete_or_changed_reconciliation_cannot_close(defect: str) -> None:
    """The first acquisition cannot replace destination, replay or frozen-inventory proof."""
    initial = reconcile_outlook_evidence(**inputs())
    replay = deepcopy(initial)
    frozen = configuration(initial)
    if defect == "destination_pending":
        replay["status"] = "destination_pending"
        replay["destination_reconciled"] = False
    elif defect == "changed_replay":
        replay["facts"][0]["activity"] = "changed"
    elif defect == "changed_inventory":
        replay["inventory_hash"] = "0" * 64
    else:
        frozen["inventory_hash"] = "0" * 64
    with pytest.raises(ValueError, match=r"reconciliation|replay|inventory"):
        close_reconciled_run(
            initial, replay, frozen, run_id="synthetic-run", evidence_class="synthetic"
        )


def test_closure_configuration_errors_do_not_echo_supplied_values() -> None:
    """Closure diagnostics remain payload-free even before the report CLI boundary."""
    initial = reconcile_outlook_evidence(**inputs())
    frozen = configuration(initial)
    sentinel = "synthetic-protected-value"
    frozen["inventory_hash"] = sentinel
    with pytest.raises(ValueError) as error:  # noqa: PT011
        close_reconciled_run(
            initial, initial, frozen, run_id="synthetic-run", evidence_class="synthetic"
        )
    assert sentinel not in str(error.value)


def test_generic_destination_does_not_claim_dataverse_provenance() -> None:
    """Matching supplied rows prove content equality, not the destination service."""
    result = reconcile_outlook_evidence(**inputs())
    assert result["destination_reconciled"] is True
    assert result["dataverse_reconciled"] is False


def test_caller_dataverse_boolean_cannot_unlock_live_closure() -> None:
    """A caller-controlled label cannot replace a supported readback verifier."""
    initial = reconcile_outlook_evidence(**inputs())
    initial["dataverse_reconciled"] = True
    initial["destination_receipt"] = {"service": "Dataverse", "verified": True}
    with pytest.raises(ValueError, match=r"Dataverse.*provenance"):
        close_reconciled_run(
            initial,
            initial,
            configuration(initial),
            run_id="unsupported-live",
            evidence_class="live_corpus",
        )
