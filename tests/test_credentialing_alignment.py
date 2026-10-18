"""Canonical model boundaries and optional backend synthetic evidence."""

from __future__ import annotations

# Independent synthetic arithmetic and subprocess-boundary test doubles.
# ruff: noqa: PLR2004
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

import pytest

from careops_process import credentialing_alignment as backend
from careops_process import credentialing_alignment_reporting as reporting
from careops_process.credentialing import CredentialingContractError, CredentialingProjection
from careops_process.credentialing_alignment import AlignmentModel, AlignmentResult, align_traces
from careops_process.credentialing_assurance import CredentialingLedger, InferenceRun


def model(xml: bytes | None = None) -> AlignmentModel:
    """Supply an explicitly bound synthetic two-step model."""
    artifact = (
        xml
        or b"""<pnml>
    <net id="test" type="http://www.pnml.org/version-2009/grammar/pnmlcoremodel"><page id="p">
    <place id="s"/><place id="m"/><place id="f"/>
    <transition id="a"><name><text>request_received</text></name></transition>
    <transition id="b"><name><text>case_completed</text></name></transition>
    <arc id="x1" source="s" target="a"/><arc id="x2" source="a" target="m"/>
    <arc id="x3" source="m" target="b"/><arc id="x4" source="b" target="f"/>
    </page></net></pnml>"""
    )
    return AlignmentModel(
        pnml=artifact,
        sha256=hashlib.sha256(artifact).hexdigest(),
        model_version="synthetic-v1",
        pathway_code="routine-renewal",
        authority_version="synthetic-v1",
        activity_mapping_version="synthetic-v1",
        initial_marking=(("s", 1),),
        final_marking=(("f", 1),),
    )


def test_unavailable_runtime_does_not_invent_fitness(tmp_path: Path) -> None:
    """Base profile remains usable without the optional interpreter."""
    result = align_traces(model(), (("request_received",),), python=tmp_path / "absent")
    assert result.status == "runtime_unavailable"
    assert result.fitness is None


def test_artifact_digest_is_checked() -> None:
    """The model reference binds actual bytes."""
    original = model()
    with pytest.raises(CredentialingContractError, match="digest"):
        replace(original, sha256="0" * 64)


@pytest.mark.parametrize("extension", [b"<inhibitor/>", b"<toolspecific/>", b"<color/>"])
def test_unsupported_semantics_fail_closed(extension: bytes) -> None:
    """A loader must not silently discard semantic extensions."""
    xml = model().pnml.replace(b"</page>", extension + b"</page>")
    with pytest.raises(CredentialingContractError, match="PNML"):
        model(xml)


def test_actual_pinned_backend_sequence() -> None:
    """Independently expected insertion/deletion/reordering costs and normalization."""
    python = optional_python()
    result = align_traces(
        model(),
        (
            ("request_received", "case_completed"),
            ("request_received",),
            ("request_received", "correction_requested", "case_completed"),
            ("case_completed", "request_received"),
        ),
        python=python,
    )
    assert result.status == "available"
    assert result.fitness == pytest.approx((1, 2 / 3, 0.8, 0.5))
    assert result.costs == (0, 10000, 10000, 20000)


def graph(
    places: tuple[str, ...],
    transitions: tuple[tuple[str, str | None], ...],
    arcs: tuple[tuple[str, str], ...],
) -> AlignmentModel:
    """Construct independent canonical synthetic choice/loop/concurrency nets."""
    place_xml = "".join(f'<place id="{p}"/>' for p in places)
    transition_xml = "".join(
        f'<transition id="{identity}">'
        + ("" if label is None else f"<name><text>{label}</text></name>")
        + "</transition>"
        for identity, label in transitions
    )
    arc_xml = "".join(
        f'<arc id="edge-{i}" source="{source}" target="{target}"/>'
        for i, (source, target) in enumerate(arcs)
    )
    return model(
        (
            '<pnml><net id="net" type="http://www.pnml.org/version-2009/grammar/pnmlcoremodel">'
            '<page id="page">' + place_xml + transition_xml + arc_xml + "</page></net></pnml>"
        ).encode()
    )


def optional_python() -> Path:
    """Use only the already installed optional runtime."""
    try:
        if version("pm4py") == backend.BACKEND_VERSION:
            return Path(sys.executable)
    except PackageNotFoundError:
        pass
    python = Path("artifacts/mining-venv/Scripts/python.exe").resolve()
    if not python.is_file():
        pytest.skip("Existing optional local runtime absent")
    return python


