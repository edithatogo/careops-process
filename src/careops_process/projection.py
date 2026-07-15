"""Build a governed, privacy-safe semantic projection from a validated OCEL log."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .discover import DiscoveryFamily
    from .ocel import OcelLog


def build_projection(
    log: OcelLog,
    *,
    families: list[DiscoveryFamily],
    generated_at_utc: datetime,
    minimum_cohort_size: int = 5,
) -> dict[str, Any]:
    """Create a semantic payload with deterministic quality indicators.

    Small cohorts are represented by counts only and have their activity/family
    detail suppressed. This keeps the projection useful for governance while
    avoiding accidental disclosure through sparse slices.
    """
    if generated_at_utc.tzinfo is None:
        message = "generated_at_utc must be timezone-aware"
        raise ValueError(message)
    if minimum_cohort_size < 1:
        message = "minimum_cohort_size must be positive"
        raise ValueError(message)
    activity_counts = Counter(event.event_type for event in log.events)
    observed = sum(event.observed_or_inferred == "observed" for event in log.events)
    watermark = max(event.timestamp_utc for event in log.events).astimezone(UTC)
    suppressed = len(log.events) < minimum_cohort_size
    activities = (
        []
        if suppressed
        else [
            {
                "activity": activity,
                "count": count,
                "mean_duration_hours": 0.0,
                "deviation_rate": round(1 - observed / len(log.events), 6),
            }
            for activity, count in sorted(activity_counts.items())
        ]
    )
    family_rows = (
        []
        if suppressed
        else [
            {"family_id": family.family_id, "label": family.label, "confidence": family.confidence}
            for family in families
        ]
    )
    return {
        "schema_version": "1.0.0",
        "generated_at_utc": generated_at_utc.astimezone(UTC).isoformat(),
        "activities": activities,
        "families": family_rows,
        "quality": {
            "event_count": len(log.events),
            "object_count": len(log.objects),
            "watermark_utc": watermark.isoformat(),
            "suppressed_small_cohort": suppressed,
        },
    }
