# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Explicit temporary episode and review evidence without clinical defaults."""

# Numeric fractions are hand-calculated synthetic expectations.
# ruff: noqa: PLR2004

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_temporary_quality import (
    TemporaryEpisodeGrant,
    TemporaryEpisodeSnapshot,
    TemporaryReportPolicy,
    TemporaryReportScope,
    TemporaryReviewGrant,
    TemporaryReviewReportPolicy,
    TemporaryReviewReportScope,
    TemporaryReviewSnapshot,
    merge_temporary_episodes,
    merge_temporary_reviews,
    parse_temporary_episode,
    parse_temporary_review,
    report_temporary_episodes,
    report_temporary_reviews,
    temporary_episode_payload,
    temporary_review_payload,
)

AS_OF = datetime(2026, 1, 10, tzinfo=UTC)
EXPIRY = AS_OF - timedelta(days=1)
START = EXPIRY - timedelta(days=1)


def episode(identity: str, state: str = "active") -> TemporaryEpisodeSnapshot:
    """Supply explicit episode evidence, no inferred expiry or conversion."""
    return TemporaryEpisodeSnapshot(
        observation_id=identity,
        episode_id=identity,
        case_id=identity,
        source_system="synthetic",
        definition_version="v1",
        snapshot_as_of_utc=AS_OF,
        captured_at_utc=AS_OF,
        observed_start_utc=START,
        effective_expiry_utc=EXPIRY,
        state=state,
        conversion_at_utc=EXPIRY if state == "converted" else None,
        observed_expiry_at_utc=EXPIRY if state == "expired" else None,
        coverage_complete=True,
    )


def test_expiry_is_not_inferred_from_elapsed_deadline() -> None:
    """Expired and source-active-past-deadline are different observed states."""
    rows = [episode("a"), episode("b"), episode("c", "expired"), episode("d", "expired")]
    result = report_temporary_episodes(
        rows,
        policy=TemporaryReportPolicy(
            definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
        ),
        scope=TemporaryReportScope(
            role="report_reader",
            granted_episodes=tuple(
                TemporaryEpisodeGrant(episode_id=row.episode_id, case_id=row.case_id)
                for row in rows
            ),
        ),
    )
    assert dict(result.episode_counts or ())["matured_source_active_past_expiry"] == 2
    assert dict(result.episode_counts or ())["matured_observed_expired"] == 2
    assert result.observed_conversion_rate == 0
    assert result.expiry_transition_episode_count == 2


def policy(**changes: Any) -> TemporaryReportPolicy:  # noqa: ANN401 - adversarial overrides
    """Use explicit source policy with controlled fixture overrides."""
    return replace(
        TemporaryReportPolicy(
            definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
        ),
        **changes,
    )


def episode_scope(rows: list[TemporaryEpisodeSnapshot]) -> TemporaryReportScope:
    """Grant the explicit observed fixture population, not arbitrary object links."""
    return TemporaryReportScope(
        role="report_reader",
        granted_episodes=tuple(
            TemporaryEpisodeGrant(episode_id=row.episode_id, case_id=row.case_id) for row in rows
        ),
    )


def episode_report(rows: list[TemporaryEpisodeSnapshot], **changes: Any) -> Any:  # noqa: ANN401
    """Report synthetic episodes under matched scope."""
    return report_temporary_episodes(rows, scope=episode_scope(rows), policy=policy(**changes))


def review(identity: str, state: str = "pending") -> TemporaryReviewSnapshot:
    """Supply an observed required review distinct from episode conversion."""
    return TemporaryReviewSnapshot(
        observation_id=identity,
        review_obligation_id=identity,
        episode_id=identity,
        case_id=identity,
        source_system="synthetic",
        definition_version="v1",
        snapshot_as_of_utc=AS_OF,
        captured_at_utc=AS_OF,
        effective_deadline_utc=EXPIRY,
        state=state,
        completion_at_utc=EXPIRY if state == "completed" else None,
        coverage_complete=True,
    )


def review_scope(rows: list[TemporaryReviewSnapshot]) -> TemporaryReviewReportScope:
    """Explicitly nest review grants within episode/case grants."""
    return TemporaryReviewReportScope(
        role="report_reader",
        granted_episodes=tuple(
            TemporaryEpisodeGrant(episode_id=row.episode_id, case_id=row.case_id) for row in rows
        ),
        granted_reviews=tuple(
            TemporaryReviewGrant(
                review_obligation_id=row.review_obligation_id,
                episode_id=row.episode_id,
                case_id=row.case_id,
            )
            for row in rows
        ),
    )