def test_actual_choice_and_repeat_loop() -> None:
    """Choice alternatives and zero/multiple visible correction loops are accepted."""
    net = graph(
        ("s", "m", "r", "f"),
        (
            ("start", "request_received"),
            ("review", "professional_review_completed"),
            ("committee", "committee_considered"),
            ("loop", "correction_requested"),
            ("finish", "case_completed"),
        ),
        (
            ("s", "start"),
            ("start", "m"),
            ("m", "review"),
            ("review", "r"),
            ("m", "committee"),
            ("committee", "r"),
            ("m", "loop"),
            ("loop", "m"),
            ("r", "finish"),
            ("finish", "f"),
        ),
    )
    result = align_traces(
        net,
        (
            ("request_received", "professional_review_completed", "case_completed"),
            ("request_received", "committee_considered", "case_completed"),
            (
                "request_received",
                "correction_requested",
                "correction_requested",
                "committee_considered",
                "case_completed",
            ),
            ("request_received", "case_completed"),
        ),
        python=optional_python(),
    )
    assert result.status == "available"
    assert result.fitness == pytest.approx((1, 1, 1, 0.8))
    assert result.costs == (0, 0, 0, 10000)


def test_actual_parallel_interleavings_and_tau_normalization() -> None:
    """Two legal concurrent orders fit despite two silent moves with nonzero raw cost."""
    net = graph(
        ("s", "m", "p1", "p2", "q1", "q2", "r", "f"),
        (
            ("start", "request_received"),
            ("split", None),
            ("review", "professional_review_completed"),
            ("committee", "committee_considered"),
            ("join", None),
            ("finish", "case_completed"),
        ),
        (
            ("s", "start"),
            ("start", "m"),
            ("m", "split"),
            ("split", "p1"),
            ("split", "p2"),
            ("p1", "review"),
            ("review", "q1"),
            ("p2", "committee"),
            ("committee", "q2"),
            ("q1", "join"),
            ("q2", "join"),
            ("join", "r"),
            ("r", "finish"),
            ("finish", "f"),
        ),
    )
    result = align_traces(
        net,
        (
            (
                "request_received",
                "professional_review_completed",
                "committee_considered",
                "case_completed",
            ),
            (
                "request_received",
                "committee_considered",
                "professional_review_completed",
                "case_completed",
            ),
            ("request_received", "professional_review_completed", "case_completed"),
        ),
        python=optional_python(),
    )
    assert result.status == "available"
    assert result.fitness == pytest.approx((1, 1, 6 / 7))
    assert result.costs == (2, 2, 10002)


@pytest.mark.parametrize("guard_tokens", [1, 2, 3])
def test_actual_weighted_transition_threshold_and_loop(guard_tokens: int) -> None:
    """A two-token guard must enable exactly at threshold and preserve loop tokens."""
    net = graph(
        ("s", "m", "g", "f"),
        (
            ("start", "request_received"),
            ("correction", "correction_requested"),
            ("finish", "case_completed"),
        ),
        (
            ("s", "start"),
            ("start", "m"),
            ("m", "finish"),
            ("finish", "f"),
            ("m", "correction"),
            ("correction", "m"),
            ("g", "correction"),
            ("correction", "g"),
        ),
    )
    xml = net.pnml.replace(
        b'source="g" target="correction"/>',
        b'source="g" target="correction"><inscription><text>2</text></inscription></arc>',
    )
    xml = xml.replace(
        b'source="correction" target="g"/>',
        b'source="correction" target="g"><inscription><text>2</text></inscription></arc>',
    )
    net = replace(
        model(xml),
        initial_marking=(("s", 1), ("g", guard_tokens)),
        final_marking=(("f", 1), ("g", guard_tokens)),
    )
    result = align_traces(
        net,
        (
            ("request_received", "correction_requested", "case_completed"),
            ("request_received", "correction_requested", "correction_requested", "case_completed"),
        ),
        python=optional_python(),
    )
    assert result.status == "available"
    assert result.fitness == pytest.approx((0.8, 2 / 3) if guard_tokens == 1 else (1, 1))
    assert result.costs == ((10000, 20000) if guard_tokens == 1 else (0, 0))


