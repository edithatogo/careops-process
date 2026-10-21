# Durable local credentialing adapter

`credentialing_store.py` adds a SQLite runtime adapter for the credentialing
projection ledger and measurement-review workflow. It implements real local
transactions and credential checks, exercised with temporary synthetic databases.
It has not been deployed to VUW or integrated with Dataverse/Entra identity.
No real-source records, tenant credentials or operating approvals were used.

## Requirements and implemented boundaries

| Requested outcome | Local implementation |
| --- | --- |
| Durable storage | One versioned database stores projection, watermark, unbounded tombstones, inference provenance, minimized dead letters, server policy, principals, candidates and review receipts. |
| Deletion/replay recovery | Each ingestion transaction restores the latest committed tombstones before merge, applies deletions before replay, removes deleted inference provenance and commits the entire replacement state with its revision. Restart never begins from an empty fallback. |
| Authenticated access | Every request resolves a random bearer credential's hash to a live, unexpired server-stored principal. Roles and case grants are loaded inside the transaction. Request methods accept no role, actor, grant-set or evidence-digest override. |
| Atomic review persistence | A candidate is persisted first. Review authenticates the actor, checks expected ledger revision, regenerates the candidate from current authorised evidence and fixed server policy, and inserts one immutable measurement-only review while holding the same transaction lock. |

## Storage and restart recovery

`create_store(path, initial_projection, policy=StorePolicy(...))` is a separate
offline administrative bootstrap. File creation is exclusive; an existing file
is never overwritten. Initial evidence is observed only. A failed bootstrap may
leave an unusable new file for administrative inspection; request methods never
repair or reset it automatically. Schema version mismatches, missing state and
invalid retained evidence fail closed.

All request operations open a fresh connection and `BEGIN IMMEDIATE` transaction.
The database uses SQLite's local rollback-journal transaction machinery and
`synchronous=FULL`. The connection commits only after the complete operation
succeeds; exceptions roll back and close it. Readers also take this conservative
lock so identity, grants, policy and evidence are one consistent transaction.
Concurrent writers serialize, with a bounded five-second lock timeout; callers
must treat timeout as an uncommitted operation and retry safely.

`ingest` is source-wide and restricted to the separately provisioned `ingestor`
role. It merges a validated compatible source projection and optional concrete
inference-run records, applies tombstones first, prunes orphan provenance, and
increments a monotone ledger revision atomically. Exact fact replay does not
duplicate facts; a successful repeat transaction still advances the revision.
Changed fact/provenance replay fails. No tombstone eviction or undelete exists.
The greatest accepted source watermark is retained by the existing merge rules;
a watermark is not proof of complete source coverage.

`record_rejection` is an explicit separate ingestion operation for controlled
dead-letter classifications and server capture time. Invalid source content is
never copied into the rejection record. A rejected merge itself rolls back; a
caller may subsequently record a minimized rejection. This separation does not
claim an atomic external source acknowledgement/checkpoint protocol.

`snapshot` returns detached protected recovery state only to the ingestion role.
Changing that returned ledger does not change persisted state. The source adapter
still owns actual acquisition, stable identities, deletion notifications, approved
source mappings and retry/checkpoint coordination.

## Local test identity and access

`provision_principal` and `revoke_principal` are **offline administration**, outside
the `SQLiteCredentialingStore` request API. Only the service/administrator OS
account may access the database and these functions. They are exercised here
solely to provision explicit synthetic test identities; they do not issue Entra,
Dataverse or organisational credentials and are not a proposed public issuer.

Provisioning returns a generated 256-bit random local bearer credential once.
Only its SHA-256 hash is stored. It does not accept low-entropy passwords. Store
the credential outside logs, code and public artifacts. Unknown, malformed,
expired, revoked and wrong-role credentials receive the same fixed access-denied
error. Re-authentication occurs on every operation; there is no cached client
principal or reusable user-selected role. Revocation takes effect for the next
transaction; an already running transaction retains its authenticated snapshot.

| Server-stored role | Request operations |
| --- | --- |
| `ingestor` | Source-wide `ingest`, protected `snapshot`, `record_rejection` |
| `case_analyst` | `read_report`, with facts/links reduced to server-stored case grants |
| `report_reader` | `read_report`, aggregate event counters under fixed server privacy policy |
| `process_owner`, `assurance_reviewer` | Persist/open scoped candidates and submit measurement-only reviews |

