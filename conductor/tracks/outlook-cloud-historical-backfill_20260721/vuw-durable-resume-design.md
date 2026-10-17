# VUW synthetic two-page durable recovery design

Status: proposed implementation checklist, 17 October 2026. This document is
not a deployed flow, a persisted checkpoint, a schema creation request already
executed, or evidence of mailbox completeness. QH work remains deferred.

## Bounded outcome and ownership

Use the verified personal VUW Developer environment and exactly two explicitly
synthetic pages, with at least two distinct synthetic case/conversation references.
No mailbox connector reads, retained 30-record evidence, new source run or copied
private evidence are required. VUW-AI-TEST acceptance remains separately blocked.

Reliability owns checkpoint metadata, publisher/solution changes, rights and ALM.
Outlook owns page processing and restart/reconciliation behavior. M365 owns
independent authenticated service readback. Coordination serializes every writer.
Governance's active metadata slot must finish before any new platform mutation.

## Existing implementation ceiling

- `contracts/power-automate-outlook-historical-backfill.json` declares a cursor,
  manifest and failure policy; it is not an executable Power Automate definition.
- `contracts/dataverse-checkpoint.mapping.json` proposes watermark and bounded
  identifier sets; it does not bind a historical page, run or frozen configuration.
- `src/careops_process/reliability.py` implements an in-memory checkpoint and
  bounded identifier history. Neither its watermark nor evicted identifier sets
  establish durable historical recovery.
- `scripts/Invoke-GraphMailboxBackfill.ps1` starts at page one, advances its cursor
  in process and publishes final local artifacts safely. It has no durable page
  cursor reload or cloud worker restart.
- `src/careops_process/outlook_dataverse_destination.py` supports deterministic
  synthetic row IDs and reconciliation. The completed two-row SDK rehearsal proved
  row behavior, not page-state persistence or cloud resume.

## Stable identity and protected state

Freeze one synthetic run UUID before any write. Preserve it across worker deaths,
retries and replay. Checkpoint identity binds the actual organization UUID, run
UUID, opaque synthetic source/folder partition and frozen configuration digest.
The cursor is mutable protected state; it must never select a new checkpoint row.
A changed scope, configuration or run is a different operation and cannot reset
an unfinished operation silently.

Discover or author an actual checkpoint entity in Developer through the supported
metadata SDK, then export the authored solution. Logical names below describe
required semantics; they are not assumed deployed names or invented publisher
columns. Reliability must supply verified entity set, primary key, field types,
lengths and access before implementation binds them.

Required retained state:

- Immutable identity/configuration binding and mapping/protocol version.
- Monotonic committed page ordinal, completed-page content digest and durable
  expected fact membership or a separately bound complete page manifest.
- Input cursor/page reference and next cursor, with an explicit terminal flag.
  Empty, missing, expired and exhausted are distinct states.
- Reconciled candidate/emitted/duplicate/rejected counts and any dead-letter
  disposition; counts alone cannot establish membership or content equality.
- Commit command/receipt identity sufficient to resolve an ambiguous acknowledgement.
- Service ETag/revision and last successful commit time; bounded diagnostic codes.

Cursor state, exact instants and private identifiers remain restricted to the
worker and accountable operators. Treat opaque continuation tokens as sensitive;
do not print them, place them in public receipts, or permit cross-origin traversal.
Accept a documented retention/disposal policy, capacity limits and fail-closed
behavior rather than pruning required page history to fit a column.

## Page processing and conditional commit

1. Authenticate the explicit Developer target and verify actual organization/user,
   configuration binding and effective row rights. Load the existing checkpoint,
   complete manifest state and exact ETag. Missing state is an explicit initialization
   decision, never an implicit empty restart of an existing run.
2. Read the next synthetic page from the frozen source fixture. Validate cursor,
   scope, page identity/order, bounded response and deterministic content digest.
   Preserve the pending input so a retry can reconcile the same page. An unstable
   or changed page must fail closed rather than become a different page silently.