def review_policy(**changes: Any) -> TemporaryReviewReportPolicy:  # noqa: ANN401
    """Explicitly attest both source coverage and required-review enumeration."""
    return replace(
        TemporaryReviewReportPolicy(
            definition_version="v1",
            as_of_utc=AS_OF,
            source_complete=True,
            required_review_population_complete=True,
            minimum_case_count=2,
        ),
        **changes,
    )


def review_report(rows: list[TemporaryReviewSnapshot], **changes: Any) -> Any:  # noqa: ANN401
    """Report known obligations without deriving requirements from episode events."""
    return report_temporary_reviews(rows, scope=review_scope(rows), policy=review_policy(**changes))


@pytest.mark.parametrize(
    ("changes", "category"),
    [
        ({"state": "out_of_scope"}, "censored_out_of_scope"),
        ({"state": "unknown"}, "unknown_status"),
        ({"coverage_complete": False}, "unknown_status"),
        ({"observed_start_utc": None}, "missing_start"),
        ({"effective_expiry_utc": None}, "missing_expiry"),
        ({"effective_expiry_utc": AS_OF}, "not_yet_matured"),
        ({"state": "closed_without_conversion"}, "matured_closed_without_conversion"),
    ],
)
def test_episode_classification_reconciles(changes: dict[str, object], category: str) -> None:
    """Missingness/censoring/future states never become converted or observed expiry."""
    rows = [replace(episode(case), **changes) for case in "ab"]  # type: ignore[arg-type]
    result = episode_report(rows)
    assert dict(result.episode_counts)[category] == 2
    assert sum(dict(result.episode_counts).values()) == result.population_episode_count == 2
    assert result.expiry_transition_excluded_episode_count == 2


def test_conversion_fractions_include_unconverted_states() -> None:
    """Two timely, two late and two active past expiry gives4/6 and2/6."""
    rows = (
        [episode(case, "converted") for case in "ab"]
        + [replace(episode(case, "converted"), conversion_at_utc=AS_OF) for case in "cd"]
        + [episode(case) for case in "ef"]
    )
    result = episode_report(rows)
    assert result.observed_conversion_rate == result.population_conversion_rate == 4 / 6
    assert result.observed_conversion_by_expiry_rate == 2 / 6
    assert result.matured_episode_count == 6


def test_early_observed_expiry_not_discarded_as_future() -> None:
    """Observed early expiry remains visible even before its effective deadline."""
    rows = [
        replace(episode(case, "expired"), effective_expiry_utc=AS_OF + timedelta(days=1))
        for case in "ab"
    ]
    result = episode_report(rows)
    assert dict(result.episode_counts)["not_yet_matured"] == 2
    assert dict(result.expiry_transition_counts)["transition_before_effective_expiry"] == 2
    assert result.expiry_transition_episode_count == 2
    assert result.matured_episode_count == 0
    assert result.observed_conversion_rate is None
    assert result.population_rate_unavailable_reason == "no_matured_episodes"


def test_late_observed_expiry_has_own_denominator() -> None:
    """Transition distribution denominator differs from the matured population."""
    rows = [replace(episode(case, "expired"), observed_expiry_at_utc=AS_OF) for case in "ab"] + [
        episode(case) for case in "cd"
    ]
    result = episode_report(rows)
    assert dict(result.expiry_transition_counts)["transition_after_effective_expiry"] == 2
    assert (
        result.expiry_transition_episode_count
        == result.expiry_transition_excluded_episode_count
        == 2
    )
    assert result.matured_episode_count == 4


def test_episode_missing_and_source_coverage_prevent_population_rate() -> None:
    """Source coverage and actual granted-population evidence remain independent."""
    rows = [episode(case, "converted") for case in "abcd"]
    result = report_temporary_episodes(rows[:2], scope=episode_scope(rows), policy=policy())
    assert result.observed_conversion_rate == 1
    assert result.population_conversion_rate is None
    assert result.population_rate_unavailable_reason == "incomplete_episode_evidence"
    assert dict(result.episode_counts or ())["missing_snapshot"] == 2
    assert (
        episode_report(rows, source_complete=False).population_rate_unavailable_reason
        == "source_coverage_unconfirmed"
    )


