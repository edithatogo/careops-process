# Implementation Plan: Cloud-only complete historical Outlook mailbox backfill

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
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 3: Full authorised mailbox reconciliation — GitHub #33

- [ ] Task: Execute the approved flow across every included folder with no convenience sample.
- [ ] Task: Verify every folder reaches end-of-pagination and produce manifests.
- [ ] Task: Reconcile source candidates to Dataverse projections and account for all exclusions.
- [ ] Task: Repeat unchanged run and verify zero new identities.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 4: OCEL process discovery — GitHub #34

- [ ] Task: Build OCEL objects, events and relations from the closed Outlook run.
- [ ] Task: Generate empirical process families, variants, hand-offs, ageing and incomplete cases.
- [ ] Task: Generate coverage-honest executive visuals and review queue.
- [ ] Task: Preserve run-manifest lineage on every output.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 5: Governance and executive validation — GitHub #35

- [ ] Task: Record information-governance, mailbox scope, retention and operator approvals.
- [ ] Task: Obtain operational-owner validation of highest-ranked process families.
- [ ] Task: Record IHG Executive fit-for-purpose decision and authorised next steps.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 6: Assurance and handover

- [ ] Task: Run repository quality, privacy, security and workflow checks.
- [ ] Task: Reconcile Conductor, GitHub issues, live evidence and residual external gates.
- [ ] Task: Update the parent M365 corpus-discovery track with the closed Outlook lane status.
- [ ] Task: Phase verification and manual Conductor checkpoint.
