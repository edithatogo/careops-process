# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Fail-closed information handling for live process-mining corpora."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class CorpusHandlingPolicy:
    """Versionable controls required before live-corpus persistence."""

    classification: str
    access_boundary: str
    approved_destination_types: tuple[str, ...]
    retention_days: int
    approved_transient_features: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject incomplete policies that cannot govern a live run."""
        if not self.classification.strip():
            message = "classification is required"
            raise ValueError(message)
        if not self.access_boundary.strip():
            message = "access boundary is required"
            raise ValueError(message)
        if not self.approved_destination_types:
            message = "at least one approved destination is required"
            raise ValueError(message)
        if self.retention_days <= 0:
            message = "retention days must be positive"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class DeletionReceipt:
    """Payload-free proof that governed artifacts were removed."""

    run_id: str
    deleted_at: datetime
    deleted_artifact_hashes: tuple[str, ...]
    deleted_artifact_count: int


def validate_destination(policy: CorpusHandlingPolicy, destination_type: str) -> None:
    """Fail closed unless a destination type is explicitly approved."""
    if destination_type not in policy.approved_destination_types:
        message = f"destination type is not approved: {destination_type}"
        raise ValueError(message)


def validate_transient_features(
    policy: CorpusHandlingPolicy,
    requested_features: tuple[str, ...],
) -> None:
    """Prevent derived-feature scope from expanding silently."""
    unapproved = set(requested_features).difference(policy.approved_transient_features)
    if unapproved:
        message = f"transient feature is not approved: {', '.join(sorted(unapproved))}"
        raise ValueError(message)


def retention_deadline(policy: CorpusHandlingPolicy, generated_at: datetime) -> datetime:
    """Calculate deterministic expiry from the approved policy."""
    return generated_at + timedelta(days=policy.retention_days)


def build_deletion_receipt(
    *,
    run_id: str,
    deleted_at: datetime,
    deleted_artifact_hashes: tuple[str, ...],
) -> DeletionReceipt:
    """Create auditable deletion evidence without retaining deleted data."""
    return DeletionReceipt(
        run_id=run_id,
        deleted_at=deleted_at,
        deleted_artifact_hashes=deleted_artifact_hashes,
        deleted_artifact_count=len(deleted_artifact_hashes),
    )
