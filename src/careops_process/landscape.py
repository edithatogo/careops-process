# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Empirical process-family landscape over object-centric traces."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from careops_process.discover import DiscoveryItem, discover_families
from careops_process.ocel import OcelLog, validate_ocel

if TYPE_CHECKING:
    from datetime import datetime

    from careops_process.ocel import OcelEvent


@dataclass(frozen=True, slots=True)
class ProcessFamilyMetric:
    """Ranked empirical family with coverage and stability indicators."""

    family_id: str
    member_count: int
    event_count: int
    source_count: int
    activity_sequence: tuple[str, ...]
    confidence: float
    temporal_stability: float
    source_dependence: float


@dataclass(frozen=True, slots=True)
class ProcessLandscape:
    """Coverage-bounded family discovery result."""

    included_event_count: int
    included_object_count: int
    families: tuple[ProcessFamilyMetric, ...]


@dataclass(frozen=True, slots=True)
class SourceSensitivityReport:
    """Impact of excluding one or more source systems."""

    excluded_sources: tuple[str, ...]
    baseline_event_count: int
    retained_event_count: int
    event_retention_fraction: float
    baseline_family_count: int
    retained_family_count: int


@dataclass(frozen=True, slots=True)
class WindowSensitivityReport:
    """Family stability across a leakage-safe temporal boundary."""

    cutoff: datetime
    earlier_event_count: int
    later_event_count: int
    earlier_family_count: int
    later_family_count: int


@dataclass(frozen=True, slots=True)
class MappingSensitivityReport:
    """Impact of an explicit activity-vocabulary mapping."""

    mapped_event_count: int
    baseline_family_count: int
    mapped_family_count: int
    changed_event_count: int


@dataclass(frozen=True, slots=True)
class OperationalPatternSummary:
    """Object-centric sequence, hand-off, loop, ageing and closure patterns."""

    directly_follows: tuple[tuple[str, str, int], ...]
    source_handoffs: tuple[tuple[str, str, int], ...]
    repeated_activity_count: int
    object_duration_seconds: tuple[float, ...]
    incomplete_object_count: int


@dataclass(frozen=True, slots=True)
class _ObjectTrace:
    object_id: str
    activities: tuple[str, ...]
    sources: tuple[str, ...]
    event_ids: tuple[str, ...]
    timestamps: tuple[datetime, ...]


def _object_traces(log: OcelLog) -> dict[str, _ObjectTrace]:
    timed: dict[str, list[tuple[datetime, str, str, str]]] = defaultdict(list)
    for event in log.events:
        for object_id in event.object_ids:
            timed[object_id].append(
                (event.timestamp_utc, event.event_type, event.source_system, event.event_id)
            )
    return {
        object_id: _ObjectTrace(
            object_id=object_id,
            activities=tuple(item[1] for item in sorted(values)),
            sources=tuple(item[2] for item in sorted(values)),
            event_ids=tuple(item[3] for item in sorted(values)),
            timestamps=tuple(item[0] for item in sorted(values)),
        )
        for object_id, values in timed.items()
    }


def discover_process_landscape(
    log: OcelLog,
    *,
    similarity_threshold: float = 0.5,
) -> ProcessLandscape:
    """Discover and rank families from observed object traces without seeded names."""
    traces = _object_traces(log)
    items = [
        DiscoveryItem(
            item_id=trace.object_id,
            activity_labels=trace.activities,
            source_system="|".join(sorted(set(trace.sources))),
        )
        for trace in sorted(traces.values(), key=lambda item: item.object_id)
    ]
    discovered = discover_families(items, similarity_threshold=similarity_threshold)
    metrics: list[ProcessFamilyMetric] = []
    for family in discovered:
        members = [traces[member_id] for member_id in family.member_ids]
        sequences = Counter(member.activities for member in members)
        dominant_sequence, dominant_count = min(
            sequences.items(), key=lambda item: (-item[1], item[0])
        )
        event_ids = {event_id for member in members for event_id in member.event_ids}
        source_by_event = {event.event_id: event.source_system for event in log.events}
        source_counts = Counter(source_by_event[event_id] for event_id in event_ids)
        event_count = len(event_ids)
        source_dependence = max(source_counts.values()) / event_count if event_count else 0.0
        stability = dominant_count / len(members)
        metrics.append(
            ProcessFamilyMetric(
                family_id=family.family_id,
                member_count=len(members),
                event_count=event_count,
                source_count=len(source_counts),
                activity_sequence=dominant_sequence,
                confidence=family.confidence,
                temporal_stability=stability,
                source_dependence=source_dependence,
            )
        )
    metrics.sort(key=lambda item: (-item.event_count, -item.member_count, item.family_id))
    return ProcessLandscape(
        included_event_count=len(log.events),
        included_object_count=len(log.objects),
        families=tuple(metrics),
    )


