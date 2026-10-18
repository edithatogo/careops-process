# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Observed destination work and inferable joint-participation privacy."""

# Hand-calculated fixture numbers express measured aggregate expectations.
# ruff: noqa: PLR2004

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_capacity_evidence import (
    CapacityAttributionClaim,
    CapacityEvidenceArtifact,
    CapacityEvidenceBundle,
    CapacityReportPolicy,
    CapacityReportScope,
    CapacityReviewerContext,
    JointParticipationGroup,
    RedeploymentActivityCount,
    RedeploymentActivityDefinition,
    RedeploymentActivityRule,
    RedeploymentCohort,
    RedeploymentSnapshot,
    ResolvedCapacityEvidenceManifest,
    activity_definition_digest,
    assess_capacity_claim,
    build_capacity_evidence,
    capacity_record_payload,
    merge_redeployment_snapshots,
    parse_capacity_record,
    report_capacity_evidence,
    report_redeployment,
    summarize_capacity_evidence,
)
from careops_process.credentialing_observations import MeasurementWindow, WorkObservation

START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 2, tzinfo=UTC)


def definition() -> RedeploymentActivityDefinition:
    """Supply versioned destination classifications, not a causal assertion."""
    return RedeploymentActivityDefinition(
        version="v1",
        activities=(
            RedeploymentActivityRule(activity_code="support", purpose="practitioner_support"),
            RedeploymentActivityRule(activity_code="other", purpose="other"),
        ),
    )


def cohort() -> RedeploymentCohort:
    """Bind one source aggregate to a frozen cohort/window/definition."""
    return RedeploymentCohort(
        cohort_ref="cohort-1",
        source_system="synthetic",
        aggregation_definition_version="aggregation-v1",
        release_epoch="epoch-1",
        start_utc=START,
        end_utc=END,
        activity_definition_digest=activity_definition_digest(definition()),
    )


def snapshot(overlap: int = 2) -> RedeploymentSnapshot:
    """Three nonempty joint atoms reconcile both purpose unions and worker totals."""
    return RedeploymentSnapshot(
        snapshot_id="snapshot-1",
        cohort=cohort(),
        eligible_worker_count=4 + overlap,
        observed_worker_count=4 + overlap,
        participating_worker_count=4 + overlap,
        higher_value_distinct_workers=2 + overlap,
        other_distinct_workers=2 + overlap,
        activities=(
            RedeploymentActivityCount(
                activity_code="support",
                observed_work_minutes=60,
                distinct_observed_workers=2 + overlap,
            ),
            RedeploymentActivityCount(
                activity_code="other",
                observed_work_minutes=40,
                distinct_observed_workers=2 + overlap,
            ),
        ),
        joint_groups=(
            JointParticipationGroup(activity_codes=frozenset({"support"}), distinct_workers=2),
            JointParticipationGroup(activity_codes=frozenset({"other"}), distinct_workers=2),
            JointParticipationGroup(
                activity_codes=frozenset({"support", "other"}), distinct_workers=overlap
            ),
        ),
        source_complete=True,
        distinct_person_aggregation_attested=True,
        joint_counts_complete_attested=True,
        activity_time_partition_attested=True,
        purpose_union_counts_attested=True,
    )


def test_safe_marginals_cannot_hide_singleton_intersection() -> None:
    """Marginal3/3 and union5 reveal an overlap of1; the entire report must suppress."""
    result = report_redeployment(
        snapshot(1),
        definition(),
        role="report_reader",
        granted_cohort_refs=frozenset({"cohort-1"}),
        expected_cohort=cohort(),
        minimum_persons=2,
    )
    assert result.suppressed
    assert result.metrics is None


def test_joint_atoms_reconcile_observed_minutes_without_summing_people() -> None:
    """Two workers per atom gives six participating, not eight marginal contributors."""
    result = report_redeployment(
        snapshot(),
        definition(),
        role="report_reader",
        granted_cohort_refs=frozenset({"cohort-1"}),
        expected_cohort=cohort(),
        minimum_persons=2,
    )
    assert result.metrics is not None
    assert result.metrics.participating_worker_count == 6
    assert result.metrics.total_observed_minutes == 100
    assert result.metrics.observed_higher_value_minutes == 60


