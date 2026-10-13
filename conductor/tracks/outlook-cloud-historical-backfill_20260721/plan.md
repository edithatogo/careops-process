# Implementation Plan: Cloud-only complete historical Outlook mailbox backfill

## Shared hardening prerequisite

Before the next live mailbox run, complete the exporter privacy, date-window,
replay and offline-test work in the
[reliability and ALM hardening plan](../reliability-alm-hardening_20261014/plan.md).
Existing completion markers are historical evidence, not proof that the current
exporter satisfies these newly identified requirements. Full mailbox execution,
reconciliation and owner approvals remain in this track.

## Phase 1: Contract and completeness gate — GitHub #31

- [x] Task: Add test-first schema for folder inventory, backfill run and per-folder manifest.
- [x] Task: Add tests for pagination exhaustion, folder exclusions, count reconciliation, privacy rejection and checkpoint regression.
- [x] Task: Align `contracts/power-automate-outlook-historical-backfill.json` with the executable validators.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 2: Power Automate cloud backfill blueprint — GitHub #32

- [x] Task: Define the existing Office 365 Outlook connection and Dataverse destination bindings without tenant secrets.
- [x] Task: Define folder inventory, nested-folder traversal and frozen-scope handling.
- [x] Task: Define `Get emails (V3)` pagination, retry, timeout and continuation handling.
- [x] Task: Define minimized projection, idempotency, dead-letter and checkpoint actions.
- [x] Task: Produce operator setup and rollback instructions for the workflow owner.
- [x] Task: Add command-line Microsoft Graph metadata backfill path (`scripts/Invoke-GraphMailboxBackfill.ps1`) with pagination and manifest output.
- [ ] Task: Obtain delegated Microsoft Graph `Mail.Read` consent for the authorised operator and execute the full mailbox run.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 3: Full authorised mailbox reconciliation — GitHub #33

- [ ] Task: Execute the approved flow across every included folder with no convenience sample.
- [ ] Task: Verify every folder reaches end-of-pagination and produce manifests.
- [ ] Task: Reconcile source candidates to Dataverse projections and account for all exclusions.
- [ ] Task: Repeat unchanged run and verify zero new identities.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 4: OCEL process discovery — GitHub #34

- [x] Task: Implement OCEL reconstruction from supplied closed-run evidence (repository capability; live execution pending).
- [x] Task: Implement empirical process-family, variant, hand-off, ageing and incomplete-case outputs (synthetic verification).
- [x] Task: Implement coverage-honest executive visuals and review queue (synthetic verification).
- [x] Task: Implement run-manifest lineage preservation on generated outputs.
- [ ] Task: Execute and validate these outputs over the actual reconciled authorised Outlook run after Phase 3.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 5: Governance and executive validation — GitHub #35

- [ ] Task: Record information-governance, mailbox scope, retention and operator approvals.
- [ ] Task: Obtain operational-owner validation of highest-ranked process families.
- [ ] Task: Record IHG Executive fit-for-purpose decision and authorised next steps.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 6: Assurance and handover

- [x] Task: Run repository quality, privacy, security and workflow checks.
- [ ] Task: Reconcile Conductor, GitHub issues, live evidence and residual external gates.
- [x] Task: Update the parent M365 corpus-discovery track with repository capability status; live Outlook closure remains pending.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Verification evidence — 2026-10-14

Phase 1 automated verification passed: Conductor validation; all 179 tests
with 90.88% overall coverage; Ruff formatting and lint; Pyright (zero errors);
and Bandit over `src`. The Phase 1 manual checkpoint remains pending.
These checks establish repository behaviour only, not live mailbox completeness.

Initial verification finding (superseded by the local repairs below):
`scripts/Invoke-GraphMailboxBackfill.ps1` persisted subject, sender, recipient
addresses and raw identifiers contrary to the privacy-minimised specification.
That projection defect has been repaired and verified offline. Full-mailbox
acceptance still requires frozen inventory, actual per-folder reads,
destination reconciliation and unchanged replay evidence.

Delegated consent, authorised mailbox scope and retention/destination approvals
remain external gates. The July access-denial evidence is historical and does
not establish the current tenant permission state. No live extraction was
attempted during this verification.

## Local repairs and review — 2026-10-14

