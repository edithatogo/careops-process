# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Synthetic case denominators, interval reconciliation and joint-cell privacy."""

# Numeric literals are independent expected fixture outcomes.
# ruff: noqa: PLR2004

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from careops_process.credentialing_local_reporting import (
    CaseReportingObservation,
    ReportingDefinition,
    WorkInterval,
    report_local_credentialing,
)
from examples.credentialing_local_reporting import synthetic_local_report


def definition() -> ReportingDefinition:
    """Supply explicit synthetic vocabularies and reporting window."""
    return ReportingDefinition(
        definition_version="synthetic-v1",
        window_code="2026-Q3",
        pathway_codes=frozenset({"renewal", "temporary"}),
        reason_codes=frozenset({"missing-document", "review-needed"}),
    )


def observation(index: int, **changes: object) -> CaseReportingObservation:
    """Build one observed case snapshot; offsets partition its elapsed time."""
    payload: dict[str, object] = {
        "observation_id": f"obs-{index}",
        "case_id": f"case-{index}",
        "source_system": "synthetic",
        "definition_version": "synthetic-v1",
        "window_code": "2026-Q3",
        "pathway_code": "renewal",
        "correction_reasons": ("missing-document",),
        "further_information_reasons": (),
        "deferral_reasons": (),
        "exception_reasons": (),
        "observed_trace": ("request_received", "correction_requested", "case_completed"),
        "elapsed_minutes": 60.0,
        "intervals": (
            {"start_minute": 0.0, "end_minute": 40.0, "state": "queue"},
            {"start_minute": 40.0, "end_minute": 55.0, "state": "active"},
            {"start_minute": 55.0, "end_minute": 60.0, "state": "unknown"},
        ),
    }
    payload.update(changes)
    return CaseReportingObservation.model_validate(payload)


def report(records: list[CaseReportingObservation], *, source_complete: bool = True):  # noqa: ANN201
    """Use an explicit four-case trusted population."""
    return report_local_credentialing(
        records,
        role="report_reader",
        granted_case_ids=frozenset(f"case-{i}" for i in range(4)),
        definition=definition(),
        source_complete=source_complete,
        minimum_case_count=2,
    )


def test_case_rates_and_time_reconcile_without_event_denominators() -> None:
    """Two pathways and outcomes have case counts independent of trace length."""
    records = [observation(i) for i in range(2)] + [
        observation(i, pathway_code="temporary", correction_reasons=()) for i in range(2, 4)
    ]
    result = report([*records, records[0]])
    assert not result.suppressed
    assert result.population_case_count == result.observed_case_count == 4
    assert result.pathway_counts == (("renewal", 2), ("temporary", 2))
    assert result.pathway_mix == (("renewal", 0.5), ("temporary", 0.5))
    assert result.rates is not None
    correction = result.rates[0]
    assert correction.measure == "correction"
    assert correction.positive_case_count == 2
    assert correction.observed_rate == correction.population_rate == 0.5
    assert correction.reason_case_counts == (("missing-document", 2),)
    assert result.time is not None
    assert result.time.elapsed_minutes == 240
    assert result.time.queue_minutes == 160
    assert result.time.active_minutes == 60
    assert result.time.unknown_minutes == 20
    assert result.variants == ((("request_received", "correction_requested", "case_completed"), 4),)
    assert "case-0" not in str(asdict(result))


def test_missing_is_not_negative() -> None:
    """Unassessed cases cannot silently reduce a rate or supply elapsed work."""
    result = report([observation(i) for i in range(2)])
    assert result.missing_case_count == 2
    assert result.rates is not None
    assert result.rates[0].observed_rate == 1
    assert result.rates[0].population_rate is None
    assert result.rates[0].missing_case_count == 2


def test_joint_cells_suppress_safe_marginals() -> None:
    """A single cross-category combination suppresses every field, including totals."""
    records = [
        observation(0, pathway_code="renewal", correction_reasons=()),
        observation(1, pathway_code="renewal"),
        observation(2, pathway_code="temporary", correction_reasons=()),
        observation(3, pathway_code="temporary"),
    ]
    assert asdict(report(records)) == {
        "suppressed": True,
        "population_case_count": None,
        "observed_case_count": None,
        "missing_case_count": None,
        "pathway_counts": None,
        "pathway_mix": None,
        "missing_pathway_case_count": None,
        "rates": None,
        "time": None,
        "variants": None,
        "missing_trace_case_count": None,
    }


