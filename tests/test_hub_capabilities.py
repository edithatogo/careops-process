"""Synthetic lane gates for the IHG Governance and Executive Action Hub."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from careops_process.hub_capabilities import (
    COMMON_CHECKS,
    DATAVERSE_CHECKS,
    FALLBACK_CHECKS,
    CapabilitySnapshot,
    assess_capabilities,
)

NOW = datetime(2026, 10, 14, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures" / "hub_capabilities"


def snapshot(lane: str = "dataverse") -> dict[str, Any]:
    """Return independently scoped, synthetic verification evidence."""
    required = COMMON_CHECKS | (DATAVERSE_CHECKS if lane == "dataverse" else FALLBACK_CHECKS)
    return {
        "schema_version": 1,
        "scope_ref": "scope-synthetic-pilot",
        "collected_at": NOW.isoformat(),
        "classification": "low_sensitivity_metadata",
        "co_owner_count": 3,
        "backup_owner_confirmed": True,
        "checks": {
            key: {
                "status": "verified",
                "scope_ref": "scope-synthetic-pilot",
                "observed_at": NOW.isoformat(),
                "evidence_ref": f"synthetic-{key}",
            }
            for key in required
        },
    }


def evaluate(value: dict[str, Any]) -> Any:  # noqa: ANN401
    """Validate before evaluating so unknown input never creates a lane."""
    return assess_capabilities(CapabilitySnapshot.model_validate(value), now=NOW)


@pytest.mark.parametrize("lane", ["dataverse", "restricted_fallback"])
def test_verified_lane(lane: str) -> None:
    """Only complete reviewed controls make a deployment lane eligible."""
    result = evaluate(snapshot(lane))
    assert result.lane == lane
    assert result.pilot_authorized is False


def test_dataverse_preferred_when_both_lanes_are_verified() -> None:
    """The restricted fallback never displaces an eligible canonical store."""
    value = snapshot()
    value["checks"].update(snapshot("restricted_fallback")["checks"])
    assert evaluate(value).lane == "dataverse"


@pytest.mark.parametrize("lane", ["dataverse", "restricted_fallback"])
@pytest.mark.parametrize("state", ["unknown", "observed", "failed", "unavailable"])
def test_every_missing_or_unverified_control_fails_closed(lane: str, state: str) -> None:
    """A read, missing control or failed probe is never verification."""
    for key in snapshot(lane)["checks"]:
        value = snapshot(lane)
        value["checks"][key]["status"] = state
        result = evaluate(value)
        assert result.lane == "fail_closed", key
        assert key in result.gaps[lane]
        del value["checks"][key]
        assert evaluate(value).lane == "fail_closed", key


@pytest.mark.parametrize("field", ["clinical_narrative", "patient_id", "approval_comments"])
def test_sensitive_or_unrecognised_input_rejected(field: str) -> None:
    """Extra fields cannot travel into the report as arbitrary payloads."""
    value = snapshot()
    value[field] = "synthetic-prohibited"
    with pytest.raises(ValidationError):
        evaluate(value)
    value = snapshot()
    value["checks"]["dataverse_access"][field] = "synthetic-prohibited"
    with pytest.raises(ValidationError):
        evaluate(value)


@pytest.mark.parametrize("value", ["false", 1, "true"])
def test_boolean_coercion_is_rejected(value: object) -> None:
    """A string or integer cannot stand in for confirmed backup ownership."""
    data = snapshot()
    data["backup_owner_confirmed"] = value
    with pytest.raises(ValidationError):
        evaluate(data)


@pytest.mark.parametrize("count", [0, 1])
def test_continuity_requires_two_owners_and_backup(count: int) -> None:
    """A technical lane remains gated on continuity outside one account."""
    value = snapshot()
    value["co_owner_count"] = count
    assert evaluate(value).lane == "fail_closed"
    value = snapshot()
    value["backup_owner_confirmed"] = False
    assert evaluate(value).lane == "fail_closed"


def test_two_owners_allowed_but_three_is_target() -> None:
    """The minimum is two and the preferred continuity arrangement is three."""
    value = snapshot()
    value["co_owner_count"] = 2
    result = evaluate(value)
    assert result.lane == "dataverse"
    assert result.continuity_target_met is False


def test_fallback_rejects_protected_information() -> None:
    """Restrict the initial fallback to low-sensitivity metadata."""
    value = snapshot("restricted_fallback")
    value["classification"] = "protected"
    assert evaluate(value).lane == "fail_closed"
    assert "classification" in evaluate(value).gaps["restricted_fallback"]


@pytest.mark.parametrize("hours", [-1, 25])
def test_future_and_stale_evidence_do_not_select_lane(hours: int) -> None:
    """Both collection and check times must be current, never future-dated."""
    for field in ("collected_at", "observed_at"):
        value = snapshot()
        timestamp = (NOW - timedelta(hours=hours)).isoformat()
        if field == "collected_at":
            value[field] = timestamp
        else:
            value["checks"]["dataverse_access"][field] = timestamp
        assert evaluate(value).lane == "fail_closed"


def test_verified_checks_need_reference_and_matching_scope() -> None:
    """Evidence from another environment cannot satisfy this pilot's controls."""
    value = snapshot()
    value["checks"]["dataverse_access"]["scope_ref"] = "scope-another-environment"
    assert evaluate(value).lane == "fail_closed"
    value["checks"]["dataverse_access"]["scope_ref"] = value["scope_ref"]
    value["checks"]["dataverse_access"]["evidence_ref"] = None
    with pytest.raises(ValidationError):
        evaluate(value)