def bundle() -> CapacityEvidenceBundle:
    """Retain actual work observations rather than a client-computed comparison."""
    baseline_start = START - timedelta(days=2)
    before = tuple(
        WorkObservation(
            observation_id=f"before-{case}",
            case_id=case,
            source_system="synthetic",
            recorded_at_utc=baseline_start,
            manual_touch_count=1,
            active_work_minutes=30,
            effort_complete=True,
        )
        for case in "ab"
    )
    after = tuple(
        WorkObservation(
            observation_id=f"after-{case}",
            case_id=case,
            source_system="synthetic",
            recorded_at_utc=START,
            manual_touch_count=1,
            active_work_minutes=20,
            effort_complete=True,
        )
        for case in "ab"
    )
    return CapacityEvidenceBundle(
        snapshot=snapshot(),
        definition=definition(),
        expected_cohort=cohort(),
        baseline_work=before,
        current_work=after,
        baseline_case_ids=frozenset("ab"),
        current_case_ids=frozenset("ab"),
        baseline_window=MeasurementWindow(
            start_utc=baseline_start,
            end_utc=START,
            source_mapping_version="mapping-v1",
            cohort_definition_version="cases-v1",
            source_complete=True,
        ),
        current_window=MeasurementWindow(
            start_utc=START,
            end_utc=END,
            source_mapping_version="mapping-v1",
            cohort_definition_version="cases-v1",
            source_complete=True,
        ),
    )


def test_bundle_keeps_per_case_difference_separate_from_total_redeployment() -> None:
    """Ten minutes per case is not sixty total minutes of causally released capacity."""
    result = summarize_capacity_evidence(
        bundle(),
        scope=CapacityReportScope(
            role="report_reader", granted_cohort_refs=frozenset({"cohort-1"})
        ),
        policy=CapacityReportPolicy(minimum_persons=2, minimum_cases=2),
    )
    assert result.effort is not None
    assert result.effort.observed_minutes_per_case_difference == 10
    assert result.redeployment is not None
    assert result.redeployment.observed_higher_value_minutes == 60
    assert result.claim_status == "no_claim"


def scope() -> CapacityReportScope:
    """Supply a frozen source cohort grant resolved by a hypothetical trusted adapter."""
    return CapacityReportScope(role="report_reader", granted_cohort_refs=frozenset({"cohort-1"}))


def policy() -> CapacityReportPolicy:
    """Keep case and person floors explicit and independently enforced."""
    return CapacityReportPolicy(minimum_persons=2, minimum_cases=2)


def redeployment(value: RedeploymentSnapshot) -> Any:  # noqa: ANN401
    """Report a synthetic bound aggregate with its source activity definition."""
    return report_redeployment(
        value,
        definition(),
        role="report_reader",
        granted_cohort_refs=frozenset({"cohort-1"}),
        expected_cohort=cohort(),
        minimum_persons=2,
    )


def artifacts() -> tuple[CapacityEvidenceArtifact, ...]:
    """Use placeholder references/digests, never actual evidence of attribution."""
    return tuple(
        CapacityEvidenceArtifact(reference=kind, artifact_kind=kind, sha256="a" * 64)
        for kind in (
            "evaluation_method",
            "population_alignment",
            "evaluation_design",
            "study_results",
        )
    )


def claim(value: CapacityEvidenceBundle | None = None, **changes: Any) -> CapacityAttributionClaim:  # noqa: ANN401
    """Bind a protected claim to exact recomputed synthetic evidence."""
    bound = value or bundle()
    record = build_capacity_evidence(bound, scope=scope(), policy=policy())
    original = CapacityAttributionClaim(
        claim_id="claim-1",
        version="v1",
        evidence_digest=record.evidence_digest,
        cohort=cohort(),
        method_code="externally_defined",
        method_version="method-v1",
        claimed_attributed_redeployment_minutes=30,
        unit="minutes",
        artifacts=artifacts(),
    )
    return replace(original, **changes)


def assess(
    value: CapacityEvidenceBundle,
    statement: CapacityAttributionClaim,
    decision: str = "accepted_for_evaluation_record",
) -> Any:  # noqa: ANN401
    """Record a hypothetical trusted adapter's external judgment, not causal proof."""
    return assess_capacity_claim(
        value,
        statement,
        scope=scope(),
        policy=policy(),
        reviewer_context=CapacityReviewerContext(
            reviewer_reference="actor-opaque", reviewer_role="assurance_reviewer"
        ),
        resolved_evidence_manifest=ResolvedCapacityEvidenceManifest(artifacts=artifacts()),
        disposition=decision,
        decided_at_utc=END,
    )