def test_conflicting_replay_fails() -> None:
    """An observation identity cannot change content."""
    with pytest.raises(ValueError, match="Conflicting"):
        report([observation(0), observation(0, pathway_code="temporary")])


@pytest.mark.parametrize("end", [59.0, 61.0])
def test_intervals_must_partition_elapsed(end: float) -> None:
    """Reject incomplete and overlong time allocations instead of guessing queue time."""
    with pytest.raises(ValueError, match="partition"):
        observation(0, intervals=({"start_minute": 0.0, "end_minute": end, "state": "active"},))


@pytest.mark.parametrize("field", ["correction", "further_information", "deferral", "exception"])
def test_each_rate_uses_cases_and_overlapping_reason_memberships(field: str) -> None:
    """Several reasons do not create several positive cases."""
    records = [
        observation(i, **{f"{field}_reasons": ("missing-document", "review-needed")})
        for i in range(2)
    ] + [observation(i, **{f"{field}_reasons": ()}) for i in range(2, 4)]
    rates = report(records).rates
    assert rates is not None
    rate = next(item for item in rates if item.measure == field)
    assert (rate.assessed_case_count, rate.positive_case_count, rate.negative_case_count) == (
        4,
        2,
        2,
    )
    assert rate.observed_rate == 0.5
    assert rate.reason_case_counts == (("missing-document", 2), ("review-needed", 2))
    assert (
        rate.reason_observed_rates
        == rate.reason_population_rates
        == (
            ("missing-document", 0.5),
            ("review-needed", 0.5),
        )
    )


def test_coverage_attestation_does_not_fill_missing_outcomes() -> None:
    """Complete observations without trusted coverage have only an observed rate."""
    rates = report([observation(i) for i in range(4)], source_complete=False).rates
    assert rates is not None
    assert rates[0].observed_rate == 1
    assert rates[0].population_rate is None
    assert rates[0].population_rate_unavailable_reason == "source_coverage_unconfirmed"


def test_all_unavailable_preserves_explicit_missingness() -> None:
    """No observations supplies no negative outcomes or observed time."""
    result = report([])
    assert not result.suppressed
    assert (
        result.population_case_count,
        result.observed_case_count,
        result.missing_case_count,
    ) == (4, 0, 4)
    assert result.pathway_counts == result.pathway_mix == result.variants == ()
    assert result.missing_trace_case_count == result.missing_pathway_case_count == 4
    assert result.rates is not None
    assert all(item.observed_rate is None for item in result.rates)
    assert result.time is not None
    assert (result.time.assessed_case_count, result.time.missing_case_count) == (0, 4)


def test_missing_fields_not_whole_case() -> None:
    """Per-measure missingness is independent of whether a case snapshot exists."""
    result = report(
        [
            observation(
                i,
                correction_reasons=None,
                pathway_code=None,
                observed_trace=None,
                elapsed_minutes=None,
                intervals=None,
            )
            for i in range(4)
        ]
    )
    assert result.observed_case_count == 4
    assert result.rates is not None
    assert result.rates[0].assessed_case_count == 0
    assert result.rates[1].negative_case_count == 4
    assert result.time is not None
    assert result.time.missing_case_count == 4


def test_consistent_case_reassessment_counts_once() -> None:
    """Different observation identifiers do not multiply the same case."""
    records = [observation(i) for i in range(4)]
    assert report([*records, observation(0, observation_id="repeat")]) == report(records)
    with pytest.raises(ValueError, match="Conflicting reporting case"):
        report([*records, observation(0, observation_id="repeat", correction_reasons=())])


def test_ungranted_case_never_changes_aggregates() -> None:
    """A structurally valid record outside the trusted population contributes nothing."""
    records = [observation(i) for i in range(4)]
    assert report([*records, observation(99, pathway_code="private-pathway")]) == report(records)


@pytest.mark.parametrize(
    "changes",
    [
        {"definition_version": "other"},
        {"window_code": "other"},
        {"pathway_code": "unregistered"},
        {"exception_reasons": ("unregistered",)},
    ],
)
def test_approved_mapping_boundaries(changes: dict[str, object]) -> None:
    """Valid-looking codes do not establish membership of a supplied vocabulary."""
    with pytest.raises(ValueError, match=r"mismatch|Unregistered"):
        report([observation(0, **changes)])