def _without_sources(log: OcelLog, excluded_sources: tuple[str, ...]) -> OcelLog:
    events = [event for event in log.events if event.source_system not in excluded_sources]
    referenced = {object_id for event in events for object_id in event.object_ids}
    objects = [item for item in log.objects if item.object_id in referenced]
    relations = [
        item
        for item in log.relations
        if item.source_object_id in referenced and item.target_object_id in referenced
    ]
    return validate_ocel(
        log.model_copy(update={"events": events, "objects": objects, "relations": relations})
    )


def source_exclusion_sensitivity(
    log: OcelLog,
    *,
    excluded_sources: tuple[str, ...],
    similarity_threshold: float = 0.5,
) -> SourceSensitivityReport:
    """Measure family and event dependence on selected source systems."""
    baseline = discover_process_landscape(log, similarity_threshold=similarity_threshold)
    retained_log = _without_sources(log, excluded_sources)
    retained = discover_process_landscape(retained_log, similarity_threshold=similarity_threshold)
    baseline_count = len(log.events)
    retained_count = len(retained_log.events)
    return SourceSensitivityReport(
        excluded_sources=tuple(sorted(excluded_sources)),
        baseline_event_count=baseline_count,
        retained_event_count=retained_count,
        event_retention_fraction=retained_count / baseline_count if baseline_count else 0.0,
        baseline_family_count=len(baseline.families),
        retained_family_count=len(retained.families),
    )


def threshold_sensitivity(
    log: OcelLog,
    thresholds: tuple[float, ...],
) -> tuple[tuple[float, int], ...]:
    """Report family counts across correlation-free similarity thresholds."""
    return tuple(
        (threshold, len(discover_process_landscape(log, similarity_threshold=threshold).families))
        for threshold in thresholds
    )


def time_window_sensitivity(log: OcelLog, *, cutoff: datetime) -> WindowSensitivityReport:
    """Compare family counts before and after a fixed temporal cutoff."""
    earlier_events = [event for event in log.events if event.timestamp_utc < cutoff]
    later_events = [event for event in log.events if event.timestamp_utc >= cutoff]
    if not earlier_events or not later_events:
        message = "time-window sensitivity requires events on both sides of cutoff"
        raise ValueError(message)

    def subset(events: list[OcelEvent]) -> OcelLog:
        event_ids = {event.event_id for event in events}
        selected = [event for event in log.events if event.event_id in event_ids]
        referenced = {object_id for event in selected for object_id in event.object_ids}
        objects = [item for item in log.objects if item.object_id in referenced]
        return validate_ocel(
            log.model_copy(update={"events": selected, "objects": objects, "relations": []})
        )

    earlier = discover_process_landscape(subset(earlier_events))
    later = discover_process_landscape(subset(later_events))
    return WindowSensitivityReport(
        cutoff=cutoff,
        earlier_event_count=len(earlier_events),
        later_event_count=len(later_events),
        earlier_family_count=len(earlier.families),
        later_family_count=len(later.families),
    )


def activity_mapping_sensitivity(
    log: OcelLog,
    mapping: dict[str, str],
    *,
    similarity_threshold: float = 0.5,
) -> MappingSensitivityReport:
    """Compare family structure before and after a versionable label mapping."""
    mapped_events = [
        event.model_copy(update={"event_type": mapping.get(event.event_type, event.event_type)})
        for event in log.events
    ]
    mapped_log = validate_ocel(log.model_copy(update={"events": mapped_events}))
    baseline = discover_process_landscape(log, similarity_threshold=similarity_threshold)
    mapped = discover_process_landscape(mapped_log, similarity_threshold=similarity_threshold)
    return MappingSensitivityReport(
        mapped_event_count=len(mapped_events),
        baseline_family_count=len(baseline.families),
        mapped_family_count=len(mapped.families),
        changed_event_count=sum(event.event_type in mapping for event in log.events),
    )


def summarize_operational_patterns(log: OcelLog) -> OperationalPatternSummary:
    """Summarize empirical object traces without assigning organisational meaning."""
    traces = _object_traces(log)
    follows: Counter[tuple[str, str]] = Counter()
    handoffs: Counter[tuple[str, str]] = Counter()
    repeated = 0
    durations: list[float] = []
    incomplete = 0
    closure_suffixes = ("_completed", "_decided", "_closed")
    for trace in traces.values():
        follows.update(zip(trace.activities, trace.activities[1:], strict=False))
        handoffs.update(zip(trace.sources, trace.sources[1:], strict=False))
        repeated += sum(
            left == right
            for left, right in zip(trace.activities, trace.activities[1:], strict=False)
        )
        if len(trace.timestamps) > 1:
            durations.append((trace.timestamps[-1] - trace.timestamps[0]).total_seconds())
        if any(activity.endswith("_created") for activity in trace.activities) and not any(
            activity.endswith(closure_suffixes) for activity in trace.activities
        ):
            incomplete += 1
    return OperationalPatternSummary(
        directly_follows=tuple(
            (left, right, count) for (left, right), count in sorted(follows.items())
        ),
        source_handoffs=tuple(
            (left, right, count) for (left, right), count in sorted(handoffs.items())
        ),
        repeated_activity_count=repeated,
        object_duration_seconds=tuple(sorted(durations)),
        incomplete_object_count=incomplete,
    )
