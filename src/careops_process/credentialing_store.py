# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Local SQLite credentialing adapter with authenticated transactional operations.

Provisioning is a separate OS-administrator interface. Request methods accept
only opaque, generated bearer credentials; roles and grants come from storage.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from careops_process.credentialing import (
    CredentialingContractError,
    CredentialingProjection,
    validate_credentialing_projection,
)
from careops_process.credentialing_alignment_reporting import AlignmentReport, report_alignments
from careops_process.credentialing_alignment_service import (
    AlignmentStoreConfig,
    validate_alignment_config,
)
from careops_process.credentialing_assurance import (
    CredentialingLedger,
    InferenceRun,
    project_credentialing_report,
)
from careops_process.credentialing_improvements import (
    HumanMeasurementReview,
    ImprovementProposal,
    propose_stage_improvements,
    review_proposal,
)
from careops_process.reliability import DeadLetter

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence
    from pathlib import Path

type Role = Literal[
    "ingestor", "case_analyst", "report_reader", "process_owner", "assurance_reviewer"
]
type Reference = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*(?![\s\S])",
    ),
]
type PolicyCode = Annotated[Reference, Field(max_length=80)]
_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_REVIEW_ROLES = frozenset({"process_owner", "assurance_reviewer"})
_SCHEMA_VERSION = 1


def _fail(message: str) -> Never:
    raise CredentialingContractError(message)


def _code(value: object) -> None:
    if type(value) is not str or _CODE.fullmatch(value) is None:
        _fail("Store references must be bounded opaque codes")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        _fail("Store timestamps must be timezone-aware")
    return value.astimezone(UTC)


