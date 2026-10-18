# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Review-obligation mathematics and distinct-case release protection."""

# Hand-calculated expected values describe synthetic observations.
# ruff: noqa: PLR2004

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_review_quality import (
    ReviewObligationGrant,
    ReviewObligationSnapshot,
    ReviewReportPolicy,
    ReviewReportScope,
    merge_review_obligation_snapshots,
    parse_review_obligation_snapshot,
    report_review_completion,
    review_obligation_snapshot_payload,
)

AS_OF = datetime(2026, 1, 10, tzinfo=UTC)
DUE = AS_OF - timedelta(days=1)


def snapshot(obligation: str, case: str, outcome: str) -> ReviewObligationSnapshot:
    """Construct explicit synthetic completion evidence without clinical rules."""
    completion = DUE if outcome == "on_time" else AS_OF if outcome == "late" else None
    return ReviewObligationSnapshot(
        observation_id=obligation,
        obligation_id=obligation,
        case_id=case,
        source_system="synthetic",
        definition_version="v1",
        review_kind="condition_review",
        snapshot_as_of_utc=AS_OF,
        captured_at_utc=AS_OF,
        effective_deadline_utc=DUE,
        state="completed" if completion else "pending",
        completion_at_utc=completion,
        coverage_complete=True,
    )


def test_obligation_denominator_includes_outstanding() -> None:
    """Two on-time, two late and two outstanding gives 4/6 completed, 2/6 on-time."""
    rows = [
        snapshot(str(index), str(index), outcome)
        for index, outcome in enumerate(
            ("on_time", "on_time", "late", "late", "pending", "pending")
        )
    ]
    result = report_review_completion(
        rows,
        policy=ReviewReportPolicy(
            definition_version="v1",
            review_kind="condition_review",
            as_of_utc=AS_OF,
            source_complete=True,
            minimum_case_count=2,
        ),
        scope=ReviewReportScope(
            role="report_reader",
            granted_obligations=tuple(
                ReviewObligationGrant(obligation_id=row.obligation_id, case_id=row.case_id)
                for row in rows
            ),
        ),
    )
    assert result.matured_obligation_count == 6
    assert result.observed_completion_rate == 4 / 6
    assert result.observed_on_time_rate == 2 / 6


def test_one_case_many_obligations_never_meets_privacy_floor() -> None:
    """Numerous obligations from one case remain one contributing case."""
    rows = [snapshot(str(index), "one-case", "on_time") for index in range(10)]
    result = report_review_completion(
        rows,
        policy=ReviewReportPolicy(
            definition_version="v1",
            review_kind="condition_review",
            as_of_utc=AS_OF,
            source_complete=True,
            minimum_case_count=2,
        ),
        scope=ReviewReportScope(
            role="report_reader",
            granted_obligations=tuple(
                ReviewObligationGrant(obligation_id=row.obligation_id, case_id=row.case_id)
                for row in rows
            ),
        ),
    )
    assert result.suppressed
    assert result.obligation_counts is None


def policy(**changes: Any) -> ReviewReportPolicy:  # noqa: ANN401 - adversarial overrides
    """Supply strict synthetic definition and coverage, with explicit overrides."""
    return replace(
        ReviewReportPolicy(
            definition_version="v1",
            review_kind="condition_review",
            as_of_utc=AS_OF,
            source_complete=True,
            minimum_case_count=2,
        ),
        **changes,
    )


def scope(rows: list[ReviewObligationSnapshot]) -> ReviewReportScope:
    """Map each explicit obligation to its independent privacy case."""
    return ReviewReportScope(
        role="report_reader",
        granted_obligations=tuple(
            ReviewObligationGrant(obligation_id=row.obligation_id, case_id=row.case_id)
            for row in rows
        ),
    )