@pytest.mark.parametrize(
    "decision", ["accepted_for_evaluation_record", "rejected", "needs_more_evidence"]
)
def test_external_judgment_is_recorded_without_causal_verification(decision: str) -> None:
    """No decision turns a claim or its accepted placeholder artifacts into proof."""
    value = bundle()
    statement = claim(value)
    review = assess(value, statement, decision)
    result = summarize_capacity_evidence(
        value,
        scope=scope(),
        policy=policy(),
        claim=statement,
        assessment=review,
        resolved_evidence_manifest=ResolvedCapacityEvidenceManifest(artifacts=artifacts()),
    )
    expected = (
        "human_assessed_external_judgment"
        if decision == "accepted_for_evaluation_record"
        else decision
    )
    assert result.claim_status == expected
    assert result.claimed_attributed_redeployment_minutes == 30
    assert "verified_causal_release" not in asdict(result)
    assert not {"reviewer", "evidence_digest", "claim_id", "cohort_ref"} & asdict(result).keys()


def test_unassessed_claim_stays_unverified() -> None:
    """Passing structural and arithmetic checks cannot establish attribution."""
    result = summarize_capacity_evidence(bundle(), scope=scope(), policy=policy(), claim=claim())
    assert result.claim_status == "unverified"
    assert result.claimed_attributed_redeployment_minutes == 30


def test_joint_suppression_blocks_all_combined_fields() -> None:
    """Claims and otherwise-safe case effort cannot reverse a rare worker atom."""
    value = replace(bundle(), snapshot=snapshot(1))
    result = summarize_capacity_evidence(value, scope=scope(), policy=policy(), claim=claim())
    assert result.suppressed
    assert all(item is None for name, item in asdict(result).items() if name != "suppressed")


def test_effort_suppression_blocks_destination_totals_and_claim() -> None:
    """Case privacy and distinct-worker privacy remain separate release constraints."""
    value = replace(bundle(), baseline_case_ids=frozenset("a"), current_case_ids=frozenset("a"))
    result = summarize_capacity_evidence(value, scope=scope(), policy=policy(), claim=claim())
    assert result.suppressed
    assert result.redeployment is None
    assert result.claim_status is None


@pytest.mark.parametrize(
    "flag",
    [
        "distinct_person_aggregation_attested",
        "joint_counts_complete_attested",
        "activity_time_partition_attested",
        "purpose_union_counts_attested",
    ],
)
def test_missing_required_aggregate_attestations_suppress_everything(flag: str) -> None:
    """Attestations are required source assertions, never inferred from arithmetic."""
    assert redeployment(replace(snapshot(), **{flag: False})).suppressed


def test_source_coverage_partial_observation_and_explicit_zero() -> None:
    """Missing workers remain unknown; complete observed zero work remains measured zero."""
    value = replace(snapshot(), eligible_worker_count=8)
    result = redeployment(value)
    assert result.metrics.missing_worker_count == 2
    assert result.metrics.full_cohort_mean_minutes is None
    assert result.metrics.mean_minutes_per_observed_worker == 100 / 6
    assert result.metrics.full_cohort_unavailable_reason == "missing_worker_coverage"
    assert (
        redeployment(
            replace(snapshot(), source_complete=False)
        ).metrics.full_cohort_unavailable_reason
        == "source_coverage_unconfirmed"
    )
    zero = replace(
        snapshot(),
        participating_worker_count=0,
        higher_value_distinct_workers=0,
        other_distinct_workers=0,
        activities=(
            RedeploymentActivityCount(
                activity_code="support", observed_work_minutes=0, distinct_observed_workers=0
            ),
            RedeploymentActivityCount(
                activity_code="other", observed_work_minutes=0, distinct_observed_workers=0
            ),
        ),
        joint_groups=(),
    )
    measured = redeployment(zero).metrics
    assert measured.total_observed_minutes == measured.full_cohort_mean_minutes == 0
    assert measured.observed_higher_value_share is None
    missing = redeployment(replace(zero, observed_worker_count=0)).metrics
    assert missing.mean_minutes_per_observed_worker is None
    assert missing.full_cohort_mean_minutes is None


