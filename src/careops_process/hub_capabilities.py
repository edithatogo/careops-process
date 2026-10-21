# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Fail-closed deployment eligibility from scoped, reviewed capability evidence.

Successful read-only probes are observations, never proof of write privileges,
multi-user sharing, DLP compatibility, continuity or organisational approval.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator

COMMON_CHECKS = frozenset(
    {
        "delegated_identity",
        "classification_approved",
        "records_controls",
        "continuity",
        "licence_compatibility",
        "connector_dlp_compatibility",
        "least_privilege_access",
    }
)
DATAVERSE_CHECKS = frozenset(
    {
        "dataverse_access",
        "customization_rights",
        "solution_import_rights",
        "app_sharing_rights",
        "multi_user_access",
        "dataverse_auditing",
        "required_connectors",
    }
)
FALLBACK_CHECKS = frozenset(
    {
        "existing_team_access",
        "sharepoint_list_access",
        "item_access_controls",
        "fallback_auditability",
        "standard_connectors",
        "approvals_access",
        "planner_access",
        "fallback_multi_user_access",
    }
)
CheckName = Literal[
    "delegated_identity",
    "classification_approved",
    "records_controls",
    "continuity",
    "licence_compatibility",
    "connector_dlp_compatibility",
    "least_privilege_access",
    "dataverse_access",
    "customization_rights",
    "solution_import_rights",
    "app_sharing_rights",
    "multi_user_access",
    "dataverse_auditing",
    "required_connectors",
    "existing_team_access",
    "sharepoint_list_access",
    "item_access_controls",
    "fallback_auditability",
    "standard_connectors",
    "approvals_access",
    "planner_access",
    "fallback_multi_user_access",
]
OpaqueReference = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")]
CheckStatus = Literal["unknown", "observed", "verified", "failed", "unavailable"]
Lane = Literal["dataverse", "restricted_fallback", "fail_closed"]


class CapabilityCheck(BaseModel):
    """A minimised observation or reviewed control, bound to one pilot scope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: CheckStatus = "unknown"
    scope_ref: OpaqueReference
    observed_at: AwareDatetime
    evidence_ref: OpaqueReference | None = None

    @model_validator(mode="after")
    def require_verification_reference(self) -> Self:
        """Require a verified check to reference controlled external evidence."""
        if self.status == "verified" and self.evidence_ref is None:
            message = "verified check requires an evidence reference"
            raise ValueError(message)
        return self


class CapabilitySnapshot(BaseModel):
    """Strict capability input; contains no identities, URLs or raw CLI output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    scope_ref: OpaqueReference
    collected_at: AwareDatetime
    classification: Literal["unconfirmed", "low_sensitivity_metadata", "protected"] = "unconfirmed"
    co_owner_count: Annotated[int, Field(strict=True, ge=0)] = 0
    backup_owner_confirmed: StrictBool = False
    checks: dict[CheckName, CapabilityCheck] = Field(
        default_factory=dict[CheckName, CapabilityCheck]
    )


class CapabilityAssessment(BaseModel):
    """Privacy-safe technical eligibility, explicitly separate from pilot approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    lane: Lane
    pilot_authorized: Literal[False] = False
    continuity_target_met: bool
    gaps: dict[str, list[str]]
    organisational_gates: tuple[str, ...] = (
        "operating_model_confirmation",
        "pilot_lane_approval",
        "information_steward_approval",
        "resource_owner_actions",
        "multi_user_pilot_verification",
    )


def _current(timestamp: datetime, now: datetime) -> bool:
    return timedelta() <= now - timestamp <= timedelta(hours=24)


def _gaps(snapshot: CapabilitySnapshot, required: frozenset[str], now: datetime) -> list[str]:
    checks = snapshot.checks
    gaps: list[str] = []
    for name in sorted(required):
        check = next((item for key, item in checks.items() if key == name), None)
        if (
            check is None
            or check.status != "verified"
            or check.scope_ref != snapshot.scope_ref
            or not _current(check.observed_at, now)
            or check.observed_at > snapshot.collected_at
        ):
            gaps.append(name)
    if snapshot.co_owner_count < 2 or not snapshot.backup_owner_confirmed:  # noqa: PLR2004
        gaps.append("ownership_continuity")
    if not _current(snapshot.collected_at, now):
        gaps.append("snapshot_freshness")
    if snapshot.classification == "unconfirmed":
        gaps.append("classification")
    return gaps


def assess_capabilities(snapshot: CapabilitySnapshot, *, now: datetime) -> CapabilityAssessment:
    """Prefer verified Dataverse, restrict fallback, or fail closed with reason codes.

    Args:
        snapshot: Validated evidence for exactly one environment/resource scope.
        now: Timezone-aware evaluation time; evidence expires after 24 hours.

    Returns:
        Technical lane eligibility and all unresolved controls for each lane.
        This result never authorizes a live pilot or production deployment.

    Raises:
        ValueError: Evaluation time lacks a timezone.

    """
    if now.tzinfo is None or now.utcoffset() is None:
        message = "evaluation time must be timezone-aware"
        raise ValueError(message)
    dataverse_gaps = _gaps(snapshot, COMMON_CHECKS | DATAVERSE_CHECKS, now)
    fallback_gaps = _gaps(snapshot, COMMON_CHECKS | FALLBACK_CHECKS, now)
    if (
        snapshot.classification != "low_sensitivity_metadata"
        and "classification" not in fallback_gaps
    ):
        fallback_gaps.append("classification")
    lane: Lane = "fail_closed"
    if not dataverse_gaps:
        lane = "dataverse"
    elif not fallback_gaps:
        lane = "restricted_fallback"
    return CapabilityAssessment(
        lane=lane,
        continuity_target_met=snapshot.co_owner_count >= 3 and snapshot.backup_owner_confirmed,  # noqa: PLR2004
        gaps={"dataverse": sorted(dataverse_gaps), "restricted_fallback": sorted(fallback_gaps)},
    )
