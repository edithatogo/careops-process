# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Explicit synthetic instruments, distinct-person aggregates and privacy release."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

import careops_process.credentialing_experience as experience
from careops_process.credentialing import CredentialingContractError


def instrument(scale: str = "nominal") -> experience.ExperienceInstrument:
    """Supply synthetic response categories without inventing a real instrument."""
    return experience.ExperienceInstrument(
        instrument_code="synthetic-instrument",
        version="synthetic-v1",
        questions=(
            experience.ExperienceQuestion(
                question_code="question-1",
                scale_kind=scale,
                selection_mode="single_select",
                categories=("category-a", "category-b"),
            ),
        ),
    )


def cohort() -> experience.ExperienceCohort:
    """Freeze a source-defined cohort and observation epoch without person links."""
    return experience.ExperienceCohort(
        source_system="synthetic",
        cohort_ref="synthetic-cohort",
        definition_version="synthetic-cohort-v1",
        epoch_ref="synthetic-epoch",
        window_start_utc=datetime(2026, 10, 1, tzinfo=UTC),
        window_end_utc=datetime(2026, 10, 8, tzinfo=UTC),
    )


def snapshot(**changes: Any) -> experience.ExperienceSnapshot:  # noqa: ANN401
    """Eight invitations, six responses and four item answers reconcile independently."""
    values: dict[str, Any] = {
        "snapshot_ref": "synthetic-snapshot",
        "source_system": "synthetic",
        "cohort": cohort(),
        "instrument_code": instrument().instrument_code,
        "instrument_version": instrument().version,
        "instrument_digest": experience.experience_instrument_digest(instrument()),
        "distinct_person_aggregation_attested": True,
        "invited_count": 8,
        "responded_count": 6,
        "questions": (
            experience.ExperienceQuestionCounts(
                question_code="question-1",
                answered_count=4,
                category_counts=(("category-a", 2), ("category-b", 2)),
            ),
        ),
    }
    values.update(changes)
    return experience.ExperienceSnapshot(**values)


def report(value: experience.ExperienceSnapshot) -> experience.ExperienceReport:
    """Release only one selected, explicitly bound source snapshot."""
    return experience.report_experience(
        value,
        instrument(),
        role="report_reader",
        granted_cohort_refs={"synthetic-cohort"},
        minimum_respondents=2,
        expected_cohort=cohort(),
    )


def test_hand_calculated_response_and_item_missingness_have_distinct_denominators() -> None:
    """Survey nonresponse and item nonresponse are not interchangeable."""
    result = report(snapshot())
    assert not result.suppressed
    assert result.metrics is not None
    metrics = result.metrics
    assert (metrics.invited_count, metrics.responded_count, metrics.nonresponded_count) == (8, 6, 2)
    assert metrics.response_rate == 6 / 8
    question = metrics.questions[0]
    assert (question.answered_count, question.missing_count) == (4, 2)
    assert dict(question.category_rates) == {"category-a": 0.5, "category-b": 0.5}
    assert question.item_response_rate == pytest.approx(4 / 6)
    assert question.item_missing_rate == pytest.approx(2 / 6)
    exported = json.dumps(asdict(result))
    assert "synthetic-cohort" not in exported
    assert "synthetic-snapshot" not in exported
    assert "2026-10" not in exported
    assert "mean" not in exported
    assert "score" not in exported


@pytest.mark.parametrize(
    "cell", ["invited", "responded", "nonresponded", "answered", "missing", "category"]
)
def test_every_nonzero_released_cell_enforces_whole_report_suppression(cell: str) -> None:
    """Totals, coverage and outcome cells cannot disclose rare distinct-person groups."""
    invited, responded, answered, counts = {
        "invited": (1, 0, 0, (0, 0)),
        "responded": (3, 1, 0, (0, 0)),
        "nonresponded": (5, 4, 4, (2, 2)),
        "answered": (5, 3, 1, (1, 0)),
        "missing": (7, 5, 4, (2, 2)),
        "category": (8, 6, 4, (1, 3)),
    }[cell]
    value = snapshot(
        invited_count=invited,
        responded_count=responded,
        questions=(
            experience.ExperienceQuestionCounts(
                question_code="question-1",
                answered_count=answered,
                category_counts=(("category-a", counts[0]), ("category-b", counts[1])),
            ),
        ),
    )
    assert report(value) == experience.ExperienceReport(suppressed=True, metrics=None)


