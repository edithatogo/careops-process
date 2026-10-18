"""Case-grain retained-ledger alignment reporting with joint-cell protection."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Never

from careops_process.credentialing import CredentialingContractError
from careops_process.credentialing_alignment import AlignmentModel, align_traces
from careops_process.credentialing_assurance import CredentialingLedger
from careops_process.credentialing_measurements import validate_measurement_scope

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet
    from pathlib import Path

    from careops_process.credentialing import CredentialingFact

_MAX_TRACES = 64
_MAX_EVENTS = 128


@dataclass(frozen=True, slots=True)
class AlignmentReport:
    """Aggregate only; a suppressed release contains no metrics or classifications."""

    status: str
    population_cases: int | None = None
    eligible_cases: int | None = None
    aligned_cases: int | None = None
    fit_cases: int | None = None
    deviating_cases: int | None = None
    mean_case_fitness: float | None = None
    exclusions: tuple[tuple[str, int], ...] | None = None
    retained_source_events: int | None = None
    observed_case_event_occurrences: int | None = None
    excluded_inferred_case_event_occurrences: int | None = None


def _fail(message: str) -> Never:
    raise CredentialingContractError(message)


def _reason(
    observed: list[CredentialingFact],
    *,
    complete: bool,
    model: AlignmentModel,
) -> str:
    if not observed:
        return "no_observed_trace"
    if not complete:
        return "partial_or_censored_trace"
    if any(
        (item.qualifiers.pathway_code, item.qualifiers.authority_mapping_version)
        != (model.pathway_code, model.authority_version)
        for item in observed
    ):
        return "model_binding_mismatch"
    if len({item.timestamp_utc for item in observed}) != len(observed):
        return "ambiguous_source_order"
    if len(observed) > _MAX_EVENTS:
        return "trace_resource_limit"
    return "eligible"


def report_alignments(  # noqa: C901, PLR0912, PLR0913 -- Cohort reconciliation boundary.
    ledger: CredentialingLedger,
    model: AlignmentModel,
    *,
    role: str,
    case_ids: AbstractSet[str],
    complete_case_ids: AbstractSet[str],
    minimum_cases: int,
    python: Path,
    timeout_seconds: float = 30,
) -> AlignmentReport:
    """Recompute from retained facts; caller authenticates scope and completeness.

    Complete means the approved observation window contains a full case trace,
    not that the case conformed or reached a model's final state. A missing final
    activity on an explicitly complete trace is a real scored deviation. Partial
    traces are excluded, rather than penalised for future unexecuted work.

    The ledger must be a consistent trusted service snapshot under its storage
    transaction/lock. This function neither authenticates role strings nor
    approves model bindings, temporal coverage or a causal evaluation.
    """
    if type(role) is not str or type(ledger) is not CredentialingLedger:
        _fail("Alignment requires concrete role and retained ledger")
    grants, floor = validate_measurement_scope(
        role=role, case_ids=case_ids, minimum_cases=minimum_cases
    )
    complete, _ = validate_measurement_scope(
        role=role, case_ids=complete_case_ids, minimum_cases=minimum_cases
    )
    if not complete <= grants:
        _fail("Trace completeness must be within granted cases")
    if type(model) is not AlignmentModel:
        _fail("Alignment requires a concrete model binding")
    model = AlignmentModel(**vars(model))
    # Reconstruct state so restored tombstones cannot be bypassed by stale facts.
    retained = CredentialingLedger(
        projection=ledger.projection,
        tombstoned_event_ids=ledger.tombstoned_event_ids,
        inference_provenance=ledger.inference_provenance,
    )
    facts = retained.projection.facts
    observations: dict[str, list[CredentialingFact]] = {case: [] for case in grants}
    inferred: Counter[str] = Counter()
    scoped_event_ids: set[str] = set()
    for fact in facts:
        linked = grants.intersection(fact.object_ids)
        if linked:
            scoped_event_ids.add(fact.event_id)
        for case in linked:
            if fact.observed_or_inferred == "observed":
                observations[case].append(fact)
            else:
                inferred[case] += 1
    cases = sorted(grants)
    reasons = {
        case: _reason(observations[case], complete=case in complete, model=model) for case in cases
    }
    signatures = {
        case: (reasons[case], bool(observations[case]), bool(inferred[case])) for case in cases
    }
    if len(grants) < floor or any(count < floor for count in Counter(signatures.values()).values()):
        return AlignmentReport("suppressed")
    eligible = [case for case in cases if reasons[case] == "eligible"]
    exclusions = tuple(
        sorted(Counter(reason for reason in reasons.values() if reason != "eligible").items())
    )
    common = AlignmentReport(
        "no_eligible_traces",
        population_cases=len(grants),
        eligible_cases=len(eligible),
        aligned_cases=0,
        exclusions=exclusions,
        retained_source_events=len(scoped_event_ids),
        observed_case_event_occurrences=sum(map(len, observations.values())),
        excluded_inferred_case_event_occurrences=sum(inferred.values()),
    )
    if not eligible:
        return common
    if len(eligible) > _MAX_TRACES:
        return replace(common, status="resource_limit")
    result = align_traces(
        model,
        tuple(tuple(item.activity for item in observations[case]) for case in eligible),
        python=python,
        timeout_seconds=timeout_seconds,
    )
    if result.status != "available" or result.fitness is None:
        return replace(common, status=result.status)
    outcome = dict(zip(eligible, result.fitness, strict=True))
    joint = Counter(
        (signatures[case], "fit" if outcome[case] == 1 else "deviating")
        if case in outcome
        else (signatures[case], "excluded")
        for case in cases
    )
    if any(count < floor for count in joint.values()):
        return AlignmentReport("suppressed")
    return replace(
        common,
        status="available",
        aligned_cases=len(eligible),
        fit_cases=sum(fitness == 1 for fitness in result.fitness),
        deviating_cases=sum(fitness < 1 for fitness in result.fitness),
        mean_case_fitness=math.fsum(result.fitness) / len(eligible),
    )
