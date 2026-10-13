"""Governance decision validation tests."""

from typing import Any

import pytest

from careops_process.governance import validate_executive_record


def record() -> dict[str, Any]:
    """Return a pending sanitized decision record."""
    return {
        "run_id": "run-1",
        "evidence_reference": "approved-ref",
        "scope_approved": False,
        "ig_approved": False,
        "owner_validation": {
            "status": "pending",
            "validated_family_count": 0,
            "unresolved_family_count": 0,
        },
        "executive_decision": "pending",
    }


def test_pending_record_is_valid() -> None:
    """Pending governance gates are valid and do not imply approval."""
    validate_executive_record(record())


def test_decision_requires_all_human_gates() -> None:
    """A decision cannot be recorded from technical completion alone."""
    value = record()
    value["executive_decision"] = "pause"
    with pytest.raises(ValueError, match="scope and IG"):
        validate_executive_record(value)


def test_invalid_decision_is_rejected() -> None:
    """Enum violations fail closed."""
    value = record()
    value["executive_decision"] = "approved"
    with pytest.raises(ValueError, match="unsupported Executive"):
        validate_executive_record(value)


def test_invalid_counts_are_rejected() -> None:
    """Negative counts fail closed."""
    value = record()
    value["owner_validation"]["validated_family_count"] = -1
    with pytest.raises(ValueError, match="non-negative"):
        validate_executive_record(value)


def test_blank_run_reference_fails_closed() -> None:
    """A governance record requires a non-empty run reference."""
    value = record()
    value["run_id"] = ""
    with pytest.raises(ValueError, match="run_id"):
        validate_executive_record(value)
