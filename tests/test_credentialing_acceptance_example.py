# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Independent expected outcomes for the executable synthetic handover example."""

from __future__ import annotations

# Expected arithmetic comes from the documented synthetic populations.
# ruff: noqa: PLR2004
import json
import runpy
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable


def _run() -> dict[str, Any]:
    example = Path(__file__).resolve().parents[1] / "examples/credentialing_acceptance.py"
    namespace = runpy.run_path(str(example), run_name="credentialing_acceptance_example")
    return cast("Callable[[], dict[str, Any]]", namespace["run_acceptance"])()


def test_synthetic_acceptance_connects_event_evidence_to_all_named_measures() -> None:
    """Reconciled event/history counts and hand-calculated measures survive integration."""
    result = _run()
    assert result["evidence_ceiling"] == "synthetic_only_no_source_or_policy_acceptance"
    assert result["events"]["observed"] == 104
    assert result["events"]["inferred"] == 8
    assert result["events"]["after_replay"] == 112
    assert result["events"]["after_tombstone_replay"] == 111
    assert result["conformance"]["routine_matches"] == 8
    assert result["conformance"]["separate_reference_models_match"] == 6
    assert result["timing"]["request_to_completion_p95_hours"] == 11
    assert result["timing"]["decision_to_register_p95_hours"] == 3
    assert result["workload"]["manual_touches"] == 16
    assert result["workload"]["active_minutes"] == 160
    assert result["workload"]["observed_minutes_per_case_difference"] == 10
    assert result["quality"]["false_positive_rate"] == 0.5
    assert result["quality"]["false_negative_rate"] == 0.5
    assert result["submission"]["observed_complete_rate"] == 0.5
    assert result["renewal"]["observed_overdue_rate"] == 0.5
    assert result["reviews"]["completion_rate"] == 0.5
    assert result["reviews"]["on_time_rate"] == 0.25
    assert result["temporary"]["conversion_rate"] == 0.5
    assert result["temporary"]["review_completion_rate"] == 0.5
    assert result["experience"]["response_rate"] == 0.75
    assert result["capacity"]["total_observed_minutes"] == 100
    assert result["capacity"]["observed_higher_value_minutes"] == 60
    assert result["capacity"]["released_capacity_requirement"] == "partial"


def test_synthetic_acceptance_preserves_redaction_missingness_and_human_scope() -> None:
    """No aggregate or proposal bypasses privacy; fixture judgments confer no authority."""
    result = _run()
    assert result["events"]["raw_field_rejected"]
    assert result["events"]["post_delete_timing_suppressed"]
    assert result["privacy"]["single_case_timing_suppressed"]
    assert result["privacy"]["single_case_proposal_count"] == 0
    assert result["temporary"]["unknown_required_review_reason"] == "review_population_unconfirmed"
    assert result["human_review"]["scope"] == "measurement_review_only"
    assert result["human_review"]["decision"] == "accepted"
    encoded = json.dumps(result)
    for prohibited in (
        "event_id",
        "case_id",
        "object_ids",
        "source_system",
        "cohort_ref",
        "reviewer_reference",
        "evidence_digest",
        "claimed_attributed_redeployment_minutes",
    ):
        assert f'"{prohibited}"' not in encoded
    assert "synthetic-case-0" not in encoded