def report(rows: list[ReviewObligationSnapshot], **changes: Any) -> Any:  # noqa: ANN401
    """Use matched trusted population for concise synthetic fixtures."""
    return report_review_completion(rows, scope=scope(rows), policy=policy(**changes))


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"state": "out_of_scope"}, "censored_out_of_scope"),
        ({"state": "unknown"}, "unknown_status"),
        ({"coverage_complete": False}, "unknown_status"),
        ({"effective_deadline_utc": None}, "missing_deadline"),
        ({"effective_deadline_utc": AS_OF}, "not_yet_due"),
        ({}, "matured_outstanding"),
    ],
)
def test_partition_and_no_matured_rates(changes: dict[str, object], expected: str) -> None:
    """Accounted exclusions and missingness occupy disjoint categories."""
    rows = [replace(snapshot(case, case, "pending"), **changes) for case in "ab"]  # type: ignore[arg-type]
    result = report(rows)
    assert dict(result.obligation_counts)[expected] == 2
    assert sum(dict(result.obligation_counts).values()) == result.population_obligation_count == 2
    if expected != "matured_outstanding":
        assert result.observed_completion_rate is None


def test_future_completed_obligations_excluded() -> None:
    """Already completed does not make a future obligation mature early."""
    rows = [
        replace(snapshot(case, case, "on_time"), effective_deadline_utc=AS_OF + timedelta(days=1))
        for case in "ab"
    ]
    result = report(rows)
    assert dict(result.obligation_counts)["not_yet_due"] == 2
    assert result.matured_obligation_count == 0
    assert result.observed_completion_rate is None
    assert result.population_rate_unavailable_reason == "no_matured_obligations"


def test_missing_grants_and_source_coverage() -> None:
    """Unobserved granted obligations never become completed or measured zeros."""
    rows = [snapshot(case, case, "on_time") for case in "abcd"]
    result = report_review_completion(rows[:2], scope=scope(rows), policy=policy())
    assert result.observed_completion_rate == 1
    assert result.population_completion_rate is None
    assert result.obligation_counts is not None
    assert dict(result.obligation_counts)["missing_snapshot"] == 2
    assert result.population_rate_unavailable_reason == "incomplete_obligation_evidence"
    all_missing = report_review_completion([], scope=scope(rows), policy=policy())
    assert all_missing.observed_completion_rate is None
    incomplete_source = report(rows, source_complete=False)
    assert incomplete_source.population_rate_unavailable_reason == "source_coverage_unconfirmed"
    assert incomplete_source.population_on_time_rate is None


def test_multiple_obligations_count_separately_with_distinct_case_support() -> None:
    """Obligation weighting is preserved even when cases have several reviews."""
    rows = [snapshot(f"{case}-{number}", case, "on_time") for case in "ab" for number in range(3)]
    result = report(rows)
    assert result.population_obligation_count == result.matured_obligation_count == 6
    assert result.population_case_count == 2
    assert result.population_completion_rate == result.population_on_time_rate == 1


def test_rare_case_cell_suppresses_large_obligation_count() -> None:
    """A rare case group cannot be hidden by many obligations in that group."""
    rows = [snapshot(f"late-{i}", "one-case", "late") for i in range(10)] + [
        snapshot(case, case, "on_time") for case in "ab"
    ]
    result = report(rows)
    assert result.suppressed
    assert all(value is None for key, value in asdict(result).items() if key != "suppressed")


def test_missing_cell_uses_granted_case_mapping_for_privacy() -> None:
    """Unobserved obligations sharing one case remain a rare missing cell."""
    observed = [snapshot(case, case, "on_time") for case in "ab"]
    absent = [snapshot(f"missing-{i}", "one-case", "pending") for i in range(10)]
    assert report_review_completion(
        observed, scope=scope(observed + absent), policy=policy()
    ).suppressed


def test_empty_scope_suppressed() -> None:
    """Empty trusted population yields no released rates or totals."""
    assert report_review_completion([], scope=scope([]), policy=policy()).suppressed


