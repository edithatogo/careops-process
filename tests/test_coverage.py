# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Coverage-ledger and evidence-classification tests."""

import pytest

from careops_process.coverage import (
    EvidenceClass,
    SourcePartition,
    build_coverage_summary,
    validate_result_claim,
)


def test_coverage_summary_uses_only_accessible_known_denominators() -> None:
    """Unknown inaccessible populations never become zero-activity claims."""
    expected_approval_count = 4
    partitions = [
        SourcePartition(
            source="dataverse",
            container="approvals",
            accessible=True,
            candidate_count=expected_approval_count,
            acquired_count=expected_approval_count,
            observation_start="2026-01-01T00:00:00Z",
            observation_end="2026-07-01T00:00:00Z",
        ),
        SourcePartition(
            source="teams",
            container="IHG",
            accessible=False,
            candidate_count=None,
            acquired_count=0,
            observation_start=None,
            observation_end=None,
            limitation="Delegated API permission unavailable",
        ),
    ]

    summary = build_coverage_summary(partitions)

    assert summary.accessible_candidate_count == expected_approval_count
    assert summary.acquired_count == expected_approval_count
    assert summary.accessible_coverage == 1.0
    assert summary.unknown_population_partitions == ("teams/IHG",)
    assert summary.tenant_wide_coverage is None


@pytest.mark.parametrize(
    ("candidate_count", "acquired_count"),
    [(None, 1), (2, 3), (-1, 0), (1, -1)],
)
def test_source_partition_rejects_incoherent_counts(
    candidate_count: int | None,
    acquired_count: int,
) -> None:
    """Coverage counts cannot silently overstate successful acquisition."""
    with pytest.raises(ValueError, match="count"):
        SourcePartition(
            source="outlook",
            container="mailbox",
            accessible=True,
            candidate_count=candidate_count,
            acquired_count=acquired_count,
            observation_start="2026-01-01T00:00:00Z",
            observation_end="2026-07-01T00:00:00Z",
        )


def test_inaccessible_partition_requires_a_limitation() -> None:
    """A permission boundary must be explainable and auditable."""
    with pytest.raises(ValueError, match="limitation"):
        SourcePartition(
            source="sharepoint",
            container="site",
            accessible=False,
            candidate_count=None,
            acquired_count=0,
            observation_start=None,
            observation_end=None,
        )


def test_partition_rejects_blank_identity_and_inaccessible_acquisition() -> None:
    """Partitions need stable identities and cannot acquire inaccessible rows."""
    with pytest.raises(ValueError, match="non-empty"):
        SourcePartition(
            source=" ",
            container="mailbox",
            accessible=True,
            candidate_count=0,
            acquired_count=0,
            observation_start="2026-01-01T00:00:00Z",
            observation_end="2026-07-01T00:00:00Z",
        )
    with pytest.raises(ValueError, match="must be zero"):
        SourcePartition(
            source="teams",
            container="IHG",
            accessible=False,
            candidate_count=None,
            acquired_count=1,
            observation_start=None,
            observation_end=None,
            limitation="Permission unavailable",
        )


def test_accessible_partition_requires_observation_period() -> None:
    """A known count without its time boundary cannot support coverage."""
    with pytest.raises(ValueError, match="observation period"):
        SourcePartition(
            source="planner",
            container="plan",
            accessible=True,
            candidate_count=1,
            acquired_count=1,
            observation_start=None,
            observation_end=None,
        )


def test_smoke_test_cannot_be_labelled_as_corpus_finding() -> None:
    """Connectivity evidence is never promoted to a process finding."""
    with pytest.raises(ValueError, match="smoke_test"):
        validate_result_claim(EvidenceClass.SMOKE_TEST, "corpus_finding")


def test_live_corpus_claim_requires_population_and_period() -> None:
    """Operational findings carry their evidence boundary."""
    with pytest.raises(ValueError, match="population"):
        validate_result_claim(
            EvidenceClass.LIVE_CORPUS,
            "corpus_finding",
            included_population=0,
            observation_start="2026-01-01T00:00:00Z",
            observation_end="2026-07-01T00:00:00Z",
        )

    validate_result_claim(
        EvidenceClass.LIVE_CORPUS,
        "corpus_finding",
        included_population=100,
        observation_start="2026-01-01T00:00:00Z",
        observation_end="2026-07-01T00:00:00Z",
    )