@pytest.mark.parametrize(
    ("changes", "category"),
    [
        ({"state": "out_of_scope"}, "censored_out_of_scope"),
        ({"state": "unknown"}, "unknown_status"),
        ({"coverage_complete": False}, "unknown_status"),
        ({"effective_deadline_utc": None}, "missing_deadline"),
        ({"effective_deadline_utc": AS_OF}, "not_yet_due"),
        ({}, "matured_outstanding"),
    ],
)
def test_review_classification_reconciles(changes: dict[str, object], category: str) -> None:
    """Separate temporary-review evidence has explicit missing and exclusion cells."""
    rows = [replace(review(case), **changes) for case in "ab"]  # type: ignore[arg-type]
    result = review_report(rows)
    assert dict(result.review_counts)[category] == 2
    assert sum(dict(result.review_counts).values()) == result.known_review_obligation_count == 2


def test_review_completion_fractions_and_population_assertion() -> None:
    """Outstanding reviews stay in the denominator and unknown requirements block full rates."""
    rows = (
        [review(case, "completed") for case in "ab"]
        + [replace(review(case, "completed"), completion_at_utc=AS_OF) for case in "cd"]
        + [review(case) for case in "ef"]
    )
    result = review_report(rows)
    assert result.observed_completion_rate == result.population_completion_rate == 4 / 6
    assert result.observed_on_time_rate == result.population_on_time_rate == 2 / 6
    unknown = review_report(rows, required_review_population_complete=False)
    assert unknown.observed_completion_rate == 4 / 6
    assert unknown.population_completion_rate is None
    assert unknown.population_rate_unavailable_reason == "review_population_unconfirmed"
    assert unknown.required_review_population_complete is False
    assert "unknown_required_review_count" not in asdict(unknown)


def test_no_known_reviews_with_unknown_requirements_not_zero_population_rate() -> None:
    """Zero known obligations does not enumerate unknown required reviews."""
    episodes = episode_scope([episode(case) for case in "ab"])
    scoped = TemporaryReviewReportScope(
        role=episodes.role, granted_episodes=episodes.granted_episodes, granted_reviews=()
    )
    result = report_temporary_reviews(
        [], scope=scoped, policy=review_policy(required_review_population_complete=False)
    )
    assert not result.suppressed
    assert result.known_review_obligation_count == 0
    assert result.observed_completion_rate is None
    assert result.population_rate_unavailable_reason == "review_population_unconfirmed"


def test_review_missing_coverage_and_empty_future_reasons() -> None:
    """Unavailable reasons follow evidence, population, source then maturity precedence."""
    rows = [review(case, "completed") for case in "abcd"]
    missing = report_temporary_reviews(rows[:2], scope=review_scope(rows), policy=review_policy())
    assert missing.population_rate_unavailable_reason == "incomplete_review_evidence"
    assert dict(missing.review_counts or ())["missing_snapshot"] == 2
    assert (
        review_report(rows, source_complete=False).population_rate_unavailable_reason
        == "source_coverage_unconfirmed"
    )
    future = [replace(row, effective_deadline_utc=AS_OF) for row in rows]
    assert review_report(future).population_rate_unavailable_reason == "no_matured_reviews"


def test_multiple_episodes_or_reviews_from_one_case_suppressed() -> None:
    """Mathematical volume cannot manufacture distinct privacy cases."""
    episodes = [replace(episode(str(i)), case_id="one") for i in range(10)]
    reviews = [replace(review(str(i)), case_id="one") for i in range(10)]
    assert episode_report(episodes).suppressed
    assert review_report(reviews).suppressed


def test_rare_expiry_transition_suppresses_entire_episode_report() -> None:
    """Transition cells are privacy checked even when main cells have enough cases."""
    rows = [episode(case, "expired") for case in "abcd"]
    rows[0] = replace(rows[0], observed_expiry_at_utc=AS_OF)
    result = episode_report(rows)
    assert result.suppressed
    assert all(value is None for key, value in asdict(result).items() if key != "suppressed")


def test_mapping_collisions_and_nested_grants_fail() -> None:
    """Each episode/review has one trusted case and reviews must belong to granted episodes."""
    grant = TemporaryEpisodeGrant(episode_id="episode", case_id="case")
    with pytest.raises(CredentialingContractError):
        TemporaryReportScope(
            role="report_reader", granted_episodes=(grant, replace(grant, case_id="other"))
        )
    with pytest.raises(CredentialingContractError):
        TemporaryReviewReportScope(
            role="report_reader",
            granted_episodes=(grant,),
            granted_reviews=(
                TemporaryReviewGrant(
                    review_obligation_id="review", episode_id="outside", case_id="case"
                ),
            ),
        )


