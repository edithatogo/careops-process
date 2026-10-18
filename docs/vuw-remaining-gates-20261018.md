# VUW remaining work and evidence needed — 18 October 2026

This is a coordination handoff for the five tracks still in progress. It does
not approve production, clinical use, new mailbox acquisition or a PR merge.
Queensland Health live/pilot work remains deferred.

## Verified starting point

- Published `b602619` passed CI, CodeQL analysis, secret scanning and workflow
  security. The latest code change remains the reviewed `ecb8fce`, whose hosted
  suite passed 1,553 tests. Optional PM4Py hosted checks remain opt-in.
- VUW Azure authentication works through the isolated per-process configuration;
  old caches and unrelated PAC/QH profiles were preserved.
- The personal Developer environment is managed. The announced retirement of
  unmanaged Developer environments does not apply to this observed target.
- Synthetic ingestion, cleanup, app publication, conditional ledger persistence
  and fresh independent service readback are recorded in the
  [hub receipt](vuw-hub-rehearsal-20261018.md).
- Local reporting, durable local review and stage effort/calendar reporting are
  implemented. The optional canonical model-conformance adapter is unfinished
  owner work and is excluded from published verification.

## Concrete remaining gates

| Gate | Next evidence or action | Owner and boundary |
| --- | --- | --- |
| Browser acceptance | Complete VUW federation sign-in in the preserved Chrome app tab, then verify the actual intake list, form and detail experience | Human sign-in; Governance verifies the app. Do not send passwords in chat. Azure CLI sign-in does not establish a Dynamics browser session. |
| Cloud worker and conditional connection | Confirm entitlement for this managed environment and exact execution context; effective DLP grouping/action/endpoint rules; approved connection identity and Dataverse resource permission; then demonstrate exact ETag forwarding and stale-write rejection in the executable worker | Platform/licensing operator evidence plus Reliability/Outlook implementation. Connector catalog and current-user service-plan labels are insufficient. No purchase, new grant or policy exception is assumed. |
| Durable historical resume | Implement the reviewed two-page synthetic cloud recovery design after the runtime/connection gate; preserve one run identity, full page membership and conditional commit receipts through fresh-worker restarts and ambiguous outcomes | Outlook, with Reliability-owned metadata and independently verified service reads. A local script, in-memory checkpoint or row replay is not deployed cloud resume. |
| App package target readiness | Exact required TEST components and solution memberships are now read-verified; resolve target role mappings and missing TEST customization/import-export/AppModule capabilities, then validate target import and actual recovery | See [target dependency readback](../conductor/tracks/reliability-alm-hardening_20261014/test-platform-dependencies-20261018.md). Read success does not grant write rights or prove import compatibility. Existing fail-closed validation remains in place until supported target-specific evidence is admitted. |
| Operational hub integration | Establish actual worker/recipient authorization, canonical persistence, approved Teams/Approvals/Planner resources, provider idempotency/reconciliation and failure continuity | Governance. Current evidence is a single-operator synthetic shell and ledger rehearsal; dispatch remains disabled. No clinical operating-model decision is inferred. |
| Real-source and study acceptance | Supply approved source/cohort mappings, pathway/authority/deadline definitions, baseline and evaluation decisions; then independently validate retrospective/prospective results and obtain named owner/governance sign-off | Accountable source and governance owners. Credentialing prepares bounded local methods; synthetic scores or observational deltas do not prove causal released capacity. |
| Hosted updater operation | After normal integration, verify ecosystem ownership on the effective default branch, an actual submodule PR, Python lockfile updates and security-update settings | Reliability. Branch configuration and historical bot PRs do not prove the post-integration result. PR 73 remains draft and unmerged. |

## Coordination rules

Owners report a ready commit with scoped verification, a precise blocker or an
actual completed service result. Review precedes publication; hosted results are
bound to the exact published revision. No whole-track completion follows from a
passing local component suite.

The M365 chat remains archived. Its pending independent hub readback was completed
by the existing review panel without reopening it. Platform writers must obtain
the serialized slot; the hub slot is currently released and charged ledger history
is retained. No repeated login, export or acquisition follows merely from an
observation timeout.

The separately approved bounded-test evidence/key deletion remains scheduled for
23 October at 13:03 Brisbane with its exact-file safeguards. No early deletion or
source-evidence copies are authorized by this handoff.
