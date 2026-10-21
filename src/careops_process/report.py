# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Deterministic, lineage-preserving report assembly for closed runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .backfill_run import run_authorised_closed_backfill, run_closed_backfill
from .correlation import evaluate_corpus_quality
from .landscape import discover_process_landscape, summarize_operational_patterns

if TYPE_CHECKING:
    from .pipeline import PipelineResult


def _run_context(result: PipelineResult, evidence: dict[str, Any]) -> dict[str, Any]:
    """Keep analytical population and uncertainty tied to the validated run."""
    partitions = evidence["partitions"]
    return {
        "coverage_ledger": {
            "run_id": result.log.log_id,
            "evidence_class": evidence["evidence_class"],
            "observation_start": evidence["configuration"]["observation_start"],
            "observation_end": evidence["configuration"]["observation_end"],
            "authorised_source_partitions": evidence["configuration"][
                "authorised_source_partitions"
            ],
            "source_candidate_count": evidence["candidate_count"],
            "source_acquired_count": sum(item["acquired_count"] for item in partitions),
            "duplicate_count": sum(item["duplicate_count"] for item in partitions),
            "rejected_count": sum(item["rejected_count"] for item in partitions),
            "filtered_count": sum(item["filtered_count"] for item in partitions),
            "included_event_count": len(result.log.events),
            "included_object_count": len(result.log.objects),
            "tenant_wide_coverage": None,
            "owner_validation_status": "pending",
            "publication_status": "restricted_analytical_review",
            "scope_limitation": "Only the frozen authorised inventory; other populations unknown",
        },
        "corpus_quality": asdict(evaluate_corpus_quality(result.log)),
        "operational_patterns": asdict(summarize_operational_patterns(result.log)),
    }


def build_closed_run_report(
    facts: list[dict[str, object]],
    evidence: dict[str, Any],
    *,
    pseudonym_secret: str,
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build OCEL, family, projection, and evidence summaries from one closed run."""
    generated_at_utc = generated_at_utc or datetime.now(UTC)
    result = run_closed_backfill(
        facts,
        evidence,
        pseudonym_secret=pseudonym_secret,
        generated_at_utc=generated_at_utc,
    )
    landscape = discover_process_landscape(result.log)
    generated = generated_at_utc.astimezone(UTC).isoformat()
    return {
        **_run_context(result, evidence),
        "report_version": "2.0.0",
        "run_id": result.log.log_id,
        "generated_at_utc": generated,
        "lineage": result.log.lineage,
        "evidence": {
            "manifest_version": evidence["manifest_version"],
            "evidence_class": evidence["evidence_class"],
            "configuration": evidence["configuration"],
            "configuration_hash": evidence["configuration_hash"],
            "content_hash": evidence["content_hash"],
            "initial_reconciliation_hash": evidence["initial_reconciliation_hash"],
            "replay_reconciliation_hash": evidence["replay_reconciliation_hash"],
            "partitions": evidence["partitions"],
            "status": evidence["status"],
            "folder_count": evidence["folder_count"],
            "page_count": evidence["page_count"],
            "candidate_count": evidence["candidate_count"],
            "pagination_exhausted": evidence["pagination_exhausted"],
            "reconciled": evidence["reconciled"],
            "idempotency_replay_verified": evidence["idempotency_replay_verified"],
            "no_raw_content_stored": evidence["no_raw_content_stored"],
        },
        "ocel": result.log.model_dump(mode="json"),
        "process_landscape": {
            "included_event_count": landscape.included_event_count,
            "included_object_count": landscape.included_object_count,
            "families": [asdict(family) for family in landscape.families],
        },
        "semantic_projection": result.projection,
    }


def build_authorised_closed_run_report(
    facts: list[dict[str, object]],
    evidence: dict[str, Any],
    pilot_entry: dict[str, Any],
    *,
    pseudonym_secret: str,
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build a report only after validating corpus pilot-entry approvals."""
    generated_at_utc = generated_at_utc or datetime.now(UTC)
    result = run_authorised_closed_backfill(
        facts,
        evidence,
        pilot_entry,
        pseudonym_secret=pseudonym_secret,
        generated_at_utc=generated_at_utc,
    )
    landscape = discover_process_landscape(result.log)
    generated = generated_at_utc.astimezone(UTC).isoformat()
    return {
        **_run_context(result, evidence),
        "report_version": "2.0.0",
        "run_id": result.log.log_id,
        "generated_at_utc": generated,
        "lineage": result.log.lineage,
        "evidence": {
            key: evidence[key]
            for key in (
                "manifest_version",
                "evidence_class",
                "configuration",
                "configuration_hash",
                "content_hash",
                "initial_reconciliation_hash",
                "replay_reconciliation_hash",
                "partitions",
                "status",
                "folder_count",
                "page_count",
                "candidate_count",
                "pagination_exhausted",
                "reconciled",
                "idempotency_replay_verified",
                "no_raw_content_stored",
            )
        },
        "ocel": result.log.model_dump(mode="json"),
        "process_landscape": {
            "included_event_count": landscape.included_event_count,
            "included_object_count": landscape.included_object_count,
            "families": [asdict(family) for family in landscape.families],
        },
        "semantic_projection": result.projection,
    }