def test_zero_answers_and_zero_responders_remain_unavailable_not_zero_scores() -> None:
    """Invited people with no responses supply no category or item-response rate."""
    result = report(
        snapshot(
            responded_count=0,
            questions=(
                experience.ExperienceQuestionCounts(
                    question_code="question-1",
                    answered_count=0,
                    category_counts=(("category-a", 0), ("category-b", 0)),
                ),
            ),
        )
    )
    assert result.metrics is not None
    question = result.metrics.questions[0]
    assert result.metrics.response_rate == 0.0
    assert question.item_response_rate is None
    assert question.item_missing_rate is None
    assert dict(question.category_rates) == {"category-a": None, "category-b": None}
    assert report(
        snapshot(
            invited_count=0,
            responded_count=0,
            questions=(
                experience.ExperienceQuestionCounts(
                    question_code="question-1",
                    answered_count=0,
                    category_counts=(("category-a", 0), ("category-b", 0)),
                ),
            ),
        )
    ).suppressed


def test_missing_source_distinct_person_attestation_suppresses_everything() -> None:
    """Local arithmetic cannot establish distinct people from aggregate integers."""
    assert report(snapshot(distinct_person_aggregation_attested=False)).metrics is None


def test_frozen_cohort_cannot_be_reused_with_another_source() -> None:
    """An identical cohort label and window cannot silently switch its source namespace."""
    with pytest.raises(CredentialingContractError):
        report(replace(snapshot(), source_system="another-source"))


def test_replay_deduplicates_one_snapshot_without_summing_overlapping_cohorts() -> None:
    """Replay union retains snapshots; reporting still accepts exactly one chosen snapshot."""
    value = snapshot()
    assert experience.merge_experience_snapshots((value,), (value,)) == (value,)
    other = replace(value, snapshot_ref="another-timepoint")
    assert len(experience.merge_experience_snapshots((value,), (other,))) == len((value, other))
    with pytest.raises(CredentialingContractError, match="replay"):
        experience.merge_experience_snapshots((value,), (replace(value, invited_count=10),))
    with pytest.raises(CredentialingContractError, match="one snapshot"):
        report(cast("Any", (value, other)))


@pytest.mark.parametrize("gap", ["window", "epoch", "cohort", "instrument", "definition"])
def test_source_window_epoch_and_instrument_bindings_cannot_drift(gap: str) -> None:
    """Version labels alone cannot silently reinterpret a selected snapshot."""
    value = snapshot()
    if gap == "instrument":
        value = replace(value, instrument_digest="0" * 64)
    else:
        fields = {
            "window": {"window_end_utc": cohort().window_end_utc + timedelta(days=1)},
            "epoch": {"epoch_ref": "another-epoch"},
            "cohort": {"cohort_ref": "another-cohort"},
            "definition": {"definition_version": "another-definition"},
        }[gap]
        value = replace(value, cohort=replace(cohort(), **fields))
    with pytest.raises(CredentialingContractError):
        report(value)


def test_ordinal_instrument_is_explicit_and_emits_no_arithmetic_score() -> None:
    """An ordered category list is not an interval scale suitable for averaging."""
    configured = instrument("ordinal")
    value = snapshot(instrument_digest=experience.experience_instrument_digest(configured))
    result = experience.report_experience(
        value,
        configured,
        role="report_reader",
        granted_cohort_refs={"synthetic-cohort"},
        minimum_respondents=2,
        expected_cohort=cohort(),
    )
    assert result.metrics is not None
    assert result.metrics.questions[0].scale_kind == "ordinal"
    with pytest.raises(CredentialingContractError, match="single"):
        replace(configured.questions[0], selection_mode="multi_select")


@pytest.mark.parametrize("bad", [True, -1, "6", 1.5])
def test_strict_counts_reject_coercion(bad: object) -> None:
    """Aggregate units are bounded integer persons, never booleans or numeric strings."""
    with pytest.raises(CredentialingContractError):
        snapshot(responded_count=bad)