def test_no_eligible_population_suppresses() -> None:
    """Empty aggregate cannot release a fabricated population zero."""
    zero = replace(
        snapshot(),
        eligible_worker_count=0,
        observed_worker_count=0,
        participating_worker_count=0,
        higher_value_distinct_workers=0,
        other_distinct_workers=0,
        joint_groups=(),
        activities=(
            RedeploymentActivityCount(
                activity_code="support", observed_work_minutes=0, distinct_observed_workers=0
            ),
            RedeploymentActivityCount(
                activity_code="other", observed_work_minutes=0, distinct_observed_workers=0
            ),
        ),
    )
    assert redeployment(zero).suppressed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("eligible_worker_count", True),
        ("observed_worker_count", 7),
        ("higher_value_distinct_workers", 7),
        ("source_complete", 1),
        ("contract_version", "next"),
        ("snapshot_id", "snapshot-1\n"),
    ],
)
def test_invalid_direct_snapshot_rejected(field: str, value: object) -> None:
    """Strict unit, identity and coverage boundaries apply to direct construction."""
    with pytest.raises(CredentialingContractError):
        replace(snapshot(), **{field: value})  # type: ignore[arg-type]


def test_duplicate_unknown_and_incomplete_joint_atoms_rejected() -> None:
    """Atoms cannot repeat, invent activities or disagree with complete worker totals."""
    original = snapshot()
    with pytest.raises(CredentialingContractError):
        replace(original, joint_groups=(*original.joint_groups, original.joint_groups[0]))
    with pytest.raises(CredentialingContractError):
        replace(
            original,
            joint_groups=(
                JointParticipationGroup(activity_codes=frozenset({"unknown"}), distinct_workers=6),
            ),
        )
    with pytest.raises(CredentialingContractError):
        replace(original, joint_groups=original.joint_groups[:2])


def test_contradictory_purpose_union_rejected_at_definition_binding() -> None:
    """Safe-looking source unions must exactly agree with declared joint membership."""
    with pytest.raises(CredentialingContractError):
        redeployment(replace(snapshot(), higher_value_distinct_workers=2))


def test_replay_never_sums_snapshots_or_rewrites_frozen_epoch() -> None:
    """Exact snapshot replay deduplicates; changed content/epoch binding fails."""
    original = snapshot()
    assert len(merge_redeployment_snapshots([original], [original])) == 1
    with pytest.raises(CredentialingContractError):
        merge_redeployment_snapshots([original], [replace(original, source_complete=False)])
    with pytest.raises(CredentialingContractError):
        merge_redeployment_snapshots(
            [original], [replace(original, snapshot_id="other", source_complete=False)]
        )


def test_reordering_equivalent_evidence_keeps_digest() -> None:
    """Canonical order and exact work replay cannot change evidence identity."""
    value = bundle()
    changed = replace(
        value,
        snapshot=replace(
            value.snapshot,
            activities=tuple(reversed(value.snapshot.activities)),
            joint_groups=tuple(reversed(value.snapshot.joint_groups)),
        ),
        baseline_work=tuple(reversed(value.baseline_work)) * 2,
    )
    assert (
        build_capacity_evidence(value, scope=scope(), policy=policy()).evidence_digest
        == build_capacity_evidence(changed, scope=scope(), policy=policy()).evidence_digest
    )


def test_changed_measurement_or_claim_invalidates_assessment() -> None:
    """Stale judgments cannot be applied to changed facts, thresholds or claimed quantities."""
    value = bundle()
    statement = claim(value)
    reviewed = assess(value, statement)
    changed_claim = replace(statement, claimed_attributed_redeployment_minutes=20)
    result = summarize_capacity_evidence(
        value,
        scope=scope(),
        policy=policy(),
        claim=changed_claim,
        assessment=reviewed,
        resolved_evidence_manifest=ResolvedCapacityEvidenceManifest(artifacts=artifacts()),
    )
    assert result.claim_status == "unverified"
    assert result.unavailable_reason == "stale_or_unresolved_assessment"
    changed = replace(
        value,
        current_work=tuple(replace(row, active_work_minutes=21) for row in value.current_work),
    )
    result = summarize_capacity_evidence(
        changed, scope=scope(), policy=policy(), claim=statement, assessment=reviewed
    )
    assert result.claim_status == "unavailable"
    assert result.unavailable_reason == "claim_evidence_binding_mismatch"