3. Use the same organization/run/fact-derived destination primary keys as the
   existing v1 codec. Create or reconcile each exact key without overwriting changed
   content. Independently verify all expected page keys and canonical payloads,
   exclusions/dead letters and count partitions before checkpoint advancement.
4. Advance checkpoint state and its page commit receipt together in one conditional
   row update using the loaded exact `If-Match` ETag. The actual table must support
   and enforce optimistic concurrency. Confirm the persisted representation and
   receipt; a local return value alone is insufficient.
5. For conflict, timeout or malformed/missing acknowledgement, re-read actual state.
   If the original page command/receipt and content match, acknowledge that commit;
   otherwise stop or retry reconciliation of the same page from confirmed state.
   Never advance on an unconfirmed write or create a fresh run to escape conflict.
6. Start the next page only from confirmed persisted state. Terminal completion
   requires both page manifests, exact destination reconciliation and confirmed
   exhaustion. A watermark is not a substitute for page exhaustion.

Event writes and checkpoint advancement are separate operations unless a real
supported transaction is implemented and tested. This design uses idempotent
row writes followed by conditional checkpoint advancement; it makes no multi-row
atomicity claim. A crash between them intentionally replays the same page.
Concurrent workers must not corrupt manifest state: use the same conditional
checkpoint revision, immutable page receipts and identical deterministic row IDs.
Conflicting content must stop both paths rather than use last-writer-wins.

## Minimal actual table and worker prerequisites

- [ ] Freeze maximum page membership, page count, manifest bytes and column
  capacity for this two-page test before authoring. Validate serialized sizes
  before writes; exceedance fails closed without trimming identity or receipt
  history. Bind these limits to the frozen configuration and discovered metadata.
- [ ] Name the single initialization owner and define create-if-absent behavior
  for a deterministic checkpoint primary key. Competing initializers must reconcile
  the actual existing binding; a conflict or lost acknowledgement must not replace
  state, silently create another row, or authorize an empty reset. Test the race.
- [ ] Freeze immutable page/command receipt retention and exact cleanup rules,
  including which receipts share the checkpoint row and how any external manifest
  references remain bound, available and protected until verification finishes.
- [ ] Reliability verifies/discovers the actual checkpoint entity or authors it
  environment-first in the isolated solution, with concurrency, field capacity,
  protected access, first-row initialization, export and rollback evidence.
- [ ] Select an executable cloud worker/flow with supported Dataverse operations,
  stable identity, connection references, DLP/licensing and operator ownership.
  A terminal Python script or a list of contract action labels is not that worker.
- [ ] Verify exact ETag conditional writes and receipt readback on the selected
  runtime. Prefer managed SDK/CLI capabilities; if the connector cannot express
  exact conditional semantics, select a supported authenticated API action or
  worker route and document that gap before authoring. Do not assume ordinary
  “Update a row” supplies compare-and-swap.
  Reliability inspected the installed SDK's ordinary `records.update` signature:
  it offers no ETag parameter. A normal update call therefore cannot implement
  this protocol by itself. Select and verify a supported conditional API surface
  in the actual licensed cloud runtime; do not emulate CAS with a prior read.
- [ ] Implement a versioned synthetic page provider, fixed run/configuration and
  protected cursor store. It must distinguish valid, expired, invalidated and
  exhausted cursors without any mailbox acquisition.
- [ ] For later real-source integration, separately establish the Outlook action's
  actual continuation visibility, token lifetime, replay/snapshot guarantees,
  inventory drift rules and approved restart policy. The synthetic provider does
  not establish those properties for `Get emails (V3)`.
- [ ] Provide independent exact-key service readback and a retained private test
  manifest identifying only the synthetic rows/checkpoints eligible for cleanup.

## Implementation and fault-injection checklist

- [ ] Add strict page/checkpoint/receipt models and offline regressions for scope,
  run/configuration mismatch, changed page content, missing fields and capacity.
- [ ] Bind actual checkpoint metadata and implement supported persisted load,
  initialization and exact-ETag advancement; do not add a local substitute store.