@pytest.mark.parametrize(
    "changes",
    [
        {"case_id": "case-0\n"},
        {"observation_id": "a@example.org"},
        {"source_system": "raw narrative"},
        {"definition_version": "v1\n"},
        {"window_code": "q1\n"},
        {"pathway_code": "renewal\n"},
        {"correction_reasons": ("text\n",)},
        {"correction_reasons": ("same", "same")},
        {"observed_trace": ("inferred_activity",)},
        {"observed_trace": ()},
        {"raw_payload": "forbidden"},
        {"elapsed_minutes": True},
        {"elapsed_minutes": float("nan")},
        {"elapsed_minutes": float("inf")},
        {"elapsed_minutes": -1},
        {"elapsed_minutes": "60"},
        {"elapsed_minutes": None},
        {"intervals": None},
        {"intervals": ({"start_minute": 0, "end_minute": 0, "state": "active"},)},
        {"intervals": ({"start_minute": 0, "end_minute": 60, "state": "inferred"},)},
        {"intervals": ({"start_minute": 1, "end_minute": 60, "state": "active"},)},
        {
            "intervals": (
                {"start_minute": 0, "end_minute": 40, "state": "active"},
                {"start_minute": 39, "end_minute": 60, "state": "queue"},
            )
        },
    ],
)
def test_invalid_observations_fail(changes: dict[str, object]) -> None:
    """Reject raw fields, malformed tokens, coerced minutes and invented partitions."""
    with pytest.raises(ValueError, match=r"validation error|Measurement|Expected"):
        observation(0, **changes)


def test_tampered_record_and_nested_interval_revalidated() -> None:
    """Frozen data is not trusted after construction."""
    record = observation(0)
    object.__setattr__(record, "case_id", "raw forbidden")
    with pytest.raises(ValueError, match=r"validation error|Measurement|Expected"):
        report([record])
    record = observation(0)
    assert record.intervals is not None
    object.__setattr__(record.intervals[0], "end_minute", -1)
    with pytest.raises(ValueError, match=r"validation error|Measurement|Expected"):
        report([record])


def test_subclasses_cannot_bypass_revalidation() -> None:
    """Reject alternate concrete types even if constructed without validation."""

    class UntrustedRecord(CaseReportingObservation):
        pass

    class UntrustedInterval(WorkInterval):
        pass

    class UntrustedDefinition(ReportingDefinition):
        pass

    record = UntrustedRecord.model_construct(**observation(0).model_dump())
    with pytest.raises(ValueError, match="concrete"):
        report([record])
    record = observation(0)
    object.__setattr__(
        record,
        "intervals",
        (UntrustedInterval.model_construct(start_minute=0, end_minute=60, state="active"),),
    )
    with pytest.raises(ValueError, match="concrete"):
        report([record])
    with pytest.raises(ValueError, match="definition"):
        report_local_credentialing(
            [],
            role="report_reader",
            granted_case_ids=frozenset[str](),
            definition=UntrustedDefinition.model_construct(),
            source_complete=True,
            minimum_case_count=2,
        )


@pytest.mark.parametrize(
    ("role", "grants", "threshold", "coverage"),
    [
        ("operator", frozenset({"case-0"}), 2, True),
        ("report_reader", ["case-0"], 2, True),
        ("report_reader", frozenset({"case-0\n"}), 2, True),
        ("report_reader", frozenset[str](), 1, True),
        ("report_reader", frozenset[str](), True, True),
        ("report_reader", frozenset[str](), 2, 1),
    ],
)
def test_scope_rejection(role: str, grants: object, threshold: object, coverage: object) -> None:
    """Public scope validation rejects role, reference, floor and boolean coercion."""
    with pytest.raises(ValueError, match=r"validation error|Measurement|Expected|concrete"):
        report_local_credentialing(
            [],
            role=role,
            granted_case_ids=grants,  # type: ignore[arg-type]
            definition=definition(),
            source_complete=coverage,  # type: ignore[arg-type]
            minimum_case_count=threshold,  # type: ignore[arg-type]
        )  # type: ignore[arg-type]


