# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Deterministic, lineage-preserving report assembly for closed runs."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .backfill_run import run_authorised_closed_backfill, run_closed_backfill
from .landscape import discover_process_landscape


def build_closed_run_report(
    facts: list[dict[str, object]],
    evidence: dict[str, Any],
    *,
    pseudonym_secret: str,
    generated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build OCEL, family, projection, and evidence summaries from one closed run."""
    result = run_closed_backfill(
        facts,
        evidence,
        pseudonym_secret=pseudonym_secret,
        generated_at_utc=generated_at_utc,
    )
    landscape = discover_process_landscape(result.log)
    generated = (generated_at_utc or datetime.now(UTC)).astimezone(UTC).isoformat()
    return {
        "report_version": "1.0.0",
        "run_id": result.log.log_id,
        "generated_at_utc": generated,
        "lineage": result.log.lineage,
        "evidence": {
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
    result = run_authorised_closed_backfill(
        facts,
        evidence,
        pilot_entry,
        pseudonym_secret=pseudonym_secret,
        generated_at_utc=generated_at_utc,
    )
    landscape = discover_process_landscape(result.log)
    generated = (generated_at_utc or datetime.now(UTC)).astimezone(UTC).isoformat()
    return {
        "report_version": "1.0.0",
        "run_id": result.log.log_id,
        "generated_at_utc": generated,
        "lineage": result.log.lineage,
        "evidence": {
            key: evidence[key]
            for key in (
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