def test_claim_bounds_and_manifest_resolution() -> None:
    """An out-of-bounds claim or unresolved artifacts cannot acquire accepted status."""
    value = bundle()
    statement = claim(value, claimed_attributed_redeployment_minutes=61)
    result = summarize_capacity_evidence(value, scope=scope(), policy=policy(), claim=statement)
    assert result.claim_status == "unavailable"
    assert result.claimed_attributed_redeployment_minutes is None
    assert result.unavailable_reason == "claim_exceeds_same_measured_redeployment"
    with pytest.raises(CredentialingContractError):
        assess(value, statement)
    statement = claim(value)
    with pytest.raises(CredentialingContractError):
        assess_capacity_claim(
            value,
            statement,
            scope=scope(),
            policy=policy(),
            reviewer_context=CapacityReviewerContext(
                reviewer_reference="actor", reviewer_role="process_owner"
            ),
            resolved_evidence_manifest=ResolvedCapacityEvidenceManifest(artifacts=()),
            disposition="accepted_for_evaluation_record",
            decided_at_utc=END,
        )
    reviewed = assess(value, statement)
    assert (
        summarize_capacity_evidence(
            value, scope=scope(), policy=policy(), claim=statement, assessment=reviewed
        ).claim_status
        == "unverified"
    )


def test_negative_effort_difference_is_not_clipped_or_converted_to_total_minutes() -> None:
    """Increased work remains a negative per-case difference without a causal default."""
    value = replace(
        bundle(),
        current_work=tuple(replace(row, active_work_minutes=40) for row in bundle().current_work),
    )
    result = summarize_capacity_evidence(value, scope=scope(), policy=policy())
    assert result.effort is not None
    assert result.effort.observed_minutes_per_case_difference == -10
    assert result.claimed_attributed_redeployment_minutes is None


def test_incomplete_constituents_make_claim_unavailable() -> None:
    """A complete observed destination total does not fill missing source/effort coverage."""
    for changed in (
        replace(bundle(), snapshot=replace(snapshot(), source_complete=False)),
        replace(bundle(), current_window=replace(bundle().current_window, source_complete=False)),
    ):
        statement = claim(changed)
        result = summarize_capacity_evidence(
            changed, scope=scope(), policy=policy(), claim=statement
        )
        assert result.claim_status == "unavailable"
        assert result.claimed_attributed_redeployment_minutes is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("unit", "hours"),
        ("claim_kind", "verified_causal_release"),
        ("claimed_attributed_redeployment_minutes", True),
        ("evidence_digest", "a" * 64 + "\n"),
    ],
)
def test_invalid_claim_units_and_proof_flags_rejected(field: str, value: object) -> None:
    """Only explicitly scoped measured-minute claims exist; no causal verification flag."""
    with pytest.raises(CredentialingContractError):
        replace(claim(), **{field: value})


@pytest.mark.parametrize("grants", ["cohort-1", ["cohort-1"], {"cohort-1\n"}])
def test_invalid_cohort_grants_rejected(grants: Any) -> None:  # noqa: ANN401
    """Iterators/lists/string codes cannot become trusted cohort authorisation."""
    with pytest.raises(CredentialingContractError):
        CapacityReportScope(role="report_reader", granted_cohort_refs=grants)


def test_mismatched_current_window_and_grant_fail() -> None:
    """Effort case population cannot be silently aligned to another staff window."""
    with pytest.raises(CredentialingContractError):
        replace(
            bundle(),
            current_window=replace(bundle().current_window, end_utc=END + timedelta(days=1)),
        )
    with pytest.raises(CredentialingContractError):
        summarize_capacity_evidence(
            bundle(),
            scope=CapacityReportScope(
                role="report_reader", granted_cohort_refs=frozenset({"other"})
            ),
            policy=policy(),
        )


def test_wire_records_roundtrip_with_nested_reconstruction() -> None:
    """Protected definition/snapshot/claim/assessment/manifest shapes roundtrip exactly."""
    statement = claim()
    reviewed = assess(bundle(), statement)
    for value in (
        definition(),
        snapshot(),
        statement,
        reviewed,
        ResolvedCapacityEvidenceManifest(artifacts=artifacts()),
    ):
        assert parse_capacity_record(capacity_record_payload(value)) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("body", "raw"),
        ("snapshot_id", "snapshot-1\n"),
        ("source_complete", 1),
        ("kind", "unknown"),
        ("eligible_worker_count", 6.0),
    ],
)
def test_invalid_snapshot_wire_rejected(field: str, value: object) -> None:
    """Runtime wire parsing rejects raw fields and JSON integer coercion ambiguity."""
    payload = capacity_record_payload(snapshot())
    payload[field] = value
    with pytest.raises(CredentialingContractError):
        parse_capacity_record(payload)


