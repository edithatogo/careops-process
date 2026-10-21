# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Read-only hub deployment dry run, with explicit artifact, authority and platform gates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from careops_process import local_alm
from careops_process.hub_capabilities import OpaqueReference  # noqa: TC001
from careops_process.hub_domain import Classification, MetadataRecord

if TYPE_CHECKING:
    from collections.abc import Sequence


class HubReleaseRequest(MetadataRecord):
    """Record neutral review pointers, never credentials, tenant bindings or approval claims."""

    schema_version: Literal[1] = 1
    mode: Literal["dry_run_only"] = "dry_run_only"
    lane: Literal["unselected", "dataverse", "restricted_fallback"] = "unselected"
    stage: Literal["dev", "test", "prod"] = "dev"
    classification: Classification = "unconfirmed"
    operating_model_ref: OpaqueReference | None = None
    publisher_confirmation_ref: OpaqueReference | None = None
    capability_verification_ref: OpaqueReference | None = None
    lane_decision_ref: OpaqueReference | None = None
    information_governance_ref: OpaqueReference | None = None
    continuity_ref: OpaqueReference | None = None
    resource_owner_approval_ref: OpaqueReference | None = None
    fallback_configuration_export_ref: OpaqueReference | None = None
    fallback_backup_ref: OpaqueReference | None = None


class HubReleasePlan(MetadataRecord):
    """Expose review steps and fixed gap codes, not permission to import or publish."""

    mode: Literal["dry_run_only"] = "dry_run_only"
    deployment_authorized: Literal[False] = False
    artifact_prepared: bool = False
    gaps: tuple[str, ...]
    stages: tuple[str, ...] = (
        "confirm_target_lane_publisher_and_operating_model",
        "verify_access_sharing_dlp_licences_and_continuity",
        "author_components_in_confirmed_environment",
        "export_before_change_and_validate_supported_components",
        "generate_neutral_settings_and_review_private_bindings",
        "package_and_review_deployment_and_restore_evidence",
        "perform_explicitly_approved_import_and_multi_user_pilot",
    )
    logical_environment_variables: tuple[str, ...] = (
        "CanonicalStore",
        "WorkflowTemplateRegistry",
        "ProtectedEvidenceBase",
        "NotificationInterval",
        "PilotClassification",
    )
    logical_connection_references: tuple[str, ...] = (
        "Teams",
        "Approvals",
        "Planner",
        "SharePoint",
        "DataverseWhenSelected",
    )
    external_gates: tuple[str, ...] = (
        "target_and_publisher_confirmation",
        "actual_component_authoring_and_exports",
        "app_flow_validation_adapter",
        "authenticated_resource_bindings",
        "information_steward_and_ihg_policy_approval",
        "multi_user_pilot",
        "manual_verification_and_production_decision",
    )


def prepare_hub_release(  # noqa: C901, PLR0912 # Report all independent readiness gaps.
    request: HubReleaseRequest,
    *,
    release: Path | None = None,
    backup: Path | None = None,
) -> HubReleasePlan:
    """Prepare a tenant-neutral review report using shared ALM where a real export is supplied."""
    gaps: set[str] = set()
    fields = {
        "operating_model_ref": "operating_model_missing",
        "capability_verification_ref": "capability_verification_missing",
        "lane_decision_ref": "pilot_lane_decision_missing",
        "information_governance_ref": "information_governance_missing",
        "continuity_ref": "continuity_missing",
        "resource_owner_approval_ref": "resource_owner_approval_missing",
    }
    for field, gap in fields.items():
        if getattr(request, field) is None:
            gaps.add(gap)
    if request.lane != "restricted_fallback" and request.publisher_confirmation_ref is None:
        gaps.add("publisher_confirmation_missing")
    if request.lane == "unselected":
        gaps.add("pilot_lane_unselected")
    if request.classification == "unconfirmed":
        gaps.add("classification_unconfirmed")
    artifact_prepared = False
    if request.lane == "dataverse":
        if release is None:
            gaps.add("solution_export_missing")
        if backup is None:
            gaps.add("prechange_backup_missing")
        if release is not None and backup is not None:
            try:
                prepared = local_alm.prepare_deployment(release, backup, request.stage)
                artifact_prepared = prepared.get("status") == "prepared-offline"
                if not artifact_prepared:
                    gaps.add("release_or_backup_invalid_or_unsupported")
            except OSError, ValueError, TypeError, RuntimeError, KeyError:
                gaps.add("release_or_backup_invalid_or_unsupported")
        # Current shared validator supports table exports, not the hub's complete app/flow bundle.
        gaps.add("hub_app_flow_validation_pending")
    if request.lane == "restricted_fallback":
        if request.classification != "low_sensitivity_metadata":
            gaps.add("fallback_classification_incompatible")
        if request.fallback_configuration_export_ref is None:
            gaps.add("fallback_configuration_export_missing")
        if request.fallback_backup_ref is None:
            gaps.add("fallback_backup_missing")
        gaps.add("fallback_resource_bindings_and_access_unverified")
    return HubReleasePlan(artifact_prepared=artifact_prepared, gaps=tuple(sorted(gaps)))


def _safe_destination(
    output: Path | None,
    request: Path | None,
    release: Path | None,
    backup: Path | None,
) -> bool:
    if output is None:
        return True
    try:
        destination = output.resolve()
        # Refuse existing files, protecting hard-link aliases and preserving prior reports.
        if destination.exists() or (request is not None and destination == request.resolve()):
            return False
        return all(
            not destination.is_relative_to(source.resolve())
            for source in (release, backup)
            if source is not None
        )
    except OSError, RuntimeError:
        return False


def main(argv: Sequence[str] | None = None) -> int:
    """Write a safe dry-run review report; expose no online deployment operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        request = (
            HubReleaseRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
            if args.request
            else HubReleaseRequest()
        )
    except OSError, ValueError:
        sys.stderr.write('{"error":"invalid_release_request"}\n')
        return 2
    if not _safe_destination(args.output, args.request, args.release, args.backup):
        sys.stderr.write('{"error":"unsafe_release_report_destination"}\n')
        return 2
    plan = prepare_hub_release(request, release=args.release, backup=args.backup)
    rendered = plan.model_dump_json(indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        except OSError:
            sys.stderr.write('{"error":"release_report_write_failed"}\n')
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
