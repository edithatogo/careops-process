"""Synthetic renewal, deletion and reporting boundary evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast, get_args

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from careops_process.credentialing import (
    Activity,
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
from careops_process.ontology import OntologyError, assert_compatible_versions, validate_terms

EXPECTED_TWO_CASE_EVENTS = 26
EXPECTED_RENEWAL_EVENTS = 13
GOLDEN_STAGES = (
    "request_received",
    "request_classified",
    "application_ready",
    "committee_scheduled",
    "committee_considered",
    "recommendation_recorded",
    "decision_routed_to_delegate",
    "delegated_decision_recorded",
    "decision_communicated",
    "register_activation_requested",
    "register_activated",
    "case_completed",
    "renewal_reminder_issued",
)


def renewal_payload(*, case_id: str = "case-1") -> dict[str, Any]:
    """Construct a complete observed synthetic renewal with explicit authority."""
    return {
        "source": "careops-approve",
        "facts": [
            {
                "event_id": f"{case_id}-evt-{index}",
                "activity": activity,
                "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
                "source_system": "synthetic",
                "object_ids": [case_id],
                "observed_or_inferred": "observed",
                "confidence": 1,
                "qualifiers": {
                    "pathway_code": "routine-renewal",
                    "authority_mapping_version": "synthetic-v1",
                },
            }
            for index, activity in enumerate(GOLDEN_STAGES)
        ],
    }


def test_credentialing_registry_matches_runtime_and_contract() -> None:
    """An unregistered activity or incompatible version cannot pass unnoticed."""
    registry = json.loads(Path("schemas/credentialing-ontology.registry.json").read_text())
    schema = json.loads(Path("contracts/credentialing-event-projection.json").read_text())
    assert_compatible_versions(registry, expected="0.1.0")
    assert set(registry["events"]) == set(get_args(Activity))
    assert set(registry["events"]) == set(schema["$defs"]["fact"]["properties"]["activity"]["enum"])
    validate_terms(registry, object_types=["credentialing_case"], event_types=list(RENEWAL_STAGES))
    with pytest.raises(OntologyError, match="unknown object"):
        validate_terms(registry, object_types=["unknown"], event_types=[])
    with pytest.raises(OntologyError, match="unknown event"):
        validate_terms(registry, object_types=[], event_types=["unknown"])
    with pytest.raises(OntologyError, match="incompatible"):
        assert_compatible_versions(registry)


def test_tombstones_remove_events_and_block_replay_beyond_checkpoint_capacity() -> None:
    """Deletion memory survives repeated merges and unrelated deletion traffic."""
    projection = validate_credentialing_projection(renewal_payload())
    ledger = CredentialingLedger(projection)
    deleted = projection.facts[0].event_id
    ledger.tombstone(deleted)
    for index in range(10_001):
        ledger.tombstone(f"unrelated-{index}")
    ledger.merge(projection)
    ledger.merge(projection)
    assert deleted not in {fact.event_id for fact in ledger.projection.facts}
    assert len(ledger.projection.facts) == len(RENEWAL_STAGES) - 1


def test_ledger_owns_a_detached_input_snapshot() -> None:
    """Caller mutation cannot silently change retained facts or pathway qualifiers."""
    projection = validate_credentialing_projection(renewal_payload())
    ledger = CredentialingLedger(projection)
    projection.facts[0].qualifiers.pathway_code = "caller-modified"
    projection.facts.clear()
    assert len(ledger.projection.facts) == EXPECTED_RENEWAL_EVENTS
    assert ledger.projection.facts[0].qualifiers.pathway_code == "routine-renewal"


def test_unrelated_tombstones_preserve_the_unaffected_snapshot() -> None:
    """Deletion memory grows without rebuilding unaffected data for every unrelated ID."""
    ledger = CredentialingLedger(validate_credentialing_projection(renewal_payload()))
    before = ledger.projection
    ledger.tombstone("unrelated-event")
    assert "unrelated-event" in ledger.tombstoned_event_ids
    assert ledger.projection is before


def test_restored_tombstones_are_detached_from_caller() -> None:
    """Clearing caller deletion memory cannot resurrect an event."""
    projection = validate_credentialing_projection(renewal_payload())
    deleted = projection.facts[0].event_id
    tombstones = {deleted}
    ledger = CredentialingLedger(projection, tombstoned_event_ids=tombstones)
    tombstones.clear()
    ledger.merge(projection)
    assert deleted not in {fact.event_id for fact in ledger.projection.facts}


def test_restored_provenance_is_detached_from_caller() -> None:
    """Caller map and nested run mutations cannot alter retained provenance."""
    payload = renewal_payload()
    payload["facts"][0]["observed_or_inferred"] = "inferred"
    projection = validate_credentialing_projection(payload)
    run = InferenceRun(run_id="run-1", provider="synthetic", model="fixture", agent_version="v1")
    provenance = {projection.facts[0].event_id: run}
    ledger = CredentialingLedger(projection, inference_provenance=provenance)
    run.provider = "changed"
    provenance.clear()
    assert ledger.inference_provenance[projection.facts[0].event_id].provider == "synthetic"


def test_existing_projection_is_revalidated() -> None:
    """Invalid assignments cannot bypass ingestion validation."""
    projection = validate_credentialing_projection(renewal_payload())
    projection.facts[0].confidence = 0.2
    with pytest.raises(ValidationError):
        validate_credentialing_projection(projection)
    with pytest.raises(ValidationError):
        CredentialingLedger(projection)


def test_failed_tombstone_preserves_all_previous_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed preparation must leave deletion memory and facts consistent."""
    ledger = CredentialingLedger(validate_credentialing_projection(renewal_payload()))
    deleted = ledger.projection.facts[0].event_id
    before = ledger.projection

    def fail_copy(*_args: object, **_kwargs: object) -> object:
        message = "injected copy failure"
        raise RuntimeError(message)

    monkeypatch.setattr(CredentialingProjection, "model_copy", fail_copy)
    with pytest.raises(RuntimeError, match="injected copy failure"):
        ledger.tombstone(deleted)
    assert ledger.projection is before
    assert deleted not in ledger.tombstoned_event_ids