def test_wire_joint_duplicate_codes_and_extra_nested_fields_rejected() -> None:
    """An array cannot silently collapse duplicate membership codes into a set."""
    payload = capacity_record_payload(snapshot())
    groups = payload["joint_groups"]
    assert isinstance(groups, list)
    groups[0]["activity_codes"] = ["support", "support"]
    with pytest.raises(CredentialingContractError):
        parse_capacity_record(payload)
    payload = capacity_record_payload(snapshot())
    cohort_data = payload["cohort"]
    assert isinstance(cohort_data, dict)
    cohort_data["patient_id"] = "prohibited"
    with pytest.raises(CredentialingContractError):
        parse_capacity_record(payload)


class _UncheckedSnapshot(RedeploymentSnapshot):
    """Synthetic adapter subclass that skips aggregate validation."""

    def __post_init__(self) -> None:
        """Skip validation for boundary regression."""


class _UncheckedPolicy(CapacityReportPolicy):
    """Synthetic policy subclass that skips privacy threshold checks."""

    def __post_init__(self) -> None:
        """Skip validation for boundary regression."""


def test_subclasses_and_forced_mutation_cannot_skip_nested_contracts() -> None:
    """All public boundaries rebuild concrete contracts instead of preserving subclasses."""
    value = snapshot()
    malformed = _UncheckedSnapshot(**{field: getattr(value, field) for field in asdict(value)})
    object.__setattr__(malformed, "source_complete", 1)
    with pytest.raises(CredentialingContractError):
        capacity_record_payload(malformed)
    with pytest.raises(CredentialingContractError):
        merge_redeployment_snapshots([], [malformed])
    with pytest.raises(CredentialingContractError):
        redeployment(malformed)
    invalid_policy = _UncheckedPolicy(minimum_persons=1, minimum_cases=1)
    with pytest.raises(CredentialingContractError):
        summarize_capacity_evidence(bundle(), scope=scope(), policy=invalid_policy)
    nested = snapshot()
    object.__setattr__(nested.joint_groups[0], "distinct_workers", True)
    with pytest.raises(CredentialingContractError):
        redeployment(nested)


@pytest.mark.parametrize("bad", [True, -1, 1.5, "1"])
def test_observed_minute_units_are_strict(bad: Any) -> None:  # noqa: ANN401
    """Integer minutes cannot be replaced by flags, fractional hours or negative values."""
    with pytest.raises(CredentialingContractError):
        RedeploymentActivityCount(
            activity_code="support", observed_work_minutes=bad, distinct_observed_workers=2
        )


def test_structural_definition_activity_and_joint_errors_rejected() -> None:
    """Joint membership, disjoint atoms and source definitions have explicit invariants."""
    with pytest.raises(CredentialingContractError):
        RedeploymentActivityRule(activity_code="support", purpose="automatically_higher_value")
    with pytest.raises(CredentialingContractError):
        replace(definition(), activities=(definition().activities[0],) * 2)
    with pytest.raises(CredentialingContractError):
        replace(snapshot(), activities=list(snapshot().activities))  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        RedeploymentActivityCount(
            activity_code="support", observed_work_minutes=0, distinct_observed_workers=2
        )
    with pytest.raises(CredentialingContractError):
        JointParticipationGroup(activity_codes=frozenset(), distinct_workers=2)
    with pytest.raises(CredentialingContractError):
        replace(snapshot(), activities=(snapshot().activities[0],) * 2)
    inconsistent = list(snapshot().activities)
    inconsistent[0] = replace(inconsistent[0], distinct_observed_workers=3)
    with pytest.raises(CredentialingContractError):
        replace(snapshot(), activities=tuple(inconsistent))


@pytest.mark.parametrize(
    "instant",
    [
        datetime(2026, 1, 1),  # noqa: DTZ001 - reject naive source time
        datetime.fromisoformat("0001-01-01T00:00:00+01:00"),
    ],
)
def test_source_window_invalid_or_overflow_instants_rejected(instant: datetime) -> None:
    """UTC normalisation failure must be a controlled contract error."""
    with pytest.raises(CredentialingContractError):
        replace(cohort(), start_utc=instant)


