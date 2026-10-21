# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: MIT

"""Authenticated retained alignment snapshots and release-time authorization."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, fields, replace
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, cast

import pytest

from careops_process import credentialing_alignment_reporting as reporting
from careops_process import credentialing_store as storage
from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)
from careops_process.credentialing_alignment import AlignmentModel, AlignmentResult
from careops_process.credentialing_alignment_service import AlignmentStoreConfig
from careops_process.credentialing_assurance import CredentialingLedger, InferenceRun
from careops_process.credentialing_store import (
    Role,
    SQLiteCredentialingStore,
    StorePolicy,
    alignment_snapshot_digest,
    create_store,
    provision_principal,
    revoke_principal,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

# Hand-calculated synthetic values and bounded concurrency deadlines.
# ruff: noqa: PLR2004


def configuration(*, revision: int = 0, python: Path | None = None) -> AlignmentStoreConfig:
    """Bind a synthetic weighted one-step net and explicit snapshot completeness."""
    xml = b"""<pnml><net id="net" type="http://www.pnml.org/version-2009/grammar/pnmlcoremodel">
    <page id="page"><place id="s"/><place id="f"/>
    <transition id="a"><name><text>request_received</text></name></transition>
    <arc id="i" source="s" target="a"><inscription><text>2</text></inscription></arc>
    <arc id="o" source="a" target="f"/></page></net></pnml>"""
    return AlignmentStoreConfig(
        model=AlignmentModel(
            pnml=xml,
            sha256=hashlib.sha256(xml).hexdigest(),
            model_version="synthetic-v1",
            pathway_code="routine-renewal",
            authority_version="synthetic-v1",
            activity_mapping_version="synthetic-v1",
            initial_marking=(("s", 2),),
            final_marking=(("f", 1),),
        ),
        python=python or Path(sys.executable),
        timeout_seconds=30,
        coverage_definition_version="synthetic-full-trace-window-v1",
        ledger_revision=revision,
        ledger_sha256=alignment_snapshot_digest(CredentialingLedger(source_projection())),
        complete_case_ids=frozenset({"case-0", "case-1"}),
    )


def source_projection() -> CredentialingProjection:
    """Build a fixed protected synthetic source snapshot without inferring completeness."""
    return validate_credentialing_projection(
        {
            "source": "careops-approve",
            "facts": [
                {
                    "event_id": f"event-{i}",
                    "activity": "request_received",
                    "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC),
                    "source_system": "synthetic",
                    "object_ids": [f"case-{i}"],
                    "observed_or_inferred": "observed",
                    "confidence": 1,
                    "qualifiers": {
                        "pathway_code": "routine-renewal",
                        "authority_mapping_version": "synthetic-v1",
                    },
                }
                for i in range(2)
            ],
        }
    )


def setup(
    tmp_path: Path,
    *,
    config: AlignmentStoreConfig | None = None,
    role: str = "report_reader",
    source: CredentialingProjection | None = None,
) -> tuple[SQLiteCredentialingStore, Path, str, str]:
    """Bootstrap protected local state and independent reader/ingestor credentials."""
    path = tmp_path / "alignment.sqlite"
    projection = source_projection() if source is None else source
    create_store(
        path,
        projection,
        policy=StorePolicy(
            authority_version="synthetic-v1",
            minimum_cases=2,
            threshold_hours=1,
            threshold_version="synthetic-v1",
        ),
    )
    expiry = datetime.now(UTC) + timedelta(hours=1)
    reader = provision_principal(
        path,
        principal_id="reader",
        role=cast("Role", role),
        case_ids=frozenset({"case-0", "case-1"}),
        expires_at_utc=expiry,
    )
    ingestor = provision_principal(
        path, principal_id="ingestor", role="ingestor", case_ids=frozenset(), expires_at_utc=expiry
    )
    return SQLiteCredentialingStore(path, alignment_config=config), path, reader, ingestor


def test_unconfigured_service_is_unavailable_and_existing_reports_work(tmp_path: Path) -> None:
    """Schema-v1 callers need no configuration or migration to keep working."""
    store, _, reader, _ = setup(tmp_path)
    result = store.read_alignment_report(reader)
    assert result.status == "configuration_unavailable"
    assert result.population_cases is None
    assert store.read_report(reader)["suppressed"] is False


def test_missing_runtime_returns_no_fabricated_fitness(tmp_path: Path) -> None:
    """Authenticated base-profile requests remain functional without the optional runtime."""
    store, _, reader, _ = setup(tmp_path, config=configuration(python=tmp_path / "missing.exe"))
    result = store.read_alignment_report(reader)
    assert result.status == "runtime_unavailable"
    assert result.mean_case_fitness is None


@pytest.mark.parametrize(
    "role", ["case_analyst", "ingestor", "process_owner", "assurance_reviewer"]
)
def test_non_reporting_roles_are_denied(tmp_path: Path, role: str) -> None:
    """A role with other legitimate permissions does not gain this report."""
    store, _, token, _ = setup(tmp_path, config=configuration(), role=role)
    with pytest.raises(PermissionError, match="denied"):
        store.read_alignment_report(token)


def test_stale_completeness_revision_has_no_metrics(tmp_path: Path) -> None:
    """Coverage is never inferred or silently refreshed after source state changes."""
    store, _, reader, _ = setup(tmp_path, config=configuration(revision=1))
    result = store.read_alignment_report(reader)
    assert result.status == "coverage_unavailable"
    assert result.population_cases is None


@pytest.fixture
def fake_backend(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[str, ...], ...]]:
    """Inspect real scope/trace selection; actual weighted parity has its own test."""
    calls: list[tuple[tuple[str, ...], ...]] = []

    def evaluate(
        _model: AlignmentModel, traces: Iterable[tuple[str, ...]], **_kwargs: object
    ) -> AlignmentResult:
        retained = tuple(traces)
        calls.append(retained)
        return AlignmentResult("available", (1.0,) * len(retained), (0,) * len(retained))

    monkeypatch.setattr(reporting, "align_traces", evaluate)
    return calls


def test_authenticated_snapshot_releases_only_aggregate(
    tmp_path: Path,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """A valid reader uses server grants, stored floor and retained observed facts."""
    store, _, reader, _ = setup(tmp_path, config=configuration())
    result = store.read_alignment_report(reader)
    assert result.status == "available"
    assert result.fit_cases == result.aligned_cases == 2
    assert result.mean_case_fitness == 1
    assert fake_backend == [(("request_received",), ("request_received",))]
    wire = json.dumps(asdict(result))
    assert "case-" not in wire
    assert "synthetic" not in wire
    assert "2026-" not in wire


def _change_principal(path: Path, field: str, value: object) -> None:
    """Act as offline administrator, without inventing a request mutation API."""
    with closing(sqlite3.connect(path)) as connection:
        row = connection.execute(
            "SELECT payload FROM principals WHERE principal_id='reader'"
        ).fetchone()
        payload: dict[str, object] = json.loads(row[0])
        payload[field] = value
        connection.execute(
            "UPDATE principals SET payload=? WHERE principal_id='reader'", (json.dumps(payload),)
        )
        connection.commit()


def test_current_grants_cannot_be_overridden(
    tmp_path: Path,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Completeness metadata cannot enlarge access or weaken the stored privacy floor."""
    store, path, reader, _ = setup(tmp_path, config=configuration())
    _change_principal(path, "case_ids", ["case-0"])
    assert store.read_alignment_report(reader) == reporting.AlignmentReport("suppressed")
    assert not fake_backend


