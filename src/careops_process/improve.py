# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Semantic process-health metrics and bounded improvement recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class ActivityMetric:
    """Aggregated activity metric suitable for a semantic model."""

    activity: str
    count: int
    mean_duration_hours: float
    deviation_rate: float


@dataclass(frozen=True, slots=True)
class ImprovementAction:
    """An explainable, human-reviewable improvement recommendation."""

    activity: str
    priority: str
    rationale: str


def recommend_improvements(
    metrics: Sequence[ActivityMetric], *, duration_limit_hours: float, deviation_limit: float
) -> list[ImprovementAction]:
    """Rank activities exceeding agreed guardrails; never auto-change workflows."""
    if duration_limit_hours <= 0 or not 0 <= deviation_limit <= 1:
        message = "improvement guardrails are invalid"
        raise ValueError(message)
    actions: list[ImprovementAction] = []
    for metric in metrics:
        duration_breach = metric.mean_duration_hours > duration_limit_hours
        deviation_breach = metric.deviation_rate > deviation_limit
        if duration_breach or deviation_breach:
            priority = "high" if duration_breach and deviation_breach else "medium"
            reasons: list[str] = []
            if duration_breach:
                reasons.append("duration")
            if deviation_breach:
                reasons.append("deviation")
            actions.append(
                ImprovementAction(
                    metric.activity, priority, f"Guardrail breach: {', '.join(reasons)}"
                )
            )
    return sorted(actions, key=lambda action: (action.priority != "high", action.activity))
