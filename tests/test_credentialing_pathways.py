# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic versioned pathway-reference and case-access tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from careops_process.credentialing import (
    CredentialingContractError,
    validate_credentialing_projection,
)
from careops_process.credentialing_pathways import (
    PATHWAY_CODES,
    PathwayReference,
    assess_pathway,
    parse_pathway_reference,
    pathway_reference_payload,
)


def reference(pathway: str = "changed-scope") -> PathwayReference:
    """Supply an explicitly synthetic source mapping, never an approved policy."""
    return PathwayReference(
        reference_id="synthetic-reference",
        version="0.1.0",
        pathway_code=pathway,
        authority_mapping_version="synthetic-authority-v1",
        source_reference="synthetic-source",
        required_stages=("request_received", "delegated_decision_recorded", "case_completed"),
        permitted_activities=(
            "request_received",
            "delegated_decision_recorded",
            "case_completed",
            "correction_requested",
        ),
        terminal_activities=("case_completed",),
    )


def payload(pathway: str = "changed-scope") -> dict[str, Any]:
    """Return observed facts matching this test's independent three-stage model."""
    return {
        "source": "careops-approve",
        "facts": [
            {
                "event_id": f"event-{i}",
                "activity": activity,
                "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i),
                "source_system": "synthetic",
                "object_ids": ["case-1"],
                "observed_or_inferred": "observed",
                "confidence": 1.0,
                "qualifiers": {
                    "pathway_code": pathway,
                    "authority_mapping_version": "synthetic-authority-v1",
                },
            }
            for i, activity in enumerate(
                ("request_received", "delegated_decision_recorded", "case_completed")
            )
        ],
    }


@pytest.mark.parametrize(
    "pathway",
    [
        "routine-renewal",
        "changed-scope",
        "mutual-recognition",
        "temporary-approval",
        "conditions-supervision",
        "review-appeal",
        "register-reconciliation",
    ],
)
def test_each_pathway_uses_its_supplied_reference(pathway: str) -> None:
    """All named pathways compare their own reference without substituting renewal."""
    result = assess_pathway(
        validate_credentialing_projection(payload(pathway)),
        reference(pathway),
        case_id="case-1",
        role="case_analyst",
        granted_case_ids={"case-1"},
    )
    assert result.status == "matches_reference"
    assert result.deviations == ()
    assert result.excluded_inferred_count == 0


def test_reference_roundtrip_rejects_drift_and_unknown_terms() -> None:
    """Only versioned registered activity codes enter an explicit reference."""
    original = reference()
    wire = pathway_reference_payload(original)
    assert parse_pathway_reference(wire) == original
    for key, value in [
        ("free_text", "not permitted"),
        ("version", "unknown"),
        ("pathway_code", "unregistered"),
    ]:
        changed = {**wire, key: value}
        with pytest.raises(CredentialingContractError):
            parse_pathway_reference(changed)
    with pytest.raises(CredentialingContractError):
        replace(original, required_stages=("unknown",))
    with pytest.raises(CredentialingContractError):
        replace(original, required_stages=("request_received", "request_received"))
    with pytest.raises(CredentialingContractError):
        replace(original, permitted_activities=("case_completed",))
    with pytest.raises(CredentialingContractError):
        replace(original, terminal_activities=("case_withdrawn",))


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "repeated",
        "reversed",
        "tied",
        "authority",
        "pathway",
        "unexpected",
        "terminal",
        "inferred",
    ],
)
def test_material_pathway_deviations_require_review(mutation: str) -> None:
    """Order, qualifiers, material gaps and inferred endpoints never match silently."""
    value = payload()
    if mutation == "missing":
        value["facts"].pop(0)
    elif mutation == "repeated":
        value["facts"].append({**value["facts"][0], "event_id": "repeated-event"})
    elif mutation == "reversed":
        value["facts"][0]["timestamp_utc"] = datetime(2027, 1, 1, tzinfo=UTC)
    elif mutation == "tied":
        value["facts"][1]["timestamp_utc"] = value["facts"][0]["timestamp_utc"]
    elif mutation in {"authority", "pathway"}:
        field = "authority_mapping_version" if mutation == "authority" else "pathway_code"
        value["facts"][0]["qualifiers"][field] = "different"
    elif mutation == "unexpected":
        value["facts"].append(
            {**value["facts"][-1], "event_id": "extra-event", "activity": "appeal_lodged"}
        )
    elif mutation == "terminal":
        value["facts"].append(
            {
                **value["facts"][-1],
                "event_id": "extra-event",
                "activity": "correction_requested",
                "timestamp_utc": datetime(2026, 1, 2, tzinfo=UTC),
            }
        )
    else:
        value["facts"][0]["observed_or_inferred"] = "inferred"
    result = assess_pathway(
        validate_credentialing_projection(value),
        reference(),
        case_id="case-1",
        role="case_analyst",
        granted_case_ids={"case-1"},
    )
    assert result.status == "review_required"
    assert result.deviations