def test_actual_weighted_consumption_production_and_exact_final_tokens() -> None:
    """Consumption two/production three and residual start tokens are not unitized."""
    xml = model().pnml
    for source, target, weight in (("s", "a", 2), ("a", "m", 3), ("m", "b", 3), ("b", "f", 2)):
        xml = xml.replace(
            f'source="{source}" target="{target}"/>'.encode(),
            (
                f'source="{source}" target="{target}"><inscription>'
                f"<text>{weight}</text></inscription></arc>"
            ).encode(),
        )
    net = replace(model(xml), initial_marking=(("s", 3),), final_marking=(("s", 1), ("f", 2)))
    result = align_traces(
        net,
        (("request_received", "case_completed"), ("request_received",)),
        python=optional_python(),
    )
    assert result.status == "available"
    assert result.fitness == pytest.approx((1, 2 / 3))
    assert result.costs == (0, 10000)
    # A final marking omitting the residual start token is unreachable; never
    # silently discard that token and manufacture a perfect fit.
    unreachable = replace(net, final_marking=(("f", 2),))
    result = align_traces(
        unreachable, (("request_received", "case_completed"),), python=optional_python()
    )
    assert result.status == "backend_error"
    assert result.fitness is None


def test_superseded_default_algorithm_policy_is_rejected() -> None:
    """The weighted-semantics repair cannot reuse the former method binding."""
    with pytest.raises(CredentialingContractError, match="policy"):
        replace(model(), cost_policy="pm4py-2.7.23.8-default-alignment-v1")


@pytest.mark.parametrize("guard_tokens", [1, 2])
def test_actual_weighted_choice_keeps_disabled_branch_distinct(guard_tokens: int) -> None:
    """A genuinely enabled alternative does not enable a weighted guarded choice."""
    net = graph(
        ("s", "m", "g", "r", "f"),
        (
            ("start", "request_received"),
            ("guarded", "correction_requested"),
            ("alternative", "professional_review_completed"),
            ("finish", "case_completed"),
        ),
        (
            ("s", "start"),
            ("start", "m"),
            ("m", "guarded"),
            ("guarded", "r"),
            ("m", "alternative"),
            ("alternative", "r"),
            ("g", "guarded"),
            ("guarded", "g"),
            ("r", "finish"),
            ("finish", "f"),
        ),
    )
    xml = net.pnml
    for source, target in (("g", "guarded"), ("guarded", "g")):
        xml = xml.replace(
            f'source="{source}" target="{target}"/>'.encode(),
            (
                f'source="{source}" target="{target}"><inscription>'
                "<text>2</text></inscription></arc>"
            ).encode(),
        )
    net = replace(
        model(xml),
        initial_marking=(("s", 1), ("g", guard_tokens)),
        final_marking=(("f", 1), ("g", guard_tokens)),
    )
    result = align_traces(
        net,
        (
            ("request_received", "professional_review_completed", "case_completed"),
            ("request_received", "correction_requested", "case_completed"),
        ),
        python=optional_python(),
    )
    assert result.status == "available"
    assert result.fitness == pytest.approx((1, 2 / 3) if guard_tokens == 1 else (1, 1))
    assert result.costs == ((0, 20000) if guard_tokens == 1 else (0, 0))


@pytest.mark.parametrize(
    "change",
    [
        (
            b'<place id="s"/>',
            b'<place id="s"><initialMarking><text>1</text></initialMarking></place>',
        ),
        (b'<place id="s"/>', b'<place id="m"/>'),
        (b'source="s"', b'source="missing"'),
        (b'target="a"', b'target="m"'),
        (b'<transition id="a">', b'<transition id="a" invisible="true">'),
        (b"request_received", b"raw narrative"),
        (b'<place id="s"/>', b""),
        (b"<pnml>", b'<!DOCTYPE pnml [<!ENTITY x "unsafe">]><pnml>'),
    ],
)
def test_malformed_or_semantically_unsupported_model(change: tuple[bytes, bytes]) -> None:
    """Invalid identities, topology, labels, embedded markings and DTDs fail closed."""
    with pytest.raises(CredentialingContractError):
        model(model().pnml.replace(*change))


@pytest.mark.parametrize(
    "marking", [(("missing", 1),), (("s", True),), (("s", 0),), (("s", 1), ("s", 1)), ()]
)
def test_explicit_markings_reject_unknown_ambiguous_or_coerced_tokens(
    marking: tuple[tuple[str, int], ...],
) -> None:
    """Neither start nor final markings are inferred from topology."""
    with pytest.raises(CredentialingContractError):
        replace(model(), initial_marking=marking)


