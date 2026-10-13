# Outlook acquired evidence interface

Version: 2.0.0; verified offline on 14 October 2026. This interface belongs to
the Graph message collector. It is distinct from the report consumer's
`manifest_version: 2.0.0` closed-run interface.

## Files and record mapping

The exporter publishes a dedicated directory containing `mail-events.jsonl`
(UTF-8 without BOM, LF separators, sorted by fact identity) and `manifest.json`.
An empty population produces a zero-byte JSONL file. No raw identifiers,
addresses, subject, narrative, folder names or mailbox address are persisted.

Each JSONL record has these fields:

| Field | Meaning |
| --- | --- |
| `id` | HMAC pseudonym over mailbox reference, immutable message ID and folder ID |
| `activity` | Observed `email_received`; no inferred process classification |
| `timestamp_utc` | UTC-normalised received timestamp |
| `source_system` | `outlook` |
| `object_ids` | One domain-separated conversation pseudonym |
| `folder_id` | Domain-separated folder pseudonym |
| `has_attachments` | Boolean metadata; attachments are not fetched |
| `importance` | Allowlisted `low`, `normal` or `high` metadata |

For downstream closed-run facts, select exactly `id`, `activity`,
`timestamp_utc`, `source_system`, `object_ids` and serialize a JSON array.
Keep folder membership in the separately reconciled partition evidence before
discarding `folder_id`. Do not pass the JSONL byte hash as the closed fact hash:
the consumer hashes canonical ASCII JSON with sorted object keys, compact
separators and preserved array order. Optional metadata is omitted by that
explicit mapping, not silently accepted by the closed-run validator.

## Acquisition manifest

`schema_version` is `2.0.0`; `status` is always `acquired`. `run_id` is a generated
UUID. `mailbox_ref` and `key_ref` bind replay without exposing protected input;
`pseudonymization_version` identifies `hmac-sha256-json-array-v1`. `since_utc`
and `until_utc` record optional inclusive/exclusive bounds. An unrestricted
collector run leaves both null; a pilot window cannot be called a full backfill.

The collector requires `-PilotEntryPath`: the common pilot approval/freeze
fields, nonempty unique authorised partitions, configuration hash and evidence
reference, plus a strict `acquisition_scope`. That object contains exactly
`mailbox_ref`, `folder_ref`, `since_utc`, `until_utc`, `output_directory_ref` and
`whole_mailbox_approved`. All four common approval/freeze flags must be true
booleans. The scope must match the requested mailbox, optional folder, time
bounds and normalized output directory using the supplied stable key. A folder
must be in the approved partitions; a mailbox-wide route additionally requires
explicit whole-mailbox approval. The record is checked before token acquisition,
directory staging or source reads. Preparation mode generates only a pending,
unapproved record and cannot be combined with acquisition mode.

`approval_hash` is SHA256 of the exact private pilot-entry file bytes;
`configuration_hash` is the approved frozen-configuration hash supplied by that
record. Neither identifies an approval person or copies the approval reference.
These bind the acquired artifact and its replay to the reviewed record; the
closed consumer separately checks the actual canonical frozen configuration.
The script verifies recorded consistency, not owner authority or signature
authenticity. Never record a synthetic approval fixture as a real decision.

With `-FolderId` supplied from the approved transient folder binding, acquisition
uses only that folder's message endpoint, verifies every returned parent-folder
ID and binds replay to `folder_ref`. `page_ledger` contains measured per-page
folder reference, sequential page number, candidates, acquired/duplicate/rejected
counts, new fact IDs and the final exhaustion flag. Without `-FolderId`, the
ledger is empty: collection pages are not guessed to be folder pages. Raw folder
IDs and continuation URLs are not persisted. Folder membership and attachment/
importance metadata remain in the acquired projection until explicit mapping.

`pages_read`, `candidate_count`, `acquired_count`, `duplicate_count`,
`rejected_count`, `retry_count`, `emitted_count`, `filtered_count` and
`dead_letter_count` are measured acquisition counters. Rejections are recorded
only as aggregate counts; dead-letter payloads and raw invalid identifiers are
not stored. `filtered_count` is zero because the API applies the requested date
filter; any returned valid fact outside that window fails the whole run.

