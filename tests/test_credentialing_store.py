# Copyright (c) 2026 CareOps contributors
# SPDX-License-Identifier: Apache-2.0

"""Durable replay, request authentication and transactional human-review tests."""

# Synthetic arithmetic expectations are deliberate literals.
# ruff: noqa: PLR2004

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from careops_process.credentialing import CredentialingProjection, validate_credentialing_projection
from careops_process.credentialing_assurance import RENEWAL_STAGES, InferenceRun
from careops_process.credentialing_store import (
    SQLiteCredentialingStore,
    StorePolicy,
    create_store,
    provision_principal,
    revoke_principal,
)

if TYPE_CHECKING:
    from pathlib import Path


def projection() -> CredentialingProjection:
    """Two complete observed cases make a releasable synthetic evidence cohort."""
    return validate_credentialing_projection(
        {
            "source": "careops-approve",
            "watermark_utc": "2026-01-02T00:00:00Z",
            "facts": [
                {
                    "event_id": f"event-{case}-{index}",
                    "activity": stage,
                    "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
                    "source_system": "synthetic",
                    "object_ids": [f"case-{case}"],
                    "observed_or_inferred": "observed",
                    "confidence": 1.0,
                    "qualifiers": {
                        "pathway_code": "routine-renewal",
                        "authority_mapping_version": "synthetic-v1",
                    },
                }
                for case in range(2)
                for index, stage in enumerate(RENEWAL_STAGES)
            ],
        }
    )


def setup_store(tmp_path: Path) -> tuple[Path, str, str]:
    """Provision credentials via the separate local administrative interface."""
    path = tmp_path / "credentialing.sqlite"
    create_store(
        path,
        projection(),
        policy=StorePolicy(
            authority_version="synthetic-v1",
            minimum_cases=2,
            threshold_hours=0.5,
            threshold_version="policy-v1",
        ),
    )
    expiry = datetime.now(UTC) + timedelta(hours=1)
    ingestor = provision_principal(
        path,
        principal_id="source-worker",
        role="ingestor",
        case_ids=frozenset(),
        expires_at_utc=expiry,
    )
    reviewer = provision_principal(
        path,
        principal_id="reviewer-one",
        role="assurance_reviewer",
        case_ids=frozenset({"case-0", "case-1"}),
        expires_at_utc=expiry,
    )
    return path, ingestor, reviewer


def test_delete_restart_and_replay_cannot_resurrect_fact(tmp_path: Path) -> None:
    """Recovery restores tombstones before accepting another source batch."""
    path, ingestor, _ = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision = store.ingest(ingestor, projection(), deleted_event_ids=("event-0-0",))
    assert revision == 1
    restarted = SQLiteCredentialingStore(path)
    restarted.ingest(ingestor, projection())
    state = restarted.snapshot(ingestor)
    assert len(state.ledger.projection.facts) == 25
    assert state.ledger.tombstoned_event_ids == {"event-0-0"}
    assert state.ledger.projection.watermark_utc == datetime(2026, 1, 2, tzinfo=UTC)