The report projection preserves the existing event-counter semantics and privacy
rules. It does not replace the separate case-rate/calendar/variant reporter or
add cross-query release accounting. Case references must be classified by the
approved source adapter before administrators assign grants.

Any production request host must provide authenticated organisational identity,
approved principal/grant lifecycle, secure credential delivery/rotation,
transport security, request auditing, rate limits and safe exception handling.
There is no HTTP listener, tenant authentication, live identity provisioning or
self-service administration in this change. Code running as the trusted service
OS account can access its database; these request checks are not an isolation
boundary against that account or a local administrator.

## Review concurrency and evidence

`open_proposals` uses current server grants and fixed server policy to recompute
and persist candidates. It returns the ledger revision and currently unreviewed
candidates. Caller-created candidates and supplied evidence hashes are not
accepted by `review`.

`review` accepts only a candidate ID, opaque command/request ID, expected revision
and controlled measurement decision. Actor, role, scope and timestamp are resolved
server-side. Any ledger change can invalidate the expected revision; the caller
must reopen current evidence. Even with the current revision, a missing, changed,
suppressed or differently scoped candidate cannot be reviewed.

The unique candidate-review key ensures one competing human decision commits.
Request IDs provide exactly-once local command effects: an exact retry by the
same authenticated actor and scope returns the committed receipt. Changed
command content or a different actor fails. A retry after later source changes
returns a **historical receipt**, not a new judgment about current evidence.
Revoked or expired identities cannot retrieve it by retry. A different request
for an already reviewed candidate fails. Reviews never mutate source workflows
or confer clinical/operational authority.

## Deployment, retention and disaster recovery limits

Use a service-private local database on storage with supported SQLite locking.
`0o600` creation is not a Windows ACL configuration: explicitly restrict the
directory, database, journal and backup access using the deployment's OS policy.
The database is not encrypted by this module. OS/disk encryption, secure hosting,
backup access and approved retention must be established before real data use.
Do not place live state on OneDrive/network/shared storage without a separately
validated SQLite storage/locking design. Tests use local temporary directories.

Logical deletion removes retained event payload and inference provenance; it
does not prove physical erasure from SQLite pages, journals, disks or backups.
Tombstone identifiers intentionally persist. Candidate scopes, evidence hashes,
aggregate candidate values and opaque reviewer audit references remain protected
audit data under a separately approved retention policy. No retention migration,
cryptographic erasure or policy approval is inferred.

Crash/restart recovery of this committed database is tested. Restoring an older
backup is a different operation and can otherwise resurrect deleted facts or
revoked identities. This adapter offers no blind backup-import/reset API. Before
disaster restore, the operator must reconcile the latest authoritative deletion
feed/monotone recovery checkpoint, credential revocations, source watermarks and
audit history, then verify consistency before exposing the store. Use a coherent
SQLite backup process; copying a live file is not an accepted backup protocol.
Disaster-recovery procedures, backup loss/RPO/RTO and actual deployment acceptance
remain open and must not be inferred from the restart tests.

## Verify locally

`uv run --no-sync pytest tests/test_credentialing_store.py --no-cov -q`

The tests use explicit synthetic identities and temporary databases. They cover
restart after deletion/replay, inferred provenance deletion, failed-merge rollback,
an actual child process exiting before commit, concurrent independent connections,
competing reviews, a forced review-insert failure, expired/revoked credentials,
scope isolation, idempotent command replay and closed failures for corrupt state.
These are component receipts, not VUW deployment or real-source acceptance.

## Verification receipt — 17 October 2026

All 27 owned tests pass with ordinary pytest assertions. Module coverage is 97%
across 235 statements and 54 branches. Independent read-only review found no
actionable correctness/security/documentation findings and independently reran
all 27 tests without connection resource warnings. Scoped lint/format, strict
typing, Bandit, Conductor validation and whitespace checks pass. The integration
slice with the original projection, assurance, improvement and measurement tests
passes 166 tests. A bounded owned-file secret-pattern scan plus review found no
matches; Gitleaks was unavailable locally. No dependency or lockfile change is needed.