def test_replay_and_consistent_obligation_duplicates_do_not_inflate() -> None:
    """Exact replay and additional capture records count one obligation."""
    rows = [snapshot(case, case, "on_time") for case in "ab"]
    duplicate = replace(rows[0], observation_id="other", captured_at_utc=AS_OF + timedelta(hours=1))
    assert report_review_completion(
        [*rows, *rows, duplicate], scope=scope(rows), policy=policy()
    ) == report(rows)
    assert len(merge_review_obligation_snapshots(rows, rows)) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_system", "other"),
        ("coverage_complete", False),
        ("effective_deadline_utc", DUE - timedelta(days=1)),
        ("state", "unknown"),
    ],
)
def test_conflicting_distinct_id_obligation_evidence_fails(field: str, value: object) -> None:
    """Contrary state/deadline/source assertions are not resolved by newest capture."""
    original = snapshot("a", "a", "pending")
    contrary = replace(original, observation_id="other", **{field: value})  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        report_review_completion([original, contrary], scope=scope([original]), policy=policy())


def test_changed_id_replay_fails() -> None:
    """Observation replay cannot change source or content."""
    original = snapshot("a", "a", "pending")
    with pytest.raises(CredentialingContractError):
        merge_review_obligation_snapshots([original], [replace(original, source_system="other")])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("case_id", "other"),
        ("review_kind", "supervision_review"),
        ("definition_version", "other"),
        ("snapshot_as_of_utc", AS_OF - timedelta(days=1)),
    ],
)
def test_wrong_grant_or_reporting_reference_fails(field: str, value: object) -> None:
    """Case mapping, kind, definition and as-of are explicit boundaries."""
    original = snapshot("a", "a", "pending")
    altered = replace(original, **{field: value})  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        report_review_completion([altered], scope=scope([original]), policy=policy())


def test_valid_ungranted_obligation_does_not_contribute() -> None:
    """A shared case alone never grants all of its obligations."""
    rows = [snapshot(case, case, "pending") for case in "ab"]
    outside = replace(snapshot("outside", "a", "on_time"), review_kind="supervision_review")
    assert report_review_completion([*rows, outside], scope=scope(rows), policy=policy()) == report(
        rows
    )


def test_scope_mapping_collision_rejected_and_duplicate_detached() -> None:
    """One obligation cannot map to two privacy cases; exact grants collapse."""
    grant = ReviewObligationGrant(obligation_id="o", case_id="a")
    with pytest.raises(CredentialingContractError):
        ReviewReportScope(
            role="report_reader", granted_obligations=(grant, replace(grant, case_id="b"))
        )
    retained = ReviewReportScope(role="report_reader", granted_obligations=(grant, grant))
    object.__setattr__(grant, "case_id", "changed")
    assert retained.granted_obligations == (ReviewObligationGrant(obligation_id="o", case_id="a"),)


@pytest.mark.parametrize("grants", ["ab", [], {"o": "a"}, (object(),)])
def test_invalid_scope_container_or_grant_rejected(grants: Any) -> None:  # noqa: ANN401
    """Lists, strings, mappings and foreign records cannot become grants."""
    with pytest.raises(CredentialingContractError):
        ReviewReportScope(role="report_reader", granted_obligations=grants)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observation_id", "o\n"),
        ("obligation_id", "o\n"),
        ("case_id", "a\n"),
        ("source_system", "synthetic\n"),
        ("definition_version", "v1\n"),
        ("source_system", "raw narrative"),
        ("review_kind", "condition_review\n"),
        ("state", []),
        ("coverage_complete", 1),
        ("contract_version", "next"),
        ("captured_at_utc", AS_OF - timedelta(seconds=1)),
        ("completion_at_utc", AS_OF),
        ("effective_deadline_utc", datetime(2026, 1, 1)),  # noqa: DTZ001 - reject naive source time
        ("effective_deadline_utc", datetime.fromisoformat("0001-01-01T00:00:00+01:00")),
    ],
)
def test_invalid_direct_record_rejected(field: str, value: object) -> None:
    """All directly constructed evidence has strict scalar/time boundaries."""
    with pytest.raises(CredentialingContractError):
        replace(snapshot("a", "a", "pending"), **{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("completion", [None, AS_OF + timedelta(seconds=1)])
def test_completed_state_requires_valid_completion(completion: datetime | None) -> None:
    """Completion cannot be absent or lie beyond the reporting instant."""
    with pytest.raises(CredentialingContractError):
        replace(snapshot("a", "a", "on_time"), completion_at_utc=completion)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("body", "raw"),
        ("kind", "other"),
        ("captured_at_utc", "2026-01-10T00:00:00Z\n"),
        ("snapshot_as_of_utc", None),
        ("effective_deadline_utc", "2026-02-30T00:00:00Z"),
        ("effective_deadline_utc", "9999-12-31T23:59:59-01:00"),
        ("coverage_complete", "true"),
    ],
)
def test_invalid_wire_rejected(field: str, value: object) -> None:
    """No raw payload, coercion, invalid date or terminal-newline timestamp."""
    payload = review_obligation_snapshot_payload(snapshot("a", "a", "pending"))
    payload[field] = value
    with pytest.raises(CredentialingContractError):
        parse_review_obligation_snapshot(payload)


