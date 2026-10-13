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

- [x] Task: Build OCEL objects, events and relations from the closed Outlook run.
- [x] Task: Generate empirical process families, variants, hand-offs, ageing and incomplete cases.
- [x] Task: Generate coverage-honest executive visuals and review queue.
- [x] Task: Preserve run-manifest lineage on every output.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 5: Governance and executive validation — GitHub #35

- [ ] Task: Record information-governance, mailbox scope, retention and operator approvals.
- [ ] Task: Obtain operational-owner validation of highest-ranked process families.
- [ ] Task: Record IHG Executive fit-for-purpose decision and authorised next steps.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Phase 6: Assurance and handover

- [x] Task: Run repository quality, privacy, security and workflow checks.
- [ ] Task: Reconcile Conductor, GitHub issues, live evidence and residual external gates.
- [x] Task: Update the parent M365 corpus-discovery track with the closed Outlook lane status.
- [ ] Task: Phase verification and manual Conductor checkpoint.

## Verification evidence — 2026-10-14

Phase 1 automated verification passed: Conductor validation; all 179 tests
with 90.88% overall coverage; Ruff formatting and lint; Pyright (zero errors);
and Bandit over `src`. The Phase 1 manual checkpoint remains pending.
These checks establish repository behaviour only, not live mailbox completeness.

Before Phase 2 live execution, correct `scripts/Invoke-GraphMailboxBackfill.ps1`:
its current projection persists subject, sender, recipient addresses and raw
identifiers, contrary to the privacy-minimised specification. It also requires
folder inventory, per-folder reconciliation and idempotent-rerun evidence before
it can satisfy the full-mailbox acceptance gate. Do not execute this script
against a live mailbox in its current form.

Delegated consent, authorised mailbox scope and retention/destination approvals
remain external gates. The July access-denial evidence is historical and does
not establish the current tenant permission state. No live extraction was
attempted during this verification.
