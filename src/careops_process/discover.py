# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Deterministic, privacy-safe process-family discovery primitives."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

TOKEN = re.compile(r"[a-z0-9]{2,}")


@dataclass(frozen=True, slots=True)
class DiscoveryItem:
    """A minimized item eligible for process-family discovery."""

    item_id: str
    activity_labels: tuple[str, ...]
    source_system: str


@dataclass(frozen=True, slots=True)
class DiscoveryFamily:
    """A stable family proposal with explainable member IDs."""

    family_id: str
    label: str
    member_ids: tuple[str, ...]
    confidence: float


def _tokens(labels: Sequence[str]) -> set[str]:
    return {token for label in labels for token in TOKEN.findall(label.lower())}


def discover_families(  # noqa: C901
    items: Sequence[DiscoveryItem], *, similarity_threshold: float = 0.5
) -> list[DiscoveryFamily]:
    """Group items by explainable token similarity without raw message text."""
    if not 0.0 < similarity_threshold <= 1.0:
        message = "similarity_threshold must be in (0, 1]"
        raise ValueError(message)
    parent = list(range(len(items)))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = root(left), root(right)
        if left_root != right_root:
            parent[right_root] = left_root

    token_sets = [_tokens(item.activity_labels) for item in items]
    for left in range(len(items)):
        for right in range(left + 1, len(items)):
            union_size = len(token_sets[left] | token_sets[right])
            similarity = (
                len(token_sets[left] & token_sets[right]) / union_size if union_size else 0.0
            )
            if similarity >= similarity_threshold:
                union(left, right)
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(items)):
        groups[root(index)].append(index)
    families: list[DiscoveryFamily] = []
    for family_number, indexes in enumerate(
        sorted(groups.values(), key=lambda group: items[group[0]].item_id), 1
    ):
        labels = sorted({label for index in indexes for label in items[index].activity_labels})
        member_ids = tuple(sorted(items[index].item_id for index in indexes))
        confidence = (
            0.25 if len(indexes) == 1 else min(1.0, 0.5 + 0.5 * (len(indexes) - 1) / len(indexes))
        )
        families.append(
            DiscoveryFamily(
                f"family-{family_number}", ", ".join(labels[:3]), member_ids, confidence
            )
        )
    return families


def active_learning_queue(families: Sequence[DiscoveryFamily], *, limit: int = 10) -> list[str]:
    """Return lowest-confidence family IDs for human review."""
    if limit < 0:
        message = "limit must not be negative"
        raise ValueError(message)
    return [
        family.family_id
        for family in sorted(families, key=lambda item: (item.confidence, item.family_id))[:limit]
    ]
