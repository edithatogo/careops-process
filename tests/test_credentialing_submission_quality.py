# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""First-submission assessment denominator, replay and privacy regressions."""

# Fixture booleans and numeric expectations express explicit measured outcomes.
# ruff: noqa: FBT001, FBT003, PLR2004

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_submission_quality import (
    FirstSubmissionObservation,
    first_submission_observation_payload,
    merge_first_submission_observations,
    parse_first_submission_observation,
    report_first_submission_quality,
)


def observation(case: str, complete: bool) -> FirstSubmissionObservation:
    """Build explicit synthetic first-submission evidence."""
    return FirstSubmissionObservation(
        observation_id=case,
        case_id=case,
        source_system="synthetic",
        recorded_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        assessment_definition_version="definition-v1",
        complete_at_first_submission=complete,
    )


def test_complete_population_rate_and_replay() -> None:
    """Four consistent cases produce one half regardless of replay."""
    rows = [
        observation("a", True),
        observation("b", True),
        observation("c", False),
        observation("d", False),
    ]
    result = report_first_submission_quality(
        rows + rows,
        role="report_reader",
        granted_case_ids={"a", "b", "c", "d"},
        assessment_definition_version="definition-v1",
        source_complete=True,
        minimum_case_count=2,
    )
    assert not result.suppressed
    assert result.population_case_count == result.assessed_case_count == 4
    assert result.complete_case_count == result.incomplete_case_count == 2
    assert result.missing_case_count == 0
    assert result.observed_complete_rate == result.population_complete_rate == 0.5


def test_missing_is_not_false() -> None:
    """Unassessed cases remain missing and preclude population rates."""
    result = report_first_submission_quality(
        [observation("a", True), observation("b", True)],
        role="report_reader",
        granted_case_ids={"a", "b", "c", "d"},
        assessment_definition_version="definition-v1",
        source_complete=True,
        minimum_case_count=2,
    )
    assert result.observed_complete_rate == 1.0
    assert result.incomplete_case_count == 0
    assert result.missing_case_count == 2
    assert result.population_complete_rate is None
    assert result.population_rate_unavailable_reason == "missing_assessments"


def test_conflicting_case_assessments_fail() -> None:
    """A later label cannot erase an earlier contrary assertion."""
    with pytest.raises(CredentialingContractError):
        report_first_submission_quality(
            [observation("a", True), observation("a", False)],
            role="report_reader",
            granted_case_ids={"a", "b"},
            assessment_definition_version="definition-v1",
            source_complete=True,
            minimum_case_count=2,
        )


def report(rows: list[FirstSubmissionObservation], **changes: Any) -> Any:  # noqa: ANN401
    """Supply explicit synthetic scope with optional adversarial overrides."""
    arguments: dict[str, Any] = {
        "role": "report_reader",
        "granted_case_ids": {"a", "b", "c", "d"},
        "assessment_definition_version": "definition-v1",
        "source_complete": True,
        "minimum_case_count": 2,
    }
    arguments.update(changes)
    return report_first_submission_quality(rows, **arguments)


def test_all_missing_has_no_rate() -> None:
    """Missing population produces no fabricated observed zeros."""
    result = report([])
    assert not result.suppressed
    assert result.assessed_case_count == result.complete_case_count == 0
    assert result.missing_case_count == 4
    assert result.observed_complete_rate is None
    assert result.population_rate_unavailable_reason == "missing_assessments"


def test_coverage_attestation_required() -> None:
    """Complete labels alone cannot establish source coverage."""
    result = report([observation(case, True) for case in "abcd"], source_complete=False)
    assert result.observed_complete_rate == 1
    assert result.population_complete_rate is None
    assert result.population_rate_unavailable_reason == "source_coverage_unconfirmed"


@pytest.mark.parametrize("labels", [(True, True, True, False), (True, False), (True, True, True)])
def test_rare_cells_suppress_every_field(labels: tuple[bool, ...]) -> None:
    """Rare incomplete, outcome or missing cells suppress totals and reasons."""
    result = report([observation(case, value) for case, value in zip("abcd", labels, strict=False)])
    assert result.suppressed
    assert all(value is None for key, value in asdict(result).items() if key != "suppressed")


def test_empty_scope_suppressed() -> None:
    """Empty grants do not release a zero-population report."""
    assert report([], granted_case_ids=set()).suppressed


def test_consistent_case_labels_collapse_and_other_cases_excluded() -> None:
    """Distinct observation IDs cannot inflate a case denominator."""
    rows = [observation("a", True), observation("b", True)]
    baseline = report(rows)
    assert (
        report(
            [
                *rows,
                replace(rows[0], observation_id="second"),
                replace(observation("outside", False), assessment_definition_version="other"),
            ]
        )
        == baseline
    )


def test_case_conflict_with_distinct_id_fails() -> None:
    """Case consistency is separate from observation replay identity."""
    with pytest.raises(CredentialingContractError):
        report([observation("a", True), replace(observation("a", False), observation_id="other")])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_system", "different"),
        ("case_id", "different"),
        ("recorded_at_utc", datetime(2026, 2, 1, tzinfo=UTC)),
    ],
)
def test_changed_replay_fails(field: str, value: object) -> None:
    """Reused observation IDs cannot silently rewrite retained history."""
    original = observation("a", True)
    changed = replace(original, **{field: value})  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        merge_first_submission_observations([original], [changed])