@pytest.mark.parametrize("credential", ["", "untrusted", "a" * 43])
def test_invalid_credentials_are_denied_before_work(
    tmp_path: Path,
    credential: str,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """An unavailable service configuration is not an authentication bypass."""
    store, _, _, _ = setup(tmp_path)
    with pytest.raises(PermissionError, match="denied"):
        store.read_alignment_report(credential)
    assert not fake_backend


@pytest.mark.parametrize("change", ["revoked", "expired"])
def test_inactive_reader_is_denied_before_work(
    tmp_path: Path,
    change: str,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Credentials are freshly loaded; service construction is not an access cache."""
    store, path, reader, _ = setup(tmp_path, config=configuration())
    if change == "revoked":
        revoke_principal(path, "reader")
    else:
        _change_principal(
            path, "expires_at_utc", (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        )
    with pytest.raises(PermissionError, match="denied"):
        store.read_alignment_report(reader)
    assert not fake_backend


@pytest.mark.parametrize(
    "change",
    [
        "ingest",
        "delete",
        "revoke",
        "grants",
        "policy",
        "expiry",
        "expiry_extended",
        "role",
        "same_revision",
    ],
)
def test_writers_are_unlocked_and_changed_access_or_evidence_is_not_released(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    """Concurrent changes finish while mining is blocked; stale/denied output never leaks."""
    store, path, reader, ingestor = setup(tmp_path, config=configuration())
    entered, release = Event(), Event()

    def held(
        _model: AlignmentModel, traces: Iterable[tuple[str, ...]], **_kwargs: object
    ) -> AlignmentResult:
        count = len(tuple(traces))
        entered.set()
        assert release.wait(4), "backend was not released"
        return AlignmentResult("available", (1.0,) * count, (0,) * count)

    monkeypatch.setattr(reporting, "align_traces", held)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(store.read_alignment_report, reader)
        try:
            assert entered.wait(2)
            started = time.monotonic()
            if change in {"ingest", "delete"}:
                empty = validate_credentialing_projection(
                    {"source": "careops-approve", "facts": []}
                )
                store.ingest(
                    ingestor, empty, deleted_event_ids=("event-0",) if change == "delete" else ()
                )
            elif change == "revoke":
                revoke_principal(path, "reader")
            elif change == "grants":
                _change_principal(path, "case_ids", ["case-0"])
            elif change == "expiry":
                _change_principal(
                    path, "expires_at_utc", (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
                )
            elif change == "expiry_extended":
                _change_principal(
                    path, "expires_at_utc", (datetime.now(UTC) + timedelta(hours=2)).isoformat()
                )
            elif change == "role":
                _change_principal(path, "role", "case_analyst")
            elif change == "same_revision":
                with closing(sqlite3.connect(path)) as connection:
                    state = json.loads(
                        connection.execute("SELECT payload FROM state").fetchone()[0]
                    )
                    state["projection"]["facts"][0]["activity"] = "case_completed"
                    connection.execute("UPDATE state SET payload=?", (json.dumps(state),))
                    connection.commit()
            else:
                with closing(sqlite3.connect(path)) as connection:
                    payload: dict[str, object] = json.loads(
                        connection.execute("SELECT policy FROM state").fetchone()[0]
                    )
                    payload["minimum_cases"] = 3
                    connection.execute("UPDATE state SET policy=?", (json.dumps(payload),))
                    connection.commit()
            assert time.monotonic() - started < 2
        finally:
            release.set()
        if change in {"revoke", "expiry", "role"}:
            with pytest.raises(PermissionError, match="denied"):
                future.result(timeout=2)
        else:
            assert future.result(timeout=2) == reporting.AlignmentReport("stale_snapshot")


def test_deletion_restart_replay_requires_fresh_coverage_and_cannot_resurrect(
    tmp_path: Path,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """A fresh trusted completeness binding never restores deleted event facts."""
    config = configuration()
    store, path, reader, ingestor = setup(tmp_path, config=config)
    original = store.snapshot(ingestor).ledger.projection
    store.ingest(ingestor, original, deleted_event_ids=("event-0", "event-1"))
    store.ingest(ingestor, original)
    assert store.read_alignment_report(reader) == reporting.AlignmentReport("coverage_unavailable")
    restored = SQLiteCredentialingStore(
        path,
        alignment_config=replace(
            config,
            ledger_revision=2,
            ledger_sha256=alignment_snapshot_digest(store.snapshot(ingestor).ledger),
        ),
    )
    result = restored.read_alignment_report(reader)
    assert result.status == "no_eligible_traces"
    assert result.retained_source_events == 0
    assert result.exclusions == (("no_observed_trace", 2),)
    assert not fake_backend


def test_model_authority_must_match_current_stored_policy(
    tmp_path: Path,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Model syntax cannot approve a different stored authority mapping."""
    config = configuration()
    config = replace(config, model=replace(config.model, authority_version="unaccepted-v2"))
    store, _, reader, _ = setup(tmp_path, config=config)
    assert store.read_alignment_report(reader) == reporting.AlignmentReport(
        "configuration_unavailable"
    )
    assert not fake_backend


def test_startup_configuration_is_detached(
    tmp_path: Path,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """Mutating a supplied record after construction cannot alter the live service."""
    config = configuration()
    store, _, reader, _ = setup(tmp_path, config=config)
    object.__setattr__(config.model, "authority_version", "unaccepted-v2")
    object.__setattr__(config, "ledger_revision", 999)
    assert store.read_alignment_report(reader).status == "available"
    assert len(fake_backend) == 1


@pytest.mark.parametrize("revision", [True, -1, 1.5, 2**63])
def test_configuration_revision_is_concrete_and_bounded(revision: object) -> None:
    """Completeness cannot be rebound through boolean or numeric coercion."""
    with pytest.raises(CredentialingContractError):
        replace(configuration(), ledger_revision=cast("int", revision))


@pytest.mark.parametrize("timeout", [True, 0, 61, float("nan"), float("inf")])
def test_configuration_timeout_is_concrete_and_bounded(timeout: float) -> None:
    """Trusted startup still validates its subprocess budget."""
    with pytest.raises(CredentialingContractError):
        replace(configuration(), timeout_seconds=timeout)


def test_actual_optional_weighted_model_with_authenticated_retained_snapshot(
    tmp_path: Path,
) -> None:
    """The pinned backend consumes two tokens and reports two granted complete cases."""
    runtime = Path("artifacts/mining-venv/Scripts/python.exe").resolve()
    try:
        if version("pm4py") == "2.7.23.8":
            runtime = Path(sys.executable)
    except PackageNotFoundError:
        pass
    if not runtime.is_file():
        pytest.skip("Existing optional runtime absent")
    store, path, reader, _ = setup(tmp_path, config=configuration(python=runtime))
    result = store.read_alignment_report(reader)
    assert result.status == "available"
    assert result.fit_cases == result.aligned_cases == 2
    assert result.mean_case_fitness == 1
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_completeness_cannot_move_to_different_store_with_same_revision(
    tmp_path: Path,
    fake_backend: list[tuple[tuple[str, ...], ...]],
) -> None:
    """A revision number alone must not admit coverage for unrelated retained facts."""
    first, second, identical = tmp_path / "one", tmp_path / "two", tmp_path / "identical"
    for directory in (first, second, identical):
        directory.mkdir()
    config = configuration()
    first_store, _, first_reader, _ = setup(first, config=config)
    altered = source_projection()
    for fact in altered.facts:
        fact.activity = "case_completed"
    other_store, _, other_reader, _ = setup(second, config=config, source=altered)
    identical_store, _, identical_reader, _ = setup(identical, config=config)
    assert first_store.read_alignment_report(first_reader).status == "available"
    assert other_store.read_alignment_report(other_reader) == reporting.AlignmentReport(
        "coverage_unavailable"
    )
    assert identical_store.read_alignment_report(identical_reader).status == "available"
    assert len(fake_backend) == 2


@pytest.mark.parametrize(
    "status",
    ["configuration_unavailable", "coverage_unavailable", "suppressed", "runtime_unavailable"],
)
def test_even_non_numeric_results_reauthenticate_before_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    """Missing/stale configuration, suppressed and unavailable paths never skip revocation."""
    config = None if status == "configuration_unavailable" else configuration()
    if status == "coverage_unavailable":
        config = replace(configuration(), ledger_revision=99)
    store, path, reader, _ = setup(tmp_path, config=config)

    def response(value: str) -> reporting.AlignmentReport:
        revoke_principal(path, "reader")
        return reporting.AlignmentReport(value)

    def compute(*_args: object, **_kwargs: object) -> reporting.AlignmentReport:
        return response(status)

    if status in {"configuration_unavailable", "coverage_unavailable"}:
        monkeypatch.setattr(storage, "AlignmentReport", response)
    else:
        monkeypatch.setattr(storage, "report_alignments", compute)
    with pytest.raises(PermissionError, match="denied"):
        store.read_alignment_report(reader)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("coverage_definition_version", ""),
        ("coverage_definition_version", "raw narrative"),
        ("ledger_sha256", "0" * 63),
        ("ledger_sha256", "a" * 64 + "\n"),
        ("complete_case_ids", {"case-0"}),
        ("complete_case_ids", frozenset({"raw narrative"})),
        ("python", Path("relative.exe")),
    ],
)
def test_invalid_trusted_configuration_fails_closed(field: str, value: object) -> None:
    """Temporal definition, identity binding and scope are validated, never guessed."""
    with pytest.raises(CredentialingContractError):
        replace(configuration(), **{field: value})


def test_config_and_nested_model_subclasses_are_rejected(tmp_path: Path) -> None:
    """Detached trusted configuration cannot preserve adversarial record subclasses."""

    class DerivedConfig(AlignmentStoreConfig):
        pass

    config = configuration()
    derived = DerivedConfig(**{field.name: getattr(config, field.name) for field in fields(config)})
    with pytest.raises(CredentialingContractError):
        setup(tmp_path, config=derived)

    class DerivedModel(AlignmentModel):
        pass

    with pytest.raises(CredentialingContractError):
        replace(config, model=DerivedModel(**vars(config.model)))


def test_digest_is_canonical_and_tracks_deletion_memory() -> None:
    """Fact input order is irrelevant, while tombstone identity is retained evidence."""
    original = source_projection()
    reordered = source_projection()
    reordered.facts.reverse()
    first, second = CredentialingLedger(original), CredentialingLedger(reordered)
    assert alignment_snapshot_digest(first) == alignment_snapshot_digest(second)
    original_digest = alignment_snapshot_digest(first)
    first.tombstone("deleted-a")
    first.tombstone("deleted-b")
    second.tombstone("deleted-b")
    second.tombstone("deleted-a")
    assert alignment_snapshot_digest(first) == alignment_snapshot_digest(second)
    assert alignment_snapshot_digest(first) != original_digest


@pytest.mark.parametrize("change", ["provenance", "dead_letter", "watermark"])
def test_digest_covers_provenance_dead_letters_and_watermark(change: str) -> None:
    """A matching event list alone is insufficient evidence of the retained state."""
    projection = source_projection()
    provenance: dict[str, InferenceRun] = {}
    if change == "provenance":
        for fact in projection.facts:
            fact.observed_or_inferred = "inferred"
            provenance[fact.event_id] = InferenceRun(
                run_id="run-one", provider="synthetic", model="synthetic", agent_version="v1"
            )
    ledger = CredentialingLedger(projection, inference_provenance=provenance)
    before = alignment_snapshot_digest(ledger)
    if change == "provenance":
        ledger.inference_provenance["event-0"].run_id = "changed-run"
    elif change == "dead_letter":
        ledger.reject("invalid-event", "schema", recorded_at_utc=datetime(2026, 1, 2, tzinfo=UTC))
    else:
        ledger.projection.watermark_utc = datetime(2026, 1, 2, tzinfo=UTC)
    assert alignment_snapshot_digest(ledger) != before
