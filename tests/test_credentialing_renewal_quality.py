"""Explicit renewal deadline, denominator and censoring evidence."""

# Numeric expectations and fixture flags are explicit measured outcomes.
# ruff: noqa: PLR2004

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_renewal_quality import (
    RenewalReportPolicy,
    RenewalReportScope,
    RenewalSnapshot,
    merge_renewal_snapshots,
    parse_renewal_snapshot,
    renewal_snapshot_payload,
    report_overdue_renewals,
)

AS_OF = datetime(2026, 1, 10, tzinfo=UTC)


def snapshot(case: str, state: str = "pending") -> RenewalSnapshot:
    """Create synthetic source-defined deadline evidence."""
    return RenewalSnapshot(
        observation_id=case,
        case_id=case,
        renewal_cycle_code="cycle-1",
        source_system="synthetic",
        definition_version="v1",
        snapshot_as_of_utc=AS_OF,
        captured_at_utc=AS_OF,
        effective_deadline_utc=AS_OF - timedelta(days=1),
        state=state,
        completion_at_utc=AS_OF if state == "completed" else None,
        coverage_complete=True,
    )


def test_matured_denominator() -> None:
    """Two completed plus two overdue obligations produce one half."""
    result = report_overdue_renewals(
        [snapshot("a"), snapshot("b"), snapshot("c", "completed"), snapshot("d", "completed")],
        policy=RenewalReportPolicy(
            definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
        ),
        scope=RenewalReportScope(role="report_reader", granted_case_ids=frozenset("abcd")),
    )
    assert result.observed_overdue_rate == result.population_overdue_rate == 0.5
    assert result.matured_case_count == 4


def test_missing_is_not_overdue() -> None:
    """Unknown population cannot become either overdue or measured zero."""
    result = report_overdue_renewals(
        [],
        policy=RenewalReportPolicy(
            definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
        ),
        scope=RenewalReportScope(role="report_reader", granted_case_ids=frozenset("ab")),
    )
    assert result.observed_overdue_rate is None
    assert result.population_rate_unavailable_reason == "incomplete_case_evidence"
    assert dict(result.case_counts or ())["missing_snapshot"] == 2


def report(rows: list[RenewalSnapshot], **changes: Any) -> Any:  # noqa: ANN401
    """Report synthetic cases using explicit default policy and grants."""
    policy = RenewalReportPolicy(
        definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
    )
    return report_overdue_renewals(
        rows,
        policy=replace(policy, **changes),
        scope=RenewalReportScope(role="report_reader", granted_case_ids=frozenset("abcd")),
    )


@pytest.mark.parametrize(
    ("state", "changes", "expected"),
    [
        ("pending", {}, "matured_outstanding_overdue"),
        ("completed", {}, "matured_completed"),
        ("out_of_scope", {"effective_deadline_utc": None}, "censored_out_of_scope"),
        ("unknown", {}, "unknown_status"),
        ("pending", {"coverage_complete": False}, "unknown_status"),
        ("pending", {"effective_deadline_utc": None}, "missing_deadline"),
        ("pending", {"effective_deadline_utc": AS_OF}, "not_yet_due"),
        ("completed", {"effective_deadline_utc": AS_OF + timedelta(days=1)}, "not_yet_due"),
    ],
)
def test_classification_partition(state: str, changes: dict[str, object], expected: str) -> None:
    """Each case occupies exactly one evidence category, not several denominators."""
    rows = [replace(snapshot(case, state), **changes) for case in "abcd"]  # type: ignore[arg-type]
    result = report(rows)
    counts = dict(result.case_counts)
    assert sum(counts.values()) == result.population_case_count == 4
    assert counts[expected] == 4


def test_future_completed_is_not_matured_or_overdue() -> None:
    """Completed obligations with future deadlines cannot inflate matured counts."""
    rows = [snapshot(case, "completed") for case in "ab"] + [
        replace(snapshot(case, "completed"), effective_deadline_utc=AS_OF + timedelta(days=1))
        for case in "cd"
    ]
    result = report(rows)
    assert result.matured_case_count == 2
    assert result.observed_overdue_rate == result.population_overdue_rate == 0


def test_missing_unknown_and_censored_stay_distinct() -> None:
    """Unknown evidence and explicit censoring reconcile independently."""
    rows = [snapshot(case, "unknown") for case in "ab"] + [
        snapshot(case, "out_of_scope") for case in "cd"
    ]
    result = report(rows)
    counts = dict(result.case_counts)
    assert counts["unknown_status"] == counts["censored_out_of_scope"] == 2
    assert result.observed_overdue_rate is None
    assert result.population_rate_unavailable_reason == "incomplete_case_evidence"


