# Review Report: Local reliability and ALM hardening — closure checkpoint

## Summary

Local implementation remains verified; final track acceptance is blocked by
live deployment permissions, incomplete updater evidence and human sign-off.
Reviewed repository checkpoint: `91b6997e5881149333c313d1693c4a135b0dbaa0`.
Concurrent uncommitted credentialing work is outside this review.

Later capability update: the existing personal VUW Developer environment has
verified customization, publisher, solution, import/export and AppModule rights
and is selected for isolated synthetic authoring/rehearsal. Named VUW-AI-DEV
denied organization membership. The VUW-AI-TEST rights and acceptance gate below
remains open; a development rehearsal does not replace it. See the coordinator's
[VUW checkpoint](../../../docs/vuw-progress-20261017.md).

## Verification Checks

- [ ] **Plan Compliance**: Partial — live ALM and updater gates remain open.
- [x] **Style Compliance**: Documentation diff checked; no implementation changed.
- [x] **New Tests**: Existing hardening regressions retained; no redundant tests added.
- [x] **Test Coverage**: Relevant categories include privacy, replay, pagination,
  interruption/publication, properties, malformed inputs, artifact integrity,
  dependency/workflow security and live checker validation. Category usefulness
  takes priority over increasing a coverage percentage.
- [x] **Test Results**: All 29 local ALM tests pass at this checkpoint. Earlier
  published integrated results remain historical exact-revision evidence, not
  certification of current concurrent work.

## Cross-lane evidence reconciliation

| Evidence owner | Accepted evidence | Limit / outstanding ownership |
| --- | --- | --- |
| Reliability | Separate VUW PAC profile established; matching server identity; enabled account; effective privileges retrieved | Missing customization/import/export/publisher/solution/model-driven app rights; reads do not establish writes |
| Reliability | Power Apps Checker finished successfully in Australia; SARIF executionSuccessful=true, zero findings; package integrity verified | Table-only unmanaged harvest; no app/flow behavior certified; private signed result URLs excluded from Git |
| Reliability | Generated settings have zero environment variables, connection references and agents | Binding N/A for this package; actual bindings for future components remain unverified |
| Outlook + M365 | Approved bounded VUW Inbox test completed with 30 minimized records, local destination readback and replay; independent downstream validation | Smoke test only; local equality does not establish Dataverse provenance or complete mailbox acquisition |
| Outlook | Folder validation fixes and combined 112 targeted tests reported; disposal follow-up retained | Durable page resume and actual Dataverse destination remain open; no new mailbox read in closure review |
| M365 | Reconciliation no longer treats arbitrary matching local records as Dataverse proof | Live destination verifier and mapping still needed; ongoing variant-report work is outside this lane's acceptance |
| Credentialing | Projection schema repair and acceptance handover committed in reviewed checkpoint | Real-source/clinical acceptance and causal capacity evidence remain external; additional measures under development |
| Governance | Dataverse adapter work and synthetic checks reported; real dispatch disabled | Trusted identity, live concurrency, app integration, operating-model acceptance and app rights remain its gates |
| Coordination | Published integrated checks previously verified; owns moving shared integration | New uncommitted work and subsequent hosted checks require its own exact-revision review |
| Dependency bots | Dependabot PR72 has successful Python/Gitleaks/Zizmor checks; Renovate onboarding merged and dashboard populated | See updater receipt: main still permits overlapping managers; Python lock regeneration and actual submodule PR not established |

## Remaining gates and decisions

1. Administrator provides suitable rights in VUW-AI-TEST only; then verify effective
   privileges before environment-first synthetic solution creation. No tenant-wide
   admin, self-elevation or unrelated-profile operation is required by this plan.
2. Perform approved synthetic baseline export, candidate import, component/job
   validation and supported recovery rehearsal. Do not treat an older managed
   import or managed uninstall as an automatic rollback.
3. Integrate updater ownership restrictions through normal PR review and inspect
   subsequent real bot evidence, lockfile updates and security-update settings.
4. Human reviews the delivered local work and these explicit limitations. A
   request to proceed is authorization to perform work, not evidence that the
   human has independently verified results.