def test_review_is_persisted_with_authenticated_actor_and_idempotent_command(
    tmp_path: Path,
) -> None:
    """Restart and retry return the same committed measurement-only review."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    proposal = proposals[0]
    reviewed = store.review(
        reviewer,
        proposal_id=proposal.proposal_id,
        request_id="request-1",
        expected_revision=revision,
        decision="accepted",
    )
    assert reviewed.review is not None
    assert reviewed.review.reviewer_reference == "reviewer-one"
    assert reviewed.review.scope == "measurement_review_only"
    assert (
        SQLiteCredentialingStore(path).review(
            reviewer,
            proposal_id=proposal.proposal_id,
            request_id="request-1",
            expected_revision=revision,
            decision="accepted",
        )
        == reviewed
    )
    with pytest.raises(ValueError, match="replay"):
        store.review(
            reviewer,
            proposal_id=proposal.proposal_id,
            request_id="request-1",
            expected_revision=revision,
            decision="rejected",
        )


def test_ledger_change_blocks_stale_review(tmp_path: Path) -> None:
    """Expected revision is checked under the same lock as evidence recomputation."""
    path, ingestor, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    store.ingest(ingestor, projection(), deleted_event_ids=("event-0-0",))
    with pytest.raises(ValueError, match="Stale"):
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="stale",
            expected_revision=revision,
            decision="accepted",
        )


def test_invalid_and_revoked_credentials_fail_on_each_request(tmp_path: Path) -> None:
    """Knowing a principal reference or having an old session grants no access."""
    path, ingestor, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    with pytest.raises(PermissionError):
        store.snapshot("source-worker")
    with pytest.raises(PermissionError):
        store.snapshot(reviewer)
    revoke_principal(path, "source-worker")
    with pytest.raises(PermissionError):
        store.snapshot(ingestor)


def test_reviewers_cannot_ingest_or_choose_roles(tmp_path: Path) -> None:
    """Writer rights are separate from human review permissions."""
    path, _, reviewer = setup_store(tmp_path)
    with pytest.raises(PermissionError):
        SQLiteCredentialingStore(path).ingest(reviewer, projection())


def test_failed_merge_rolls_back_deletion_and_revision(tmp_path: Path) -> None:
    """Deleting first cannot leave deletion committed when the batch conflicts."""
    path, ingestor, _ = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    changed = projection().model_dump(mode="json")
    changed["source"] = "careops-decisions"
    with pytest.raises(ValueError, match="source"):
        store.ingest(
            ingestor, validate_credentialing_projection(changed), deleted_event_ids=("event-0-0",)
        )
    state = store.snapshot(ingestor)
    assert state.revision == 0
    assert not state.ledger.tombstoned_event_ids
    assert len(state.ledger.projection.facts) == 26


def test_inferred_provenance_survives_restart_and_is_deleted_atomically(tmp_path: Path) -> None:
    """An inferred event and its provenance share one recovery boundary."""
    path, ingestor, _ = setup_store(tmp_path)
    payload = projection().model_dump(mode="json")
    payload["facts"] = [
        {
            **payload["facts"][0],
            "event_id": "inferred-event",
            "observed_or_inferred": "inferred",
            "confidence": 0.8,
        }
    ]
    batch = validate_credentialing_projection(payload)
    run = InferenceRun(run_id="run-1", provider="synthetic", model="test", agent_version="v1")
    store = SQLiteCredentialingStore(path)
    with pytest.raises(ValueError, match="provenance"):
        store.ingest(ingestor, batch)
    store.ingest(ingestor, batch, provenance={"inferred-event": run})
    restored = SQLiteCredentialingStore(path).snapshot(ingestor)
    assert restored.ledger.inference_provenance == {"inferred-event": run}
    store.ingest(ingestor, batch, deleted_event_ids=("inferred-event",))
    store.ingest(ingestor, batch, provenance={"inferred-event": run})
    restored = SQLiteCredentialingStore(path).snapshot(ingestor)
    assert not restored.ledger.inference_provenance
    assert all(fact.event_id != "inferred-event" for fact in restored.ledger.projection.facts)


def test_concurrent_ingestion_serializes_without_lost_update(tmp_path: Path) -> None:
    """Two independent connections retain both source changes."""
    path, ingestor, _ = setup_store(tmp_path)

    def ingest_one(index: int) -> int:
        payload = projection().model_dump(mode="json")
        payload["facts"] = [{**payload["facts"][0], "event_id": f"extra-{index}"}]
        return SQLiteCredentialingStore(path).ingest(
            ingestor, validate_credentialing_projection(payload)
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(ingest_one, range(2))) == [1, 2]
    assert len(SQLiteCredentialingStore(path).snapshot(ingestor).ledger.projection.facts) == 28


def test_concurrent_review_commits_only_one_human_decision(tmp_path: Path) -> None:
    """Distinct commands racing for one candidate yield one committed review."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)

    def review_one(index: int) -> str:
        try:
            store.review(
                reviewer,
                proposal_id=proposals[0].proposal_id,
                request_id=f"request-{index}",
                expected_revision=revision,
                decision="accepted",
            )
        except ValueError as error:
            assert str(error) == "Proposal already reviewed"  # noqa: PT017 - distinguish racing outcomes
            return "conflict"
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(review_one, range(2))) == ["committed", "conflict"]
    with closing(sqlite3.connect(path)) as connection, connection:
        assert connection.execute("SELECT count(*) FROM reviews").fetchone()[0] == 1