def test_no_matured_and_no_coverage_have_explicit_reasons() -> None:
    """No overdue denominator is unavailable; coverage has documented precedence."""
    rows = [replace(snapshot(case), effective_deadline_utc=AS_OF) for case in "abcd"]
    assert report(rows).population_rate_unavailable_reason == "no_matured_cases"
    assert (
        report(rows, source_complete=False).population_rate_unavailable_reason
        == "source_coverage_unconfirmed"
    )
    assert (
        report([snapshot(case) for case in "abcd"], source_complete=False).population_overdue_rate
        is None
    )


def test_replay_and_consistent_case_duplicates_cannot_change_rates() -> None:
    """Distinct capture records collapse only when their case evidence agrees."""
    rows = [snapshot(case) for case in "abcd"]
    duplicate = replace(rows[0], observation_id="other", captured_at_utc=AS_OF + timedelta(hours=1))
    assert report(rows) == report([*rows, *rows, duplicate])
    assert len(merge_renewal_snapshots(rows, rows)) == 4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_system", "other"),
        ("renewal_cycle_code", "cycle-2"),
        ("effective_deadline_utc", AS_OF),
        ("coverage_complete", False),
        ("state", "unknown"),
    ],
)
def test_conflicting_case_snapshots_fail(field: str, value: object) -> None:
    """No latest-state/deadline preference erases contradictory evidence."""
    original = snapshot("a")
    conflicting = replace(original, observation_id="other", **{field: value})  # type: ignore[arg-type]
    with pytest.raises(CredentialingContractError):
        report([original, conflicting])


def test_changed_id_replay_fails() -> None:
    """An observation identity cannot switch sources silently."""
    original = snapshot("a")
    with pytest.raises(CredentialingContractError):
        merge_renewal_snapshots([original], [replace(original, source_system="other")])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("definition_version", "other"),
        ("snapshot_as_of_utc", AS_OF - timedelta(days=1)),
    ],
)
def test_wrong_reporting_reference_fails(field: str, value: object) -> None:
    """Explicit report instant/definition never selects a latest snapshot."""
    with pytest.raises(CredentialingContractError):
        report([replace(snapshot("a"), **{field: value})])  # type: ignore[arg-type]


def test_valid_outside_grants_does_not_change_report() -> None:
    """Other case evidence cannot affect aggregate counts or denominator."""
    rows = [snapshot(case) for case in "abcd"]
    assert report(rows) == report([*rows, replace(snapshot("outside"), definition_version="other")])


def test_rare_cells_suppress_all_fields() -> None:
    """One completed, missing, censored or future case suppresses every value."""
    base = [snapshot(case) for case in "abc"]
    for extra in [
        [],
        [snapshot("d", "completed")],
        [snapshot("d", "out_of_scope")],
        [replace(snapshot("d"), effective_deadline_utc=AS_OF)],
    ]:
        result = report(base + extra)
        assert result.suppressed
        assert all(value is None for key, value in asdict(result).items() if key != "suppressed")


def test_empty_grants_suppressed() -> None:
    """Empty population does not produce a zero rate."""
    result = report_overdue_renewals(
        [],
        policy=RenewalReportPolicy(
            definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
        ),
        scope=RenewalReportScope(role="report_reader", granted_case_ids=frozenset()),
    )
    assert result.suppressed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observation_id", "a\n"),
        ("case_id", "a\n"),
        ("renewal_cycle_code", "cycle-1\n"),
        ("source_system", "synthetic\n"),
        ("definition_version", "v1\n"),
        ("source_system", "person@example.org"),
        ("source_system", "raw narrative"),
        ("coverage_complete", 1),
        ("state", "pending\n"),
        ("state", []),
        ("captured_at_utc", AS_OF - timedelta(seconds=1)),
        ("completion_at_utc", AS_OF),
        ("contract_version", "next"),
        ("effective_deadline_utc", datetime(2026, 1, 1)),  # noqa: DTZ001 - adversarial naive time
        ("effective_deadline_utc", datetime.fromisoformat("0001-01-01T00:00:00+01:00")),
    ],
)
def test_invalid_direct_snapshot_rejected(field: str, value: object) -> None:
    """Strict evidence types and UTC normalisation reject malformed records."""
    with pytest.raises(CredentialingContractError):
        replace(snapshot("a"), **{field: value})  # type: ignore[arg-type]