def test_trace_input_consumption_is_bounded() -> None:
    """An oversized iterator is stopped at max+1 without materialising the rest."""
    consumed = 0

    def traces() -> Iterator[tuple[str, ...]]:
        nonlocal consumed
        for _ in range(1000000):
            consumed += 1
            yield ("request_received",)

    result = align_traces(model(), traces(), python=Path(sys.executable))
    assert result.status == "resource_limit"
    assert consumed == 65


def test_wrong_or_absent_optional_package_is_explicit() -> None:
    """The normal profile can execute the worker without importing a mining dependency."""
    try:
        if version("pm4py") == backend.BACKEND_VERSION:
            pytest.skip("Current interpreter intentionally has pinned optional backend")
    except PackageNotFoundError:
        pass
    result = align_traces(model(), (("request_received",),), python=Path(sys.executable))
    assert result.status == "version_mismatch"
    assert result.fitness is None


@pytest.mark.parametrize(
    ("fitness", "costs"),
    [
        ([10**400], [0]),
        ([True], [0]),
        ([float("nan")], [0]),
        ([1.1], [0]),
        ([], []),
        ([1], [True]),
        ([1], [-1]),
    ],
)
def test_malformed_backend_numbers_are_unavailable(
    fitness: object,
    costs: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed IPC cannot throw an overflow or fabricate a valid result."""
    payload = {
        "status": "available",
        "backend": backend.BACKEND_VERSION,
        "policy": backend.COST_POLICY,
        "fitness": fitness,
        "costs": costs,
    }

    def reply(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        Path(args[4]).write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess[bytes](args, 0)

    monkeypatch.setattr(backend.subprocess, "run", reply)
    assert align_traces(
        model(), (("request_received",),), python=Path(sys.executable)
    ) == AlignmentResult("backend_error")


def test_actual_child_timeout_is_killed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real subprocess timeout path terminates a slow child and returns no fitness."""
    original = subprocess.run

    def slow(_args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return original(
            [sys.executable, "-I", "-c", "import time; time.sleep(5)"],
            timeout=cast("float", kwargs["timeout"]),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    monkeypatch.setattr(backend.subprocess, "run", slow)
    start = time.monotonic()
    result = align_traces(
        model(), (("request_received",),), python=Path(sys.executable), timeout_seconds=0.1
    )
    assert result.status == "resource_limit"
    assert result.fitness is None
    assert time.monotonic() - start < 3


def ledger_for(traces: tuple[tuple[str, ...], ...]) -> CredentialingLedger:
    """Generate fixed synthetic event traces, with distinct source IDs per case."""
    return CredentialingLedger(
        CredentialingProjection.model_validate(
            {
                "source": "careops-approve",
                "facts": [
                    {
                        "event_id": f"case-{case}-event-{index}",
                        "activity": label,
                        "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
                        "source_system": "synthetic",
                        "object_ids": [f"case-{case}"],
                        "observed_or_inferred": "observed",
                        "confidence": 1,
                        "qualifiers": {
                            "pathway_code": "routine-renewal",
                            "authority_mapping_version": "synthetic-v1",
                        },
                    }
                    for case, trace in enumerate(traces)
                    for index, label in enumerate(trace)
                ],
            }
        )
    )


def report(
    ledger: CredentialingLedger, *, cases: int = 2, complete: frozenset[str] | None = None
) -> reporting.AlignmentReport:
    """Provide trusted synthetic grants and explicit complete-case coverage."""
    grants = frozenset(f"case-{i}" for i in range(cases))
    return reporting.report_alignments(
        ledger,
        model(),
        role="report_reader",
        case_ids=grants,
        complete_case_ids=grants if complete is None else complete,
        minimum_cases=2,
        python=Path(sys.executable),
    )


@pytest.fixture
def captured_backend(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[str, ...], ...]]:
    """Inspect selected traces; numeric engine parity is tested separately above."""
    seen: list[tuple[tuple[str, ...], ...]] = []

    def evaluate(
        _model: object, traces: tuple[tuple[str, ...], ...], **_kwargs: object
    ) -> AlignmentResult:
        seen.append(traces)
        fitness = tuple(1.0 if t == ("request_received", "case_completed") else 0.5 for t in traces)
        return AlignmentResult("available", fitness, tuple(0 for _ in traces))

    monkeypatch.setattr(reporting, "align_traces", evaluate)
    return seen


def test_retained_replay_deletion_and_real_deviations(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Replay does not duplicate; tombstones survive replay; missing complete steps score."""
    ledger = ledger_for((("request_received", "case_completed"),) * 2)
    original = ledger.projection.model_copy(deep=True)
    ledger.merge(original)
    assert report(ledger).fit_cases == 2
    for case in range(2):
        ledger.tombstone(f"case-{case}-event-1")
    ledger.merge(original)
    result = report(ledger)
    assert result.deviating_cases == 2
    assert result.aligned_cases == 2
    assert result.mean_case_fitness == 0.5
    assert result.retained_source_events == 2
    assert captured_backend[-1] == (("request_received",),) * 2


def test_partial_trace_excluded_without_running_engine(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Open cases are not scored against future unexecuted activities."""
    result = report(ledger_for((("request_received",),) * 2), complete=frozenset())
    assert result.status == "no_eligible_traces"
    assert result.exclusions == (("partial_or_censored_trace", 2),)
    assert result.mean_case_fitness is None
    assert not captured_backend


def test_singleton_outcome_suppresses_every_field(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """A single deviating case is hidden even when the total cohort passes."""
    ledger = ledger_for((("request_received", "case_completed"),) * 2 + (("request_received",),))
    assert report(ledger, cases=3) == reporting.AlignmentReport("suppressed")
    assert len(captured_backend) == 1


@pytest.mark.parametrize("problem", ["ties", "authority", "pathway", "missing"])
def test_exclusions_reconcile_to_population(
    problem: str,
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Structural missingness and qualifier/order ambiguity remain explicit."""
    ledger = ledger_for((("request_received", "case_completed"),) * 2)
    if problem == "missing":
        ledger = ledger_for(((), ()))
    for fact in ledger.projection.facts:
        if problem == "ties":
            fact.timestamp_utc = datetime(2026, 1, 1, tzinfo=UTC)
        elif problem == "authority":
            fact.qualifiers.authority_mapping_version = "unaccepted-v2"
        elif problem == "pathway":
            fact.qualifiers.pathway_code = "another-pathway"
    result = report(ledger)
    assert result.status == "no_eligible_traces"
    assert result.eligible_cases == 0
    assert sum(count for _, count in result.exclusions or ()) == result.population_cases
    assert not captured_backend


def test_ungranted_cases_do_not_enter_trace_or_counts(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """No inference from a source object's presence grants case access."""
    ledger = ledger_for((("request_received", "case_completed"),) * 2 + (("case_withdrawn",),))
    result = report(ledger)
    assert result.retained_source_events == 4
    assert captured_backend == [(("request_received", "case_completed"),) * 2]
    assert "case-" not in json.dumps(asdict(result))


def test_event_identity_and_case_occurrence_units_differ(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """One event linked to two granted cases remains one source event, two occurrences."""
    ledger = ledger_for((("request_received", "case_completed"),))
    for fact in ledger.projection.facts:
        fact.object_ids.append("case-1")
    result = report(ledger)
    assert result.retained_source_events == 2
    assert result.observed_case_event_occurrences == 4
    assert result.fit_cases == 2
    assert len(captured_backend) == 1


def test_inferred_events_are_not_aligned_and_joint_presence_is_protected(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Inferred facts cannot complete a trace; a rare inference contributor suppresses."""
    ledger = ledger_for((("request_received", "case_completed"),) * 2)
    for fact in ledger.projection.facts:
        if fact.activity == "case_completed":
            fact.observed_or_inferred = "inferred"
            ledger.inference_provenance[fact.event_id] = InferenceRun(
                run_id="synthetic", provider="synthetic", model="synthetic", agent_version="v1"
            )
    result = report(ledger)
    assert result.excluded_inferred_case_event_occurrences == 2
    assert captured_backend[-1] == (("request_received",),) * 2
    ledger.tombstone("case-0-event-1")
    assert report(ledger) == reporting.AlignmentReport("suppressed")


@pytest.mark.parametrize("floor", [True, 1, 2.0])
def test_unsafe_privacy_floor_rejected(floor: object) -> None:
    """Privacy floors cannot be disabled by scalar coercion."""
    with pytest.raises(CredentialingContractError):
        reporting.report_alignments(
            ledger_for(((), ())),
            model(),
            role="report_reader",
            case_ids=frozenset({"case-0", "case-1"}),
            complete_case_ids=frozenset(),
            minimum_cases=cast("int", floor),
            python=Path(sys.executable),
        )


@pytest.mark.parametrize(
    "failure", ["crash", "missing", "oversize", "malformed", "deep", "shape", "oserror"]
)
def test_backend_protocol_failures_are_explicit(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed, absent, oversized or malformed response never yields partial fitness."""

    def reply(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if failure == "oserror":
            raise OSError
        if failure == "oversize":
            Path(args[4]).write_text(" " * 32769, encoding="utf-8")
        elif failure == "malformed":
            Path(args[4]).write_text("{", encoding="utf-8")
        elif failure == "deep":
            Path(args[4]).write_text("[" * 16000 + "0" + "]" * 16000, encoding="utf-8")
        elif failure == "shape":
            Path(args[4]).write_text("[]", encoding="utf-8")
        return subprocess.CompletedProcess[bytes](args, 1 if failure == "crash" else 0)

    monkeypatch.setattr(backend.subprocess, "run", reply)
    expected = "runtime_unavailable" if failure == "oserror" else "backend_error"
    assert align_traces(
        model(), (("request_received",),), python=Path(sys.executable)
    ) == AlignmentResult(expected)


@pytest.mark.parametrize("trace", [(), ("raw narrative",), ("request_received",) * 129])
def test_invalid_or_oversized_trace_rejected(trace: tuple[str, ...]) -> None:
    """Empty traces are missing evidence, never a perfect empty run."""
    with pytest.raises(CredentialingContractError):
        align_traces(model(), (trace,), python=Path(sys.executable))


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 61])
def test_unsafe_timeout_rejected(timeout: float) -> None:
    """The child always has an explicit finite bounded timeout."""
    with pytest.raises(CredentialingContractError):
        align_traces(
            model(), (("request_received",),), python=Path(sys.executable), timeout_seconds=timeout
        )


def test_backend_unavailability_keeps_eligible_and_excluded_denominators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable mining is not conformance zero; populations still reconcile."""

    def unavailable(*_args: object, **_kwargs: object) -> AlignmentResult:
        return AlignmentResult("runtime_unavailable")

    monkeypatch.setattr(reporting, "align_traces", unavailable)
    result = report(ledger_for((("request_received",),) * 2))
    assert result.status == "runtime_unavailable"
    assert result.eligible_cases == result.population_cases == 2
    assert result.aligned_cases == 0
    assert result.fit_cases is None
    assert result.mean_case_fitness is None


def test_batch_resource_limit_does_not_run_backend(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Bounded local batches are explicit; this function does not silently sample."""
    result = report(ledger_for((("request_received",),) * 66), cases=66)
    assert result.status == "resource_limit"
    assert result.eligible_cases == 66
    assert not captured_backend


def test_long_trace_exclusion_does_not_run_backend(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """A long complete trace remains a counted exclusion, not a truncated sample."""
    result = report(ledger_for((("request_received",) * 129,) * 2))
    assert result.exclusions == (("trace_resource_limit", 2),)
    assert result.eligible_cases == 0
    assert not captured_backend


def test_partial_and_missing_groups_reconcile_with_aligned_cases(
    captured_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Denominators count distinct cases, with separate primary exclusion groups."""
    ledger = ledger_for(
        (("request_received", "case_completed"),) * 2 + (("request_received",),) * 2 + ((), ())
    )
    result = report(ledger, cases=6, complete=frozenset({"case-0", "case-1", "case-4", "case-5"}))
    assert result.status == "available"
    assert result.population_cases == 6
    assert result.aligned_cases == result.eligible_cases == 2
    assert result.exclusions == (("no_observed_trace", 2), ("partial_or_censored_trace", 2))
    assert len(captured_backend) == 1


def test_complete_case_scope_cannot_extend_grants() -> None:
    """Completeness attestations cannot create additional access."""
    with pytest.raises(CredentialingContractError):
        report(ledger_for(((), ())), complete=frozenset({"ungranted"}))


def test_mutated_model_is_revalidated_at_execution() -> None:
    """Frozen records bypassed via object mutation cannot alter the admitted artifact."""
    binding = model()
    object.__setattr__(binding, "sha256", "0" * 64)
    with pytest.raises(CredentialingContractError, match="digest"):
        align_traces(binding, (("request_received",),), python=Path(sys.executable))


def test_model_and_ledger_subclasses_are_not_trusted() -> None:
    """Public boundaries do not preserve adversarial validation subclasses."""

    class DerivedModel(AlignmentModel):
        pass

    binding = DerivedModel(**vars(model()))
    with pytest.raises(CredentialingContractError):
        align_traces(binding, (("request_received",),), python=Path(sys.executable))

    class DerivedLedger(CredentialingLedger):
        pass

    with pytest.raises(CredentialingContractError):
        report(DerivedLedger(ledger_for(((), ())).projection))
