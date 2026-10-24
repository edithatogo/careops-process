# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Closed-run evidence must bind inputs, scope and measured reconciliation."""

from copy import deepcopy
from typing import Any

import pytest

from careops_process.backfill_run import run_authorised_closed_backfill, run_closed_backfill
from tests.backfill_fixture import digest, sealed_evidence

FACTS: list[dict[str, Any]] = [
    {
        "id": "fact-1",
        "activity": "request_received",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "source_system": "outlook",
        "object_ids": ["request-1"],
    }
]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_count", 20),
        ("page_count", 2),
        ("folder_count", 2),
        ("content_hash", "0" * 64),
        ("configuration_hash", "0" * 64),
        ("manifest_version", "1.0.0"),
        ("partitions", []),
    ],
)
def test_run_rejects_unbound_summary(field: str, value: object) -> None:
    """Summary declarations cannot substitute for matching input manifests."""
    evidence = sealed_evidence(FACTS)
    evidence[field] = value
    with pytest.raises(ValueError, match=r"mismatch|required"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_count", 3),
        ("acquired_count", 2),
        ("emitted_count", 0),
        ("fact_ids", ["missing"]),
        ("content_hash", "0" * 64),
        ("next_link_exhausted", False),
        ("source_system", "planner"),
        ("partition_id", "outside-approved-scope"),
    ],
)
def test_run_rejects_invalid_partition(field: str, value: object) -> None:
    """Each partition must reconcile its records, emitted identities and source."""
    evidence = sealed_evidence(FACTS)
    evidence["partitions"][0][field] = value
    with pytest.raises(ValueError, match=r"reconcile|mismatch|unknown|exhausted|match"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106


def test_authorised_run_rejects_configuration_not_approved() -> None:
    """Approval must bind the exact configuration used by this acquisition run."""
    evidence = sealed_evidence(FACTS)
    entry = {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": ["outlook-authorised-mailbox"],
        "evidence_reference": "synthetic-reference",
        "configuration_hash": "0" * 64,
    }
    with pytest.raises(ValueError, match="configuration"):
        run_authorised_closed_backfill(FACTS, evidence, entry, pseudonym_secret="synthetic-key")  # noqa: S106


def test_changed_facts_cannot_reuse_closed_manifest() -> None:
    """A manifest from different inputs cannot give a new corpus closed lineage."""
    facts = deepcopy(FACTS)
    facts[0]["activity"] = "changed_activity"
    with pytest.raises(ValueError, match="content hash mismatch"):
        run_closed_backfill(facts, sealed_evidence(FACTS), pseudonym_secret="synthetic-key")  # noqa: S106


def test_one_source_record_can_emit_multiple_events() -> None:
    """Record reconciliation is independent of source-to-event cardinality."""
    facts: list[dict[str, Any]] = [
        *FACTS,
        {**FACTS[0], "id": "fact-2", "activity": "request_completed"},
    ]
    result = run_closed_backfill(facts, sealed_evidence(facts), pseudonym_secret="synthetic-key")  # noqa: S106
    assert len(result.log.events) == len(facts)
    assert digest(facts) in result.log.lineage


@pytest.mark.parametrize(
    "timestamp",
    [
        "2025-12-31T23:59:59Z",
        "2026-01-02T00:00:00Z",
        "2026-01-01T00:00:00",
    ],
)
def test_run_rejects_outside_or_naive_observations(timestamp: str) -> None:
    """The frozen observation boundary is timezone-aware and half-open."""
    facts = deepcopy(FACTS)
    facts[0]["timestamp_utc"] = timestamp
    with pytest.raises(ValueError, match=r"observation period|timezone"):
        run_closed_backfill(facts, sealed_evidence(facts), pseudonym_secret="synthetic-key")  # noqa: S106


@pytest.mark.parametrize("change", ["duplicate_fact", "raw_field", "unassigned_fact"])
def test_run_rejects_incomplete_fact_provenance(change: str) -> None:
    """Every unique allowlisted fact must belong to exactly one measured partition."""
    facts = deepcopy(FACTS)
    evidence = sealed_evidence(facts)
    if change == "duplicate_fact":
        facts.append(facts[0])
    elif change == "raw_field":
        facts[0]["subject"] = "synthetic prohibited narrative"
    else:
        facts.append({**facts[0], "id": "unassigned"})
        evidence["content_hash"] = digest(facts)
    with pytest.raises(ValueError, match=r"duplicate|allowlist|missing partition"):
        run_closed_backfill(facts, evidence, pseudonym_secret="synthetic-key")  # noqa: S106


def test_empty_inventory_partition_is_preserved() -> None:
    """An exhausted empty folder is not confused with an absent manifest."""
    evidence = sealed_evidence(FACTS)
    configuration = evidence["configuration"]
    configuration["authorised_source_partitions"].append("empty-folder")
    evidence["configuration_hash"] = digest(configuration)
    empty: dict[str, Any] = {
        **evidence["partitions"][0],
        "partition_id": "empty-folder",
        "candidate_count": 0,
        "acquired_count": 0,
        "emitted_count": 0,
        "fact_ids": [],
        "content_hash": digest([]),
    }
    evidence["partitions"].append(empty)
    evidence["folder_count"] = 2
    evidence["page_count"] = 2
    result = run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106
    assert len(result.log.events) == len(FACTS)


@pytest.mark.parametrize("count_field", ["duplicate_count", "rejected_count", "filtered_count"])
def test_source_record_exclusions_are_accounted_separately(count_field: str) -> None:
    """Count reconciliation includes explicit exclusions without fabricating events."""
    evidence = sealed_evidence(FACTS)
    evidence["candidate_count"] = 2
    evidence["partitions"][0]["candidate_count"] = 2
    evidence["partitions"][0][count_field] = 1
    result = run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106
    assert len(result.log.events) == len(FACTS)


def test_run_rejects_unknown_evidence_fields() -> None:
    """The manifest cannot smuggle raw narrative through arbitrary envelope fields."""
    evidence = sealed_evidence(FACTS)
    evidence["subject"] = "synthetic prohibited content"
    with pytest.raises(ValueError, match="evidence structure"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106


def test_run_requires_an_explicit_evidence_class() -> None:
    """Synthetic and smoke-test output cannot silently become live corpus evidence."""
    evidence = sealed_evidence(FACTS)
    evidence.pop("evidence_class", None)
    with pytest.raises(ValueError, match="evidence structure"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106


def test_acquired_export_cannot_be_promoted_by_summary_flags() -> None:
    """Collection-level acquisition success is not folder/destination closure."""
    evidence = sealed_evidence(FACTS)
    evidence["status"] = "acquired"
    with pytest.raises(ValueError, match="closed backfill run"):
        run_closed_backfill(FACTS, evidence, pseudonym_secret="synthetic-key")  # noqa: S106


def test_pilot_scope_must_match_approved_configuration() -> None:
    """A valid configuration hash does not authorise a different approved partition list."""
    evidence = sealed_evidence(FACTS)
    entry = {
        "source_owner_approved": True,
        "ig_approved": True,
        "configuration_frozen": True,
        "rollback_retention_approved": True,
        "authorised_source_partitions": ["different-approved-partition"],
        "configuration_hash": evidence["configuration_hash"],
        "evidence_reference": "synthetic-reference",
    }
    with pytest.raises(ValueError, match="approval scope"):
        run_authorised_closed_backfill(FACTS, evidence, entry, pseudonym_secret="synthetic-key")  # noqa: S106
