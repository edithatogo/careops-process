# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic deterministic proposal provenance and human-review transitions."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

import careops_process.credentialing_improvements as improvements
from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)
from careops_process.credentialing_assurance import RENEWAL_STAGES

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet


def _projection(*, event_suffix: str = "a") -> CredentialingProjection:
    return validate_credentialing_projection(
        {
            "source": "careops-approve",
            "facts": [
                {
                    "event_id": f"event-{case}-{index}-{event_suffix}",
                    "activity": activity,
                    "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
                    "source_system": "synthetic",
                    "object_ids": [f"case-{case}"],
                    "observed_or_inferred": "observed",
                    "confidence": 1.0,
                    "qualifiers": {
                        "pathway_code": "routine-renewal",
                        "authority_mapping_version": "synthetic-v1",
                    },
                }
                for case in range(2)
                for index, activity in enumerate(RENEWAL_STAGES)
            ],
        }
    )


def _propose(
    projection: CredentialingProjection | None = None,
    *,
    threshold: object = 0.5,
    cases: AbstractSet[str] = frozenset({"case-0", "case-1"}),
    version: str = "policy-v1",
) -> tuple[improvements.ImprovementProposal, ...]:
    return improvements.propose_stage_improvements(
        projection or _projection(),
        role="report_reader",
        case_ids=cases,
        minimum_cases=2,
        authority_version="synthetic-v1",
        threshold_hours=threshold,
        threshold_version=version,
    )


def _review(proposal: improvements.ImprovementProposal) -> improvements.ImprovementProposal:
    return improvements.review_proposal(
        proposal,
        decision="accepted",
        reviewer_reference="reviewer-opaque",
        reviewer_role="process_owner",
        decided_at_utc=datetime(2026, 6, 1, tzinfo=UTC),
        current_evidence_digest=proposal.evidence_digest,
    )


def test_proposals_are_deterministic_breach_candidates_with_no_source_ids() -> None:
    """Only genuine p95 breaches emit controlled investigation hypotheses."""
    proposals = _propose()
    assert proposals == _propose()
    assert proposals
    first = proposals[0]
    assert first.measured_p95_hours > first.threshold_hours
    assert first.investigation_code == "investigate_stage_delay"
    assert first.review is None
    exported = json.dumps(asdict(first), default=str)
    assert "case-0" not in exported
    assert "event-0" not in exported
    assert "2026-01-01" not in exported
    assert _propose(threshold=1_000.0) == ()


def test_provenance_replacement_with_identical_aggregates_changes_proposal_id() -> None:
    """Replacing observed evidence invalidates review even when quantiles stay equal."""
    first = _propose()[0]
    changed = _propose(_projection(event_suffix="b"))[0]
    assert first.measured_p95_hours == changed.measured_p95_hours
    assert first.evidence_digest != changed.evidence_digest
    assert first.proposal_id != changed.proposal_id
    assert _propose(threshold=0.25)[0].proposal_id != first.proposal_id
    assert _propose(version="policy-v2")[0].proposal_id != first.proposal_id
    assert _propose(threshold=0.25)[0].evidence_digest != first.evidence_digest
    assert _propose(version="policy-v2")[0].evidence_digest != first.evidence_digest


def test_suppressed_or_empty_populations_emit_no_proposals() -> None:
    """Whole-report privacy cannot be bypassed through a hypothesis endpoint."""
    assert _propose(cases=frozenset()) == ()
    assert _propose(cases={"case-0"}) == ()


@pytest.mark.parametrize("threshold", [True, "1", 0, -1, float("inf"), float("nan")])
def test_invalid_thresholds_fail_closed(threshold: object) -> None:
    """Policy thresholds require finite positive numeric hours without coercion."""
    with pytest.raises(CredentialingContractError):
        _propose(threshold=threshold)