@pytest.mark.parametrize("domain", ["episode", "review"])
def test_replay_and_consistent_duplicates_are_idempotent(domain: str) -> None:
    """Each domain deduplicates replay without conflating episode and review identity."""
    if domain == "episode":
        rows = [episode(case) for case in "ab"]
        duplicate = replace(
            rows[0], observation_id="other", captured_at_utc=AS_OF + timedelta(hours=1)
        )
        assert report_temporary_episodes(
            [*rows, *rows, duplicate], scope=episode_scope(rows), policy=policy()
        ) == episode_report(rows)
        assert len(merge_temporary_episodes(rows, rows)) == 2
    else:
        rows_review = [review(case) for case in "ab"]
        duplicate_review = replace(
            rows_review[0], observation_id="other", captured_at_utc=AS_OF + timedelta(hours=1)
        )
        assert report_temporary_reviews(
            [*rows_review, *rows_review, duplicate_review],
            scope=review_scope(rows_review),
            policy=review_policy(),
        ) == review_report(rows_review)
        assert len(merge_temporary_reviews(rows_review, rows_review)) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_system", "other"),
        ("coverage_complete", False),
        ("effective_expiry_utc", AS_OF),
        ("state", "unknown"),
    ],
)
def test_conflicting_episode_evidence_fails(field: str, value: object) -> None:
    """A different ID cannot hide contrary episode state or deadline assertions."""
    row = episode("a")
    altered = replace(row, observation_id="other", **{field: value})  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes([row, altered], scope=episode_scope([row]), policy=policy())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("episode_id", "other"),
        ("case_id", "other"),
        ("definition_version", "other"),
        ("snapshot_as_of_utc", AS_OF - timedelta(days=1)),
    ],
)
def test_review_must_match_trusted_scope_and_reference(field: str, value: object) -> None:
    """Review mapping, source definition and instant are exact."""
    row = review("a")
    altered = replace(row, **{field: value})  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews([altered], scope=review_scope([row]), policy=review_policy())


@pytest.mark.parametrize("domain", ["episode", "review"])
def test_changed_id_replay_rejected(domain: str) -> None:
    """Observation identities cannot change source across replay."""
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - paired domain boundaries
        if domain == "episode":
            row = episode("a")
            merge_temporary_episodes([row], [replace(row, source_system="other")])
        else:
            row_review = review("a")
            merge_temporary_reviews([row_review], [replace(row_review, source_system="other")])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observation_id", "a\n"),
        ("episode_id", "a\n"),
        ("case_id", "a\n"),
        ("source_system", "synthetic\n"),
        ("definition_version", "v1\n"),
        ("coverage_complete", 1),
        ("state", []),
        ("contract_version", "next"),
        ("captured_at_utc", AS_OF - timedelta(seconds=1)),
        ("observed_start_utc", AS_OF + timedelta(seconds=1)),
        ("effective_expiry_utc", START - timedelta(seconds=1)),
        ("conversion_at_utc", EXPIRY),
        ("observed_expiry_at_utc", EXPIRY),
        ("effective_expiry_utc", datetime(2026, 1, 1)),  # noqa: DTZ001 - reject naive time
        ("effective_expiry_utc", datetime.fromisoformat("0001-01-01T00:00:00+01:00")),
    ],
)
def test_invalid_direct_episode_rejected(field: str, value: object) -> None:
    """Strict scalar and chronological boundaries apply before any aggregation."""
    with pytest.raises(CredentialingContractError):
        replace(episode("a"), **{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("state", "field"), [("converted", "conversion_at_utc"), ("expired", "observed_expiry_at_utc")]
)
@pytest.mark.parametrize(
    "instant", [None, START - timedelta(seconds=1), AS_OF + timedelta(seconds=1)]
)
def test_terminal_episode_requires_valid_transition(
    state: str, field: str, instant: datetime | None
) -> None:
    """Terminal assertions need observed transitions within the known episode window."""
    with pytest.raises(CredentialingContractError):
        replace(episode("a", state), **{field: instant})  # type: ignore[arg-type]


@pytest.mark.parametrize("instant", [None, AS_OF + timedelta(seconds=1)])
def test_completed_review_requires_completion(instant: datetime | None) -> None:
    """A review cannot be complete without evidence at/before as-of."""
    with pytest.raises(CredentialingContractError):
        replace(review("a", "completed"), completion_at_utc=instant)


def test_noncompleted_review_cannot_carry_completion() -> None:
    """Completion and pending state cannot be asserted together."""
    with pytest.raises(CredentialingContractError):
        replace(review("a"), completion_at_utc=EXPIRY)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("body", "raw"),
        ("kind", "other"),
        ("snapshot_as_of_utc", None),
        ("captured_at_utc", "2026-01-10T00:00:00Z\n"),
        ("effective_expiry_utc", "2026-02-30T00:00:00Z"),
        ("coverage_complete", "true"),
    ],
)
def test_invalid_wire_episode_rejected(field: str, value: object) -> None:
    """Exact wire keys and strict formats reject narrative, coercion and newline bypasses."""
    payload = temporary_episode_payload(episode("a"))
    payload[field] = value
    with pytest.raises(CredentialingContractError):
        parse_temporary_episode(payload)