def test_naive_timestamps_and_unknown_checks_rejected() -> None:
    """Unbounded names and ambiguous dates fail validation."""
    value = snapshot()
    value["collected_at"] = "2026-10-14T00:00:00"
    with pytest.raises(ValidationError):
        evaluate(value)
    value = snapshot()
    value["checks"]["tenant_admin_consent"] = value["checks"]["dataverse_access"]
    with pytest.raises(ValidationError):
        evaluate(value)


def test_report_does_not_copy_evidence_details() -> None:
    """The export contains only lane, fixed reason codes and continuity flags."""
    value = snapshot()
    rendered = evaluate(value).model_dump_json()
    assert "synthetic-dataverse_access" not in rendered
    assert "scope-synthetic-pilot" not in rendered
    assert "fail_closed" not in rendered


def test_ambiguous_evaluation_time_is_rejected() -> None:
    """Reject naive evaluation times rather than assuming a local timezone."""
    value = CapabilitySnapshot.model_validate(snapshot())
    with pytest.raises(ValueError, match="timezone-aware"):
        assess_capabilities(value, now=datetime(2026, 10, 14))  # noqa: DTZ001


def test_evidence_cannot_postdate_its_snapshot() -> None:
    """A later check cannot be silently attached to an earlier collected record."""
    value = snapshot()
    value["collected_at"] = (NOW - timedelta(minutes=1)).isoformat()
    assert evaluate(value).lane == "fail_closed"


def test_generated_schema_matches_executable_contract() -> None:
    """Keep the reusable JSON schema aligned with the validated input model."""
    schema_path = Path(__file__).parents[1] / "contracts" / "hub-capabilities.schema.json"
    assert (
        json.loads(schema_path.read_text(encoding="utf-8"))
        == CapabilitySnapshot.model_json_schema()
    )


@given(st.sets(st.sampled_from(sorted(COMMON_CHECKS | DATAVERSE_CHECKS)), min_size=1))
def test_any_subset_of_removed_dataverse_controls_fails_closed(removed: set[str]) -> None:
    """Missing control combinations cannot accidentally open the preferred lane."""
    value = snapshot()
    for key in removed:
        del value["checks"][key]
    assert evaluate(value).lane == "fail_closed"


@pytest.mark.parametrize("lane", ["dataverse", "restricted_fallback", "fail_closed"])
def test_checked_in_synthetic_fixtures(lane: str) -> None:
    """Examples are runnable contract fixtures, not live tenant claims."""
    value = json.loads((FIXTURES / f"{lane}.json").read_text(encoding="utf-8"))
    assert evaluate(value).lane == lane
