# Closed-run evidence interface, version 2.0.0

This contract is owned by M365 closed-run evidence/reporting. The Outlook
exporter or Power Automate workflow must produce it before the report consumer
will accept a run. Version 1 summary-only evidence is rejected. This document is
an interface definition, not live approval or evidence of a completed extraction.

## Frozen configuration

`configuration` is a strict object containing exactly:

- `authorised_source_partitions`: unique, nonblank pseudonymous folder/partition IDs; enumerate all admitted folders, including empty ones.
- `observation_start` and `observation_end`: ISO timestamps with explicit timezone; the interval is start-inclusive and end-exclusive.
- `destination_reference`: approved evidence-store reference, never credentials.
- `retention_policy_version`: approved retention/disposal policy version.
- `mapping_version`: activity/object projection version.
- `inventory_hash`: canonical hash of the frozen full folder inventory, including nested relationships, exclusions and source denominators.

`configuration_hash` is SHA-256 of the canonical JSON object. The pilot-entry
approval must contain this exact hash and the exact authorised partition list.
Approval of the hash binds the inventory, period, destination, retention and
mapping configuration. The software checks recorded consistency; owners remain
responsible for approving the referenced records and store.

## Run envelope

Retain `run_id`, `status=closed`, `folder_count`, `page_count`, `candidate_count`
and the strictly boolean true gates `pagination_exhausted`, `reconciled`,
`idempotency_replay_verified`, `no_raw_content_stored`. Add:

- `manifest_version`: `2.0.0`.
- `evidence_class`: `synthetic`, `smoke_test` or `live_corpus`; never infer it from run success.
- `initial_reconciliation_hash` and `replay_reconciliation_hash`: canonical hashes of the separately supplied reconciliation artifacts.
- `configuration` and `configuration_hash` as above.
- `content_hash`: canonical JSON SHA-256 of the complete minimized fact array.
- `partitions`: one strict manifest for every configured partition.

Run folder/page/candidate totals must equal the partition totals. Raw narrative,
addresses and source identifiers must not appear in facts or manifests. Keep
actual approvals, manifests and reports in the approved evidence location.

## Partition manifests

Every manifest contains exactly `partition_id`, `source_system`, `pages_read`,
`candidate_count`, `acquired_count`, `duplicate_count`, `rejected_count`,
`filtered_count`, `emitted_count`, `fact_ids`, `content_hash`,
`next_link_exhausted`.

Counts are non-negative strict integers, never booleans or strings. Every folder
must exhaust pagination and record at least one page, including an empty-result
page. Reconcile:

`candidate_count = acquired_count + duplicate_count + rejected_count + filtered_count`

These are source-record counts. A record can emit multiple lifecycle events;
`emitted_count` is separately checked against the unique `fact_ids` list. Each
emitted fact must appear in exactly one partition; all references must exist in
the input and have the same `source_system`. Events cannot be emitted from a
partition with zero acquired source records. The partition content hash covers
its selected facts in their original order within the complete fact array.

An empty partition has zero counts, an empty `fact_ids` list and the hash of
`[]`. It remains in the inventory. A completely empty corpus cannot produce a
discovery report; preserve its acquisition ledger as zero observations instead.

## Hash encoding and consumer compatibility

Use `careops_process.backfill_evidence.evidence_digest` as the reference:
UTF-8 bytes of `json.dumps(value, sort_keys=True, separators=(",", ":"),
ensure_ascii=True)`, then SHA-256 lowercase hex. Array order is significant;
exporters must persist the exact fact order they hashed. PowerShell's ordinary
`ConvertTo-Json` output is not this canonical encoding. A producer may invoke
the Python helper on its minimized JSON exports; never feed raw exports into it.

Facts contain exactly `id`, `activity`, `timestamp_utc`, `source_system`,
`object_ids`. Normalize exporter aliases before hashing; no additional fields
are silently stripped by the consumer. The existing public CLI arguments remain
unchanged, but its evidence and approval inputs require the new fields.
Report version is `2.0.0`, and reports retain the validated manifests,
configuration and hashes. OCEL lineage includes run, input and configuration
hashes. Keep deterministic source ordering across replay; this contract does not
replace measured replay, per-page acquisition logs or operational-owner review.

## Validation limits

The consumer verifies internal consistency and input binding. Hashes are
integrity checks, not signatures or independent proof of access, source counts,
pagination exhaustion or owner authority. The workflow operator must retain
source/per-page logs and actual replay evidence in the authoritative store.
The pilot still requires human and source-system verification. No tenant-wide
coverage claim follows from a complete authorised partition inventory.

## Graph exporter acquisition-to-closure boundary

