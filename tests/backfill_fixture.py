# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Sealed synthetic backfill evidence used by contract regression tests."""

import hashlib
import json
from typing import Any


def digest(value: object) -> str:
    """Hash canonical JSON with the evidence contract encoding."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def sealed_evidence(facts: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a synthetic one-folder acquisition manifest, never a live approval."""
    configuration = {
        "authorised_source_partitions": ["outlook-authorised-mailbox"],
        "observation_start": "2026-01-01T00:00:00Z",
        "observation_end": "2026-01-02T00:00:00Z",
        "destination_reference": "synthetic-store",
        "retention_policy_version": "synthetic-policy-v1",
        "mapping_version": "1.0.0",
        "inventory_hash": digest(["outlook-authorised-mailbox"]),
    }
    return {
        "run_id": "run-1",
        "status": "closed",
        "folder_count": 1,
        "page_count": 1,
        "candidate_count": 1,
        "pagination_exhausted": True,
        "reconciled": True,
        "idempotency_replay_verified": True,
        "no_raw_content_stored": True,
        "manifest_version": "2.0.0",
        "evidence_class": "synthetic",
        "configuration": configuration,
        "configuration_hash": digest(configuration),
        "content_hash": digest(facts),
        "initial_reconciliation_hash": digest({"synthetic-snapshot": "initial"}),
        "replay_reconciliation_hash": digest({"synthetic-snapshot": "replay"}),
        "partitions": [
            {
                "partition_id": "outlook-authorised-mailbox",
                "source_system": "outlook",
                "pages_read": 1,
                "candidate_count": 1,
                "acquired_count": 1,
                "duplicate_count": 0,
                "rejected_count": 0,
                "filtered_count": 0,
                "emitted_count": len(facts),
                "fact_ids": [fact["id"] for fact in facts],
                "content_hash": digest(facts),
                "next_link_exhausted": True,
            }
        ],
    }
