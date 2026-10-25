# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Synthetic managed-CLI boundaries for identity and conditional ledger persistence."""

import json
import subprocess
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from careops_process import hub_dataverse_adapter as a
from careops_process.hub_notifications import reserve_notification
from tests.test_hub_notifications import ledger, reserve

ORG = "00000000-0000-0000-0000-000000000001"
USER = "00000000-0000-0000-0000-000000000002"
IDENTITY_SCHEMA_CALLS = 2
LOAD_CALLS = 3
UNIT = "00000000-0000-0000-0000-000000000003"


def config() -> a.StoreConfig:
    """Use explicit synthetic schema, never a proposed real publisher prefix."""
    return a.StoreConfig(
        environment_url="https://synthetic.crm.dynamics.com",
        organization_id=ORG,
        table_name="synthetic_ledger",
        entity_set="synthetic_ledgers",
        payload_column="synthetic_payload",
        allowed_user_ids=(USER,),
    )


class FakeCli:
    """Record argv and return deterministic managed-CLI JSON responses."""

    def __init__(self, responses: list[a.CliResult]) -> None:
        """Provide exact replies in expected call order."""
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args: tuple[str, ...]) -> a.CliResult:
        """Never invoke a real executable during synthetic tests."""
        self.calls.append(args)
        return self.responses.pop(0)


def response(value: object) -> a.CliResult:
    """Render one authenticated HTTP body, without headers or token fixtures."""
    return a.CliResult(exit_code=0, output=json.dumps(value))


def identity() -> a.CliResult:
    """Supply a WhoAmI response bound to configured sandbox organization."""
    return response({"OrganizationId": ORG, "UserId": USER, "BusinessUnitId": UNIT})


def metadata() -> a.CliResult:
    """Supply authoritative entity mapping and concurrency capability."""
    return response(
        {
            "LogicalName": "synthetic_ledger",
            "EntitySetName": "synthetic_ledgers",
            "IsOptimisticConcurrencyEnabled": True,
        }
    )


def row(value: object, etag: str = 'W/"1"') -> a.CliResult:
    """Store a complete serialized notification ledger in one field."""
    return response({"@odata.etag": etag, "synthetic_payload": a.encode_ledger(value)})


def test_load_resolves_identity_and_mapping_before_reading_durable_ledger() -> None:
    """Identity and record ETag come from authenticated provider responses."""
    cli = FakeCli([identity(), metadata(), row(ledger())])
    loaded = a.DataverseLedgerStore(config(), cli).load(ledger())
    assert loaded.ledger == ledger()
    assert loaded.etag == 'W/"1"'
    assert loaded.user_id == USER
    assert all("--environment" in call for call in cli.calls)
    assert "WhoAmI" in cli.calls[0][cli.calls[0].index("--path") + 1]


def test_conditional_commit_requires_etag_and_exact_full_state_readback() -> None:
    """A single conditional row update stores reservation and receipt together."""
    proposed = reserve_notification(ledger(), reserve())
    cli = FakeCli(
        [
            identity(),
            metadata(),
            row(ledger()),
            identity(),
            metadata(),
            row(proposed.ledger, 'W/"2"'),
        ]
    )
    store = a.DataverseLedgerStore(replace(config(), writes_enabled=True), cli)
    loaded = store.load(ledger())
    committed = store.commit(loaded, proposed)
    assert committed.ledger == proposed.ledger
    assert committed.etag == 'W/"2"'
    assert 'If-Match:W/"1"' in cli.calls[-1]
    assert "Prefer:return=representation" in cli.calls[-1]
    assert "PATCH" in cli.calls[-1]
    plan = a.prepare_delivery(committed, proposed.receipt.command_ref)
    assert plan.provider_intent_ref == "intent-0"
    assert plan.dispatch_enabled is False


@pytest.mark.parametrize(
    "failure",
    [
        a.CliResult(exit_code=1, output="private 412 response"),
        a.CliResult(exit_code=0, output=""),
        a.CliResult(exit_code=0, output="private malformed"),
    ],
)
def test_ambiguous_commit_never_returns_a_delivery_plan(failure: a.CliResult) -> None:
    """Conflict, timeout and malformed/empty responses never establish a winning commit."""
    proposed = reserve_notification(ledger(), reserve())
    cli = FakeCli([identity(), metadata(), row(ledger()), identity(), metadata(), failure])
    store = a.DataverseLedgerStore(replace(config(), writes_enabled=True), cli)
    loaded = store.load(ledger())
    with pytest.raises(a.AdapterError, match="commit_unconfirmed") as error:
        store.commit(loaded, proposed)
    assert "private" not in str(error.value)