def test_forced_process_exit_recovers_previous_complete_transaction(tmp_path: Path) -> None:
    """An abrupt writer exit before COMMIT cannot expose a partial ledger."""
    path, ingestor, _ = setup_store(tmp_path)
    script = """
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE state SET revision=999,payload=? WHERE id=1', ('corrupt-uncommitted',))
os._exit(23)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path)], check=False, timeout=10)  # noqa: S603
    assert result.returncode == 23
    state = SQLiteCredentialingStore(path).snapshot(ingestor)
    assert state.revision == 0
    assert len(state.ledger.projection.facts) == 26


def test_failed_review_insert_leaves_candidate_open_and_retryable(tmp_path: Path) -> None:
    """A storage fault cannot leave a review partially accepted."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "CREATE TRIGGER fail_review BEFORE INSERT ON reviews "
            "BEGIN SELECT RAISE(ABORT, 'synthetic-fault'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic-fault"):
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="retry",
            expected_revision=revision,
            decision="accepted",
        )
    with closing(sqlite3.connect(path)) as connection, connection:
        assert connection.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0
        connection.execute("DROP TRIGGER fail_review")
    assert proposals[0] in store.open_proposals(reviewer)[1]
    assert (
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="retry",
            expected_revision=revision,
            decision="accepted",
        ).review
        is not None
    )


def test_server_grants_control_analyst_and_aggregate_responses(tmp_path: Path) -> None:
    """Credentials cannot request a different role or a broader case population."""
    path, _, _ = setup_store(tmp_path)
    expiry = datetime.now(UTC) + timedelta(hours=1)
    analyst = provision_principal(
        path,
        principal_id="analyst",
        role="case_analyst",
        case_ids=frozenset({"case-0"}),
        expires_at_utc=expiry,
    )
    reader = provision_principal(
        path,
        principal_id="reader",
        role="report_reader",
        case_ids=frozenset({"case-0"}),
        expires_at_utc=expiry,
    )
    store = SQLiteCredentialingStore(path)
    response = json.dumps(store.read_report(analyst))
    assert "case-0" in response
    assert "case-1" not in response
    assert store.read_report(reader) == {"suppressed": True, "metrics": None}
    with pytest.raises(PermissionError):
        store.open_proposals(analyst)


def test_only_credential_hash_is_stored_and_expiry_is_enforced(tmp_path: Path) -> None:
    """A database token hash is not accepted as a bearer credential."""
    path, ingestor, _ = setup_store(tmp_path)
    with closing(sqlite3.connect(path)) as connection, connection:
        token_hash, payload = connection.execute(
            "SELECT token_hash,payload FROM principals WHERE principal_id='source-worker'",
        ).fetchone()
        assert ingestor not in token_hash + payload
        principal = json.loads(payload)
        principal["expires_at_utc"] = "2000-01-01T00:00:00Z"
        connection.execute(
            "UPDATE principals SET payload=? WHERE principal_id='source-worker'",
            (json.dumps(principal),),
        )
    store = SQLiteCredentialingStore(path)
    with pytest.raises(PermissionError):
        store.snapshot(token_hash)
    with pytest.raises(PermissionError):
        store.snapshot(ingestor)


