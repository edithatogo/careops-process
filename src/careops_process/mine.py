"""Small, deterministic conformance primitives with an optional PM4Py seam."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class ConformanceResult:
    """Explainable conformance metrics for a sequence of activities."""

    fitness: float
    precision: float
    observed_variants: tuple[tuple[str, ...], ...]
    deviations: tuple[str, ...]


def discover_variants(traces: Sequence[Sequence[str]]) -> list[tuple[tuple[str, ...], int]]:
    """Return deterministic trace variants ordered by frequency then identity."""
    counts = Counter(tuple(trace) for trace in traces if trace)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def conformance(traces: Sequence[Sequence[str]], *, reference: Sequence[str]) -> ConformanceResult:
    """Compare traces to a reference path without mutating event facts."""
    if not reference:
        message = "reference must not be empty"
        raise ValueError(message)
    if not traces:
        message = "traces must not be empty"
        raise ValueError(message)
    reference_tuple = tuple(reference)
    deviations: list[str] = []
    matched = 0
    total = 0
    for trace in traces:
        trace_tuple = tuple(trace)
        total += max(len(trace_tuple), len(reference_tuple))
        matched += sum(
            left == right for left, right in zip(trace_tuple, reference_tuple, strict=False)
        )
        if trace_tuple != reference_tuple:
            deviations.append(" -> ".join(trace_tuple) or "empty trace")
    fitness = matched / total if total else 0.0
    variants = tuple(variant for variant, _count in discover_variants(traces))
    reference_activities = set(reference_tuple)
    observed_activities = {activity for trace in traces for activity in trace}
    precision = (
        len(reference_activities & observed_activities) / len(observed_activities)
        if observed_activities
        else 0.0
    )
    return ConformanceResult(fitness, precision, variants, tuple(deviations))
