# VUW development checkpoint — 17 October 2026

Current live work is VUW development/testing. Queensland Health acquisition,
clinical governance and pilot acceptance are deferred. Tenant-neutral local
reporting separately requested by the operator does not authorize QH access.

## Verified repository revision

Published code revision `7e0812317d0077a8be6f5bdb408bd3ceaaeb19ed` passed all
expected hosted workflows:

- [CI](https://github.com/edithatogo/careops-process/actions/runs/39032148555):
  1,465 tests; line coverage 7138/7297 (97.82%); branch coverage 2064/2170
  (95.12%). Formatting, lint, strict typing, Conductor, both offline PowerShell
  suites, Bandit and dependency audit passed.
- [CodeQL](https://github.com/edithatogo/careops-process/actions/runs/39032148554),
  [secret scan](https://github.com/edithatogo/careops-process/actions/runs/39032148551)
  and [workflow security](https://github.com/edithatogo/careops-process/actions/runs/39032148573)
  passed. Optional PM4Py remains intentionally skipped.

This revision includes the folder-inventory validation repair, separation of
local destination equality from Dataverse provenance, the reviewed managed-CLI
notification-ledger adapter scaffold and the credentialing schema/acceptance
handover. Coordinator checks passed 97 reconciliation/evidence tests, 80 adapter/
notification/view tests before the cleanup repair, then all 21 adapter tests
after it. A separate reviewer passed the final 81 combined tests. Independent
Draft 2020-12 validation accepted runtime-exported synthetic data and rejected
all nine tested terminal-newline mutations, using a disposable UV overlay with
no project dependency or lockfile change.

The current revision also includes protected case reporting, the local SQLite
credentialing adapter and synthetic Dataverse writer/provenance adapters.
Independent review repaired missing organization evidence and timestamp precision
loss; the final 76 focused tests passed. SQLite authentication and recovery are
local adapter evidence, not Entra/Dataverse identity or disaster-restore acceptance.

## Actual VUW evidence and limits

| Area | Verified result | Still required |
| --- | --- | --- |
| Coordination | All five finish/follow-on handoffs delivered; supported chat inspection recovered | Individual steering calls can still fail; a failed send is not delivery |
| Authentication | Separate VUW PAC profile connected to VUW-AI-TEST; PAC and server identity matched | Dataverse CLI has a separate authentication surface; no successful CLI data-plane session is claimed |
| Test target | VUW-AI-TEST is a Dataverse-linked Sandbox; current user enabled with Read-Write access mode | Effective privileges lack required customization, import/export, publisher/solution write and model-driven AppModule capabilities; access mode is not an authorization grant |
| Development target | The existing personal VUW Developer environment has verified customization, publisher, solution, import/export and AppModule privileges; selected for isolated synthetic authoring/rehearsal. Named VUW-AI-DEV returned organization-membership denial | Inventory and protect existing components, establish the isolated baseline, then verify actual deployment/readback/recovery; success here cannot close Test acceptance |
| Live checker | Reviewed unmanaged table-only package `careops_process` 1.0.0.0 checked in Australia; downloaded SARIF has `executionSuccessful=true`, zero findings; artifact hash independently matched | No app/flow behavior, functional test or deployment/restore proof |
| Binding | Current package has zero environment variables, connection references and agents | Binding is N/A for this package; future app/flow bindings remain unverified |
| Import/export/restore | Personal Developer baseline imported and exported; solution-description change restored and read-verified | Test-target rights and acceptance; description recovery does not prove schema/data rollback or disaster restore |
| Outlook | Approved 30-record local Inbox smoke remains separate. Two synthetic Developer rows created, exact service readback independently verified, unchanged replay added zero rows; both test rows deleted and absence confirmed | Durable cloud page checkpoints and authorised full-population evidence; synthetic run identity does not prove global deduplication or live-corpus closure |
| Hub | Two new UserOwned tables created and read-verified with optimistic concurrency; ledger Memo capacity 1,000,000 characters | App, isolated first-row/CAS rehearsal and export remain in progress; no real notifications or clinical acceptance |

The coordinator inspected the downloaded checker ZIP without extracting it and
confirmed SARIF execution success and zero results. Its SHA-256 is
`9dbdace8715fcab9b4437d054b7d9b86a4ee92dcf2859df070ee5a7553a37294`.
Raw logs, signed download URLs, private bindings and effective privilege responses
remain ignored outside public Git. No environment customization or ledger write
is inferred from the checker upload or successful reads.

## Ownership and next steps

Reliability owns VUW authentication, effective capability checks, the shared
publisher/solution baseline and ALM rehearsal. After read-only verification, the
coordinator selected the existing personal VUW Developer environment for isolated
synthetic authoring/rehearsal. Inventory and pre-change export precede writes;
success there cannot substitute for VUW-AI-TEST deployment acceptance. Governance owns
hub tables/app after that verified handoff. Outlook owns mailbox destination
integration; M365 owns service-origin provenance and discovery/report integration.
Credentialing owns the separately requested local reporting work. Owners must
coordinate shared solution changes sequentially.

For the test-target rights gate, an administrator can assign sandbox-scoped
System Customizer or an approved equivalent capability set; maker/flow and app
sharing rights must be verified separately. Do not request tenant-wide admin or
self-elevate. See Microsoft's [customization guidance](https://learn.microsoft.com/en-us/power-apps/maker/model-driven-apps/privileges-required-customization)
and [model-driven app sharing requirements](https://learn.microsoft.com/en-us/power-apps/maker/model-driven-apps/share-model-driven-app).

Updater ownership restrictions are on the integration branch, while main still
has the earlier overlapping configuration. Bot operational evidence and human
verification therefore remain incomplete. Draft PR 73 is unmerged. Five tracks
remain in progress; no production, clinical or whole-project acceptance is claimed.

Approved bounded-test evidence/key disposal remains scheduled for 23 October at
13:03 Brisbane, after the seven-day deadline; Codex must be available. The
handoff retry automation was deleted after confirmed delivery. Host native
failures remain unresolved and BIOS is unchanged.