class _Record(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        regex_engine="python-re",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class StorePolicy(_Record):
    """Immutable server-controlled measurement policy for this one source store."""

    authority_version: PolicyCode
    minimum_cases: int = Field(strict=True, ge=2)
    threshold_hours: float = Field(strict=True, gt=0, le=1_000_000_000, allow_inf_nan=False)
    threshold_version: PolicyCode


class _Principal(_Record):
    principal_id: PolicyCode
    role: Role
    case_ids: frozenset[Reference]
    expires_at_utc: datetime

    @field_validator("expires_at_utc")
    @classmethod
    def aware_expiry(cls, value: datetime) -> datetime:
        return _aware(value)


class _DeadLetter(_Record):
    fact_id: Reference
    reason: Literal["schema", "conflicting_replay", "throttled", "timeout", "transient"]
    retryable: bool = Field(strict=True)
    recorded_at_utc: datetime

    @field_validator("recorded_at_utc")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        return _aware(value)


class _State(_Record):
    projection: CredentialingProjection
    tombstones: frozenset[Reference]
    provenance: dict[Reference, InferenceRun]
    dead_letters: tuple[_DeadLetter, ...]


@dataclass(frozen=True, slots=True)
class LedgerSnapshot:
    """Detached protected ingestion/recovery state, never a reporting response."""

    revision: int
    ledger: CredentialingLedger


def _ledger(state: _State) -> CredentialingLedger:
    return CredentialingLedger(
        projection=state.projection,
        tombstoned_event_ids=set(state.tombstones),
        inference_provenance=state.provenance,
        dead_letters=[DeadLetter(**item.model_dump()) for item in state.dead_letters],
    )


def _serialized(ledger: CredentialingLedger) -> str:
    return _State(
        projection=validate_credentialing_projection(ledger.projection),
        tombstones=frozenset(ledger.tombstoned_event_ids),
        provenance=ledger.inference_provenance,
        dead_letters=tuple(
            _DeadLetter.model_validate(asdict(item)) for item in ledger.dead_letters
        ),
    ).model_dump_json()


def alignment_snapshot_digest(ledger: CredentialingLedger) -> str:
    """Fingerprint a protected retained snapshot for trusted coverage configuration.

    This administrative helper authenticates nothing. Its digest is not a public
    reporting value, model acceptance or proof of temporal completeness.
    """
    if type(ledger) is not CredentialingLedger:
        _fail("Expected concrete retained ledger")
    retained = _ledger(_State.model_validate_json(_serialized(ledger)))
    payload = json.loads(_serialized(retained))
    payload["tombstones"] = sorted(payload["tombstones"])
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@contextmanager
def _transaction(path: Path) -> Generator[sqlite3.Connection]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        _fail("Store path must identify an existing database file")
    connection = sqlite3.connect(resolved.as_uri() + "?mode=rw", uri=True, timeout=5)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("BEGIN IMMEDIATE")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version != _SCHEMA_VERSION:
            _fail("Unsupported credentialing store schema version")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_store(path: Path, projection: CredentialingProjection, *, policy: StorePolicy) -> None:
    """Offline administrative bootstrap; never overwrite an existing store.

    Operators must protect the file/directory with OS access controls. Initial
    bootstrap admits observed evidence only; inferred facts enter via ingestion.
    """
    if type(policy) is not StorePolicy:
        _fail("Expected concrete server policy")
    policy = StorePolicy.model_validate(
        {key: getattr(policy, key) for key in StorePolicy.model_fields}
    )
    ledger = CredentialingLedger(validate_credentialing_projection(projection))
    payload = _serialized(ledger)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    connection = sqlite3.connect(path)
    try:
        connection.executescript("""
            PRAGMA synchronous=FULL;
            BEGIN IMMEDIATE;
            CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL,
                               payload TEXT NOT NULL, policy TEXT NOT NULL);
            CREATE TABLE principals(principal_id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
                                    payload TEXT NOT NULL,
                                    active INTEGER NOT NULL CHECK(active IN (0,1)));
            CREATE TABLE proposals(proposal_id TEXT PRIMARY KEY, scope TEXT NOT NULL,
                                   payload TEXT NOT NULL);
            CREATE TABLE reviews(request_id TEXT PRIMARY KEY, proposal_id TEXT UNIQUE NOT NULL,
                                 actor TEXT NOT NULL, command TEXT NOT NULL, payload TEXT NOT NULL,
                                 FOREIGN KEY(proposal_id) REFERENCES proposals(proposal_id));
        """)
        connection.execute("INSERT INTO state VALUES(1,0,?,?)", (payload, policy.model_dump_json()))
        connection.execute("PRAGMA user_version=1")
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def provision_principal(
    path: Path,
    *,
    principal_id: str,
    role: Role,
    case_ids: frozenset[str],
    expires_at_utc: datetime,
) -> str:
    """Offline OS-admin operation: return a new 256-bit credential exactly once.

    This does not accept passwords, expose provisioning over a request endpoint,
    or grant any Microsoft/clinical authority. Store only SHA-256 of random tokens.
    """
    principal = _Principal(
        principal_id=principal_id, role=role, case_ids=case_ids, expires_at_utc=expires_at_utc
    )
    if principal.expires_at_utc <= datetime.now(UTC):
        _fail("Provisioned credential must expire in the future")
    token = secrets.token_urlsafe(32)
    with _transaction(path) as connection:
        connection.execute(
            "INSERT INTO principals VALUES(?,?,?,1)",
            (
                principal.principal_id,
                hashlib.sha256(token.encode()).hexdigest(),
                principal.model_dump_json(),
            ),
        )
    return token


def revoke_principal(path: Path, principal_id: str) -> None:
    """Offline OS-admin revocation, effective on the next transaction."""
    _code(principal_id)
    with _transaction(path) as connection:
        connection.execute("UPDATE principals SET active=0 WHERE principal_id=?", (principal_id,))


def _authenticate(connection: sqlite3.Connection, token: str, roles: frozenset[str]) -> _Principal:
    if type(token) is not str or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
        msg = "Credentialing access denied"
        raise PermissionError(msg)
    row = connection.execute(
        "SELECT payload FROM principals WHERE token_hash=? AND active=1",
        (hashlib.sha256(token.encode()).hexdigest(),),
    ).fetchone()
    if row is None:
        msg = "Credentialing access denied"
        raise PermissionError(msg)
    principal = _Principal.model_validate_json(row[0])
    if principal.expires_at_utc <= datetime.now(UTC) or principal.role not in roles:
        msg = "Credentialing access denied"
        raise PermissionError(msg)
    return principal


def _load(connection: sqlite3.Connection) -> tuple[int, CredentialingLedger, StorePolicy]:
    row = connection.execute("SELECT revision,payload,policy FROM state WHERE id=1").fetchone()
    if row is None or type(row[0]) is not int or row[0] < 0:
        _fail("Credentialing store state is unavailable")
    return (
        row[0],
        _ledger(_State.model_validate_json(row[1])),
        StorePolicy.model_validate_json(row[2]),
    )


def _proposal_payload(proposal: ImprovementProposal) -> str:
    return json.dumps(asdict(proposal), default=lambda value: value.isoformat(), allow_nan=False)


def _parse_proposal(payload: str) -> ImprovementProposal:
    fields = json.loads(payload)
    fields["alternative_explanation_codes"] = tuple(fields["alternative_explanation_codes"])
    if fields["review"] is not None:
        review = fields["review"]
        review["decided_at_utc"] = datetime.fromisoformat(review["decided_at_utc"])
        fields["review"] = HumanMeasurementReview(**review)
    return ImprovementProposal(**fields)


def _proposals(
    ledger: CredentialingLedger, principal: _Principal, policy: StorePolicy
) -> tuple[ImprovementProposal, ...]:
    return propose_stage_improvements(
        ledger.projection,
        role="report_reader",
        case_ids=principal.case_ids,
        minimum_cases=policy.minimum_cases,
        authority_version=policy.authority_version,
        threshold_hours=policy.threshold_hours,
        threshold_version=policy.threshold_version,
    )


class SQLiteCredentialingStore:
    """Authenticated request surface, opening a fresh transaction per operation.

    File and backup access belongs only to the service and offline administrators.
    API credentials must be carried over a trusted local channel or TLS endpoint.
    """

    def __init__(self, path: Path, *, alignment_config: AlignmentStoreConfig | None = None) -> None:
        """Bind an existing store without provisioning users or creating files."""
        self._path = path.resolve(strict=True)
        self._alignment_config = (
            None if alignment_config is None else validate_alignment_config(alignment_config)
        )

    def read_alignment_report(self, token: str) -> AlignmentReport:
        """Authenticate a consistent snapshot, compute unlocked, recheck before release.

        No request-controlled policy, path, completeness or scope is accepted.
        The final transaction is the authorization/evidence linearization point;
        changes before it discard output, changes after it affect later requests.
        """
        with _transaction(self._path) as connection:
            principal = _authenticate(connection, token, frozenset({"report_reader"}))
            revision, ledger, policy = _load(connection)
            snapshot_digest = alignment_snapshot_digest(ledger)
        config = self._alignment_config
        if config is None:
            result = AlignmentReport("configuration_unavailable")
        else:
            config = validate_alignment_config(config)
            if config.ledger_revision != revision or config.ledger_sha256 != snapshot_digest:
                result = AlignmentReport("coverage_unavailable")
            elif config.model.authority_version != policy.authority_version:
                result = AlignmentReport("configuration_unavailable")
            else:
                result = report_alignments(
                    ledger,
                    config.model,
                    role=principal.role,
                    case_ids=principal.case_ids,
                    complete_case_ids=config.complete_case_ids.intersection(principal.case_ids),
                    minimum_cases=policy.minimum_cases,
                    python=config.python,
                    timeout_seconds=config.timeout_seconds,
                )
        # Never hold the SQLite write lock during optional backend computation.
        with _transaction(self._path) as connection:
            current = _authenticate(connection, token, frozenset({"report_reader"}))
            current_revision, current_ledger, current_policy = _load(connection)
            if (
                current,
                current_revision,
                current_policy,
                alignment_snapshot_digest(current_ledger),
            ) != (
                principal,
                revision,
                policy,
                snapshot_digest,
            ):
                return AlignmentReport("stale_snapshot")
            return result

    def snapshot(self, token: str) -> LedgerSnapshot:
        """Return detached source-wide state to an authenticated ingestion worker."""
        with _transaction(self._path) as connection:
            _authenticate(connection, token, frozenset({"ingestor"}))
            revision, ledger, _ = _load(connection)
            return LedgerSnapshot(revision, ledger)

    def ingest(
        self,
        token: str,
        incoming: CredentialingProjection,
        *,
        deleted_event_ids: Sequence[str] = (),
        provenance: Mapping[str, InferenceRun] | None = None,
    ) -> int:
        """Atomically persist deletion memory, provenance, merged facts and watermark."""
        with _transaction(self._path) as connection:
            _authenticate(connection, token, frozenset({"ingestor"}))
            revision, ledger, _ = _load(connection)
            if type(deleted_event_ids) not in (tuple, list):
                _fail("Deletion batch must be a concrete tuple or list of event references")
            for event_id in deleted_event_ids:
                _code(event_id)
                ledger.tombstone(event_id)
            for event_id, run in (provenance or {}).items():
                _code(event_id)
                if type(run) is not InferenceRun:
                    _fail("Expected concrete inference provenance")
                validated = InferenceRun.model_validate(
                    {key: getattr(run, key) for key in InferenceRun.model_fields}
                )
                for value in validated.model_dump().values():
                    _code(value)
                if event_id in ledger.tombstoned_event_ids:
                    continue
                existing = ledger.inference_provenance.get(event_id)
                if existing is not None and existing != validated:
                    _fail("Conflicting inference provenance replay")
                ledger.inference_provenance[event_id] = validated
            ledger.merge(incoming)
            live_inferred = {
                fact.event_id
                for fact in ledger.projection.facts
                if fact.observed_or_inferred == "inferred"
            }
            ledger.inference_provenance = {
                key: run for key, run in ledger.inference_provenance.items() if key in live_inferred
            }
            connection.execute(
                "UPDATE state SET revision=?,payload=? WHERE id=1",
                (revision + 1, _serialized(ledger)),
            )
            return revision + 1

    def record_rejection(self, token: str, *, event_id: str, reason: str) -> int:
        """Persist a minimized dead letter, with server time and controlled reason."""
        with _transaction(self._path) as connection:
            _authenticate(connection, token, frozenset({"ingestor"}))
            revision, ledger, _ = _load(connection)
            ledger.reject(event_id, reason, recorded_at_utc=datetime.now(UTC))
            connection.execute(
                "UPDATE state SET revision=?,payload=? WHERE id=1",
                (revision + 1, _serialized(ledger)),
            )
            return revision + 1

    def read_report(self, token: str) -> dict[str, object]:
        """Resolve access grants server-side and project only the permitted response."""
        with _transaction(self._path) as connection:
            principal = _authenticate(
                connection, token, frozenset({"case_analyst", "report_reader"})
            )
            _, ledger, policy = _load(connection)
            return project_credentialing_report(
                ledger.projection,
                role=principal.role,
                case_ids=set(principal.case_ids),
                minimum_cases=policy.minimum_cases,
            )

    def open_proposals(self, token: str) -> tuple[int, tuple[ImprovementProposal, ...]]:
        """Persist evidence-bound candidates, without accepting a caller's digest."""
        with _transaction(self._path) as connection:
            principal = _authenticate(connection, token, _REVIEW_ROLES)
            revision, ledger, policy = _load(connection)
            proposals = _proposals(ledger, principal, policy)
            result: list[ImprovementProposal] = []
            for proposal in proposals:
                connection.execute(
                    "INSERT OR IGNORE INTO proposals VALUES(?,?,?)",
                    (
                        proposal.proposal_id,
                        json.dumps(sorted(principal.case_ids)),
                        _proposal_payload(proposal),
                    ),
                )
                if (
                    connection.execute(
                        "SELECT 1 FROM reviews WHERE proposal_id=?", (proposal.proposal_id,)
                    ).fetchone()
                    is None
                ):
                    result.append(proposal)
            return revision, tuple(result)

    def review(
        self,
        token: str,
        *,
        proposal_id: str,
        request_id: str,
        expected_revision: int,
        decision: str,
    ) -> ImprovementProposal:
        """Authenticate, resolve current evidence and commit exactly one human review."""
        _code(proposal_id)
        _code(request_id)
        if type(expected_revision) is not int or expected_revision < 0:
            _fail("Expected revision must be a nonnegative concrete integer")
        if type(decision) is not str or decision not in {
            "accepted",
            "rejected",
            "needs_more_evidence",
        }:
            _fail("Unsupported measurement-review decision")
        with _transaction(self._path) as connection:
            principal = _authenticate(connection, token, _REVIEW_ROLES)
            scope = json.dumps(sorted(principal.case_ids))
            command = json.dumps((proposal_id, expected_revision, decision, scope))
            previous = connection.execute(
                "SELECT actor,command,payload FROM reviews WHERE request_id=?", (request_id,)
            ).fetchone()
            if previous is not None:
                if previous[0] != principal.principal_id or previous[1] != command:
                    _fail("Conflicting review command replay")
                return _parse_proposal(previous[2])
            revision, ledger, policy = _load(connection)
            if revision != expected_revision:
                _fail("Stale review evidence revision")
            proposal = next(
                (
                    item
                    for item in _proposals(ledger, principal, policy)
                    if item.proposal_id == proposal_id
                ),
                None,
            )
            retained = connection.execute(
                "SELECT scope,payload FROM proposals WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
            if (
                proposal is None
                or retained is None
                or retained[0] != scope
                or _parse_proposal(retained[1]) != proposal
            ):
                _fail("Review requires a persisted candidate and current authorised evidence")
            if (
                connection.execute(
                    "SELECT 1 FROM reviews WHERE proposal_id=?", (proposal_id,)
                ).fetchone()
                is not None
            ):
                _fail("Proposal already reviewed")
            reviewed = review_proposal(
                proposal,
                decision=decision,
                reviewer_reference=principal.principal_id,
                reviewer_role=principal.role,
                decided_at_utc=datetime.now(UTC),
                current_evidence_digest=proposal.evidence_digest,
            )
            connection.execute(
                "INSERT INTO reviews VALUES(?,?,?,?,?)",
                (
                    request_id,
                    proposal_id,
                    principal.principal_id,
                    command,
                    _proposal_payload(reviewed),
                ),
            )
            return reviewed