Host native crashes remain unresolved. Hosted success does not repair or certify
the host. Optional pipeline execution remains unperformed and is not required
without relevant approved resources. No full-corpus, clinical or production
acceptance is inferred from the cross-lane handoff.

## Human verification record

Status: **awaiting explicit response**. No sign-off was invented or backdated.

Reviewable decision: accept the completed local phases and bounded VUW smoke-test/
checker evidence with the listed limitations, while retaining the whole track as
in progress until live ALM and updater acceptance evidence is complete; or request
specific corrections. This checkpoint cannot close unperformed external work.

## Final disposition

### Subsequent read-only development capability check

On 17 October, VUW-AI-DEV returned HTTP 403, Dataverse code `0x80072560`:
the user is not a member of that organization. The existing personal VUW Developer
environment verified the same VUW identity, enabled read/write access, and 5,997
effective privileges. Create/write customization, publish, import/export,
create/write publisher, solution and model-driven app privileges were returned
at Global depth. This establishes an available development authoring capability,
not a completed rehearsal, app-sharing proof or VUW-AI-TEST acceptance.
No authentication profiles or environment content were changed by these checks.
Publisher/solution/table inventory and an isolated synthetic baseline were the
next steps at that checkpoint; their completed evidence follows.

### Subsequent bounded Developer rehearsal

Inventory found no CareOps publisher, solution or `cop_` table collisions. The
existing reviewed unmanaged `careops_process` 1.0.0.0 package was imported into the
personal VUW Developer environment with its original `careops_publisher` / `cop`
metadata. The asynchronous import completed successfully. The resulting baseline
was exported successfully before the recovery mutation; its local ZIP passed CRC
verification and has SHA-256
`46fb0cca2109e3fe6d9ff9c9648fd7fb31dd4ef5d659ce9a2edfb65e4e5e3818`.

Using the official Dataverse Python SDK 1.1.0 in an isolated local environment,
the new solution's description was changed to a synthetic marker, independently
read back, restored to its original null value, then independently read back with
the version unchanged. This proves recovery of that one metadata property only.
It does not prove schema/data rollback, managed promotion or TEST acceptance.
The imported baseline is intentionally retained for the coordinated next lane.

Actual event-table metadata was shared privately with Outlook, M365, Governance
and Coordination. The five fields are activity (String 100), event key (String
200), object IDs (Memo 4000), source system (String 100) and timestamp (DateAndTime,
TimeZoneIndependent). The primary key is a GUID; no alternate keys or run field
exist. Synthetic deterministic run-scoped GUIDs and exact-ID readback may support
a bounded experiment, but cannot establish server event-key uniqueness, global
deduplication or query-based run isolation. No retained mailbox data was written.
All writes are complete for this bounded rehearsal; Coordination owns subsequent
single-writer scheduling. Real org bindings, raw responses and export remain local.

### Cross-lane synthetic service verification and cleanup

The [Outlook destination receipt](../../../docs/outlook-dataverse-destination.md)
and commit `9967919` record two synthetic Developer rows created and read back
exactly, with unchanged replay creating zero additional rows. M365 independently
queried actual service identity and both primary keys, verifying organization,
user, organization lookups and canonical contents. This is bounded
`synthetic_service_readback`, not evidence inferred from a local JSON receipt.

In a separately serialized cleanup slot, Outlook rechecked identity and both
complete payloads, deleted exactly those two rows through the SDK, and confirmed
both absent. The slot was released to Governance. The lane reports 64 focused
destination/reconciliation tests passing. No retained real-mailbox evidence was
used, and this does not establish server event-key uniqueness, durable cloud
checkpoint recovery, complete-corpus ingestion or TEST acceptance.

Coordination reports integrated revision `7e08123` published with CI, secret scan
and workflow security successful; CodeQL was pending at that handoff. That report
does not supersede an exact-head completed CodeQL result or certify subsequent
Governance app/ledger mutations. No platform operations were performed while
finishing this documentation checkpoint. TEST, updater and human gates stay open.

Keep the track registered and retain its folder. No archive, deletion, PR merge,
production change or completion status is justified at this checkpoint.