def test_wire_roundtrip_detaches_and_normalises() -> None:
    """Offset-equivalent wire times preserve the same administrative evidence."""
    original = snapshot("a", "a", "on_time")
    payload = review_obligation_snapshot_payload(original)
    payload["snapshot_as_of_utc"] = "2026-01-10T10:00:00+10:00"
    assert parse_review_obligation_snapshot(payload) == original
    retained = merge_review_obligation_snapshots([], [original])
    object.__setattr__(original, "case_id", "changed")
    assert retained[0].case_id == "a"


@pytest.mark.parametrize("boundary", ["payload", "merge", "report"])
def test_forced_record_mutation_revalidated(boundary: str) -> None:
    """Public boundaries do not trust frozen dataclass internals."""
    original = snapshot("a", "a", "pending")
    trusted = scope([original])
    object.__setattr__(original, "coverage_complete", 1)
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - three public entry points
        if boundary == "payload":
            review_obligation_snapshot_payload(original)
        elif boundary == "merge":
            merge_review_obligation_snapshots([], [original])
        else:
            report_review_completion([original], scope=trusted, policy=policy())


def test_policy_scope_and_grant_mutation_revalidated() -> None:
    """Frozen policy and nested grants are validated at report use."""
    current = policy()
    trusted = scope([snapshot("a", "a", "pending")])
    object.__setattr__(current, "source_complete", 1)
    with pytest.raises(CredentialingContractError):
        report_review_completion([], scope=trusted, policy=current)
    object.__setattr__(current, "source_complete", True)
    object.__setattr__(next(iter(trusted.granted_obligations)), "case_id", "a\n")
    with pytest.raises(CredentialingContractError):
        report_review_completion([], scope=trusted, policy=current)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("review_kind", "unknown"),
        ("source_complete", 1),
        ("minimum_case_count", True),
        ("minimum_case_count", 1),
        ("definition_version", "v1\n"),
    ],
)
def test_invalid_policy_rejected(field: str, value: object) -> None:
    """Reporting parameters require explicit strict trusted values."""
    with pytest.raises(CredentialingContractError):
        policy(**{field: value})


def test_wrong_role_and_foreign_record_rejected() -> None:
    """Case analyst and arbitrary objects cannot bypass public contracts."""
    with pytest.raises(CredentialingContractError):
        ReviewReportScope(role="case_analyst", granted_obligations=())
    with pytest.raises(CredentialingContractError):
        review_obligation_snapshot_payload(object())  # type: ignore[arg-type]


def test_supervision_uses_explicit_matching_kind() -> None:
    """The same arithmetic supports separately defined supervision reviews."""
    rows = [
        replace(snapshot(case, case, "on_time"), review_kind="supervision_review") for case in "ab"
    ]
    result = report(rows, review_kind="supervision_review")
    assert result.population_completion_rate == result.population_on_time_rate == 1
    assert (
        not {"case_id", "obligation_id", "source_system", "captured_at_utc"} & asdict(result).keys()
    )


def test_frozenset_grants_detach_to_canonical_tuple() -> None:
    """An explicit immutable grant set has stable detached ordering."""
    grants = frozenset(
        {
            ReviewObligationGrant(obligation_id="b", case_id="b"),
            ReviewObligationGrant(obligation_id="a", case_id="a"),
        }
    )
    result = ReviewReportScope(role="report_reader", granted_obligations=grants)
    assert tuple(grant.obligation_id for grant in result.granted_obligations) == ("a", "b")