def test_minimized_rejections_are_durable(tmp_path: Path) -> None:
    """Failure metadata has a controlled reason and excludes raw content."""
    path, ingestor, _ = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    store.record_rejection(ingestor, event_id="unsafe narrative", reason="schema")
    state = SQLiteCredentialingStore(path).snapshot(ingestor)
    assert state.ledger.dead_letters[0].fact_id == "unidentified"
    assert state.ledger.dead_letters[0].reason == "schema"
    with pytest.raises(ValueError, match="controlled"):
        store.record_rejection(ingestor, event_id="event", reason="raw error text")


def test_existing_store_cannot_be_overwritten(tmp_path: Path) -> None:
    """Administrative bootstrap is exclusive, preserving prior state and identities."""
    path, ingestor, _ = setup_store(tmp_path)
    with pytest.raises(FileExistsError):
        create_store(
            path,
            projection(),
            policy=StorePolicy(
                authority_version="synthetic-v1",
                minimum_cases=2,
                threshold_hours=0.5,
                threshold_version="policy-v1",
            ),
        )
    assert SQLiteCredentialingStore(path).snapshot(ingestor).revision == 0


def test_unknown_well_formed_credential_is_denied(tmp_path: Path) -> None:
    """A correctly shaped but unregistered token is not an authenticated identity."""
    path, _, _ = setup_store(tmp_path)
    with pytest.raises(PermissionError, match="access denied"):
        SQLiteCredentialingStore(path).snapshot("x" * 43)


@pytest.mark.parametrize("decision", ["deploy", "accepted\n", ""])
def test_review_cannot_expand_measurement_authority(tmp_path: Path, decision: str) -> None:
    """No command can persist an operational decision or arbitrary narrative."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    with pytest.raises(ValueError, match="Unsupported"):
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="request",
            expected_revision=revision,
            decision=decision,
        )


def test_review_requires_current_authorized_persisted_candidate(tmp_path: Path) -> None:
    """A plausible proposal ID does not establish current evidence or a persisted candidate."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("DELETE FROM proposals WHERE proposal_id=?", (proposals[0].proposal_id,))
    with pytest.raises(ValueError, match="persisted candidate"):
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="request",
            expected_revision=revision,
            decision="accepted",
        )
    with pytest.raises(ValueError, match="revision"):
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="request",
            expected_revision=True,
            decision="accepted",
        )