def test_wrong_definition_fails() -> None:
    """Wrong definitions in granted cases fail before suppression."""
    with pytest.raises(CredentialingContractError):
        report([replace(observation("a", True), assessment_definition_version="other")])


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "case_analyst"},
        {"granted_case_ids": "abcd"},
        {"granted_case_ids": ["a", "b"]},
        {"granted_case_ids": {"a\n", "b"}},
        {"minimum_case_count": True},
        {"minimum_case_count": 1},
        {"source_complete": 1},
        {"assessment_definition_version": "definition-v1\n"},
    ],
)
def test_invalid_scope_fails(changes: dict[str, object]) -> None:
    """Scope and coverage flags cannot be coerced into authorisation evidence."""
    with pytest.raises(CredentialingContractError):
        report([], **changes)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observation_id", "a\n"),
        ("case_id", "a\n"),
        ("source_system", "synthetic\n"),
        ("assessment_definition_version", "definition-v1\n"),
        ("source_system", "person@example.org"),
        ("source_system", "raw narrative"),
        ("source_system", "x" * 81),
        ("observation_id", ""),
        ("complete_at_first_submission", 1),
        ("complete_at_first_submission", "false"),
        ("recorded_at_utc", "2026-01-01T00:00:00Z"),
        ("recorded_at_utc", datetime(2026, 1, 1)),  # noqa: DTZ001 - reject naive instants
        ("contract_version", "next"),
    ],
)
def test_invalid_direct_records_fail(field: str, value: object) -> None:
    """Direct construction validates the same evidence boundaries."""
    with pytest.raises(CredentialingContractError):
        replace(observation("a", True), **{field: value})  # type: ignore[arg-type]


def test_wire_roundtrip_and_utc_normalisation() -> None:
    """Wire records preserve aware instants and contain exactly admitted fields."""
    original = replace(
        observation("a", True),
        recorded_at_utc=datetime(
            2026,
            1,
            1,
            10,
            tzinfo=timezone(timedelta(hours=10)),
        ),
    )
    assert original.recorded_at_utc == datetime(2026, 1, 1, tzinfo=UTC)
    assert (
        parse_first_submission_observation(first_submission_observation_payload(original))
        == original
    )
    assert merge_first_submission_observations([original], [original]) == (original,)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("body", "prohibited"),
        ("kind", "evaluation"),
        ("contract_version", "next"),
        ("complete_at_first_submission", 0),
        ("case_id", "a\n"),
        ("recorded_at_utc", "2026-01-01T00:00:00Z\n"),
        ("recorded_at_utc", "2026-02-30T00:00:00Z"),
        ("recorded_at_utc", "2026-01-01T00:00:00"),
    ],
)
def test_invalid_wire_records_fail(field: str, value: object) -> None:
    """Wire ingestion rejects extra fields and invalid scalar/time representations."""
    payload = first_submission_observation_payload(observation("a", True))
    payload[field] = value
    with pytest.raises(CredentialingContractError):
        parse_first_submission_observation(payload)


@pytest.mark.parametrize("boundary", ["payload", "merge", "report"])
def test_forced_mutation_revalidated(boundary: str) -> None:
    """Frozen dataclasses are not a substitute for boundary validation."""
    altered = observation("a", True)
    object.__setattr__(altered, "complete_at_first_submission", 1)
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - exercise three public boundaries
        if boundary == "payload":
            first_submission_observation_payload(altered)
        elif boundary == "merge":
            merge_first_submission_observations([], [altered])
        else:
            report([altered])


def test_merge_detaches_records_and_report_omits_identifiers() -> None:
    """Retained state and released counts do not expose source records."""
    original = observation("a", True)
    retained = merge_first_submission_observations([], [original])
    object.__setattr__(original, "case_id", "changed")
    assert retained[0].case_id == "a"
    released = asdict(report([observation(case, True) for case in "abcd"]))
    assert not {"case_id", "observation_id", "source_system", "recorded_at_utc"} & released.keys()


def test_wrong_record_type_rejected() -> None:
    """Foreign records fail with a controlled contract error."""
    with pytest.raises(CredentialingContractError):
        first_submission_observation_payload(object())  # type: ignore[arg-type]


def test_same_case_same_time_conflict_not_resolved_by_order() -> None:
    """No ordering of contradictory labels is silently preferred."""
    yes = observation("a", True)
    no = replace(observation("a", False), observation_id="other")
    for rows in ([yes, no], [no, yes]):
        with pytest.raises(CredentialingContractError):
            report(rows)


@pytest.mark.parametrize("suffix", ["Z", "z", "+00:00"])
def test_aware_wire_timestamp_spellings(suffix: str) -> None:
    """Supported RFC3339 UTC spellings represent the same instant."""
    payload = first_submission_observation_payload(observation("a", True))
    payload["recorded_at_utc"] = "2026-01-01T00:00:00" + suffix
    assert parse_first_submission_observation(payload) == observation("a", True)


@pytest.mark.parametrize(
    "timestamp",
    [
        "0001-01-01T00:00:00+01:00",
        "9999-12-31T23:59:59-01:00",
    ],
)
def test_utc_normalisation_overflow_is_controlled(timestamp: str) -> None:
    """Valid offset syntax must not escape as an unhandled datetime overflow."""
    payload = first_submission_observation_payload(observation("a", True))
    payload["recorded_at_utc"] = timestamp
    with pytest.raises(CredentialingContractError):
        parse_first_submission_observation(payload)
    instant = datetime.fromisoformat(timestamp)
    with pytest.raises(CredentialingContractError):
        replace(observation("a", True), recorded_at_utc=instant)
