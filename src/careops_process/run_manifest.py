# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Machine-readable corpus pilot entry and publication gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from careops_process.coverage import SourcePartition


@dataclass(frozen=True, slots=True)
class PilotRunManifest:
    """Evidence and approval state for one corpus-scale run."""

    run_id: str
    policy_version: str
    partitions: tuple[SourcePartition, ...]
    source_owner_approved: bool
    information_governance_approved: bool
    configuration_frozen: bool
    rollback_defined: bool
    repeat_run_verified: bool

    def __post_init__(self) -> None:
        """Require a stable run identity and at least one admitted partition."""
        if not self.run_id.strip() or not self.policy_version.strip():
            message = "run_id and policy_version are required"
            raise ValueError(message)
        if not self.partitions:
            message = "at least one source partition is required"
            raise ValueError(message)


def assert_pilot_ready(manifest: PilotRunManifest) -> None:
    """Fail closed until every external and operational gate is evidenced."""
    missing = [
        name
        for name, value in (
            ("source_owner_approved", manifest.source_owner_approved),
            ("information_governance_approved", manifest.information_governance_approved),
            ("configuration_frozen", manifest.configuration_frozen),
            ("rollback_defined", manifest.rollback_defined),
            ("repeat_run_verified", manifest.repeat_run_verified),
        )
        if not value
    ]
    if missing:
        message = "pilot gates incomplete: " + ", ".join(missing)
        raise ValueError(message)
