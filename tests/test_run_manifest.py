# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Corpus pilot entry and publication gate tests."""

import pytest

from careops_process.coverage import SourcePartition
from careops_process.run_manifest import PilotRunManifest, assert_pilot_ready


def partition() -> SourcePartition:
    """Return a complete synthetic partition."""
    return SourcePartition(
        source="planner",
        container="assigned_tasks",
        accessible=True,
        candidate_count=28,
        acquired_count=28,
        observation_start="2025-08-11T00:00:00Z",
        observation_end="2026-02-26T00:00:00Z",
    )


def manifest(
    *,
    source_owner_approved: bool = False,
    information_governance_approved: bool = False,
    configuration_frozen: bool = False,
    rollback_defined: bool = False,
    repeat_run_verified: bool = False,
) -> PilotRunManifest:
    """Return a manifest with explicit gate defaults."""
    return PilotRunManifest(
        run_id="run-20260721",
        policy_version="1.0.0",
        partitions=(partition(),),
        source_owner_approved=source_owner_approved,
        information_governance_approved=information_governance_approved,
        configuration_frozen=configuration_frozen,
        rollback_defined=rollback_defined,
        repeat_run_verified=repeat_run_verified,
    )


def test_pilot_gate_reports_all_external_prerequisites() -> None:
    """A local manifest cannot silently pass an unapproved pilot."""
    with pytest.raises(ValueError, match="source_owner_approved") as error:
        assert_pilot_ready(manifest())

    assert "information_governance_approved" in str(error.value)
    assert "configuration_frozen" in str(error.value)
    assert "rollback_defined" in str(error.value)
    assert "repeat_run_verified" in str(error.value)


def test_pilot_gate_passes_only_after_all_gates_are_evidenced() -> None:
    """Complete-population evidence remains separate from authorization."""
    assert_pilot_ready(
        manifest(
            source_owner_approved=True,
            information_governance_approved=True,
            configuration_frozen=True,
            rollback_defined=True,
            repeat_run_verified=True,
        )
    )