def test_missing_record_is_not_a_new_empty_quota_ledger() -> None:
    """A failed GET cannot authorize initialization or upsert fallback."""
    cli = FakeCli([identity(), metadata(), a.CliResult(exit_code=1, output="404")])
    with pytest.raises(a.AdapterError, match="read_unconfirmed"):
        a.DataverseLedgerStore(config(), cli).load(ledger())
    assert all("PATCH" not in call for call in cli.calls)


@pytest.mark.parametrize("change", ["org", "user", "concurrency", "mapping"])
def test_identity_or_metadata_mismatch_blocks_record_access(change: str) -> None:
    """No configured role or authority is inferred from mere authentication."""
    who: dict[str, object] = {"OrganizationId": ORG, "UserId": USER, "BusinessUnitId": UNIT}
    schema: dict[str, object] = {
        "LogicalName": "synthetic_ledger",
        "EntitySetName": "synthetic_ledgers",
        "IsOptimisticConcurrencyEnabled": True,
    }
    if change == "org":
        who["OrganizationId"] = UNIT
    elif change == "user":
        who["UserId"] = UNIT
    elif change == "concurrency":
        schema["IsOptimisticConcurrencyEnabled"] = False
    else:
        schema["EntitySetName"] = "other_records"
    cli = FakeCli([response(who), response(schema)])
    with pytest.raises(a.AdapterError):
        a.DataverseLedgerStore(config(), cli).load(ledger())
    assert len(cli.calls) <= IDENTITY_SCHEMA_CALLS


def test_serialization_roundtrip_revalidates_all_nested_receipt_bindings() -> None:
    """Restored JSON remains subject to the existing concrete ledger invariants."""
    proposed = reserve_notification(ledger(), reserve())
    assert a.decode_ledger(a.encode_ledger(proposed.ledger)) == proposed.ledger
    payload: Any = json.loads(a.encode_ledger(proposed.ledger))
    payload["ledger"]["reservations"][0]["provider_intent_ref"] = "different"
    with pytest.raises(a.AdapterError, match="invalid_ledger"):
        a.decode_ledger(json.dumps(payload))


def test_write_switch_and_replay_cannot_dispatch() -> None:
    """Default adapters are read-only and exact command replay is not another delivery."""
    proposed = reserve_notification(ledger(), reserve())
    cli = FakeCli([identity(), metadata(), row(ledger())])
    store = a.DataverseLedgerStore(config(), cli)
    loaded = store.load(ledger())
    with pytest.raises(a.AdapterError, match="writes_disabled"):
        store.commit(loaded, proposed)
    assert len(cli.calls) == LOAD_CALLS
    cli = FakeCli([identity(), metadata(), row(proposed.ledger)])
    loaded = a.DataverseLedgerStore(config(), cli).load(ledger())
    with pytest.raises(a.AdapterError, match="not_committed_attempt"):
        a.prepare_delivery(loaded, "reserve-0")


def test_row_identity_ignores_scope_policy_and_history_origin() -> None:
    """Changing mutable configuration cannot create fresh recipient/channel quota storage."""
    original = a.row_id(config(), ledger())
    assert original == a.row_id(config(), replace(ledger(), scope_ref="other"))
    assert original != a.row_id(config(), replace(ledger(), recipient_ref="other"))


def test_storage_identity_is_partitioned_by_organization_and_tenant() -> None:
    """Distinct organizations and tenants cannot resolve to the same storage row."""
    original = a.row_id(config(), ledger())
    other_organization = replace(
        config(),
        organization_id="00000000-0000-0000-0000-000000000004",
    )
    other_tenant = replace(ledger(), tenant_ref="other-tenant")

    assert a.row_id(other_organization, ledger()) != original
    assert a.row_id(config(), other_tenant) != original


def test_foreign_tenant_ledger_readback_is_rejected() -> None:
    """A provider row with a different tenant binding cannot be accepted."""
    foreign_ledger = replace(ledger(), tenant_ref="other-tenant")
    cli = FakeCli([identity(), metadata(), row(foreign_ledger)])

    with pytest.raises(a.AdapterError, match="ledger_binding_mismatch"):
        a.DataverseLedgerStore(config(), cli).load(ledger())

    assert len(cli.calls) == LOAD_CALLS


