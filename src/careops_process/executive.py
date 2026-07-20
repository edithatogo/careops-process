"""Coverage-honest executive process landscape projections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from careops_process.coverage import EvidenceClass

if TYPE_CHECKING:
    from datetime import datetime

    from careops_process.landscape import ProcessLandscape


@dataclass(frozen=True, slots=True)
class EvidenceBoundary:
    """Mandatory evidence context carried by every executive output."""

    evidence_class: EvidenceClass
    observation_start: datetime
    observation_end: datetime
    accessible_denominator: int
    included_population: int
    exclusions: tuple[str, ...]
    generated_at: datetime

    def __post_init__(self) -> None:
        """Reject inconsistent populations and observation periods."""
        if self.included_population <= 0 or self.accessible_denominator <= 0:
            message = "population values must be positive"
            raise ValueError(message)
        if self.included_population > self.accessible_denominator:
            message = "included population cannot exceed accessible population"
            raise ValueError(message)
        if self.observation_end < self.observation_start:
            message = "population observation period is reversed"
            raise ValueError(message)
        if self.generated_at.tzinfo is None:
            message = "generated_at must include a timezone"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ExecutiveFamily:
    """Privacy-screened family card for executive interpretation."""

    family_id: str
    member_count: int | None
    event_count: int | None
    activity_sequence: tuple[str, ...]
    confidence: float
    temporal_stability: float
    source_dependence: float
    validation_status: str
    suppressed: bool


@dataclass(frozen=True, slots=True)
class ExecutiveLandscape:
    """Executive projection with no implied tenant-wide denominator."""

    boundary: EvidenceBoundary
    families: tuple[ExecutiveFamily, ...]
    tenant_wide_coverage: None = None


@dataclass(frozen=True, slots=True)
class ImprovementCandidate:
    """A validated family handed to governed experiment design."""

    family_id: str
    status: str = "requires_governance_decision"
    auto_apply: bool = False


def build_executive_landscape(
    landscape: ProcessLandscape,
    boundary: EvidenceBoundary,
    *,
    small_cell_threshold: int = 5,
) -> ExecutiveLandscape:
    """Build a suppressed landscape without promoting unvalidated findings."""
    if boundary.evidence_class is not EvidenceClass.LIVE_CORPUS:
        message = "executive process landscapes require live_corpus evidence"
        raise ValueError(message)
    if small_cell_threshold <= 0:
        message = "small-cell threshold must be positive"
        raise ValueError(message)
    families: list[ExecutiveFamily] = []
    for family in landscape.families:
        suppressed = family.member_count < small_cell_threshold
        families.append(
            ExecutiveFamily(
                family_id=family.family_id,
                member_count=None if suppressed else family.member_count,
                event_count=None if suppressed else family.event_count,
                activity_sequence=() if suppressed else family.activity_sequence,
                confidence=family.confidence,
                temporal_stability=family.temporal_stability,
                source_dependence=family.source_dependence,
                validation_status="unvalidated",
                suppressed=suppressed,
            )
        )
    return ExecutiveLandscape(boundary=boundary, families=tuple(families))


def build_improvement_candidates(
    landscape: ExecutiveLandscape,
) -> tuple[ImprovementCandidate, ...]:
    """Hand off only validated, unsuppressed families without automation."""
    return tuple(
        ImprovementCandidate(family_id=family.family_id)
        for family in landscape.families
        if family.validation_status == "validated" and not family.suppressed
    )
