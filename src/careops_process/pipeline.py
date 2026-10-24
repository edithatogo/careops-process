# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Execute the governed synthetic-to-semantic process-mining pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .discover import DiscoveryFamily, DiscoveryItem, discover_families
from .ingest import facts_to_ocel
from .mine import ConformanceResult, conformance
from .projection import build_projection

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from .ocel import OcelLog


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Auditable outputs produced by one bounded ingestion-and-mining run."""

    log: OcelLog
    families: tuple[DiscoveryFamily, ...]
    projection: dict[str, object]
    conformance: ConformanceResult | None


def run_pipeline(  # noqa: PLR0913
    facts: Sequence[Mapping[str, object]],
    *,
    log_id: str,
    schema_version: str,
    pseudonym_secret: str,
    generated_at_utc: datetime,
    reference: Sequence[str] | None = None,
    minimum_cohort_size: int = 5,
) -> PipelineResult:
    """Run ingestion, family discovery, conformance, and projection.

    The function accepts only the minimized fact boundary used by the live
    pilot contract. It never exposes source content and returns all outputs in
    one immutable result suitable for a test, CI job, or approved connector.
    """
    log = facts_to_ocel(
        facts,
        log_id=log_id,
        schema_version=schema_version,
        pseudonym_secret=pseudonym_secret,
    )
    object_ids = [item.object_id for item in log.objects]
    items_by_object: dict[str, list[str]] = {object_id: [] for object_id in object_ids}
    sources_by_object: dict[str, str] = {}
    traces_by_object: dict[str, list[tuple[datetime, str]]] = {
        object_id: [] for object_id in items_by_object
    }
    for event in log.events:
        for object_id in event.object_ids:
            items_by_object[object_id].append(event.event_type)
            sources_by_object.setdefault(object_id, event.source_system)
            traces_by_object[object_id].append((event.timestamp_utc, event.event_type))
    discovery_items = [
        DiscoveryItem(object_id, tuple(labels), sources_by_object[object_id])
        for object_id, labels in sorted(items_by_object.items())
    ]
    families = tuple(discover_families(discovery_items))
    traces = [
        [activity for _timestamp, activity in sorted(items)]
        for items in traces_by_object.values()
        if items
    ]
    result_conformance = conformance(traces, reference=reference) if reference is not None else None
    projection = build_projection(
        log,
        families=list(families),
        generated_at_utc=generated_at_utc,
        minimum_cohort_size=minimum_cohort_size,
    )
    return PipelineResult(log, families, projection, result_conformance)