def test_reconciliation_and_retained_mutation_fail_closed() -> None:
    """A source cannot release contradictory totals or bypass frozen validation."""
    with pytest.raises(CredentialingContractError):
        snapshot(responded_count=9)
    with pytest.raises(CredentialingContractError):
        replace(snapshot().questions[0], answered_count=3)
    value = snapshot()
    object.__setattr__(value.questions[0], "answered_count", 3)
    with pytest.raises(CredentialingContractError):
        report(value)


def test_wire_roundtrips_and_forbidden_fields() -> None:
    """Exact envelopes reject narrative, respondent IDs and terminal-newline tokens."""
    value = snapshot()
    payload = experience.experience_snapshot_payload(value)
    assert experience.parse_experience_snapshot(payload) == value
    profile = experience.experience_instrument_payload(instrument())
    assert experience.parse_experience_instrument(profile) == instrument()
    for key, bad in (
        ("comment", "forbidden"),
        ("respondent_id", "person-1"),
        ("source_system", "synthetic\n"),
        ("distinct_person_aggregation_attested", "true"),
    ):
        with pytest.raises(CredentialingContractError):
            experience.parse_experience_snapshot({**payload, key: bad})


@pytest.mark.parametrize("field", ["window_start_utc", "window_end_utc"])
@pytest.mark.parametrize(
    "bad", ["2026-10-01T00:00:00", "2026-02-30T00:00:00Z", "2026-10-01T00:00:00+00:60"]
)
def test_wire_windows_reject_naive_invalid_and_normalizable_offsets(field: str, bad: str) -> None:
    """Lexical offset validation precedes Python's permissive timestamp normalization."""
    payload = experience.experience_snapshot_payload(snapshot())
    bound = cast("dict[str, object]", payload["cohort"])
    bound[field] = bad
    with pytest.raises(CredentialingContractError):
        experience.parse_experience_snapshot(payload)


@pytest.mark.parametrize(
    "grants", ["synthetic-cohort", ["synthetic-cohort"], iter(["synthetic-cohort"]), None]
)
def test_cohort_grants_are_not_case_or_string_shortcuts(grants: object) -> None:
    """A case-style token or one-shot iterator cannot silently change cohort authorization."""
    with pytest.raises(CredentialingContractError, match="grant"):
        experience.report_experience(
            snapshot(),
            instrument(),
            role="report_reader",
            granted_cohort_refs=cast("Any", grants),
            minimum_respondents=2,
            expected_cohort=cohort(),
        )


def test_late_question_rare_cell_suppresses_earlier_valid_results() -> None:
    """The release gate applies after every question, not separately to partial results."""
    configured = replace(
        instrument(),
        questions=(
            *instrument().questions,
            replace(instrument().questions[0], question_code="question-2"),
        ),
    )
    value = snapshot(
        instrument_digest=experience.experience_instrument_digest(configured),
        questions=(
            *snapshot().questions,
            experience.ExperienceQuestionCounts(
                question_code="question-2",
                answered_count=4,
                category_counts=(("category-a", 1), ("category-b", 3)),
            ),
        ),
    )
    result = experience.report_experience(
        value,
        configured,
        role="report_reader",
        granted_cohort_refs={"synthetic-cohort"},
        minimum_respondents=2,
        expected_cohort=cohort(),
    )
    assert result == experience.ExperienceReport(suppressed=True, metrics=None)


def test_instrument_digest_pins_ordinal_order_and_full_definition() -> None:
    """Ordinal order changes meaning while nominal ordering is representational only."""
    nominal = instrument()
    shuffled = replace(
        nominal,
        questions=(
            replace(
                nominal.questions[0],
                categories=tuple(reversed(nominal.questions[0].categories)),
            ),
        ),
    )
    assert experience.experience_instrument_digest(
        nominal
    ) == experience.experience_instrument_digest(shuffled)
    ordinal = instrument("ordinal")
    reversed_ordinal = replace(
        ordinal,
        questions=(
            replace(
                ordinal.questions[0],
                categories=tuple(reversed(ordinal.questions[0].categories)),
            ),
        ),
    )
    assert experience.experience_instrument_digest(
        ordinal
    ) != experience.experience_instrument_digest(reversed_ordinal)