def test_wire_roundtrips_and_detachment() -> None:
    """Independent domains roundtrip with aware offset-equivalent timestamps."""
    row = episode("a")
    payload = temporary_episode_payload(row)
    payload["snapshot_as_of_utc"] = "2026-01-10T10:00:00+10:00"
    assert parse_temporary_episode(payload) == row
    reviewed = review("a", "completed")
    assert parse_temporary_review(temporary_review_payload(reviewed)) == reviewed
    retained = merge_temporary_episodes([], [row])
    object.__setattr__(row, "case_id", "changed")
    assert retained[0].case_id == "a"


@pytest.mark.parametrize("boundary", ["payload", "merge", "report"])
def test_episode_forced_mutation_revalidated(boundary: str) -> None:
    """Frozen state does not bypass any public evidence boundary."""
    row = episode("a")
    trusted = episode_scope([row])
    object.__setattr__(row, "coverage_complete", 1)
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - three boundaries
        if boundary == "payload":
            temporary_episode_payload(row)
        elif boundary == "merge":
            merge_temporary_episodes([], [row])
        else:
            report_temporary_episodes([row], scope=trusted, policy=policy())


def test_policy_scope_and_nested_review_grant_revalidated() -> None:
    """Review population assertion and nested mappings are revalidated at use."""
    trusted = review_scope([review("a")])
    current = review_policy()
    object.__setattr__(current, "required_review_population_complete", 1)
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews([], scope=trusted, policy=current)
    object.__setattr__(current, "required_review_population_complete", True)
    object.__setattr__(next(iter(trusted.granted_reviews)), "case_id", "other")
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews([], scope=trusted, policy=current)


@pytest.mark.parametrize("grants", ["a", [], {"a": "a"}, (object(),)])
def test_invalid_episode_grant_container_rejected(grants: Any) -> None:  # noqa: ANN401
    """Only explicit validated immutable grant collections are admitted."""
    with pytest.raises(CredentialingContractError):
        TemporaryReportScope(role="report_reader", granted_episodes=grants)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_complete", 1),
        ("minimum_case_count", True),
        ("minimum_case_count", 1),
        ("definition_version", "v1\n"),
    ],
)
def test_invalid_policy_rejected(field: str, value: object) -> None:
    """Reporting flags, version and distinct-case floor cannot be coerced."""
    with pytest.raises(CredentialingContractError):
        policy(**{field: value})


def test_foreign_evidence_and_empty_scope() -> None:
    """Wrong domain records and empty populations cannot release measured zeros."""
    with pytest.raises(CredentialingContractError):
        temporary_episode_payload(review("a"))  # type: ignore[arg-type]
    assert episode_report([]).suppressed
    assert review_report([]).suppressed


def test_review_distinct_id_conflict_and_multiple_obligations() -> None:
    """Review obligations count separately; contradictory states never overwrite."""
    rows = [review(case) for case in "ab"]
    conflict = replace(rows[0], observation_id="other", coverage_complete=False)
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews(
            [*rows, conflict], scope=review_scope(rows), policy=review_policy()
        )
    additional = [
        replace(
            row,
            observation_id=f"other-{row.observation_id}",
            review_obligation_id=f"other-{row.review_obligation_id}",
        )
        for row in rows
    ]
    result = review_report(rows + additional)
    assert result.known_review_obligation_count == result.matured_review_count == 4
    assert result.population_episode_count == result.population_case_count == 2


