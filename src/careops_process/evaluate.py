# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Leakage-safe evaluation and lightweight drift/novelty metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class DriftReport:
    """Distribution drift report over minimized labels."""

    divergence: float
    novel_labels: tuple[str, ...]
    drifted: bool


def temporal_split[T](
    items: Sequence[T], *, train_fraction: float = 0.8
) -> tuple[list[T], list[T]]:
    """Split already time-ordered items without random leakage."""
    if not 0.0 < train_fraction < 1.0:
        message = "train_fraction must be in (0, 1)"
        raise ValueError(message)
    cut = max(1, min(len(items) - 1, round(len(items) * train_fraction))) if len(items) > 1 else 0
    return list(items[:cut]), list(items[cut:])


def label_drift(
    baseline: Sequence[str], current: Sequence[str], *, threshold: float = 0.2
) -> DriftReport:
    """Calculate symmetric Jensen-Shannon divergence and novelty."""
    if not baseline or not current:
        message = "baseline and current labels must not be empty"
        raise ValueError(message)
    if threshold < 0:
        message = "threshold must not be negative"
        raise ValueError(message)
    left, right = Counter(baseline), Counter(current)
    labels = set(left) | set(right)
    left_total, right_total = len(baseline), len(current)
    divergence = 0.0
    for label in labels:
        p = left[label] / left_total
        q = right[label] / right_total
        midpoint = (p + q) / 2
        if p:
            divergence += 0.5 * p * log(p / midpoint)
        if q:
            divergence += 0.5 * q * log(q / midpoint)
    novel = tuple(sorted(set(current) - set(baseline)))
    return DriftReport(divergence, novel, divergence > threshold or bool(novel))