def test_commit_cannot_rewind_persisted_evaluation_watermark() -> None:
    """Two individually valid histories must still preserve cross-revision freshness."""
    command = replace(reserve(), enabled=False, now=reserve().now + timedelta(hours=2))
    actual = reserve_notification(ledger(), command).ledger
    rewound = replace(actual, evaluated_at=reserve().now)
    proposed = reserve_notification(rewound, reserve(1, revision=1))
    cli = FakeCli(
        [identity(), metadata(), row(actual), identity(), metadata(), row(proposed.ledger, 'W/"2"')]
    )
    store = a.DataverseLedgerStore(replace(config(), writes_enabled=True), cli)
    loaded = store.load(ledger())
    with pytest.raises(a.AdapterError, match="invalid_proposal"):
        store.commit(loaded, proposed)
    assert all("PATCH" not in call for call in cli.calls)


def test_windows_npm_shim_is_not_executed_through_a_command_shell(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Call the official Node entry point directly when PATH resolves an npm batch shim."""
    shim = tmp_path / "dataverse.cmd"
    entry = tmp_path / "node_modules" / "@microsoft" / "dataverse" / "bin" / "dataverse.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("synthetic entry", encoding="utf-8")
    node = tmp_path / "node.exe"
    observed: list[list[str]] = []

    def which(name: str) -> str:
        return str(node if name == "node" else shim)

    def invoke(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setattr(a.shutil, "which", which)
    monkeypatch.setattr(a.subprocess, "run", invoke)
    a.run_cli(("auth", "who"))
    assert observed[0][:2] == [str(node), str(entry)]


@pytest.mark.parametrize("field", ["windows", "reservations", "receipts"])
def test_invalid_json_collection_shapes_are_not_coerced_to_empty_history(field: str) -> None:
    """Empty objects or strings must not be interpreted as empty persisted arrays."""
    payload: Any = json.loads(a.encode_ledger(ledger()))
    payload["ledger"][field] = {}
    with pytest.raises(a.AdapterError, match="invalid_ledger"):
        a.decode_ledger(json.dumps(payload))


def test_missing_identity_and_payload_fields_return_fixed_codes() -> None:
    """Unexpected response shape must not leak raw provider output or unhandled keys."""
    cli = FakeCli([response({})])
    with pytest.raises(a.AdapterError):
        a.DataverseLedgerStore(config(), cli).load(ledger())


def test_direct_runner_sanitizes_temporary_cleanup_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cleanup after a potentially completed write cannot expose private filesystem details."""
    original_unlink = Path.unlink
    observed: list[Path] = []

    def unlink(path: Path, *, missing_ok: bool = False) -> None:
        del missing_ok
        observed.append(path)
        error = "synthetic private tempfile path"
        raise PermissionError(error)

    def executable(_name: str) -> str:
        return "dataverse.exe"

    def invoke(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setattr(a.shutil, "which", executable)
    monkeypatch.setattr(a.subprocess, "run", invoke)
    monkeypatch.setattr(a.Path, "unlink", unlink)
    try:
        with pytest.raises(a.AdapterError, match="request_unconfirmed") as error:
            a.run_cli(("api", "request", "--body", '{"synthetic":"payload"}'))
        assert "private" not in str(error.value)
    finally:
        for path in observed:
            original_unlink(path, missing_ok=True)


def test_managed_runner_uses_temporary_body_file_and_cleans_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Large ledger payloads avoid Windows argv limits and disappear after the CLI exits."""
    observed: list[Path] = []

    def invoke(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        payload = Path(argv[argv.index("--body-file") + 1])
        observed.append(payload)
        assert payload.read_text(encoding="utf-8") == '{"synthetic":"payload"}'
        assert "--body" not in argv
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    def executable(_name: str) -> str:
        return "dataverse.exe"

    monkeypatch.setattr(a.shutil, "which", executable)
    monkeypatch.setattr(a.subprocess, "run", invoke)
    result = a.run_cli(("api", "request", "--body", '{"synthetic":"payload"}'))
    assert result.exit_code == 0
    assert observed
    assert not observed[0].exists()
    cli = FakeCli([identity(), metadata(), response({"@odata.etag": 'W/"1"'})])
    with pytest.raises(a.AdapterError):
        a.DataverseLedgerStore(config(), cli).load(ledger())