def test_valid_out_of_grant_records_do_not_affect_either_report() -> None:
    """Other episodes/reviews never affect trusted reporting populations."""
    episodes = [episode(case) for case in "ab"]
    reviews = [review(case) for case in "ab"]
    outside_episode = replace(episode("outside"), definition_version="other")
    outside_review = replace(review("outside"), definition_version="other")
    assert report_temporary_episodes(
        [*episodes, outside_episode], scope=episode_scope(episodes), policy=policy()
    ) == episode_report(episodes)
    assert report_temporary_reviews(
        [*reviews, outside_review], scope=review_scope(reviews), policy=review_policy()
    ) == review_report(reviews)


def test_review_rare_missing_cell_suppresses_all_fields() -> None:
    """Absent review observations still have case mappings for suppression."""
    rows = [review(case) for case in "abc"]
    result = report_temporary_reviews(rows[:2], scope=review_scope(rows), policy=review_policy())
    assert result.suppressed
    assert all(value is None for key, value in asdict(result).items() if key != "suppressed")


def test_scope_detaches_grants_and_reports_omit_identifiers() -> None:
    """No release contains case/episode/obligation identifiers or source instants."""
    grant = TemporaryEpisodeGrant(episode_id="a", case_id="a")
    trusted = TemporaryReportScope(role="report_reader", granted_episodes=frozenset({grant}))
    object.__setattr__(grant, "case_id", "changed")
    assert next(iter(trusted.granted_episodes)).case_id == "a"
    assert (
        not {"episode_id", "case_id", "review_obligation_id", "captured_at_utc"}
        & asdict(review_report([review(case) for case in "ab"])).keys()
    )


@pytest.mark.parametrize("boundary", ["payload", "merge", "report"])
def test_review_forced_mutation_revalidated(boundary: str) -> None:
    """The review domain independently validates frozen records at every boundary."""
    row = review("a")
    trusted = review_scope([row])
    object.__setattr__(row, "completion_at_utc", EXPIRY)
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - three public boundaries
        if boundary == "payload":
            temporary_review_payload(row)
        elif boundary == "merge":
            merge_temporary_reviews([], [row])
        else:
            report_temporary_reviews([row], scope=trusted, policy=review_policy())


def test_episode_scope_and_policy_mutations_revalidated() -> None:
    """Episode grants and base policy are detached again at report time."""
    trusted = episode_scope([episode("a")])
    current = policy()
    object.__setattr__(current, "source_complete", 1)
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes([], scope=trusted, policy=current)
    object.__setattr__(current, "source_complete", True)
    object.__setattr__(next(iter(trusted.granted_episodes)), "case_id", "a\n")
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes([], scope=trusted, policy=current)


class _UncheckedEpisode(TemporaryEpisodeSnapshot):
    """Synthetic adapter subclass with overridden validation."""

    def __post_init__(self) -> None:
        """Represent an adapter subclass that suppresses contract validation."""


class _UncheckedPolicy(TemporaryReportPolicy):
    """Synthetic policy subclass with overridden validation."""

    def __post_init__(self) -> None:
        """Represent a policy subclass that bypasses the privacy floor."""


def test_snapshot_subclass_cannot_bypass_boundary_validation() -> None:
    """Export and merge must reconstruct the declared concrete snapshot contract."""
    altered = _UncheckedEpisode(**asdict(episode("a")))
    object.__setattr__(altered, "coverage_complete", 1)
    with pytest.raises(CredentialingContractError):
        temporary_episode_payload(altered)
    with pytest.raises(CredentialingContractError):
        merge_temporary_episodes([], [altered])


def test_policy_subclass_cannot_lower_distinct_case_floor() -> None:
    """Report-time reconstruction must not dispatch to a subclass validator."""
    untrusted = _UncheckedPolicy(
        definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=1
    )
    rows = [episode("a")]
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes(rows, scope=episode_scope(rows), policy=untrusted)


class _UncheckedReviewPolicy(TemporaryReviewReportPolicy):
    """Synthetic review policy that skips inherited validation."""

    def __post_init__(self) -> None:
        """Skip validation to exercise report-time reconstruction."""


class _UncheckedScope(TemporaryReportScope):
    """Synthetic scope that skips role and grant validation."""

    def __post_init__(self) -> None:
        """Skip validation to exercise report-time reconstruction."""


