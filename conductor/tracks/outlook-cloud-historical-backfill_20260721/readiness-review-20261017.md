# Review Report: Historical Outlook backfill readiness — 17 October 2026

## Summary

The bounded VUW development test is complete; full-mailbox pilot acceptance
remains unproven, with concrete folder-validation and destination-provenance
repairs committed and verified together.

## Verification Checks

- [x] **Plan Compliance**: Partial — schema, synthetic traversal, page/replay
  safeguards and the authorized 30-record bounded test are evidenced; actual
  full-folder Dataverse acquisition and owner/Executive acceptance remain open.
- [x] **Style Compliance**: Pass — scoped Ruff lint/format and strict Pyright.
- [x] **New Tests**: Yes — seven failing-then-passing synthetic regressions.
- [x] **Test Coverage**: Partial — targeted behavioral cases and the existing
  Outlook suite cover the repair; they do not prove deployed checkpoint resume.
- [x] **Test Results**: Passed — 112 targeted Python tests across contract,
  evidence, reconciliation, integration, closed-report CLI and publication on
  `037cd90` plus `7f376db`. Offline PowerShell approval/privacy/pagination/
  replay/window/failure tests and scoped Bandit also pass. This is scoped
  verification; the coordinator owns the shared final suite.

## Findings

### High — inconsistent inventory dispositions could overstate completeness (fixed)

`_inventory` accepted an included descendant of an excluded ancestor. It also
accepted `source-inaccessible` as the reason for an excluded folder and accepted
an included folder carrying an exclusion reason. Those snapshots could hide
unknown coverage or contradict the collector's inherited exclusion policy.
Commit `037cd90` rejects all three forms. Separate synthetic regressions failed
before the fix and pass afterwards.

### Medium — malformed source envelopes bypassed sanitized failure (fixed)

Inventory traversal assumed the callback's page and each folder row were
dictionaries. A malformed response raised AttributeError rather than the
protected validation error. Commit `037cd90` validates these runtime shapes;
four synthetic envelope/row cases now fail with sanitized diagnostics.

### High — supplied destination equality did not establish Dataverse origin (fixed)

The pre-review reconciler set `dataverse_reconciled` for any matching supplied
destination records. Local or synthetic count/content equality cannot prove
Dataverse service readback. M365's coordinated repair `7f376db` makes generic
destination reconciliation explicit and leaves `dataverse_reconciled` false.
Synthetic/smoke closure remains available; live-corpus closure fails closed
because no supported service-provenance adapter exists. A caller boolean or
receipt-shaped JSON cannot unlock it. The combined regressions pass. Do not
use the bounded local VUW result as a Dataverse certificate.

## Folder, pagination and resume readiness

| Boundary | Current evidence | Production limit |
| --- | --- | --- |
| Nested/hidden folder inventory | Synthetic traversal, paginated children, parent/count drift, cycles, inherited exclusion and malformed-response regressions | Actual approved inventory adapter and frozen QH folder snapshot are not verified |
| Message pagination | Offline exporter end-of-pages, unsafe destination, loop, retry and page-ledger regressions | The actual VUW test exhausted one page; no live multi-page or full-mailbox coverage claim |
| Reconciliation | Strict fact/page models, source denominators, per-page membership, destination equality, exclusions and replay fixtures | Service-origin Dataverse readback proof remains a separate capability |
| Restart/replay | Exporter re-reads from page one and preserves a previously published artifact on failure | No durable mid-page resume is implemented in the helper; deployed checkpoint/resume must be demonstrated separately |
| Bound VUW test | Actual 30 initial / 30 local destination / 30 replay, unchanged content, no new identities | Smoke test of one fixed Inbox window; not a full FolderEntry inventory or a QH pilot |

No mailbox acquisition, account switching or platform mutation was performed
for this review. The existing disposal follow-up was read and verified active
for **23 October 2026 at 13:03 Australia/Brisbane**, after the precise approved
deadline. Its exact 14-file allowlist includes the unique encrypted key and
forbids early/recursive deletion or source changes. No duplicate schedule or
early deletion was created. Execution requires Codex to be available.

### Cloud checkpoint definition versus executable resume

The original Phase 2 task is to **define** minimized projection, idempotency,
dead-letter and checkpoint actions. The historical backfill contract declares
the mailbox/folder/page-cursor/watermark key, per-folder `checkpoint_state`
manifest field and no-advance-on-failure invariant. It is an acquisition
contract, not an importable Logic Apps/Power Automate flow definition.

The separate TESL arrival-flow contract lists `read_checkpoint`, projection,
watermark validation, write and `advance_checkpoint` ordering. Its validator
checks unique identifiers, checkpoint-safe order and failure protection.
The Dataverse checkpoint mapping defines watermark and bounded identifier-set
columns; the Python IngestionCheckpoint is explicitly an in-memory model.
Neither the mapping nor the model proves a historical per-folder cursor was
committed, restored or transactionally coordinated with a real Dataverse write.
The helper separately provides safe publication/restart from page one.

The original plan's offline checkpoint-contract/regression work can be checked
without any new storage selection. Durable historical cursor recovery cannot
be demonstrated by these fixtures alone: it requires the approved Dataverse
checkpoint binding and an executable cloud adapter with verified commit and
recovery semantics. There is no remaining existing offline executable cloud
resume artifact to run. No replacement local persistence architecture was
introduced for this review.

Verification: 38 existing flow-contract, reliability, contract-file and
historical-backfill-contract tests passed. These establish offline ordering,
monotonic watermark, idempotency and failure-policy behavior only. Conductor
validation and diff checks also passed; no tenant operation was performed.

## Smallest actual-pilot input set

Supply these three private records, without identifiers or approvals in Git:

1. **QH source and scope record:** workflow/mailbox owner and authority evidence;
   existing approved Outlook connection; explicit included/excluded/inaccessible
   folder inventory with measured denominators and nested/hidden policy; exact
   observation bounds (or explicitly unrestricted history). Freeze and hash it.
2. **Destination and operation record:** approved Dataverse environment/table,
   actual connection and effective read/write rights; field mapping and unique
   idempotency key; checkpoint store, accountable operator and rollback owner;
   classification/access/audit/retention/disposal/records-export decisions and
   any legal hold. Bind these to the same frozen configuration.
3. **Approval and acceptance record:** source-owner and applicable IG decisions
   referencing those exact source/destination/configuration hashes, followed by
   operational-owner validation and the required Executive fit-for-purpose
   decision before operational use. VUW authorization supplies none of these
   QH decisions.

These records are inputs, not evidence that the remaining technical work is
already deployed. A supported source-to-Dataverse adapter must then produce
service-origin readback, durable checkpoint/restart evidence, all-folder page
manifests, independent unchanged replay and a contract-valid closed run before
OCEL/process output is accepted. Do not fill missing denominators, invent
provenance receipts, reinterpret local JSONL as Dataverse or waive unresolved
folders to make closure pass. The Conductor track stays in progress.