def test_invalid_cohort_window_and_definition_binding_rejected() -> None:
    """No source identity/window or activity mapping can drift under the frozen cohort."""
    with pytest.raises(CredentialingContractError):
        replace(cohort(), end_utc=START)
    with pytest.raises(CredentialingContractError):
        report_redeployment(
            snapshot(),
            definition(),
            role="case_analyst",
            granted_cohort_refs=frozenset({"cohort-1"}),
            expected_cohort=cohort(),
            minimum_persons=2,
        )
    missing_activity = replace(
        snapshot(),
        activities=(
            RedeploymentActivityCount(
                activity_code="support", observed_work_minutes=100, distinct_observed_workers=6
            ),
        ),
        joint_groups=(
            JointParticipationGroup(activity_codes=frozenset({"support"}), distinct_workers=6),
        ),
        higher_value_distinct_workers=6,
        other_distinct_workers=0,
    )
    with pytest.raises(CredentialingContractError):
        redeployment(missing_activity)


def test_frozen_epoch_cannot_change_window_under_a_new_snapshot_id() -> None:
    """Release epochs bind full source/cohort definitions instead of only snapshot IDs."""
    original = snapshot()
    changed = replace(
        original, snapshot_id="other", cohort=replace(cohort(), end_utc=END + timedelta(days=1))
    )
    with pytest.raises(CredentialingContractError):
        merge_redeployment_snapshots([original], [changed])


def test_missing_complete_joint_atoms_suppresses_and_inferable_complements_stay_safe() -> None:
    """Incomplete atom data cannot be promoted by a purpose-union attestation."""
    partial = replace(snapshot(), joint_counts_complete_attested=False, joint_groups=())
    assert redeployment(partial).suppressed
    rare_nonparticipation = replace(snapshot(), eligible_worker_count=7, observed_worker_count=7)
    assert redeployment(rare_nonparticipation).suppressed
    record = build_capacity_evidence(
        replace(bundle(), snapshot=snapshot(1)), scope=scope(), policy=policy()
    )
    assert record.suppressed
    assert record.redeployment.metrics is None
    assert record.effort.observed_minutes_per_case_difference is None


def test_retained_work_records_and_windows_are_concrete() -> None:
    """Wrong types and changed observation replay cannot enter recomputation."""
    with pytest.raises(CredentialingContractError):
        replace(bundle(), baseline_window=object())  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        replace(bundle(), baseline_work=(object(),))  # type: ignore[arg-type]
    original = bundle()
    altered = replace(original.baseline_work[0], active_work_minutes=31)
    with pytest.raises(CredentialingContractError):
        replace(original, baseline_work=(*original.baseline_work, altered))


def test_provenance_requirements_are_explicit_but_not_authentication() -> None:
    """A claim cannot omit or duplicate a role; placeholders never prove real evidence exists."""
    with pytest.raises(CredentialingContractError):
        CapacityEvidenceArtifact(
            reference="artifact", artifact_kind="causal_proof_boolean", sha256="a" * 64
        )
    with pytest.raises(CredentialingContractError):
        replace(claim(), artifacts=(artifacts()[0],) * 4)
    with pytest.raises(CredentialingContractError):
        replace(claim(), artifacts=artifacts()[:3])
    with pytest.raises(CredentialingContractError):
        CapacityReviewerContext(reviewer_reference="actor", reviewer_role="report_reader")
    review = assess(bundle(), claim())
    with pytest.raises(CredentialingContractError):
        replace(review, scope="verified_causal_release")


def test_early_or_unbound_assessments_rejected() -> None:
    """Judgments cannot predate observations or acquire meaning without their retained claim."""
    value = bundle()
    statement = claim(value)
    reviewed = assess(value, statement)
    with pytest.raises(CredentialingContractError):
        assess_capacity_claim(
            value,
            statement,
            scope=scope(),
            policy=policy(),
            reviewer_context=reviewed.reviewer,
            resolved_evidence_manifest=ResolvedCapacityEvidenceManifest(artifacts=artifacts()),
            disposition="rejected",
            decided_at_utc=START,
        )
    with pytest.raises(CredentialingContractError):
        summarize_capacity_evidence(value, scope=scope(), policy=policy(), assessment=reviewed)
    rare = replace(value, snapshot=snapshot(1))
    with pytest.raises(CredentialingContractError):
        assess(rare, claim(rare))