class _UncheckedReviewScope(TemporaryReviewReportScope):
    """Synthetic nested scope that skips role and grant validation."""

    def __post_init__(self) -> None:
        """Skip validation to exercise report-time reconstruction."""


def test_review_policy_subclass_cannot_skip_population_flag_validation() -> None:
    """Required-review population flags remain strict at report boundaries."""
    malformed = _UncheckedReviewPolicy(**asdict(review_policy()))
    object.__setattr__(malformed, "required_review_population_complete", 1)
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews([], scope=review_scope([]), policy=malformed)


def test_scope_subclasses_cannot_skip_role_validation() -> None:
    """Both scope domains reconstruct concrete trusted-shape contracts."""
    malformed = _UncheckedScope(role="case_analyst", granted_episodes=())
    nested = _UncheckedReviewScope(role="case_analyst", granted_episodes=(), granted_reviews=())
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes([], scope=malformed, policy=policy())
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews([], scope=nested, policy=review_policy())


class _UncheckedReviewSnapshot(TemporaryReviewSnapshot):
    """Synthetic review adapter record that skips validation."""

    def __post_init__(self) -> None:
        """Skip validation to exercise concrete reconstruction."""


class _UncheckedEpisodeGrant(TemporaryEpisodeGrant):
    """Synthetic grant subtype that must never reach dataclass replacement."""

    def __post_init__(self) -> None:
        """Skip validation to exercise the exact-type grant guard."""


class _UncheckedReviewGrant(TemporaryReviewGrant):
    """Synthetic nested grant subtype that skips validation."""

    def __post_init__(self) -> None:
        """Skip validation to exercise the exact-type grant guard."""


@pytest.mark.parametrize("boundary", ["payload", "merge", "report"])
def test_review_snapshot_subclass_validated_at_every_boundary(boundary: str) -> None:
    """Review export, merge and report all rebuild the declared concrete record."""
    original = review("a")
    trusted = review_scope([original])
    altered = _UncheckedReviewSnapshot(**asdict(original))
    object.__setattr__(altered, "coverage_complete", 1)
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - three public boundaries
        if boundary == "payload":
            temporary_review_payload(altered)
        elif boundary == "merge":
            merge_temporary_reviews([], [altered])
        else:
            report_temporary_reviews([altered], scope=trusted, policy=review_policy())


def test_episode_snapshot_subclass_validated_at_report_boundary() -> None:
    """Episode reporting rebuilds subclass records as well as export/merge."""
    original = episode("a")
    trusted = episode_scope([original])
    altered = _UncheckedEpisode(**asdict(original))
    object.__setattr__(altered, "coverage_complete", 1)
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes([altered], scope=trusted, policy=policy())


def test_grant_subclasses_rejected_before_replacement() -> None:
    """Only exact declared grant types may reach replace, even with valid fields."""
    episode_grant = _UncheckedEpisodeGrant(episode_id="a", case_id="a")
    review_grant = _UncheckedReviewGrant(episode_id="a", case_id="a", review_obligation_id="r")
    with pytest.raises(CredentialingContractError):
        TemporaryReportScope(role="report_reader", granted_episodes=(episode_grant,))
    with pytest.raises(CredentialingContractError):
        TemporaryReviewReportScope(
            role="report_reader", granted_episodes=(episode_grant,), granted_reviews=()
        )
    with pytest.raises(CredentialingContractError):
        TemporaryReviewReportScope(
            role="report_reader",
            granted_episodes=(TemporaryEpisodeGrant(episode_id="a", case_id="a"),),
            granted_reviews=(review_grant,),
        )


def test_grant_subclasses_rejected_after_scope_mutation() -> None:
    """Report-time scope reconstruction repeats the exact-type nested grant guards."""
    episodes = episode_scope([episode("a")])
    reviews = review_scope([review("a")])
    object.__setattr__(
        episodes, "granted_episodes", (_UncheckedEpisodeGrant(episode_id="a", case_id="a"),)
    )
    object.__setattr__(
        reviews,
        "granted_reviews",
        (_UncheckedReviewGrant(episode_id="a", case_id="a", review_obligation_id="a"),),
    )
    with pytest.raises(CredentialingContractError):
        report_temporary_episodes([], scope=episodes, policy=policy())
    with pytest.raises(CredentialingContractError):
        report_temporary_reviews([], scope=reviews, policy=review_policy())
