# Authenticated local alignment reporting

`SQLiteCredentialingStore.read_alignment_report(token)` connects the existing
retained ledger, stored access policy and optional canonical-model alignment
reporter. Only an active, unexpired **report_reader** may use it. Ingestors,
case analysts, process owners and assurance reviewers retain their other
permissions but receive no implicit access to this report.

This is a local synthetic-capable adapter, not VUW/Entra authentication,
Dataverse deployment, an approved source model or an accepted capacity study.
The original track and operational acceptance gates remain open.

## Trusted startup configuration

The request accepts only the bearer token. Role, case grants, privacy threshold,
model, interpreter/path, timeout and completeness cannot be supplied as request
overrides. The constructor optionally accepts a trusted `AlignmentStoreConfig`:

- A concrete validated `AlignmentModel`, including artifact digest, explicit
  markings, activity/pathway/authority binding and the pinned semantics method.
- An absolute service-configured Python path and finite timeout up to 60 seconds.
  The base profile imports no PM4Py. An absent runtime is unavailable rather
  than a synthetic fitness result.
- An explicit `coverage_definition_version` identifying the accepted **temporal
  inclusion/completion criteria for the entire retained snapshot**. This is
  protected source-owner metadata, not proof that the criteria are appropriate
  or that evidence satisfies them. No temporal window, case completeness or
  clinical completion is inferred from activity labels.
- The exact ledger revision and canonical retained-state SHA-256, plus a frozen
  set of source-classified complete-case references. Complete means a full
  observed trace is covered, not that it conforms or reaches a model final state.

The configuration and nested model are reconstructed and detached at startup;
record/scalar coercion or subclass bypasses are rejected. Configuration remains
immutable for that service instance. A new accepted coverage/model configuration
requires a new trusted instance, not a reporting request.

The canonical digest binds retained projection, deletion memory, provenance,
watermark and dead-letter state. Mapping keys and tombstone sets are canonical;
projection validation supplies deterministic event order. `alignment_snapshot_digest`
is an administrative helper for protected retained snapshots. Its value is never
returned in the aggregate. Hash syntax alone authenticates no source or approval.

Revision numbers are store-local. A completeness configuration for store A must
not become valid for unrelated facts in store B merely because both have revision
zero. The digest prevents that substitution. Genuinely identical retained state
can have the same digest; no new database identity registry is implied.

The stored privacy threshold always applies. The model authority must match the
stored authority. Effective complete cases are the configured set intersected
with the freshly stored principal's case grants; completeness never creates
access. Missing configuration, mismatched authority or stale revision/digest
produces an unavailable report with no counts. Ingestion, deletion or a recorded
source rejection requires fresh accepted snapshot coverage before another
alignment result can be released; it is never automatically approved.

## Consistency and revocation

The service first authenticates and loads principal, ledger, policy, revision and
digest in one short transaction. It closes the transaction before running the
existing pure alignment reporter. The optional worker therefore holds no SQLite
write lock; ingestion and revocation can proceed while it runs.

Before returning **any** result, including suppressed or unavailable results, a
second short transaction reauthenticates the same token and reloads evidence.
It compares the full principal, including role, grants and expiry, the stored
policy, ledger revision and canonical retained-state digest. Revocation,
expiration or a now-ineligible role raises the existing uniform access-denied
error. Changed grants, policy or evidence discard the entire computed report and
return `stale_snapshot` with no metrics. Even a state change that accidentally
reuses a revision is detected. There is no automatic expensive retry.

The successful final validation transaction is the release's authorization and
evidence linearization point. Changes after it affect subsequent releases; no
service can retroactively withdraw a result already authorised and returned.
A coherent older database and its matching older startup configuration can
still pass a digest check. The digest is not an anti-rollback or freshness proof.
Approved disaster recovery must reconcile authoritative deletion/revocation
history and monotone checkpoints before serving restored state, as described in
the store manual.

Longitudinal/differencing privacy, transport, token lifecycle, host ACLs,
encryption and disaster recovery remain deployment responsibilities.

## Storage and output boundaries

Existing schema-v1 stores and constructor calls remain compatible. No migration,
new table, model-approval registry or request configuration endpoint is added.
Trusted service startup must supply the admitted configuration after restart.
An unconfigured service can still use its existing reports and review methods;
alignment reporting is explicitly unavailable.

Reports preserve the existing joint-case suppression and equal-weight case-mean
fitness semantics. They contain no case/event IDs, model/source references,
temporal metadata, protected digest or per-trace alignments. Snapshot/source-wide
state remains restricted to the existing authenticated ingestion interface.
See [alignment semantics and limits](credentialing-model-alignments.md) and
[local-store deployment boundaries](credentialing-store.md).

## Verification

Run `uv run --no-sync pytest tests/test_credentialing_alignment_store.py --no-cov -q`.
The synthetic tests cover stored role/grant boundaries, unavailable configuration,
strict detached records, stale coverage, wrong-store/same-revision evidence,
deletion/restart/replay and an actual pinned-backend weighted model.

Thread-event barriers hold mining while another connection ingests, deletes,
revokes, changes grants/policy/expiry/role, or alters evidence without advancing
the revision. Those writes finish before mining is released; no stale or revoked
result is returned. Separate tests verify final authorization on missing/stale
configuration, suppressed and unavailable paths. These are local evidence,
not operational source acceptance, causal capacity or governance sign-off.