- [ ] Author and export the actual worker/flow with a fixture page source and
  persisted restart path. Preserve the same frozen run across fresh invocations.
- [ ] Fresh-worker reload resumes after confirmed page one and commits page two.
- [ ] Kill after part of page-one destination writes: restart reconciles those
  keys, completes the page and advances once, with no new identities on replay.
- [ ] Kill after all page writes but before checkpoint update: restart reads the
  old checkpoint, replays the same page and advances only after full reconciliation.
- [ ] Lose acknowledgement after a successful checkpoint update: fresh reload
  recognizes the original persisted page receipt without skipping or duplicating.
- [ ] Force checkpoint CAS conflict and two competing workers: only a matching
  confirmed commit may progress; changed content and stale bindings fail closed.
- [ ] Exercise expired/invalidated cursor: preserve last confirmed state, report
  an explicit recovery-required condition and do not infer exhaustion or restart
  with a new run. Any restart-from-page-one policy needs its own accepted semantics.
- [ ] Exercise missing row/manifest, partial readback, unavailable service, count
  mismatch, privacy rejection and page drift: no checkpoint advancement.
- [ ] Independent readback verifies exactly two exhausted page manifests, their
  memberships/content, stable run binding and unchanged destination identity set.
- [ ] Export the actual authored components and record private service evidence,
  scoped checks, limitations and independent review before claiming cloud recovery.

## Exact cleanup and evidence limits

After independent verification, obtain the coordinated cleanup writer slot.
Reverify target identity and exact synthetic run/configuration, compare every
allowlisted row's current payload, and delete only those primary keys. Include
the checkpoint/page receipts and any synthetic dead letters explicitly created
for this test. Stop on changed ownership/content; never use a broad table delete.
Read each key afterward to confirm absence, record a minimized receipt and release
the writer slot explicitly. Handle local private receipts under their stated
retention policy; do not delete or copy the separate retained mailbox evidence.

Success demonstrates durable recovery for this synthetic provider and deployed
worker in personal VUW Developer only. It does not prove real mailbox pagination,
full-folder inventory, full-run completeness, global cross-run event uniqueness,
VUW-AI-TEST deployment rights or QH acceptance. No platform operation is performed
by adopting this checklist.

Reliability's read-only ALM review found no blocking design issue. That review
requires the capacity, initialization-race, receipt-retention and conditional-API
decisions above before metadata authoring. Runtime feasibility remains under
assessment; this review does not authorize or establish deployed cloud recovery.

## Read-only runtime feasibility receipt

Reliability completed the bounded check on 17 October 2026. PAC 2.13.1 connection
listing against the explicit personal Developer target succeeded with “No results
returned.” Flow listing succeeded, but identified no verified CareOps worker or
conditional action. This is a bounded discovery result, not proof that no worker
can exist. The pre-baseline custom-table inventory contained no checkpoint or
watermark table; no actual checkpoint mapping has subsequently been handed off.

The local Dataverse CLI supports explicit target URLs, arbitrary request headers
and response-header inclusion, but has no authenticated profile and is not a cloud
runtime. The installed SDK's ordinary update operation has no ETag parameter.
Neither observation establishes a deployable conditional checkpoint worker.

One candidate for further assessment is a solution-aware Power Automate flow
with an actual Dataverse connection and a delegated HTTP action supporting exact
`If-Match`, status and response-header handling. This candidate has not been
verified available: licensing, connection creation/use, DLP, resource permissions
and action capabilities remain unresolved. Do not assume premium entitlement,
tenant-admin approval, consent or an existing connection from this design.

The next gate is therefore to select an actual permitted cloud runtime and verify
its conditional-write connection before checkpoint metadata or flow authoring.
After that, finalize the bounded schema, rights, initialization, retention and
recovery test contract, then obtain the coordinated writer slot. No new mailbox
acquisition is needed to resolve this runtime prerequisite. Reliability retained
the private connection/flow-listing receipts in the ignored ALM artifact directory.
No authentication, metadata or source changes were performed by the assessment.