@pytest.mark.parametrize(
    ("role", "grants"),
    [("report_reader", {"case-1"}), ("case_analyst", set[str]()), ("case_analyst", "case-1")],
)
def test_case_access_fails_closed(role: str, grants: object) -> None:
    """A role label or a character iterable cannot manufacture case access."""
    with pytest.raises(CredentialingContractError):
        assess_pathway(
            validate_credentialing_projection(payload()),
            reference(),
            case_id="case-1",
            role=role,
            granted_case_ids=grants,
        )


def test_empty_observed_trace_is_insufficient_evidence() -> None:
    """A supplied reference alone never establishes observed process execution."""
    projection = validate_credentialing_projection({"source": "careops-approve", "facts": []})
    result = assess_pathway(
        projection, reference(), case_id="case-1", role="case_analyst", granted_case_ids={"case-1"}
    )
    assert result.status == "insufficient_evidence"
    assert not set(PATHWAY_CODES) - {
        "routine-renewal",
        "changed-scope",
        "mutual-recognition",
        "temporary-approval",
        "conditions-supervision",
        "review-appeal",
        "register-reconciliation",
    }


@pytest.mark.parametrize(
    ("pathway", "stages"),
    [
        (
            "changed-scope",
            (
                "request_received",
                "professional_review_completed",
                "delegated_decision_recorded",
                "case_completed",
            ),
        ),
        (
            "mutual-recognition",
            ("request_received", "application_ready", "register_activated", "case_completed"),
        ),
        (
            "temporary-approval",
            ("temporary_approval_started", "temporary_approval_expired", "case_completed"),
        ),
        (
            "conditions-supervision",
            ("condition_applied", "supervision_plan_started", "case_completed"),
        ),
        (
            "review-appeal",
            ("appeal_lodged", "review_commenced", "review_or_appeal_decided", "case_completed"),
        ),
        (
            "register-reconciliation",
            (
                "register_activation_requested",
                "register_reconciliation_failed",
                "register_activated",
                "case_completed",
            ),
        ),
    ],
)
def test_distinct_synthetic_models_are_not_hardcoded_to_renewal(
    pathway: str,
    stages: tuple[str, ...],
) -> None:
    """Deliberately synthetic stage choices exercise independent mapping behavior."""
    model = replace(reference(pathway), required_stages=stages, permitted_activities=stages)
    value = payload(pathway)
    seed = value["facts"][0]
    value["facts"] = [
        {
            **seed,
            "event_id": f"different-{index}",
            "activity": activity,
            "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
        }
        for index, activity in enumerate(stages)
    ]
    projection = validate_credentialing_projection(value)
    result = assess_pathway(
        projection, model, case_id="case-1", role="case_analyst", granted_case_ids={"case-1"}
    )
    assert result.status == "matches_reference"
    wrong = assess_pathway(
        projection,
        reference(pathway),
        case_id="case-1",
        role="case_analyst",
        granted_case_ids={"case-1"},
    )
    assert wrong.status == "review_required"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_id", "unsafe narrative"),
        ("source_reference", "name@example.invalid"),
        ("required_stages", []),
        ("required_stages", "request_received"),
        ("permitted_activities", ["unknown"]),
        ("terminal_activities", []),
        ("authority_mapping_version", 5),
    ],
)
def test_invalid_reference_wire_values_fail_closed(field: str, value: object) -> None:
    """Wrong containers, identities, missing terms and coercion cannot enter models."""
    wire = pathway_reference_payload(reference())
    wire[field] = value
    with pytest.raises(CredentialingContractError):
        parse_pathway_reference(wire)


def test_permitted_optional_activity_preserves_reference_match() -> None:
    """Optional mapped work is accepted when required stages and terminal order hold."""
    value = payload()
    extra = {
        **value["facts"][0],
        "event_id": "optional-work",
        "activity": "correction_requested",
        "timestamp_utc": datetime(2026, 1, 1, 0, 30, tzinfo=UTC),
    }
    value["facts"].append(extra)
    result = assess_pathway(
        validate_credentialing_projection(value),
        reference(),
        case_id="case-1",
        role="case_analyst",
        granted_case_ids=frozenset({"case-1"}),
    )
    assert result.status == "matches_reference"


def test_activity_after_an_alternative_terminal_requires_review() -> None:
    """A terminal withdrawal cannot be followed by another terminal or more work."""
    model = replace(
        reference(),
        required_stages=("request_received",),
        permitted_activities=("request_received", "case_withdrawn", "case_completed"),
        terminal_activities=("case_withdrawn", "case_completed"),
    )
    value = payload()
    value["facts"][1]["activity"] = "case_withdrawn"
    result = assess_pathway(
        validate_credentialing_projection(value),
        model,
        case_id="case-1",
        role="case_analyst",
        granted_case_ids={"case-1"},
    )
    assert result.status == "review_required"
    assert "activity_after_terminal" in result.deviations