@given(
    a=st.integers(0, 15),
    b=st.integers(0, 15),
    missing=st.integers(0, 15),
    absent=st.integers(0, 15),
)
def test_distinct_person_partitions_never_release_a_singleton_cell(
    a: int, b: int, missing: int, absent: int
) -> None:
    """Generated partitions preserve coverage arithmetic and whole-release privacy."""
    answered, responded, invited = a + b, a + b + missing, a + b + missing + absent
    value = snapshot(
        invited_count=invited,
        responded_count=responded,
        questions=(
            experience.ExperienceQuestionCounts(
                question_code="question-1",
                answered_count=answered,
                category_counts=(("category-a", a), ("category-b", b)),
            ),
        ),
    )
    result = report(value)
    if (
        any(count == 1 for count in (a, b, missing, absent, answered, responded, invited))
        or not invited
    ):
        assert result.metrics is None
    else:
        assert result.metrics is not None
        assert result.metrics.responded_count + result.metrics.nonresponded_count == invited


def _skip_post_init(_self: object) -> None:
    pass


def _bypass(value: Any, **changes: Any) -> Any:  # noqa: ANN401 - adversarial dynamic subclass fixture
    base = cast("type[Any]", type(value))
    subtype = type("ValidationBypass", (base,), {"__post_init__": _skip_post_init})
    values = {field.name: getattr(value, field.name) for field in fields(value) if field.init}
    return subtype(**{**values, **changes})


@pytest.mark.parametrize("boundary", ["export", "merge", "report"])
@pytest.mark.parametrize("record", ["snapshot", "cohort", "question_counts"])
def test_subclass_validation_bypass_cannot_enter_snapshot_boundaries(
    boundary: str,
    record: str,
) -> None:
    """Overrides cannot admit impossible response totals, windows or category partitions."""
    value = snapshot()
    bound = cohort()
    if record == "snapshot":
        value = _bypass(value, responded_count=10)
    elif record == "cohort":
        bound = _bypass(bound, window_end_utc=bound.window_start_utc)
        object.__setattr__(value, "cohort", bound)
    else:
        bad_question = _bypass(value.questions[0], answered_count=3)
        object.__setattr__(value, "questions", (bad_question,))
    with pytest.raises(CredentialingContractError):
        _snapshot_boundary(boundary, value, bound)


def _snapshot_boundary(
    boundary: str, value: experience.ExperienceSnapshot, bound: experience.ExperienceCohort
) -> None:
    if boundary == "export":
        experience.experience_snapshot_payload(value)
    elif boundary == "merge":
        experience.merge_experience_snapshots((), (value,))
    else:
        experience.report_experience(
            value,
            instrument(),
            role="report_reader",
            granted_cohort_refs={"synthetic-cohort"},
            minimum_respondents=2,
            expected_cohort=bound,
        )


@pytest.mark.parametrize("boundary", ["export", "digest", "report"])
@pytest.mark.parametrize("record", ["instrument", "question_definition"])
def test_subclass_validation_bypass_cannot_redefine_instrument_contract(
    boundary: str,
    record: str,
) -> None:
    """Unsupported profile versions and multiselect cannot hide behind matching fingerprints."""
    configured = instrument()
    wire = experience.experience_instrument_payload(configured)
    if record == "instrument":
        configured = _bypass(configured, contract_version="9.9.9")
        wire["contract_version"] = "9.9.9"
    else:
        bad_question = _bypass(configured.questions[0], selection_mode="multi_select")
        object.__setattr__(configured, "questions", (bad_question,))
        cast("list[dict[str, object]]", wire["questions"])[0]["selection_mode"] = "multi_select"
    value = snapshot(
        instrument_digest=hashlib.sha256(
            json.dumps(wire, sort_keys=True, separators=(",", ":")).encode(),
        ).hexdigest()
    )
    with pytest.raises(CredentialingContractError):
        _instrument_boundary(boundary, configured, value)


def _instrument_boundary(
    boundary: str, configured: experience.ExperienceInstrument, value: experience.ExperienceSnapshot
) -> None:
    if boundary == "export":
        experience.experience_instrument_payload(configured)
    elif boundary == "digest":
        experience.experience_instrument_digest(configured)
    else:
        experience.report_experience(
            value,
            configured,
            role="report_reader",
            granted_cohort_refs={"synthetic-cohort"},
            minimum_respondents=2,
            expected_cohort=cohort(),
        )