@pytest.mark.parametrize("completion", [None, AS_OF + timedelta(seconds=1)])
def test_completed_requires_past_or_present_completion(completion: datetime | None) -> None:
    """Future completion cannot establish a completed state at the snapshot."""
    with pytest.raises(CredentialingContractError):
        replace(snapshot("a", "completed"), completion_at_utc=completion)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("body", "raw"),
        ("kind", "other"),
        ("contract_version", "other"),
        ("snapshot_as_of_utc", None),
        ("captured_at_utc", "2026-01-10T00:00:00Z\n"),
        ("effective_deadline_utc", "2026-02-30T00:00:00Z"),
        ("effective_deadline_utc", "9999-12-31T23:59:59-01:00"),
        ("coverage_complete", "true"),
    ],
)
def test_invalid_wire_snapshot_rejected(field: str, value: object) -> None:
    """Wire input accepts no raw fields, coercion or malformed instants."""
    payload = renewal_snapshot_payload(snapshot("a"))
    payload[field] = value
    with pytest.raises(CredentialingContractError):
        parse_renewal_snapshot(payload)


def test_wire_roundtrip_and_detachment() -> None:
    """Round trips detach records and preserve canonical offset-equivalent instants."""
    original = snapshot("a")
    payload = renewal_snapshot_payload(original)
    payload["snapshot_as_of_utc"] = "2026-01-10T10:00:00+10:00"
    assert parse_renewal_snapshot(payload) == original
    retained = merge_renewal_snapshots([], [original])
    object.__setattr__(original, "case_id", "changed")
    assert retained[0].case_id == "a"


@pytest.mark.parametrize("boundary", ["payload", "merge", "report"])
def test_record_mutation_cannot_bypass_validation(boundary: str) -> None:
    """Frozen instances are still revalidated at each public boundary."""
    item = snapshot("a")
    object.__setattr__(item, "coverage_complete", 1)
    with pytest.raises(CredentialingContractError):  # noqa: PT012 - three public boundaries
        if boundary == "payload":
            renewal_snapshot_payload(item)
        elif boundary == "merge":
            merge_renewal_snapshots([], [item])
        else:
            report([item])


def test_policy_and_scope_mutations_revalidated() -> None:
    """A forged frozen policy or grants cannot bypass report validation."""
    policy = RenewalReportPolicy(
        definition_version="v1", as_of_utc=AS_OF, source_complete=True, minimum_case_count=2
    )
    scope = RenewalReportScope(role="report_reader", granted_case_ids=frozenset("ab"))
    object.__setattr__(policy, "source_complete", 1)
    with pytest.raises(CredentialingContractError):
        report_overdue_renewals([], policy=policy, scope=scope)
    object.__setattr__(policy, "source_complete", True)
    object.__setattr__(scope, "granted_case_ids", "ab")
    with pytest.raises(CredentialingContractError):
        report_overdue_renewals([], policy=policy, scope=scope)


def test_wrong_record_type_rejected() -> None:
    """Foreign records produce a controlled error."""
    with pytest.raises(CredentialingContractError):
        renewal_snapshot_payload(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("definition_version", "v1\n"),
        ("source_complete", 1),
        ("minimum_case_count", True),
        ("minimum_case_count", 1),
        ("as_of_utc", datetime(2026, 1, 10)),  # noqa: DTZ001 - reject naive policy time
    ],
)
def test_invalid_report_policy_rejected(field: str, value: object) -> None:
    """Policy is validated before any snapshot data can influence a report."""
    with pytest.raises(CredentialingContractError):
        report([], **{field: value})


@pytest.mark.parametrize("grants", ["ab", ["a", "b"], {"a\n", "b"}])
def test_invalid_scope_grants_rejected(grants: Any) -> None:  # noqa: ANN401
    """No implicit iterator/list/string authorisation or newline references."""
    with pytest.raises(CredentialingContractError):
        RenewalReportScope(role="report_reader", granted_case_ids=grants)


def test_untrusted_role_rejected() -> None:
    """Case access does not grant aggregate reporting authority."""
    with pytest.raises(CredentialingContractError):
        RenewalReportScope(role="case_analyst", granted_case_ids=frozenset("ab"))


def test_report_omits_identifiers_and_source_times() -> None:
    """Aggregate output contains only controlled count labels and numbers."""
    result = asdict(report([snapshot(case) for case in "abcd"]))
    assert (
        not {"case_id", "renewal_cycle_code", "observation_id", "captured_at_utc"} & result.keys()
    )