def test_rejection_does_not_require_missing_artifacts_to_be_fabricated() -> None:
    """An externally recorded rejection may retain incomplete resolution evidence."""
    value = bundle()
    statement = claim(value)
    manifest = ResolvedCapacityEvidenceManifest(artifacts=())
    rejected = assess_capacity_claim(
        value,
        statement,
        scope=scope(),
        policy=policy(),
        reviewer_context=CapacityReviewerContext(
            reviewer_reference="actor", reviewer_role="assurance_reviewer"
        ),
        resolved_evidence_manifest=manifest,
        disposition="rejected",
        decided_at_utc=END,
    )
    assert (
        summarize_capacity_evidence(
            value,
            scope=scope(),
            policy=policy(),
            claim=statement,
            assessment=rejected,
            resolved_evidence_manifest=manifest,
        ).claim_status
        == "rejected"
    )
    forged = replace(rejected, decision="accepted_for_evaluation_record")
    result = summarize_capacity_evidence(
        value,
        scope=scope(),
        policy=policy(),
        claim=statement,
        assessment=forged,
        resolved_evidence_manifest=manifest,
    )
    assert result.claim_status == "unverified"
    assert result.unavailable_reason == "assessment_artifact_binding_mismatch"


@pytest.mark.parametrize(
    "timestamp", ["2026-01-01T00:00:00Z\n", "2026-02-30T00:00:00Z", "9999-12-31T23:59:59-01:00"]
)
def test_wire_timestamps_are_strict_and_bounded(timestamp: str) -> None:
    """Wire dates reject terminal-newline bypass, invalid calendars and UTC overflow."""
    payload = capacity_record_payload(snapshot())
    nested = payload["cohort"]
    assert isinstance(nested, dict)
    nested["start_utc"] = timestamp
    with pytest.raises(CredentialingContractError):
        parse_capacity_record(payload)


def test_wire_nested_mapping_array_and_foreign_export_errors() -> None:
    """Every nested wire container has an exact admitted structural shape."""
    payload = capacity_record_payload(snapshot())
    payload["cohort"] = []
    with pytest.raises(CredentialingContractError):
        parse_capacity_record(payload)
    payload = capacity_record_payload(snapshot())
    payload["activities"] = {}
    with pytest.raises(CredentialingContractError):
        parse_capacity_record(payload)
    with pytest.raises(CredentialingContractError):
        capacity_record_payload(object())  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        activity_definition_digest(object())  # type: ignore[arg-type]


def test_safe_observed_cohort_never_authorises_publication_of_claimed_subset() -> None:
    """A one-minute externally claimed subset has no separate person-release evidence."""
    value = bundle()
    protected_claim = claim(value, claimed_attributed_redeployment_minutes=1)
    reviewed = assess(value, protected_claim)
    private = summarize_capacity_evidence(
        value,
        scope=scope(),
        policy=policy(),
        claim=protected_claim,
        assessment=reviewed,
        resolved_evidence_manifest=ResolvedCapacityEvidenceManifest(artifacts=artifacts()),
    )
    assert private.claimed_attributed_redeployment_minutes == 1
    assert private.claim_status == "human_assessed_external_judgment"
    public = report_capacity_evidence(value, scope=scope(), policy=policy())
    assert not public.suppressed
    assert (
        not {
            "claim_status",
            "claimed_attributed_redeployment_minutes",
            "assessment",
            "reviewer",
            "claim_id",
            "evidence_digest",
        }
        & asdict(public).keys()
    )
    assert public.redeployment is not None
    assert public.redeployment.observed_higher_value_minutes == 60


def test_public_projection_suppresses_every_field_on_rare_joint_atom() -> None:
    """The public measurement projection cannot leak the safe effort component."""
    result = report_capacity_evidence(
        replace(bundle(), snapshot=snapshot(1)), scope=scope(), policy=policy()
    )
    assert result.suppressed
    assert all(value is None for key, value in asdict(result).items() if key != "suppressed")


def test_joint_atoms_cannot_exceed_total_workers() -> None:
    """Contradictory source atom totals fail even before per-activity reconciliation."""
    value = snapshot()
    groups = (*value.joint_groups[:2], replace(value.joint_groups[2], distinct_workers=10))
    with pytest.raises(CredentialingContractError):
        replace(value, joint_groups=groups)


def test_nonobject_wire_root_has_controlled_rejection() -> None:
    """A JSON array cannot escape wire validation as an attribute error."""
    with pytest.raises(CredentialingContractError):
        parse_capacity_record([])  # type: ignore[arg-type]
