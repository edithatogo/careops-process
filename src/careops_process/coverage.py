# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Coverage accounting and evidence-claim safeguards."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceClass(StrEnum):
    """Evidence classes with materially different permitted claims."""

    SYNTHETIC = "synthetic"
    SMOKE_TEST = "smoke_test"
    LIVE_CORPUS = "live_corpus"


@dataclass(frozen=True, slots=True)
class SourcePartition:
    """Observed acquisition boundary for one source container and period."""

    source: str
    container: str
    accessible: bool
    candidate_count: int | None
    acquired_count: int
    observation_start: str | None
    observation_end: str | None
    limitation: str | None = None

    def __post_init__(self) -> None:
        """Reject coverage states that could produce misleading totals."""
        if not self.source.strip() or not self.container.strip():
            message = "source and container must be non-empty"
            raise ValueError(message)
        if self.acquired_count < 0:
            message = "acquired count cannot be negative"
            raise ValueError(message)
        if self.candidate_count is not None and self.candidate_count < 0:
            message = "candidate count cannot be negative"
            raise ValueError(message)
        if self.accessible:
            if self.candidate_count is None:
                message = "accessible partition requires a candidate count"
                raise ValueError(message)
            if self.acquired_count > self.candidate_count:
                message = "acquired count cannot exceed candidate count"
                raise ValueError(message)
            if not self.observation_start or not self.observation_end:
                message = "accessible partition requires an observation period"
                raise ValueError(message)
        else:
            if self.acquired_count != 0:
                message = "inaccessible partition acquired count must be zero"
                raise ValueError(message)
            if not self.limitation or not self.limitation.strip():
                message = "inaccessible partition requires a limitation"
                raise ValueError(message)

    @property
    def key(self) -> str:
        """Return a stable human-readable partition key."""
        return f"{self.source}/{self.container}"


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    """Aggregate coverage without implying an unknown tenant denominator."""

    accessible_candidate_count: int
    acquired_count: int
    accessible_coverage: float | None
    unknown_population_partitions: tuple[str, ...]
    tenant_wide_coverage: None = None


def build_coverage_summary(partitions: list[SourcePartition]) -> CoverageSummary:
    """Summarize only known accessible denominators and retain unknowns."""
    accessible = [partition for partition in partitions if partition.accessible]
    candidate_count = sum(partition.candidate_count or 0 for partition in accessible)
    acquired_count = sum(partition.acquired_count for partition in accessible)
    coverage = acquired_count / candidate_count if candidate_count else None
    unknowns = tuple(sorted(partition.key for partition in partitions if not partition.accessible))
    return CoverageSummary(
        accessible_candidate_count=candidate_count,
        acquired_count=acquired_count,
        accessible_coverage=coverage,
        unknown_population_partitions=unknowns,
    )


def validate_result_claim(
    evidence_class: EvidenceClass,
    claim: str,
    *,
    included_population: int | None = None,
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> None:
    """Validate whether an evidence class can support the requested claim."""
    if claim == "corpus_finding" and evidence_class is not EvidenceClass.LIVE_CORPUS:
        message = f"{evidence_class.value} evidence cannot support a corpus_finding claim"
        raise ValueError(message)
    if claim == "corpus_finding" and (
        included_population is None
        or included_population <= 0
        or not observation_start
        or not observation_end
    ):
        message = "corpus findings require a positive included population and observation period"
        raise ValueError(message)