`Invoke-GraphMailboxBackfill.ps1` currently emits `status=acquired`, not
`closed`. It exhausts a Graph message collection, retains pseudonymous folder
references and verifies collection-level replay, but explicitly leaves folder
inventory and Dataverse reconciliation unverified. **Do not rename its status
or set closure flags to make it pass this consumer.** An acquired export is
rejected even if collection-level `reconciled` is true.

Before closure, the authorised workflow operator must retain, in the approved
store:

1. Owner/IG approval bound to the frozen configuration hash, including all
   authorised nested folders, exclusions, observation period, destination and
   retention policy.
2. Independently verified folder inventory and acquisition page logs for every
   admitted folder, including empty folders. Produce per-folder candidate,
   acquired, duplicate, rejected and filtered record counts from these logs.
   A mailbox-wide count cannot be divided or guessed to obtain folder counts.
3. The minimized canonical facts actually persisted at the approved destination.
   Compare their unique identities and approved projected fields with acquired
   facts; resolve missing/conflicting records, dead letters and tombstones before
   declaring destination reconciliation.
4. A repeat acquisition/destination run over unchanged input/configuration,
   proving identical identities, minimized values and counts, with zero new
   identities. Preserve the source replay evidence and destination reconciliation.
5. A v2 manifest containing the independently measured folder ledgers and exact
   hashes of the canonical fact array and frozen configuration. Run the report
   command only after those records are complete and the approval binds its hash.

Exporter records include `folder_id`, `has_attachments` and `importance`; the
current canonical report fact contract has only the five fields above. Mapping
must occur in the approved store before hashing: retain `folder_id` as the
partition provenance in the manifest, and explicitly exclude the two optional
metadata features unless a later mapping contract admits them. Keep the
original acquired file hash as acquisition evidence; its JSONL byte hash is
not interchangeable with the canonical-array hash consumed here.

The current exporter does not supply verified per-folder page logs or
Dataverse destination evidence. Those closure inputs remain pending in the
Outlook lane. This M365 change supplies a strict consumer and schema, not a
tool that manufactures those missing inputs. Cloud-only production acceptance
still follows the sanctioned Power Automate/Outlook connector route; the Graph
exporter's collection check alone does not satisfy that acceptance criterion.


## Local acquisition-to-closure support

The Outlook lane now provides `reconcile_outlook_evidence`, tested with
synthetic nested, empty and excluded folders, page accounting and independently
supplied destination snapshots. It validates minimized field mapping and returns
`reconciled` or `destination_pending`. It does not read the tenant or prove live
execution, and deliberately does not mark replay or full-mailbox verification.

Matching destination rows establish generic content reconciliation only:
`destination_reconciled` records that comparison; `dataverse_reconciled` stays
false because this offline function cannot verify service provenance. There is
currently no supported Dataverse readback provenance verifier. Caller flags or
service labels cannot replace one. Consequently this helper rejects
`live_corpus` closure, including caller-forged Dataverse flags. Synthetic and
smoke-test closure retain their explicit non-pilot evidence classes. A future
live adapter must bind actual authorised destination/environment/readback
receipts before live closure can be enabled.

M365 `close_reconciled_run(initial, replay, configuration, run_id=...,
evidence_class=...)` accepts two successful source/destination reconciliations.
It checks both inventories against the approved frozen `inventory_hash`, compares
partition accounting and complete minimized facts, validates both snapshots
against the v2 manifest, and records canonical hashes of both reconciliation
artifacts. Changed/missing destination, changed replay facts or partition counts,
and inventory/configuration mismatch prevent closure.

Use this sequence for synthetic or smoke-test evidence in the approved store:

1. Supply the measured frozen folder inventory, per-folder page ledgers,
   collector facts and independently exported destination facts to Outlook's
   reconciliation function for the initial run.
2. Supply the independently repeated source/page/destination evidence to the
   same function for replay. Do not duplicate the initial artifact and describe
   it as a measured repeat run.
3. Use `close_reconciled_run` with the owner-approved configuration and correct
   evidence class. Retain both input reconciliation artifacts beside the closed
   envelope; its two reconciliation hashes bind those retained artifacts.
4. Pass the canonical initial facts, closed envelope and approval record to the
   report command. The approval configuration hash and exact scope must match.

The synthetic end-to-end regression passes the two-folder reconciliations through
closure and the authorised report consumer, preserving an empty folder and a
source duplicate. Negative tests reject destination-pending results and changed
replay/inventory/configuration. These tests are repository evidence only.

The functions verify supplied artifacts, not their origin or the fact that two
live acquisitions actually happened. Source-system logs, actual destination
exports, owner/IG approval and operational review remain independent live gates.
A standalone mailbox `acquired` manifest cannot satisfy this handoff because it
lacks the required independent folder/page and destination evidence.
