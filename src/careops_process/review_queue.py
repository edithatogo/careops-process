# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Versioned human review for discovered process families."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from careops_process.landscape import ProcessLandscape


class ReviewDecision(StrEnum):
    """Permitted owner-review outcomes."""

    ACCEPT = "accept"
    REJECT = "reject"
    MERGE = "merge"
    SPLIT = "split"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """Privacy-minimized review state for one discovered family."""

    family_id: str
    evidence_reference: str
    confidence: float
    source_dependence: float
    status: str = "pending"
    decision: ReviewDecision | None = None
    reviewer_id: str | None = None
    rationale_code: str | None = None
    configuration_version: str | None = None
    target_family_ids: tuple[str, ...] = ()


def build_review_queue(landscape: ProcessLandscape, *, limit: int = 100) -> tuple[ReviewItem, ...]:
    """Prioritize low-confidence and source-dependent proposals."""
    if limit < 0:
        message = "review limit cannot be negative"
        raise ValueError(message)
    ranked = sorted(
        landscape.families,
        key=lambda family: (family.confidence, -family.source_dependence, family.family_id),
    )
    return tuple(
        ReviewItem(
            family_id=family.family_id,
            evidence_reference=f"family:{family.family_id}",
            confidence=family.confidence,
            source_dependence=family.source_dependence,
        )
        for family in ranked[:limit]
    )


def record_review_decision(  # noqa: PLR0913
    item: ReviewItem,
    *,
    decision: ReviewDecision,
    reviewer_id: str,
    rationale_code: str,
    configuration_version: str,
    target_family_ids: tuple[str, ...] = (),
) -> ReviewItem:
    """Record one immutable, versioned human decision."""
    if item.status != "pending":
        message = "only pending review items can be decided"
        raise ValueError(message)
    if decision in {ReviewDecision.MERGE, ReviewDecision.SPLIT} and not target_family_ids:
        message = "merge or split decision requires a target family"
        raise ValueError(message)
    if not reviewer_id.strip() or not rationale_code.strip() or not configuration_version.strip():
        message = "reviewer, rationale, and configuration version are required"
        raise ValueError(message)
    return replace(
        item,
        status="decided",
        decision=decision,
        reviewer_id=reviewer_id,
        rationale_code=rationale_code,
        configuration_version=configuration_version,
        target_family_ids=target_family_ids,
    )