def test_dead_letter_never_retains_payload_or_validation_details() -> None:
    """Sensitive error values and identifiers are not copied into failure records."""
    ledger = CredentialingLedger(
        validate_credentialing_projection({"source": "dataverse", "facts": []})
    )
    ledger.reject(
        "not a safe identifier", "schema", recorded_at_utc=datetime(2026, 1, 1, tzinfo=UTC)
    )
    record = ledger.dead_letters[0]
    assert record.fact_id == "unidentified"
    assert record.reason == "schema"
    assert not hasattr(record, "payload")
    with pytest.raises(CredentialingContractError, match="reason"):
        ledger.reject(
            "evt-1", "raw sensitive reason", recorded_at_utc=datetime(2026, 1, 1, tzinfo=UTC)
        )


def test_golden_renewal_is_complete_without_ai() -> None:
    """A complete observed trace gives reproducible reference-model evidence."""
    result = assess_routine_renewal(
        validate_credentialing_projection(renewal_payload()),
        "case-1",
        authority_version="synthetic-v1",
    )
    assert result.status == "matches_reference"
    assert result.deviations == ()
    assert result.excluded_inferred_count == 0


@pytest.mark.parametrize("mutation", ["missing", "order", "authority", "pathway", "inferred"])
def test_material_renewal_deviations_are_explainable(mutation: str) -> None:
    """Missing, reordered or unqualified facts never certify a complete path."""
    payload = renewal_payload()
    if mutation == "missing":
        payload["facts"].pop(0)
    elif mutation == "order":
        payload["facts"][0]["timestamp_utc"] = datetime(2027, 1, 1, tzinfo=UTC)
    elif mutation == "authority":
        payload["facts"][0]["qualifiers"]["authority_mapping_version"] = "stale"
    elif mutation == "pathway":
        payload["facts"][0]["qualifiers"]["pathway_code"] = "temporary"
    else:
        payload["facts"][0]["observed_or_inferred"] = "inferred"
    result = assess_routine_renewal(
        validate_credentialing_projection(payload), "case-1", authority_version="synthetic-v1"
    )
    assert result.status != "matches_reference"
    assert result.deviations


