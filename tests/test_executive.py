"""Coverage-honest executive output tests."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from careops_process.coverage import EvidenceClass
from careops_process.executive import (
    EvidenceBoundary,
    build_executive_landscape,
    build_improvement_candidates,
)
from careops_process.landscape import ProcessFamilyMetric, ProcessLandscape


def boundary() -> EvidenceBoundary:
    """Return an explicit partial-corpus boundary."""
    return EvidenceBoundary(
        evidence_class=EvidenceClass.LIVE_CORPUS,
        observation_start=datetime(2025, 8, 11, tzinfo=UTC),
        observation_end=datetime(2026, 2, 26, tzinfo=UTC),
        accessible_denominator=28,
        included_population=28,
        exclusions=("Outlook denied", "SharePoint denied", "Teams inconclusive"),
        generated_at=datetime(2026, 7, 20, tzinfo=UTC),
    )


def landscape() -> ProcessLandscape:
    """Return one material and one small synthetic family."""
    return ProcessLandscape(
        included_event_count=38,
        included_object_count=35,
        families=(
            ProcessFamilyMetric(
                "family-1",
                30,
                35,
                1,
                ("planner_task_created",),
                0.98,
                0.51,
                1.0,
            ),
            ProcessFamilyMetric(
                "family-2",
                2,
                3,
                1,
                ("planner_task_completed",),
                0.5,
                0.5,
                1.0,
            ),
        ),
    )


def test_executive_landscape_carries_coverage_and_uncertainty() -> None:
    """Every output remains interpretable against its evidence boundary."""
    output = build_executive_landscape(landscape(), boundary(), small_cell_threshold=5)

    assert output.boundary == boundary()
    assert output.tenant_wide_coverage is None
    assert output.families[0].confidence == pytest.approx(0.98)
    assert output.families[0].source_dependence == 1.0
    assert output.families[0].validation_status == "unvalidated"


def test_small_family_is_suppressed() -> None:
    """Small cells expose no detailed sequence or exact population."""
    output = build_executive_landscape(landscape(), boundary(), small_cell_threshold=5)
    small = output.families[1]

    assert small.suppressed is True
    assert small.member_count is None
    assert small.activity_sequence == ()


def test_smoke_test_cannot_build_executive_process_landscape() -> None:
    """Connectivity evidence cannot become an executive process finding."""
    smoke = boundary().__class__(
        evidence_class=EvidenceClass.SMOKE_TEST,
        observation_start=boundary().observation_start,
        observation_end=boundary().observation_end,
        accessible_denominator=4,
        included_population=4,
        exclusions=("all other sources",),
        generated_at=boundary().generated_at,
    )
    with pytest.raises(ValueError, match="live_corpus"):
        build_executive_landscape(landscape(), smoke)


def test_invalid_boundary_fails_closed() -> None:
    """Population and time-range inconsistencies cannot be published."""
    with pytest.raises(ValueError, match="population"):
        EvidenceBoundary(
            evidence_class=EvidenceClass.LIVE_CORPUS,
            observation_start=datetime(2026, 2, 26, tzinfo=UTC),
            observation_end=datetime(2025, 8, 11, tzinfo=UTC),
            accessible_denominator=10,
            included_population=11,
            exclusions=(),
            generated_at=datetime(2026, 7, 20, tzinfo=UTC),
        )


def test_improvement_handoff_requires_validated_unsuppressed_family() -> None:
    """Analytics never changes a workflow or proposes from unvalidated output."""
    output = build_executive_landscape(landscape(), boundary(), small_cell_threshold=5)
    assert build_improvement_candidates(output) == ()

    validated = replace(
        output,
        families=(replace(output.families[0], validation_status="validated"),),
    )
    candidates = build_improvement_candidates(validated)
    assert candidates[0].status == "requires_governance_decision"
    assert candidates[0].auto_apply is False