def test_rare_variant_suppresses_even_when_pathway_and_rates_are_safe() -> None:
    """A singleton variant cannot escape via otherwise common categories."""
    records = [observation(i) for i in range(4)]
    records[0] = observation(0, observed_trace=("request_received", "case_withdrawn"))
    assert report(records).suppressed


def test_wire_round_trip_and_schema_are_current() -> None:
    """Published structural schema matches the actual runtime model."""
    record = observation(0)
    assert CaseReportingObservation.model_validate_json(record.model_dump_json()) == record
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1] / "contracts" / "credentialing-case-reporting.json"
        ).read_text()
    )
    assert schema == CaseReportingObservation.model_json_schema()


def test_finite_inputs_cannot_overflow_released_totals() -> None:
    """Large but individually finite spans must not produce infinite summaries."""
    records = [
        observation(
            i,
            elapsed_minutes=1e308,
            intervals=({"start_minute": 0.0, "end_minute": 1e308, "state": "active"},),
        )
        for i in range(4)
    ]
    with pytest.raises(ValueError, match="finite range"):
        report(records)


def test_zero_elapsed_is_explicit_not_missing() -> None:
    """A source-attested instantaneous case has an empty zero-length partition."""
    result = report([observation(i, elapsed_minutes=0.0, intervals=()) for i in range(4)])
    assert result.time is not None
    assert (result.time.assessed_case_count, result.time.missing_case_count) == (4, 0)
    assert result.time.elapsed_minutes == 0


def test_runnable_example_has_independent_case_and_time_expectations() -> None:
    """Repeated correction activities remain one positive assessment per case."""
    result = synthetic_local_report()
    assert not result.suppressed
    assert result.population_case_count == 4
    assert result.pathway_counts == (("renewal", 2), ("temporary", 2))
    assert result.rates is not None
    assert [(rate.measure, rate.observed_rate) for rate in result.rates] == [
        ("correction", 0.5),
        ("further_information", 0),
        ("deferral", 0),
        ("exception", 0.5),
    ]
    assert result.variants is not None
    assert [count for _, count in result.variants] == [2, 2]
    assert result.variants[1][0] == (
        "request_received",
        "correction_requested",
        "correction_received",
        "correction_requested",
        "correction_received",
        "case_completed",
    )
    assert result.time is not None
    assert (
        result.time.elapsed_minutes,
        result.time.queue_minutes,
        result.time.active_minutes,
        result.time.unknown_minutes,
    ) == (240, 160, 60, 20)


def test_integer_subclass_cannot_disable_suppression() -> None:
    """A hostile numeric comparison must never release a singleton report."""

    class FalseFloor(int):
        def __lt__(self, _other: object) -> bool:
            return False

        def __gt__(self, _other: object) -> bool:
            return False

    with pytest.raises(ValueError, match="concrete"):
        report_local_credentialing(
            [observation(0)],
            role="report_reader",
            granted_case_ids=frozenset({"case-0"}),
            definition=definition(),
            source_complete=True,
            minimum_case_count=FalseFloor(2),
        )


def test_scalar_subclasses_cannot_override_scope_comparisons() -> None:
    """Keep trusted scope inputs detached from custom equality/hash behavior."""

    class ReferenceSubclass(str):
        __slots__ = ()

    with pytest.raises(ValueError, match="concrete"):
        report_local_credentialing(
            [],
            role=ReferenceSubclass("report_reader"),
            granted_case_ids=frozenset(),
            definition=definition(),
            source_complete=True,
            minimum_case_count=2,
        )

    with pytest.raises(ValueError, match="concrete"):
        report_local_credentialing(
            [],
            role="report_reader",
            granted_case_ids=frozenset({ReferenceSubclass("case-0")}),
            definition=definition(),
            source_complete=True,
            minimum_case_count=2,
        )


@given(st.lists(st.integers(min_value=0, max_value=3), max_size=30))
def test_replay_and_order_cannot_change_any_released_measure(replay: list[int]) -> None:
    """Arbitrary replay/order leaves case demand, rates, time and variants invariant."""
    records = [observation(i) for i in range(4)]
    repeated = [records[index] for index in replay]
    assert report([*reversed(records), *repeated]) == report(records)
