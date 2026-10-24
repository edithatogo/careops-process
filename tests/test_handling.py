# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Live-corpus information-handling control tests."""

from datetime import UTC, datetime

import pytest

from careops_process.handling import (
    CorpusHandlingPolicy,
    build_deletion_receipt,
    retention_deadline,
    validate_destination,
    validate_transient_features,
)


def policy() -> CorpusHandlingPolicy:
    """Return a strict synthetic policy."""
    return CorpusHandlingPolicy(
        classification="sensitive_operational_metadata",
        access_boundary="ihg_authorised_operators",
        approved_destination_types=("local_encrypted", "approved_dataverse"),
        retention_days=30,
        approved_transient_features=("activity_terms",),
    )


def test_destination_must_be_explicitly_approved() -> None:
    """Public CI and repository paths fail closed."""
    validate_destination(policy(), "local_encrypted")
    with pytest.raises(ValueError, match="destination"):
        validate_destination(policy(), "public_ci_artifact")


def test_transient_features_require_explicit_allow_list() -> None:
    """Derived features cannot expand silently into identity or narrative."""
    validate_transient_features(policy(), ("activity_terms",))
    with pytest.raises(ValueError, match="transient feature"):
        validate_transient_features(policy(), ("activity_terms", "person_identity"))


def test_retention_deadline_is_policy_derived() -> None:
    """Live run expiry is deterministic and auditable."""
    generated = datetime(2026, 7, 19, tzinfo=UTC)
    deadline = retention_deadline(policy(), generated)
    assert (deadline - generated).days == policy().retention_days


def test_invalid_policy_fails_closed() -> None:
    """Empty boundaries and non-positive retention cannot authorize a run."""
    with pytest.raises(ValueError, match="access boundary"):
        CorpusHandlingPolicy(
            classification="sensitive",
            access_boundary=" ",
            approved_destination_types=("local_encrypted",),
            retention_days=30,
            approved_transient_features=(),
        )
    with pytest.raises(ValueError, match="retention"):
        CorpusHandlingPolicy(
            classification="sensitive",
            access_boundary="operators",
            approved_destination_types=("local_encrypted",),
            retention_days=0,
            approved_transient_features=(),
        )
    with pytest.raises(ValueError, match="classification"):
        CorpusHandlingPolicy(
            classification=" ",
            access_boundary="operators",
            approved_destination_types=("local_encrypted",),
            retention_days=30,
            approved_transient_features=(),
        )
    with pytest.raises(ValueError, match="destination"):
        CorpusHandlingPolicy(
            classification="sensitive",
            access_boundary="operators",
            approved_destination_types=(),
            retention_days=30,
            approved_transient_features=(),
        )


def test_deletion_receipt_contains_no_payload() -> None:
    """Deletion evidence records hashes and counts, never deleted content."""
    receipt = build_deletion_receipt(
        run_id="run-1",
        deleted_at=datetime(2026, 8, 18, tzinfo=UTC),
        deleted_artifact_hashes=("a" * 64, "b" * 64),
    )
    assert receipt.deleted_artifact_count == len(receipt.deleted_artifact_hashes)
    assert not hasattr(receipt, "payload")
