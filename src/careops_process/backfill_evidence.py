"""Versioned, input-bound completeness evidence for closed acquisition runs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Count = Annotated[int, Field(ge=0)]
Label = Annotated[str, Field(min_length=1, pattern=r"\S")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
FACT_FIELDS = frozenset({"id", "activity", "timestamp_utc", "source_system", "object_ids"})


class FrozenConfiguration(BaseModel):
    """Approved source inventory, observation and records controls."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    authorised_source_partitions: list[Label]
    observation_start: Label
    observation_end: Label
    destination_reference: Label
    retention_policy_version: Label
    mapping_version: Label
    inventory_hash: Digest


class PartitionEvidence(BaseModel):
    """Record accounting and emitted-fact membership for one inventoried folder."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    partition_id: Label
    source_system: Label
    pages_read: Count
    candidate_count: Count
    acquired_count: Count
    duplicate_count: Count
    rejected_count: Count
    filtered_count: Count
    emitted_count: Count
    fact_ids: list[Label]
    content_hash: Digest
    next_link_exhausted: bool


class BoundRunEvidence(BaseModel):
    """Strict public shape of the v2 closed-run evidence envelope."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    manifest_version: Literal["2.0.0"]
    evidence_class: Literal["synthetic", "smoke_test", "live_corpus"]
    run_id: Label
    status: Literal["closed"]
    folder_count: Count
    page_count: Count
    candidate_count: Count
    pagination_exhausted: bool
    reconciled: bool
    idempotency_replay_verified: bool
    no_raw_content_stored: bool
    configuration: FrozenConfiguration
    configuration_hash: Digest
    content_hash: Digest
    partitions: list[PartitionEvidence]
    initial_reconciliation_hash: Digest
    replay_reconciliation_hash: Digest