def test_review_cannot_use_another_principals_scope_or_command(tmp_path: Path) -> None:
    """Changing the reviewer's grants changes evidence, even with a known candidate ID."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    other = provision_principal(
        path,
        principal_id="other",
        role="process_owner",
        case_ids=frozenset({"case-0"}),
        expires_at_utc=datetime.now(UTC) + timedelta(hours=1),
    )
    with pytest.raises(ValueError, match="current authorised evidence"):
        store.review(
            other,
            proposal_id=proposals[0].proposal_id,
            request_id="request",
            expected_revision=revision,
            decision="accepted",
        )
    store.review(
        reviewer,
        proposal_id=proposals[0].proposal_id,
        request_id="request",
        expected_revision=revision,
        decision="accepted",
    )
    with pytest.raises(ValueError, match="replay"):
        store.review(
            other,
            proposal_id=proposals[0].proposal_id,
            request_id="request",
            expected_revision=revision,
            decision="accepted",
        )
    assert proposals[0] not in store.open_proposals(reviewer)[1]


def test_provenance_replay_conflicts_roll_back_state(tmp_path: Path) -> None:
    """Changed inferred provenance cannot silently replace retained attribution."""
    path, ingestor, _ = setup_store(tmp_path)
    payload = projection().model_dump(mode="json")
    payload["facts"] = [
        {
            **payload["facts"][0],
            "event_id": "inferred-event",
            "observed_or_inferred": "inferred",
            "confidence": 0.8,
        }
    ]
    batch = validate_credentialing_projection(payload)
    run = InferenceRun(run_id="run-1", provider="synthetic", model="test", agent_version="v1")
    store = SQLiteCredentialingStore(path)
    store.ingest(ingestor, batch, provenance={"inferred-event": run})
    with pytest.raises(ValueError, match="Conflicting"):
        store.ingest(
            ingestor,
            batch,
            provenance={"inferred-event": run.model_copy(update={"run_id": "run-2"})},
        )
    assert store.snapshot(ingestor).revision == 1
    assert store.snapshot(ingestor).ledger.inference_provenance["inferred-event"].run_id == "run-1"


def test_schema_mismatch_and_corrupt_state_fail_closed(tmp_path: Path) -> None:
    """No empty-state fallback may hide database/version loss."""
    path, ingestor, _ = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError, match="schema version"):
        store.snapshot(ingestor)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("PRAGMA user_version=1")
        connection.execute("DELETE FROM state")
    with pytest.raises(ValueError, match="unavailable"):
        store.snapshot(ingestor)


def test_administrative_expiry_and_policy_validation(tmp_path: Path) -> None:
    """Offline provisioning cannot silently accept invalid policy or expired identities."""
    path, _, _ = setup_store(tmp_path)
    with pytest.raises(ValueError, match="future"):
        provision_principal(
            path,
            principal_id="expired",
            role="report_reader",
            case_ids=frozenset(),
            expires_at_utc=datetime(2000, 1, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        provision_principal(
            path,
            principal_id="naive",
            role="report_reader",
            case_ids=frozenset(),
            expires_at_utc=datetime(2030, 1, 1),  # noqa: DTZ001 - deliberately invalid input
        )
    with pytest.raises(ValueError, match="validation error"):
        StorePolicy(
            authority_version="synthetic-v1",
            minimum_cases=True,
            threshold_hours=0.5,
            threshold_version="policy-v1",
        )


def test_deleted_event_memory_is_not_evicted_on_restart(tmp_path: Path) -> None:
    """More than the generic checkpoint limit cannot discard an old tombstone."""
    path, ingestor, _ = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    deleted = ("event-0-0", *(f"deleted-{index}" for index in range(10_001)))
    store.ingest(ingestor, projection(), deleted_event_ids=deleted)
    restarted = SQLiteCredentialingStore(path)
    restarted.ingest(ingestor, projection())
    state = restarted.snapshot(ingestor)
    assert len(state.ledger.tombstoned_event_ids) == 10_002
    assert all(fact.event_id != "event-0-0" for fact in state.ledger.projection.facts)


def test_scalar_deletion_batch_and_raw_references_rejected(tmp_path: Path) -> None:
    """A string must not be interpreted as a sequence of event identities."""
    path, ingestor, _ = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    with pytest.raises(ValueError, match="Deletion batch"):
        store.ingest(ingestor, projection(), deleted_event_ids="event-0-0")
    with pytest.raises(ValueError, match="bounded opaque"):
        store.ingest(ingestor, projection(), deleted_event_ids=("event-0-0\n",))
    assert store.snapshot(ingestor).revision == 0


def test_revoked_reviewer_cannot_retrieve_committed_receipt(tmp_path: Path) -> None:
    """Idempotence never bypasses current credential validation."""
    path, _, reviewer = setup_store(tmp_path)
    store = SQLiteCredentialingStore(path)
    revision, proposals = store.open_proposals(reviewer)
    store.review(
        reviewer,
        proposal_id=proposals[0].proposal_id,
        request_id="request",
        expected_revision=revision,
        decision="accepted",
    )
    revoke_principal(path, "reviewer-one")
    with pytest.raises(PermissionError, match="access denied"):
        store.review(
            reviewer,
            proposal_id=proposals[0].proposal_id,
            request_id="request",
            expected_revision=revision,
            decision="accepted",
        )