def test_empty_trace_is_insufficient_evidence() -> None:
    """Absence of observed evidence cannot be labelled conformant."""
    result = assess_routine_renewal(
        validate_credentialing_projection(renewal_payload()),
        "absent",
        authority_version="synthetic-v1",
    )
    assert result.status == "insufficient_evidence"


def test_reporting_suppresses_all_small_cohort_cells_and_identifiers() -> None:
    """Broader reporting reveals neither totals nor detail of a small cohort."""
    projection = validate_credentialing_projection(renewal_payload())
    report = project_credentialing_report(
        projection, role="report_reader", case_ids={"case-1"}, minimum_cases=5
    )
    assert report == {"suppressed": True, "metrics": None}


def test_reporting_reconciles_counts_and_case_access_is_scoped() -> None:
    """An authorised analyst sees only explicitly granted case sequences."""
    payload = renewal_payload()
    payload["facts"].extend(renewal_payload(case_id="case-2")["facts"])
    projection = validate_credentialing_projection(payload)
    report = project_credentialing_report(
        projection, role="report_reader", case_ids={"case-1", "case-2"}, minimum_cases=2
    )
    metrics = report["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["event_count"] == EXPECTED_TWO_CASE_EVENTS
    assert "case-1" not in json.dumps(report)
    scoped = project_credentialing_report(
        projection, role="case_analyst", case_ids={"case-1"}, minimum_cases=2
    )
    facts = scoped["facts"]
    assert isinstance(facts, list)
    assert len(cast("list[object]", facts)) == EXPECTED_RENEWAL_EVENTS
    assert "case-2" not in json.dumps(scoped)
    with pytest.raises(CredentialingContractError, match="role"):
        project_credentialing_report(projection, role="unknown", case_ids=set(), minimum_cases=2)
    with pytest.raises(CredentialingContractError, match="minimum"):
        project_credentialing_report(
            projection, role="report_reader", case_ids=set(), minimum_cases=1
        )


def test_restored_deletion_memory_filters_old_projection() -> None:
    """Restoring tombstones cannot resurrect facts from an older snapshot."""
    projection = validate_credentialing_projection(renewal_payload())
    deleted = projection.facts[0].event_id
    restored = CredentialingLedger(projection, tombstoned_event_ids={deleted})
    assert deleted not in {fact.event_id for fact in restored.projection.facts}
    with pytest.raises(CredentialingContractError, match="safe"):
        restored.tombstone("unsafe deletion reference")
    with pytest.raises(CredentialingContractError, match="timezone"):
        restored.reject("evt-1", "schema", recorded_at_utc=datetime(2026, 1, 1))  # noqa: DTZ001
    restored.reject("evt-1", "timeout", recorded_at_utc=datetime(2026, 1, 1, tzinfo=UTC))
    assert restored.dead_letters[0].retryable


@pytest.mark.parametrize("mutation", ["repeated", "additional", "tied", "no_authority"])
def test_ambiguous_or_exception_paths_require_review(mutation: str) -> None:
    """Repeated stages, exceptions and timestamp ties never match silently."""
    payload = renewal_payload()
    authority = "synthetic-v1"
    if mutation in {"repeated", "additional"}:
        extra = {**payload["facts"][0], "event_id": "extra-event"}
        if mutation == "additional":
            extra["activity"] = "validation_failed"
        payload["facts"].append(extra)
    elif mutation == "tied":
        payload["facts"][1]["timestamp_utc"] = payload["facts"][0]["timestamp_utc"]
    else:
        authority = ""
    result = assess_routine_renewal(
        validate_credentialing_projection(payload),
        "case-1",
        authority_version=authority,
    )
    assert result.status == "review_required"
    assert result.deviations


def test_rare_activity_suppresses_totals_even_in_a_large_cohort() -> None:
    """A rare exception cannot be derived by subtraction from a released total."""
    payload = renewal_payload()
    payload["facts"].extend(renewal_payload(case_id="case-2")["facts"])
    extra = {**payload["facts"][0], "activity": "validation_failed", "event_id": "rare-event"}
    payload["facts"].append(extra)
    projection = validate_credentialing_projection(payload)
    report = project_credentialing_report(
        projection,
        role="report_reader",
        case_ids={"case-1", "case-2"},
        minimum_cases=2,
    )
    assert report == {"suppressed": True, "metrics": None}
    empty = project_credentialing_report(
        projection,
        role="report_reader",
        case_ids=set(),
        minimum_cases=2,
    )
    assert empty == {"suppressed": True, "metrics": None}


def test_case_projection_removes_ungranted_linked_objects() -> None:
    """A permitted event must not reveal other linked case or practitioner IDs."""
    payload = renewal_payload()
    payload["facts"][0]["object_ids"].extend(["case-other", "practitioner-reference"])
    report = project_credentialing_report(
        validate_credentialing_projection(payload),
        role="case_analyst",
        case_ids={"case-1"},
        minimum_cases=2,
    )
    encoded = json.dumps(report)
    assert "case-other" not in encoded
    assert "practitioner-reference" not in encoded


def test_inferred_ledger_events_require_processing_run_provenance() -> None:
    """Inference labels alone cannot enter the assurance ledger without run evidence."""
    payload = renewal_payload()
    payload["facts"][0]["observed_or_inferred"] = "inferred"
    projection = validate_credentialing_projection(payload)
    with pytest.raises(CredentialingContractError, match="provenance"):
        CredentialingLedger(projection)
    ledger = CredentialingLedger(
        validate_credentialing_projection(renewal_payload(case_id="other"))
    )
    with pytest.raises(CredentialingContractError, match="provenance"):
        ledger.merge(projection)


def test_bounded_provenance_is_retained_only_in_restricted_state() -> None:
    """Labelled inference with run evidence stays separate and is deleted safely."""
    payload = renewal_payload()
    payload["facts"][0]["observed_or_inferred"] = "inferred"
    projection = validate_credentialing_projection(payload)
    event_id = projection.facts[0].event_id
    run = InferenceRun(run_id="run-1", provider="synthetic", model="fixture", agent_version="v1")
    ledger = CredentialingLedger(projection, inference_provenance={event_id: run})
    ledger.merge(projection)
    result = assess_routine_renewal(ledger.projection, "case-1", authority_version="synthetic-v1")
    assert result.excluded_inferred_count == 1
    assert "missing:request_received" in result.deviations
    ledger.tombstone(event_id)
    assert event_id not in ledger.inference_provenance
    ledger.merge(projection)
    assert event_id not in {fact.event_id for fact in ledger.projection.facts}
    with pytest.raises(ValidationError):
        InferenceRun.model_validate({**run.model_dump(), "raw_prompt": "prohibited"})


@given(st.sets(st.integers(min_value=0, max_value=12)))
def test_arbitrary_deleted_stage_sets_never_reappear(indices: set[int]) -> None:
    """Deletion and replay preserve exactly the retained observed event population."""
    projection = validate_credentialing_projection(renewal_payload())
    ledger = CredentialingLedger(projection)
    deleted = {projection.facts[index].event_id for index in indices}
    for event_id in deleted:
        ledger.tombstone(event_id)
    ledger.merge(projection)
    assert {fact.event_id for fact in ledger.projection.facts} == {
        fact.event_id for fact in projection.facts if fact.event_id not in deleted
    }


@pytest.mark.parametrize("threshold", [True, 2.5, "5", None])
def test_reporting_threshold_requires_explicit_integer_policy(threshold: object) -> None:
    """Misconfigured runtime thresholds fail closed rather than releasing data."""
    with pytest.raises(CredentialingContractError, match="minimum"):
        project_credentialing_report(
            validate_credentialing_projection(renewal_payload()),
            role="report_reader",
            case_ids={"case-1"},
            minimum_cases=threshold,
        )


def test_projection_schema_accepts_runtime_nullable_qualifiers() -> None:
    """Exported optional qualifiers remain valid at the published JSON boundary."""
    schema = json.loads(Path("contracts/credentialing-event-projection.json").read_text())
    properties = schema["$defs"]["fact"]["properties"]["qualifiers"]["properties"]
    fact = validate_credentialing_projection(renewal_payload()).facts[0].model_dump(mode="json")
    for key, value in fact["qualifiers"].items():
        rule = properties[key]
        if value is None:
            assert "null" in rule.get("type", []) or None in rule.get("enum", [])