- [x] Task: Replace unsafe Graph projection with allowlisted keyed pseudonyms and sanitized diagnostics.
- [x] Task: Verify encoded UTC windows, explicit timezones, bounded retries, safe pagination, duplicate/replay accounting and empty results offline.
- [x] Task: Stage directory publication, protect a previous artifact, block concurrent writers and verify failed publication/recovery paths.
- [x] Task: Add folder-scoped acquisition with measured page ledgers and scope-bound replay.
- [x] Task: Add nested/hidden-folder inventory traversal, explicit inherited exclusions and drift/cycle checks through an approved-source adapter interface.
- [x] Task: Reconcile supplied frozen inventory/page ledgers and canonical destination snapshots without inventing writes or approval.
- [x] Task: Verify canonical partitions and initial/replay reconciliation against M365's closure interface using synthetic evidence only.
- [x] Task: Enforce contract identity prohibitions, pseudonym domains and source metadata allowlisting with failing-then-passing regressions.
- [x] Task: Document acquired evidence, operator preparation, VUW-first proposal, closure inputs and Queensland Health promotion gates.
- [x] Task: Commit the verified local repairs as `1554aaf` and conduct the [scoped Conductor review](review-20261014.md).
- [x] Task: Enforce pilot-entry approvals before token/source access, bind exact mailbox/folder/window/output scope and retain approval/configuration hashes in acquired evidence.
- [x] Task: Provide an unapproved local preparation mode with no source/token access, false approval flags and no overwrite of an existing review record.
- [ ] Task: Complete manual Conductor verification and actual authorised full-folder/source-to-Dataverse run, replay and governance decisions.

Local evidence: 56 Outlook Python tests pass; scoped Python coverage is 97.89%
lines and 90.00% branches. The offline PowerShell exporter suite passes,
including cross-language pseudonym encoding, folder page ledgers, retries,
concurrent writer rejection, publication rollback and a failed-recovery backup.
Scoped Ruff, strict Pyright and Bandit pass. Installed dependencies have no known
vulnerabilities in pip-audit (the local project itself is not a PyPI audit target).
Conductor validation passes. These are repository checks, not tenant evidence.

The shared suite passed an earlier 352-test snapshot. A later full-suite run
was interrupted during collection by the concurrent Teams implementation's
missing `apply_decision_transition` import in `tests/test_hub_decisions.py`.
Shared final verification is coordinated separately; do not infer it from
Outlook's scoped results.

Latest subsequent shared snapshot: 537 passed, 7 failed in the concurrent Teams
decision/domain implementation. The [review failure record](review-20261014.md)
lists every failing test. No Outlook failure was observed in that run; the
shared suite remains unverified until its owners finish and recheck.

GitHub reconciliation: #30, #33, #34 and #35 remain open; #31 and #32 are closed
for contract/blueprint work. Their closed state does not establish live
completeness. No GitHub status or comments were changed during this work.

The user confirmed that no approved pilot mailbox scope/destination currently
exists and proposed VUW before Queensland Health, with a personal Azure account
as another possible access check. Actual account access, consent, configuration
approval, connection binding, retention/destination controls, full folder reads,
destination writes and replay are still pending. No live acquisition or consent
request was attempted. The sanctioned Power Automate route remains the production
acceptance route; Graph/offline helpers do not replace its live verification.

## Continuation audit — approval boundary

Verified continuation implementation commit: `4039eac`.

The completion audit found that the Graph exporter previously relied on the
operator runbook rather than validating pilot approval before token acquisition.
That local gap is now repaired: `-PilotEntryPath` is required for acquisition,
with strict true approval/freeze flags and exact scope binding. The acquired
manifest and replay bind the approval-file and approved configuration hashes.
`-PreparePilotEntryPath` only creates an unapproved local proposal and neither
requests a token nor reads a mailbox. It leaves approvals false and does not
overwrite existing records. Tests use transient synthetic fixtures and mocked
token/source functions, never tenant approval records.

Verification: the expanded offline PowerShell suite passes approval denial,
scope mismatch, primitive-type confusion, proposal preparation/no-overwrite,
non-null UTC-window handling across PowerShell versions, and all earlier
privacy/replay/recovery cases. The 62 Outlook/M365 contract, reconciliation and
integration tests pass. Azure CLI 2.91.0 is now installed; VUW Azure/Graph
identity and Power Automate environment access were subsequently verified.
The operator authorized a VUW Inbox-only seven-day metadata development test
and selected their Developer environment's existing Outlook connection route.
Connection enumeration needs separate FlowAgent authentication, which remains
incomplete. No mailbox extraction or connection identity verification occurred.
VUW is testing only; Queensland Health is the actual pilot and requires its
own approval, frozen configuration and destination records.

The full objective remains unproven. Live consent, mailbox/folder scope,
destination/retention approval, deployed connector verification, full-folder
acquisition, destination reconciliation, unchanged live replay, process-owner
validation, Executive decision and manual Conductor checkpoints remain pending.
See the [requirement-level completion audit](completion-audit-20261014.md).
