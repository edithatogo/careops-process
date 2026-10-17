"""Managed Dataverse CLI identity/CAS scaffolding; real delivery remains disabled."""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404
import tempfile
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit
from uuid import UUID, uuid5

from careops_process.hub_notifications import (
    AdmissionResult,
    CommandReceipt,
    DeliveryEvidence,
    NotificationLedger,
    NotificationWindow,
    Reservation,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_MAX_BYTES = 900_000
_CONTEXT = "app=dataverse-skills/1.16.1;skill=dv-data;agent=codex"
_ETAG = re.compile(r'W/"[0-9]+"')


class AdapterError(ValueError):
    """Return fixed safe error codes without leaking provider bodies or identities."""


def _check(condition: bool, code: str) -> None:  # noqa: FBT001 - contract predicate
    if not condition:
        raise AdapterError(code)


def _guid(value: object) -> str:
    _check(type(value) is str, "invalid_identity")
    value = cast("str", value)
    try:
        parsed = UUID(value)
    except ValueError, TypeError, AttributeError:
        error_code = "invalid_identity"
        raise AdapterError(error_code) from None
    _check(str(parsed) == value and parsed.int != 0, "invalid_identity")
    return value


@dataclass(frozen=True, slots=True)
class CliResult:
    """Capture a CLI result in memory; never include output in diagnostics."""

    exit_code: int
    output: str


def run_cli(args: tuple[str, ...]) -> CliResult:
    """Use existing managed CLI credentials without creating/selecting profiles."""
    executable = shutil.which("dataverse")
    _check(executable is not None, "dataverse_cli_missing")
    prefix = [str(executable)]
    if Path(str(executable)).suffix.lower() in {".cmd", ".bat", ".ps1"}:
        entry = (
            Path(str(executable)).parent
            / "node_modules"
            / "@microsoft"
            / "dataverse"
            / "bin"
            / "dataverse.js"
        )
        node = shutil.which("node")
        _check(
            entry.is_file()
            and node is not None
            and Path(str(node)).suffix.lower() not in {".cmd", ".bat", ".ps1"},
            "dataverse_native_entry_missing",
        )
        prefix = [str(node), str(entry)]
    body_path: Path | None = None
    try:
        if "--body" in args:
            position = args.index("--body")
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".json", delete=False
            ) as body_file:
                body_path = Path(body_file.name)
                body_file.write(args[position + 1])
            args = (*args[:position], "--body-file", str(body_path), *args[position + 2 :])
        result = subprocess.run(  # noqa: S603 # nosec B603
            [*prefix, *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        error_code = "request_unconfirmed"
        raise AdapterError(error_code) from None
    finally:
        if body_path is not None:
            body_path.unlink(missing_ok=True)
    return CliResult(result.returncode, result.stdout)


@dataclass(frozen=True, slots=True, kw_only=True)
class StoreConfig:
    """Require discovered environment/schema and separately approved principal allowlist."""

    environment_url: str
    organization_id: str
    table_name: str
    entity_set: str
    payload_column: str
    allowed_user_ids: tuple[str, ...] = ()
    writes_enabled: bool = False

    def __post_init__(self) -> None:
        """Reject endpoint/header/path injection and any inferred permission mapping."""
        parsed = urlsplit(self.environment_url)
        _check(
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.port is None
            and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
            and parsed.path in {"", "/"}
            and not any(c.isspace() for c in self.environment_url),
            "invalid_environment",
        )
        object.__setattr__(self, "environment_url", self.environment_url.rstrip("/"))
        _guid(self.organization_id)
        for value in (self.table_name, self.entity_set, self.payload_column):
            _check(
                type(value) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", value) is not None,
                "invalid_schema_mapping",
            )
        _check(
            type(self.allowed_user_ids) is tuple and type(self.writes_enabled) is bool,
            "invalid_config",
        )
        for value in self.allowed_user_ids:
            _guid(value)
        _check(len(set(self.allowed_user_ids)) == len(self.allowed_user_ids), "invalid_config")


def _json_default(value: object) -> str:
    if type(value) is datetime:
        return value.isoformat()
    error_code = "invalid_ledger"
    raise AdapterError(error_code)


def encode_ledger(value: object) -> str:
    """Serialize the complete concrete ledger and all command/effect receipts together."""
    _check(type(value) is NotificationLedger, "invalid_ledger")
    try:
        validated = replace(cast("NotificationLedger", value))
        encoded = json.dumps(
            {"version": 1, "ledger": asdict(validated)},
            default=_json_default,
            sort_keys=True,
            separators=(",", ":"),
        )
        _check(len(encoded.encode()) <= _MAX_BYTES, "ledger_capacity_reached")
    except ValueError, TypeError, AttributeError:
        error_code = "invalid_ledger"
        raise AdapterError(error_code) from None
    return encoded


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _check(key not in result, "invalid_json")
        result[key] = value
    return result


def _object(value: object) -> dict[str, Any]:
    _check(type(value) is dict, "invalid_json")
    return cast("dict[str, Any]", value)


def _record_values(value: object, names: set[str]) -> dict[str, Any]:
    record = _object(value).copy()
    _check(set(record) == names, "invalid_ledger")
    return record


def _date(value: object) -> datetime:
    _check(type(value) is str, "invalid_ledger")
    return datetime.fromisoformat(cast("str", value))


def decode_ledger(value: object) -> NotificationLedger:
    """Restore typed records and re-run the ledger's full nested history validation."""
    try:
        _check(type(value) is str, "invalid_ledger")
        value = cast("str", value)
        _check(len(value.encode()) <= _MAX_BYTES, "invalid_ledger")
        envelope = _record_values(
            json.loads(value, object_pairs_hook=_pairs), {"version", "ledger"}
        )
        _check(type(envelope["version"]) is int and envelope["version"] == 1, "invalid_ledger")
        record = _record_values(envelope["ledger"], {f.name for f in fields(NotificationLedger)})
        for collection in ("windows", "reservations", "receipts"):
            _check(type(record[collection]) is list, "invalid_ledger")
        windows: list[NotificationWindow] = []
        for raw in record["windows"]:
            item = _record_values(raw, {f.name for f in fields(NotificationWindow)})
            windows.append(
                NotificationWindow(
                    start=_date(item["start"]), end=_date(item["end"]), limit=item["limit"]
                )
            )
        reservations: list[Reservation] = []
        for raw in record["reservations"]:
            item = _record_values(raw, {f.name for f in fields(Reservation)})
            _check(type(item["evidence"]) is list, "invalid_ledger")
            evidence: list[DeliveryEvidence] = []
            for raw_evidence in item["evidence"]:
                event = _record_values(raw_evidence, {f.name for f in fields(DeliveryEvidence)})
                event["observed_at"] = _date(event["observed_at"])
                evidence.append(DeliveryEvidence(**event))
            item.update(
                window_start=_date(item["window_start"]),
                created_at=_date(item["created_at"]),
                evidence=tuple(evidence),
            )
            reservations.append(Reservation(**item))
        receipts: list[CommandReceipt] = []
        for raw in record["receipts"]:
            item = _record_values(raw, {f.name for f in fields(CommandReceipt)})
            item["window_start"] = _date(item["window_start"])
            receipts.append(CommandReceipt(**item))
        record.update(
            history_origin=_date(record["history_origin"]),
            windows=tuple(windows),
            reservations=tuple(reservations),
            receipts=tuple(receipts),
            evaluated_at=None if record["evaluated_at"] is None else _date(record["evaluated_at"]),
        )
        return NotificationLedger(**record)
    except ValueError, TypeError, AttributeError, KeyError, OverflowError:
        error_code = "invalid_ledger"
        raise AdapterError(error_code) from None


def row_id(config: StoreConfig, ledger: NotificationLedger) -> str:
    """Derive one organization/tenant/recipient/channel row, independent of scope/policy/window."""
    _check(type(config) is StoreConfig and type(ledger) is NotificationLedger, "invalid_binding")
    config, ledger = replace(config), replace(ledger)
    return str(
        uuid5(
            UUID(config.organization_id),
            json.dumps(
                [ledger.tenant_ref, ledger.recipient_ref, ledger.channel_ref], separators=(",", ":")
            ),
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class LoadedLedger:
    """Keep private read context and whether this invocation confirmed an attempt commit."""

    ledger: NotificationLedger
    etag: str
    user_id: str
    storage_id: str
    committed_command_ref: str | None = None


class DataverseLedgerStore:
    """Use provider-enforced conditional PATCH, not a read/update application lock."""

    def __init__(
        self, config: StoreConfig, runner: Callable[[tuple[str, ...]], CliResult] = run_cli
    ) -> None:
        """Inject transport for tests; production runner uses existing Dataverse CLI auth."""
        _check(type(config) is StoreConfig, "invalid_config")
        self.config = replace(config)
        self.runner = runner

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: tuple[str, ...] = (),
        body: dict[str, str] | None = None,
        error: str = "read_unconfirmed",
    ) -> dict[str, Any]:
        args = (
            "api",
            "request",
            "--target",
            "dataverse",
            "--environment",
            self.config.environment_url,
            "--method",
            method,
            "--path",
            path,
            "--context",
            _CONTEXT,
        )
        for header in headers:
            args += ("--header", header)
        if body is not None:
            args += ("--body", json.dumps(body, separators=(",", ":")))
        try:
            result = self.runner(args)
            _check(type(result) is CliResult and result.exit_code == 0, error)
            return _object(json.loads(result.output, object_pairs_hook=_pairs))
        except ValueError, TypeError, OSError, subprocess.TimeoutExpired:
            raise AdapterError(error) from None

    def _identity(self) -> str:
        who = self._request("GET", "/api/data/v9.2/WhoAmI")
        _check(
            _guid(who.get("OrganizationId")) == self.config.organization_id, "organization_mismatch"
        )
        user = _guid(who.get("UserId"))
        _guid(who.get("BusinessUnitId"))
        _check(user in self.config.allowed_user_ids, "principal_not_authorized")
        schema = self._request(
            "GET",
            "/api/data/v9.2/EntityDefinitions(LogicalName='"
            + self.config.table_name
            + "')?$select=LogicalName,EntitySetName,IsOptimisticConcurrencyEnabled",
        )
        _check(
            schema.get("LogicalName") == self.config.table_name
            and schema.get("EntitySetName") == self.config.entity_set
            and schema.get("IsOptimisticConcurrencyEnabled") is True,
            "schema_concurrency_unverified",
        )
        return user

    def _path(self, identifier: str) -> str:
        return f"/api/data/v9.2/{self.config.entity_set}({_guid(identifier)})"

    def load(self, binding: NotificationLedger) -> LoadedLedger:
        """Require an existing row; missing/denied/failed reads never initialize new quota."""
        user = self._identity()
        identifier = row_id(self.config, binding)
        response = self._request(
            "GET", self._path(identifier) + "?$select=" + self.config.payload_column
        )
        state = decode_ledger(response.get(self.config.payload_column))
        _check(
            (
                state.tenant_ref,
                state.recipient_ref,
                state.channel_ref,
                state.scope_ref,
                state.history_origin,
            )
            == (
                binding.tenant_ref,
                binding.recipient_ref,
                binding.channel_ref,
                binding.scope_ref,
                binding.history_origin,
            ),
            "ledger_binding_mismatch",
        )
        etag = response.get("@odata.etag")
        _check(type(etag) is str and _ETAG.fullmatch(etag) is not None, "etag_missing")
        return LoadedLedger(
            ledger=state, etag=cast("str", etag), user_id=user, storage_id=identifier
        )

    def commit(self, previous: LoadedLedger, proposal: AdmissionResult) -> LoadedLedger:
        """Commit one complete next revision; uncertainty grants no delivery permission."""
        _check(self.config.writes_enabled, "writes_disabled")
        _check(
            type(previous) is LoadedLedger and type(proposal) is AdmissionResult, "invalid_proposal"
        )
        old = decode_ledger(encode_ledger(previous.ledger))
        new = decode_ledger(encode_ledger(proposal.ledger))
        _check(
            not proposal.replayed
            and new.revision == old.revision + 1
            and new.receipts[:-1] == old.receipts
            and new.receipts[-1] == proposal.receipt
            and new.evaluated_at is not None
            and new.evaluated_at >= (old.evaluated_at or old.history_origin),
            "invalid_proposal",
        )
        _check(
            row_id(self.config, old) == previous.storage_id == row_id(self.config, new)
            and (old.scope_ref, old.history_origin) == (new.scope_ref, new.history_origin)
            and type(previous.etag) is str
            and _ETAG.fullmatch(previous.etag) is not None,
            "invalid_proposal",
        )
        _check(self._identity() == previous.user_id, "identity_changed")
        encoded = encode_ledger(new)
        response = self._request(
            "PATCH",
            self._path(previous.storage_id),
            headers=("If-Match:" + previous.etag, "Prefer:return=representation"),
            body={self.config.payload_column: encoded},
            error="commit_unconfirmed",
        )
        _check(response.get(self.config.payload_column) == encoded, "commit_unconfirmed")
        etag = response.get("@odata.etag")
        _check(
            type(etag) is str and _ETAG.fullmatch(etag) is not None and etag != previous.etag,
            "commit_unconfirmed",
        )
        return LoadedLedger(
            ledger=new,
            etag=cast("str", etag),
            user_id=previous.user_id,
            storage_id=previous.storage_id,
            committed_command_ref=proposal.receipt.command_ref,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class DeliveryPlan:
    """Prepare idempotency metadata only; no provider or send operation exists."""

    provider_intent_ref: str
    reservation_ref: str
    candidate_fingerprint: str
    dispatch_enabled: bool = False


def prepare_delivery(committed: LoadedLedger, command_ref: str) -> DeliveryPlan:
    """Refuse read/replay/reconciliation states; even a committed plan cannot send."""
    _check(
        type(committed) is LoadedLedger and committed.committed_command_ref == command_ref,
        "not_committed_attempt",
    )
    ledger = decode_ledger(encode_ledger(committed.ledger))
    receipt = ledger.receipts[-1]
    _check(
        receipt.command_ref == command_ref and receipt.decision in {"reserved", "retry"},
        "not_committed_attempt",
    )
    reservation = next(
        r for r in ledger.reservations if r.reservation_ref == receipt.reservation_ref
    )
    return DeliveryPlan(
        provider_intent_ref=reservation.provider_intent_ref,
        reservation_ref=reservation.reservation_ref,
        candidate_fingerprint=reservation.candidate_fingerprint,
    )