def evidence_digest(value: object) -> str:
    """Hash UTF-8 canonical JSON; array order remains part of the input contract."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _require(condition: bool, message: str) -> None:  # noqa: FBT001
    if not condition:
        raise ValueError(message)


def _period(configuration: FrozenConfiguration) -> tuple[datetime, datetime]:
    start = datetime.fromisoformat(configuration.observation_start)
    end = datetime.fromisoformat(configuration.observation_end)
    _require(
        start.utcoffset() is not None and end.utcoffset() is not None,
        "observation period requires explicit timezones",
    )
    _require(start < end, "observation period must be increasing")
    return start, end


def _manifest(evidence: dict[str, object]) -> BoundRunEvidence:
    _require(evidence.get("manifest_version") == "2.0.0", "bound manifest_version 2.0.0 required")
    try:
        return BoundRunEvidence.model_validate(evidence)
    except ValidationError:
        message = "bound evidence structure is invalid"
        raise ValueError(message) from None


def validate_bound_evidence(facts: list[dict[str, object]], evidence: dict[str, object]) -> str:
    """Verify measured partition membership, record counts and input/configuration hashes."""
    manifest = _manifest(evidence)
    configuration = manifest.configuration
    config_hash = evidence_digest(configuration.model_dump())
    _require(evidence.get("configuration_hash") == config_hash, "configuration hash mismatch")
    start, end = _period(configuration)
    approved = configuration.authorised_source_partitions
    _require(
        bool(approved) and len(set(approved)) == len(approved),
        "configuration requires unique authorised partitions",
    )
    partitions = manifest.partitions
    _require(bool(partitions), "partition manifests required")
    keys = [item.partition_id for item in partitions]
    _require(
        len(set(keys)) == len(keys) and set(keys) == set(approved),
        "partition inventory does not match frozen scope",
    )
    by_id: dict[str, dict[str, object]] = {}
    positions: dict[str, int] = {}
    for position, fact in enumerate(facts):
        _require(frozenset(fact) == FACT_FIELDS, "facts must contain only the minimized allowlist")
        identifier = fact.get("id")
        _require(isinstance(identifier, str) and bool(identifier.strip()), "fact identity required")
        identifier = str(identifier)
        _require(identifier not in by_id, "duplicate emitted fact identity")
        by_id[identifier] = fact
        positions[identifier] = position
        timestamp = fact.get("timestamp_utc")
        _require(isinstance(timestamp, str), "fact timestamp must be a string")
        parsed = datetime.fromisoformat(str(timestamp))
        _require(parsed.utcoffset() is not None, "fact timestamp requires explicit timezone")
        _require(start <= parsed < end, "fact outside frozen observation period")
    assigned: set[str] = set()
    for partition in partitions:
        accounted = (
            partition.acquired_count
            + partition.duplicate_count
            + partition.rejected_count
            + partition.filtered_count
        )
        _require(partition.candidate_count == accounted, "partition source counts do not reconcile")
        _require(
            partition.next_link_exhausted and partition.pages_read > 0,
            "partition pagination is not exhausted",
        )
        identifiers = partition.fact_ids
        _require(len(set(identifiers)) == len(identifiers), "duplicate partition fact identity")
        _require(partition.emitted_count == len(identifiers), "partition emitted count mismatch")
        _require(
            partition.acquired_count > 0 or not identifiers,
            "events cannot be emitted without acquired source records",
        )
        _require(not assigned.intersection(identifiers), "fact assigned to multiple partitions")
        _require(set(identifiers).issubset(by_id), "partition references an unknown fact")
        selected = [by_id[key] for key in sorted(identifiers, key=positions.__getitem__)]
        _require(
            all(fact["source_system"] == partition.source_system for fact in selected),
            "partition source does not match emitted facts",
        )
        _require(
            evidence_digest(selected) == partition.content_hash, "partition content hash mismatch"
        )
        assigned.update(identifiers)
    _require(assigned == set(by_id), "emitted facts missing partition provenance")
    _require(evidence.get("folder_count") == len(partitions), "folder count mismatch")
    _require(
        evidence.get("page_count") == sum(item.pages_read for item in partitions),
        "page count mismatch",
    )
    _require(
        evidence.get("candidate_count") == sum(item.candidate_count for item in partitions),
        "candidate count mismatch",
    )
    content_hash = evidence_digest(facts)
    _require(evidence.get("content_hash") == content_hash, "run content hash mismatch")
    return f"closed-run:{evidence['run_id']}|facts:{content_hash}|configuration:{config_hash}"


def close_reconciled_run(
    initial: dict[str, Any],
    replay: dict[str, Any],
    configuration: dict[str, Any],
    *,
    run_id: str,
    evidence_class: str,
) -> dict[str, Any]:
    """Close independently supplied source/destination reconciliation and replay evidence."""
    try:
        frozen = FrozenConfiguration.model_validate(configuration)
    except ValidationError:
        message = "closure frozen configuration is invalid"
        raise ValueError(message) from None
    for snapshot in (initial, replay):
        _require(
            snapshot.get("status") == "reconciled" and snapshot.get("dataverse_reconciled") is True,
            "source and destination reconciliation is required for both snapshots",
        )
        _require(
            snapshot.get("inventory_hash") == frozen.inventory_hash,
            "reconciliation inventory differs from frozen configuration",
        )
    _require(initial.get("facts") == replay.get("facts"), "replay minimized facts changed")
    _require(
        initial.get("partitions") == replay.get("partitions"), "replay partition evidence changed"
    )
    _require(
        initial.get("content_hash") == replay.get("content_hash"), "replay content hash changed"
    )
    evidence: dict[str, Any] = {
        "manifest_version": "2.0.0",
        "evidence_class": evidence_class,
        "run_id": run_id,
        "status": "closed",
        "pagination_exhausted": True,
        "reconciled": True,
        "idempotency_replay_verified": True,
        "no_raw_content_stored": True,
        "configuration": frozen.model_dump(),
        "configuration_hash": evidence_digest(frozen.model_dump()),
        "initial_reconciliation_hash": evidence_digest(initial),
        "replay_reconciliation_hash": evidence_digest(replay),
        **{
            key: initial.get(key)
            for key in (
                "folder_count",
                "page_count",
                "candidate_count",
                "content_hash",
                "partitions",
            )
        },
    }
    for snapshot in (initial, replay):
        raw_facts = snapshot.get("facts")
        _require(isinstance(raw_facts, list), "reconciliation facts must be an array")
        facts = cast("list[dict[str, object]]", raw_facts)
        snapshot_evidence: dict[str, object] = {
            **evidence,
            **{
                key: snapshot.get(key)
                for key in (
                    "folder_count",
                    "page_count",
                    "candidate_count",
                    "content_hash",
                    "partitions",
                )
            },
        }
        validate_bound_evidence(facts, snapshot_evidence)
    return evidence