@pytest.mark.parametrize("decision", ["accepted", "rejected", "needs_more_evidence"])
def test_review_records_a_single_measurement_only_decision(decision: str) -> None:
    """All allowed decisions preserve immutable evidence and confer no live authority."""
    proposal = _propose()[0]
    reviewed = improvements.review_proposal(
        proposal,
        decision=decision,
        reviewer_reference="reviewer-opaque",
        reviewer_role="assurance_reviewer",
        decided_at_utc=datetime(2026, 6, 1, tzinfo=UTC),
        current_evidence_digest=proposal.evidence_digest,
    )
    assert proposal.review is None
    assert reviewed.review is not None
    assert reviewed.review.decision == decision
    assert reviewed.proposal_id == proposal.proposal_id
    assert reviewed.review.scope == "measurement_review_only"
    with pytest.raises(CredentialingContractError):
        _review(reviewed)


@pytest.mark.parametrize("gap", ["role", "reference", "time", "decision", "stale"])
def test_unsafe_or_stale_review_is_rejected(gap: str) -> None:
    """Access, controlled references, aware time and unchanged evidence are mandatory."""
    proposal = _propose()[0]
    with pytest.raises(CredentialingContractError):
        improvements.review_proposal(
            proposal,
            decision="approve_case" if gap == "decision" else "accepted",
            reviewer_reference="person@example.invalid" if gap == "reference" else "opaque",
            reviewer_role="report_reader" if gap == "role" else "process_owner",
            decided_at_utc=datetime(2026, 6, 1, tzinfo=UTC).replace(tzinfo=None)
            if gap == "time"
            else datetime(2026, 6, 1, tzinfo=UTC),
            current_evidence_digest="0" * 64 if gap == "stale" else proposal.evidence_digest,
        )


def test_tampered_proposal_is_revalidated_at_review_boundary() -> None:
    """Bypassed frozen fields cannot change the measured evidence being reviewed."""
    proposal = _propose()[0]
    object.__setattr__(proposal, "measured_p95_hours", 999.0)
    with pytest.raises(CredentialingContractError):
        _review(proposal)


def test_semantically_equal_fact_order_preserves_evidence_identity() -> None:
    """Input row ordering does not create a new hypothesis or reset human review."""
    projection = _projection()
    reordered = validate_credentialing_projection(
        {
            **projection.model_dump(mode="python"),
            "facts": list(reversed(projection.facts)),
        }
    )
    assert _propose(projection) == _propose(reordered)


def test_changed_content_cannot_reuse_proposal_identity() -> None:
    """Ordinary frozen-record replacement also validates identity consistency."""
    with pytest.raises(CredentialingContractError):
        replace(_propose()[0], threshold_hours=0.25)


def test_review_record_cannot_change_scope_or_evidence() -> None:
    """Retained review records cannot be repurposed as operational authority."""
    proposal = _review(_propose()[0])
    assert proposal.review is not None
    with pytest.raises(CredentialingContractError):
        replace(proposal.review, scope="clinical_approval")
    with pytest.raises(CredentialingContractError):
        replace(proposal, review=replace(proposal.review, evidence_digest="0" * 64))
    with pytest.raises(CredentialingContractError):
        replace(proposal, rule_version="unknown")
    with pytest.raises(CredentialingContractError):
        replace(proposal, evidence_digest="not-a-digest")


def test_ungranted_and_inferred_facts_do_not_change_proposal_identity() -> None:
    """Only granted observed evidence contributes to the provenance fingerprint."""
    projection = _projection()
    unrelated = projection.facts[0].model_dump(mode="python")
    unrelated.update(event_id="ungranted", object_ids=["outside"])
    inferred = projection.facts[0].model_dump(mode="python")
    inferred.update(event_id="inferred", observed_or_inferred="inferred", confidence=0.4)
    extended = validate_credentialing_projection(
        {
            **projection.model_dump(mode="python"),
            "facts": [*projection.facts, unrelated, inferred],
        }
    )
    assert _propose(projection) == _propose(extended)
