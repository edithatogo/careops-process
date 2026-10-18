# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Run disconnected synthetic acceptance; output aggregates, never source/policy approval.

Run from the repository: uv run --no-sync python examples/credentialing_acceptance.py
All definitions, grants, attestations and reviewer decisions below are FIXTURES.
Measurement populations are independent; no person-to-case linkage is inferred.
"""

# Fixture splits are explicit arithmetic inputs, not production policy defaults.
# ruff: noqa: PLR2004

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast

import careops_process.credentialing_capacity_evidence as capacity
import careops_process.credentialing_experience as experience
import careops_process.credentialing_observations as observations
import careops_process.credentialing_renewal_quality as renewal
import careops_process.credentialing_review_quality as reviews
import careops_process.credentialing_submission_quality as submission
import careops_process.credentialing_temporary_quality as temporary
from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)
from careops_process.credentialing_assurance import (
    RENEWAL_STAGES,
    CredentialingLedger,
    InferenceRun,
    assess_routine_renewal,
    project_credentialing_report,
)
from careops_process.credentialing_improvements import propose_stage_improvements, review_proposal
from careops_process.credentialing_measurements import report_stage_times
from careops_process.credentialing_pathways import PathwayReference, assess_pathway
from careops_process.ontology import assert_compatible_versions, validate_terms

if TYPE_CHECKING:
    from careops_process.credentialing_improvements import ImprovementProposal

_START = datetime(2026, 1, 2, tzinfo=UTC)
_END = _START + timedelta(days=1)
_AUTHORITY = "synthetic-v1"
_CASE_COUNT = 8
_FLOOR = 2


def _cases(prefix: str = "case") -> tuple[str, ...]:
    return tuple(f"synthetic-{prefix}-{index}" for index in range(_CASE_COUNT))


def _released[T](value: T | None) -> T:
    if value is None:
        message = "Synthetic acceptance fixture was unexpectedly suppressed"
        raise RuntimeError(message)
    return value


def _projection(*, inferred: bool = True) -> CredentialingProjection:
    facts: list[dict[str, object]] = []
    for case in _cases():
        for index, activity in enumerate(RENEWAL_STAGES):
            facts.append(
                {
                    "event_id": f"event-{case}-{index}",
                    "activity": activity,
                    "timestamp_utc": _START + timedelta(hours=index),
                    "source_system": "synthetic",
                    "object_ids": [case],
                    "observed_or_inferred": "observed",
                    "confidence": 1.0,
                    "qualifiers": {
                        "pathway_code": "routine-renewal",
                        "authority_mapping_version": _AUTHORITY,
                    },
                }
            )
        if inferred:
            facts.append(
                {
                    "event_id": f"inferred-{case}",
                    "activity": "application_ready",
                    "timestamp_utc": _START + timedelta(hours=2),
                    "source_system": "synthetic",
                    "object_ids": [case],
                    "observed_or_inferred": "inferred",
                    "confidence": 0.8,
                    "qualifiers": {
                        "pathway_code": "routine-renewal",
                        "authority_mapping_version": _AUTHORITY,
                    },
                }
            )
    return validate_credentialing_projection({"source": "careops-approve", "facts": facts})


def _separate_models() -> int:
    models = {
        "changed-scope": (
            "request_received",
            "professional_review_completed",
            "delegated_decision_recorded",
            "case_completed",
        ),
        "mutual-recognition": (
            "request_received",
            "application_ready",
            "delegated_decision_recorded",
            "case_completed",
        ),
        "temporary-approval": (
            "temporary_approval_started",
            "temporary_approval_expired",
            "case_completed",
        ),
        "conditions-supervision": (
            "condition_applied",
            "supervision_plan_started",
            "case_completed",
        ),
        "review-appeal": (
            "review_commenced",
            "appeal_lodged",
            "review_or_appeal_decided",
            "case_completed",
        ),
        "register-reconciliation": (
            "register_activation_requested",
            "register_activated",
            "case_completed",
        ),
    }
    matches = 0
    for pathway, stages in models.items():
        reference = PathwayReference(
            reference_id=f"synthetic-{pathway}",
            version="0.1.0",
            pathway_code=pathway,
            authority_mapping_version=_AUTHORITY,
            source_reference="synthetic-source",
            required_stages=stages,
            permitted_activities=stages,
            terminal_activities=("case_completed",),
        )
        projection = validate_credentialing_projection(
            {
                "source": "careops-approve",
                "facts": [
                    {
                        "event_id": f"synthetic-{index}",
                        "activity": activity,
                        "timestamp_utc": _START + timedelta(hours=index),
                        "source_system": "synthetic",
                        "object_ids": ["synthetic-independent-case"],
                        "observed_or_inferred": "observed",
                        "confidence": 1.0,
                        "qualifiers": {
                            "pathway_code": pathway,
                            "authority_mapping_version": _AUTHORITY,
                        },
                    }
                    for index, activity in enumerate(stages)
                ],
            }
        )
        result = assess_pathway(
            projection,
            reference,
            case_id="synthetic-independent-case",
            role="case_analyst",
            granted_case_ids=frozenset({"synthetic-independent-case"}),
        )
        matches += result.status == "matches_reference"
    return matches


def _proposals(
    projection: CredentialingProjection, cases: frozenset[str]
) -> tuple[ImprovementProposal, ...]:
    return propose_stage_improvements(
        projection,
        role="report_reader",
        case_ids=cases,
        minimum_cases=_FLOOR,
        authority_version=_AUTHORITY,
        threshold_hours=0.5,
        threshold_version="synthetic-threshold-v1",
    )


def _process_pack() -> dict[str, object]:
    projection = _projection()
    cases = frozenset(_cases())
    run = InferenceRun(
        run_id="synthetic-run",
        provider="synthetic",
        model="synthetic",
        agent_version="synthetic-v1",
    )
    ledger = CredentialingLedger(
        projection,
        inference_provenance={
            fact.event_id: run
            for fact in projection.facts
            if fact.observed_or_inferred == "inferred"
        },
    )
    ledger.merge(projection)
    after_replay = len(ledger.projection.facts)
    counts = cast(
        "dict[str, object]",
        _released(
            project_credentialing_report(
                ledger.projection,
                role="report_reader",
                case_ids=set(cases),
                minimum_cases=_FLOOR,
            )["metrics"]
        ),
    )
    matches = sum(
        assess_routine_renewal(ledger.projection, case, authority_version=_AUTHORITY).status
        == "matches_reference"
        for case in cases
    )
    times = report_stage_times(
        ledger.projection,
        role="report_reader",
        case_ids=cases,
        minimum_cases=_FLOOR,
        authority_version=_AUTHORITY,
    )
    intervals = {measure.interval_id: measure for measure in _released(times.measures)}
    candidates = _proposals(ledger.projection, cases)
    # Recompute current authoritative fixture evidence, rather than trust a retained client digest.
    current = _proposals(ledger.projection, cases)[0]
    reviewed = review_proposal(
        candidates[0],
        decision="accepted",
        reviewer_reference="synthetic-reviewer",
        reviewer_role="process_owner",
        decided_at_utc=_END,
        current_evidence_digest=current.evidence_digest,
    )
    review = _released(reviewed.review)
    one_case = frozenset({_cases()[0]})
    rare = report_stage_times(
        ledger.projection,
        role="report_reader",
        case_ids=one_case,
        minimum_cases=_FLOOR,
        authority_version=_AUTHORITY,
    )
    raw_rejected = False
    try:
        validate_credentialing_projection(
            {"source": "careops-approve", "facts": [], "body": "prohibited"}
        )
    except CredentialingContractError:
        raw_rejected = True
    ledger.reject("synthetic-invalid", "schema", recorded_at_utc=_START)
    ledger.tombstone(f"event-{_cases()[0]}-12")
    ledger.merge(projection)
    deleted_times = report_stage_times(
        ledger.projection,
        role="report_reader",
        case_ids=cases,
        minimum_cases=_FLOOR,
        authority_version=_AUTHORITY,
    )
    return {
        "events": {
            "observed": counts["observed_event_count"],
            "inferred": counts["inferred_event_count"],
            "after_replay": after_replay,
            "after_tombstone_replay": len(ledger.projection.facts),
            "dead_letter_count": len(ledger.dead_letters),
            "raw_field_rejected": raw_rejected,
            "post_delete_timing_suppressed": deleted_times.suppressed,
        },
        "conformance": {
            "routine_matches": matches,
            "separate_reference_models_match": _separate_models(),
        },
        "timing": {
            "request_to_completion_p95_hours": intervals[
                "request_received__case_completed"
            ].p95_hours,
            "decision_to_register_p95_hours": intervals[
                "delegated_decision_recorded__register_activated"
            ].p95_hours,
        },
        "human_review": {
            "candidate_count": len(candidates),
            "decision": review.decision,
            "scope": review.scope,
        },
        "privacy": {
            "single_case_timing_suppressed": rare.suppressed,
            "single_case_proposal_count": len(_proposals(projection, one_case)),
        },
    }


def _work(minutes: int, *, baseline: bool = False) -> tuple[observations.WorkObservation, ...]:
    return tuple(
        observations.WorkObservation(
            observation_id=f"synthetic-work-{case}",
            case_id=case,
            source_system="synthetic",
            recorded_at_utc=_START - timedelta(days=1) if baseline else _START,
            manual_touch_count=2,
            active_work_minutes=minutes,
            effort_complete=True,
        )
        for case in _cases()
    )


def _window(*, baseline: bool = False) -> observations.MeasurementWindow:
    return observations.MeasurementWindow(
        start_utc=_START - timedelta(days=1) if baseline else _START,
        end_utc=_START if baseline else _END,
        source_mapping_version="synthetic-mapping-v1",
        cohort_definition_version="synthetic-cohort-v1",
        source_complete=True,
    )


def _work_quality() -> dict[str, object]:
    cases = frozenset(_cases())
    effort = _released(
        observations.report_effort(
            _work(20), role="report_reader", case_ids=cases, minimum_cases=_FLOOR
        ).metrics
    )
    difference = observations.compare_effort(
        _work(30, baseline=True),
        _work(20),
        baseline_window=_window(baseline=True),
        current_window=_window(),
        baseline_case_ids=cases,
        current_case_ids=cases,
        role="report_reader",
        minimum_cases=_FLOOR,
    )
    quality = _released(
        observations.report_quality(
            tuple(
                observations.EvaluationObservation(
                    observation_id=f"synthetic-evaluation-{case}",
                    case_id=case,
                    source_system="synthetic",
                    recorded_at_utc=_START,
                    alert_raised=index < 4,
                    requirement_present=index % 4 < 2,
                    evaluation_reference_version="synthetic-evaluation-v1",
                )
                for index, case in enumerate(_cases())
            ),
            role="report_reader",
            case_ids=cases,
            minimum_cases=_FLOOR,
            reference_version="synthetic-evaluation-v1",
        ).metrics
    )
    return {
        "workload": {
            "manual_touches": effort.total_manual_touches,
            "active_minutes": effort.total_active_work_minutes,
            "observed_minutes_per_case_difference": difference.observed_minutes_per_case_difference,
        },
        "quality": {
            "false_positive_rate": quality.false_positive_rate,
            "false_negative_rate": quality.false_negative_rate,
        },
    }


def _submission_renewal() -> dict[str, object]:
    cases = frozenset(_cases("submission"))
    first = submission.report_first_submission_quality(
        tuple(
            submission.FirstSubmissionObservation(
                observation_id=case,
                case_id=case,
                source_system="synthetic",
                recorded_at_utc=_START,
                assessment_definition_version="synthetic-v1",
                complete_at_first_submission=index < 4,
            )
            for index, case in enumerate(sorted(cases))
        ),
        role="report_reader",
        granted_case_ids=cases,
        assessment_definition_version="synthetic-v1",
        source_complete=True,
        minimum_case_count=_FLOOR,
    )
    due_cases = frozenset(_cases("renewal"))
    due = renewal.report_overdue_renewals(
        tuple(
            renewal.RenewalSnapshot(
                observation_id=case,
                case_id=case,
                renewal_cycle_code="synthetic-cycle",
                source_system="synthetic",
                definition_version="synthetic-v1",
                snapshot_as_of_utc=_END,
                captured_at_utc=_END,
                effective_deadline_utc=_START,
                state="completed" if index < 4 else "pending",
                completion_at_utc=_END if index < 4 else None,
                coverage_complete=True,
            )
            for index, case in enumerate(sorted(due_cases))
        ),
        policy=renewal.RenewalReportPolicy(
            definition_version="synthetic-v1",
            as_of_utc=_END,
            source_complete=True,
            minimum_case_count=_FLOOR,
        ),
        scope=renewal.RenewalReportScope(role="report_reader", granted_case_ids=due_cases),
    )
    return {
        "submission": {
            "observed_complete_rate": first.observed_complete_rate,
            "population_complete_rate": first.population_complete_rate,
        },
        "renewal": {"observed_overdue_rate": due.observed_overdue_rate},
    }


def _review_completion() -> dict[str, object]:
    cases = _cases("review")
    result = reviews.report_review_completion(
        tuple(
            reviews.ReviewObligationSnapshot(
                observation_id=case,
                obligation_id=case,
                case_id=case,
                source_system="synthetic",
                definition_version="synthetic-v1",
                review_kind="supervision_review",
                snapshot_as_of_utc=_END,
                captured_at_utc=_END,
                effective_deadline_utc=_START,
                state="completed" if index < 4 else "pending",
                completion_at_utc=_START if index < 2 else _END if index < 4 else None,
                coverage_complete=True,
            )
            for index, case in enumerate(cases)
        ),
        policy=reviews.ReviewReportPolicy(
            definition_version="synthetic-v1",
            review_kind="supervision_review",
            as_of_utc=_END,
            source_complete=True,
            minimum_case_count=_FLOOR,
        ),
        scope=reviews.ReviewReportScope(
            role="report_reader",
            granted_obligations=tuple(
                reviews.ReviewObligationGrant(obligation_id=case, case_id=case) for case in cases
            ),
        ),
    )
    return {
        "reviews": {
            "completion_rate": result.observed_completion_rate,
            "on_time_rate": result.observed_on_time_rate,
        }
    }


def _temporary() -> dict[str, object]:
    cases = _cases("temporary")
    grants = tuple(temporary.TemporaryEpisodeGrant(episode_id=case, case_id=case) for case in cases)
    snapshots = tuple(
        temporary.TemporaryEpisodeSnapshot(
            observation_id=case,
            episode_id=case,
            case_id=case,
            source_system="synthetic",
            definition_version="synthetic-v1",
            snapshot_as_of_utc=_END,
            captured_at_utc=_END,
            observed_start_utc=_START - timedelta(days=1),
            effective_expiry_utc=_START,
            state="converted" if index < 4 else "active" if index < 6 else "expired",
            conversion_at_utc=_START if index < 2 else _END if index < 4 else None,
            observed_expiry_at_utc=_START if index >= 6 else None,
            coverage_complete=True,
        )
        for index, case in enumerate(cases)
    )
    result = temporary.report_temporary_episodes(
        snapshots,
        scope=temporary.TemporaryReportScope(role="report_reader", granted_episodes=grants),
        policy=temporary.TemporaryReportPolicy(
            definition_version="synthetic-v1",
            as_of_utc=_END,
            source_complete=True,
            minimum_case_count=_FLOOR,
        ),
    )
    review_rows = tuple(
        temporary.TemporaryReviewSnapshot(
            observation_id=case,
            review_obligation_id=case,
            episode_id=case,
            case_id=case,
            source_system="synthetic",
            definition_version="synthetic-v1",
            snapshot_as_of_utc=_END,
            captured_at_utc=_END,
            effective_deadline_utc=_START,
            state="completed" if index < 4 else "pending",
            completion_at_utc=_START if index < 2 else _END if index < 4 else None,
            coverage_complete=True,
        )
        for index, case in enumerate(cases)
    )
    scope = temporary.TemporaryReviewReportScope(
        role="report_reader",
        granted_episodes=grants,
        granted_reviews=tuple(
            temporary.TemporaryReviewGrant(review_obligation_id=case, episode_id=case, case_id=case)
            for case in cases
        ),
    )
    policy = temporary.TemporaryReviewReportPolicy(
        definition_version="synthetic-v1",
        as_of_utc=_END,
        source_complete=True,
        required_review_population_complete=True,
        minimum_case_count=_FLOOR,
    )
    reviewed = temporary.report_temporary_reviews(review_rows, scope=scope, policy=policy)
    unknown = temporary.report_temporary_reviews(
        review_rows, scope=scope, policy=replace(policy, required_review_population_complete=False)
    )
    return {
        "temporary": {
            "conversion_rate": result.observed_conversion_rate,
            "conversion_by_expiry_rate": result.observed_conversion_by_expiry_rate,
            "observed_expiry_episode_count": result.expiry_transition_episode_count,
            "review_completion_rate": reviewed.observed_completion_rate,
            "review_on_time_rate": reviewed.observed_on_time_rate,
            "unknown_required_review_reason": unknown.population_rate_unavailable_reason,
        }
    }


def _experience() -> dict[str, object]:
    instrument = experience.ExperienceInstrument(
        instrument_code="synthetic-instrument",
        version="synthetic-v1",
        questions=(
            experience.ExperienceQuestion(
                question_code="synthetic-question",
                scale_kind="nominal",
                selection_mode="single_select",
                categories=("category-a", "category-b"),
            ),
        ),
    )
    cohort = experience.ExperienceCohort(
        source_system="synthetic",
        cohort_ref="synthetic-experience",
        definition_version="synthetic-v1",
        epoch_ref="synthetic-epoch",
        window_start_utc=_START,
        window_end_utc=_END,
    )
    snapshot = experience.ExperienceSnapshot(
        snapshot_ref="synthetic-snapshot",
        source_system="synthetic",
        cohort=cohort,
        instrument_code=instrument.instrument_code,
        instrument_version=instrument.version,
        instrument_digest=experience.experience_instrument_digest(instrument),
        distinct_person_aggregation_attested=True,
        invited_count=8,
        responded_count=6,
        questions=(
            experience.ExperienceQuestionCounts(
                question_code="synthetic-question",
                answered_count=4,
                category_counts=(("category-a", 2), ("category-b", 2)),
            ),
        ),
    )
    result = _released(
        experience.report_experience(
            snapshot,
            instrument,
            role="report_reader",
            granted_cohort_refs=frozenset({cohort.cohort_ref}),
            minimum_respondents=_FLOOR,
            expected_cohort=cohort,
        ).metrics
    )
    return {
        "experience": {
            "response_rate": result.response_rate,
            "item_response_rate": result.questions[0].item_response_rate,
            "item_missing_rate": result.questions[0].item_missing_rate,
        }
    }


def _capacity() -> dict[str, object]:
    definition = capacity.RedeploymentActivityDefinition(
        version="synthetic-v1",
        activities=(
            capacity.RedeploymentActivityRule(
                activity_code="support", purpose="practitioner_support"
            ),
            capacity.RedeploymentActivityRule(activity_code="other", purpose="other"),
        ),
    )
    cohort = capacity.RedeploymentCohort(
        cohort_ref="synthetic-worker-cohort",
        source_system="synthetic",
        aggregation_definition_version="synthetic-v1",
        release_epoch="synthetic-epoch",
        start_utc=_START,
        end_utc=_END,
        activity_definition_digest=capacity.activity_definition_digest(definition),
    )
    snapshot = capacity.RedeploymentSnapshot(
        snapshot_id="synthetic-snapshot",
        cohort=cohort,
        eligible_worker_count=6,
        observed_worker_count=6,
        participating_worker_count=6,
        higher_value_distinct_workers=4,
        other_distinct_workers=4,
        activities=(
            capacity.RedeploymentActivityCount(
                activity_code="support", observed_work_minutes=60, distinct_observed_workers=4
            ),
            capacity.RedeploymentActivityCount(
                activity_code="other", observed_work_minutes=40, distinct_observed_workers=4
            ),
        ),
        joint_groups=tuple(
            capacity.JointParticipationGroup(activity_codes=codes, distinct_workers=2)
            for codes in (
                frozenset({"support"}),
                frozenset({"other"}),
                frozenset({"support", "other"}),
            )
        ),
        source_complete=True,
        distinct_person_aggregation_attested=True,
        joint_counts_complete_attested=True,
        activity_time_partition_attested=True,
        purpose_union_counts_attested=True,
    )
    bundle = capacity.CapacityEvidenceBundle(
        snapshot=snapshot,
        definition=definition,
        expected_cohort=cohort,
        baseline_work=_work(30, baseline=True),
        current_work=_work(20),
        baseline_case_ids=frozenset(_cases()),
        current_case_ids=frozenset(_cases()),
        baseline_window=_window(baseline=True),
        current_window=_window(),
    )
    result = capacity.report_capacity_evidence(
        bundle,
        scope=capacity.CapacityReportScope(
            role="report_reader", granted_cohort_refs=frozenset({cohort.cohort_ref})
        ),
        policy=capacity.CapacityReportPolicy(minimum_persons=_FLOOR, minimum_cases=_FLOOR),
    )
    observed = _released(result.redeployment)
    return {
        "capacity": {
            "total_observed_minutes": observed.total_observed_minutes,
            "observed_higher_value_minutes": observed.observed_higher_value_minutes,
            "observed_minutes_per_case_difference": _released(
                result.effort
            ).observed_minutes_per_case_difference,
            "released_capacity_requirement": "partial",
        }
    }


def run_acceptance() -> dict[str, object]:
    """Exercise all named local measures using fixtures; confer no real-world acceptance."""
    registry = json.loads(
        (
            Path(__file__).resolve().parents[1] / "schemas/credentialing-ontology.registry.json"
        ).read_text(encoding="utf-8")
    )
    assert_compatible_versions(registry, expected="0.1.0")
    validate_terms(registry, object_types=["credentialing_case"], event_types=list(RENEWAL_STAGES))
    return {
        "evidence_ceiling": "synthetic_only_no_source_or_policy_acceptance",
        "ontology": {"version": "0.1.0", "registered_terms_valid": True},
        **_process_pack(),
        **_work_quality(),
        **_submission_renewal(),
        **_review_completion(),
        **_temporary(),
        **_experience(),
        **_capacity(),
    }


if __name__ == "__main__":
    print(json.dumps(run_acceptance(), sort_keys=True, indent=2))  # noqa: T201 - documented CLI output