The reconciliation equation is candidate = acquired + duplicate + rejected.
Each accepted source record emits one fact, so emitted = acquired. No aggregate
success counter implies a successful destination write.

`content_hash` is the lowercase SHA256 of the exact JSONL file bytes, described
by `content_hash_encoding: sha256:utf8-jsonl-lf`. `generated_at_utc` dates the
manifest. `pagination_exhausted` and `no_raw_content_stored` describe this
collector run. `replay_compared`, `new_identity_count` and
`idempotency_replay_verified` distinguish initial acquisition, changed output
and an unchanged verified replay. `full_mailbox_verified`,
`folder_inventory_verified`, `dataverse_reconciled` remain false.

## Evidence required to close

The collector manifest deliberately cannot pass the closed-run report gate.
The workflow must first supply independently obtained evidence of:

1. Approved, frozen mailbox/folder inventory, including empty, hidden, excluded
   and inaccessible folders, with explicit exclusion reasons and inventory hash.
2. Every included folder's own pages exhausted, count reconciliation, timestamp
   bounds, hashes, fact membership, rejection handling and checkpoint state.
3. Successful idempotent Dataverse writes reconciled against acquisition, and
   an unchanged source/destination rerun with zero new identities.
4. Frozen observation start/end, destination reference, retention policy and
   mapping versions, bound by the configuration hash to actual owner/IG approval.
5. Closed `manifest_version: 2.0.0` partitions with measured source counters,
   emitted IDs/counts and canonical per-partition and overall fact hashes.

Mailbox-list page counts cannot be assigned to individual folders. Grouping
observed facts cannot discover empty or inaccessible folders or prove a frozen
inventory. Do not synthesize per-folder exhaustion or destination success from
this collector's flags. There is no automatic acquired-to-closed promotion.

## Offline inventory and reconciliation support

`careops_process.outlook_reconciliation.collect_folder_inventory` implements
nested traversal through a supplied approved connection adapter. The adapter
receives parent ID, continuation and `include_hidden=True`; it must validate
cursor destinations and handle approved authentication/retries before any
network request. The helper traverses all child folders, follows every source
page, checks child-count drift, rejects repeated IDs/cycles and records explicit
inherited exclusions. It projects only keyed folder references, parent links,
disposition/reason codes, children-enumerated state and source-record counts.
Raw IDs are transient. Use the collector's `mailbox_ref` and the same decoded
pseudonym key; the HMAC JSON-array encoding is verified across Python/PowerShell.
No live connection adapter is executed by this helper or its tests.

Freeze the full minimized inventory and its canonical hash before collection.
Included folders require an independently measured `source_record_count`; Graph
folder `totalItemCount` is an item denominator and must match the authorised
message population/observation, not be assumed equal for a filtered pilot. An
excluded folder records a fixed reason; inaccessible folders prevent complete
reconciliation. Recheck the source inventory against the freeze before closure.

`reconcile_outlook_evidence(inventory, collector_facts, pages,
destination_facts)` validates the frozen hierarchy, page sequence/exhaustion,
source counters, acquired memberships and a supplied canonical destination
snapshot. Concatenate genuine folder-specific ledgers and records; do not
create them from mailbox-wide page totals. It rejects unresolved rejections,
scope/count drift, missing/conflicting destination records and duplicate fact
assignments. The source denominator counts distinct records; page candidates
also include repeated acquisition attempts.

The result contains canonical facts, strict consumer partitions, inventory/page
ledger/fact hashes and run totals. It is `destination_pending` if no snapshot is
supplied, otherwise `reconciled`; neither state is `closed`, and no approval,
unchanged replay or full-mailbox verification is created. Internal consistency
of supplied evidence is not proof that a tenant read or write happened.

M365's `close_reconciled_run(initial, replay, configuration, run_id=...,
evidence_class=...)` provides the separate closure interface. Both snapshots
must independently reconcile source/destination, match the approved inventory
hash in the frozen configuration, and have unchanged facts, partitions and
content hashes. It binds initial/replay evidence hashes. The report command
separately enforces pilot approval matching that configuration. The synthetic
producer-to-consumer regression explicitly labels evidence `synthetic` and
does not record live approval or tenant verification.
