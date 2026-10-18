# VUW hub development checkpoint — 18 October 2026

The selected personal VUW Developer environment now contains a synthetic intake
table, notification-ledger table and published model-driven intake app. The
bounded operator rehearsal exercised the existing Python ledger and store
against real Dataverse conditional writes. Browser acceptance, a hosted worker,
provider delivery and deployment to VUW-AI-TEST remain open.

The user restricted current work to VUW development. QH clinical/source/pilot
work remains deferred, and the original credentialing and governance tracks
remain incomplete. No clinical authority, quorum, conflict, ratification or
source approval is inferred from this checkpoint.

## Actual authored components

The existing unmanaged `careops_process` solution and `careops_publisher` / `cop`
publisher were reused after Reliability completed its baseline and bounded
description-property recovery. Fresh organization, operator and active VUW
domain checks matched the private target binding. Every SDK/PAC operation used
the explicit Developer endpoint; no authentication profile was created or
selected by this lane.

| Component | Actual server evidence |
| --- | --- |
| `cop_HubIntake` | User-owned; optimistic concurrency enabled; synthetic reference, test category and source-reference fields |
| `cop_NotificationLedger` | User-owned; optimistic concurrency enabled; `cop_payload` is a create/update-capable Memo with maximum length 1,000,000 characters |
| Intake main form and active view | Server-generated templates retrieved and modified to expose the supplied synthetic intake fields |
| Model-driven app | Created through the installed `pac model create` with explicit target and solution; published after validation returned success with **zero issues** |
| Navigation | Exactly one intake table page; ledger storage is absent from app navigation |

The final app component readback contains the intended intake entity, main form,
active view and generated sitemap. An earlier generic Entity-table reference
produced four warnings despite a successful validation boolean; it was corrected
and revalidated before this checkpoint. A separately created unused navigation
component was deleted only after exact identity/content checks and zero app
references; its subsequent exact read returned absent.

The app exposes synthetic intake/list/detail. Canonical transitions, clinical
decisions and real notification dispatch remain disconnected. No role definitions,
privilege grants, global auditing or security settings were edited. The actual
export nevertheless contains two app role-map references generated with the
app; target sharing and those role bindings require verification.

## Actual ledger persistence and concurrency

Before the isolated first-row migration, the exact deterministic row was checked
absent. One empty synthetic ledger was explicitly created with its fixed history
origin, then its payload and ownership were independently read back. Missing-row
reads in the product adapter still fail closed; the rehearsal did not add an
automatic empty-ledger or upsert fallback.

The real `DataverseLedgerStore` and notification engine ran with the current
operator explicitly configured as the synthetic worker. A narrowly scoped HTTP
runner used existing managed Azure CLI credentials: the installed SDK's ordinary
update interface has no ETag argument, and no Dataverse CLI profile was created.
This validates the store's injected transport path, not the default CLI runner's
authenticated live behavior.

Two readers obtained the same row ETag and proposed distinct next commands.
Their competing conditional PATCH operations returned **200 and 412**. Final
readback reconciled to revision **1**, one reservation and one command receipt,
with the complete winning payload intact. Both attempts used the same verified
worker identity; this is not a multi-user access-control test.

Exact command replay preserved current history and could not commit another
write. A newly loaded read context could not prepare an attempt, and the winning
commit's delivery plan remained dispatch-disabled. No provider request was made.
The one charged synthetic reservation and its receipt are retained; history was
not deleted, reset or repinned after the rehearsal.

M365 was assigned a fresh independent service readback. Its follow-up verification
encountered noninteractive Azure CLI token-acquisition failure after correcting
its SDK ETag handling. Independent live verification therefore remains pending;
that authentication failure is not a finding against the stored ledger or app.
Reliability remains the authentication owner. Following the user's VUW login
request, it restored a usable isolated Azure CLI configuration without changing
the old cache or unrelated PAC/QH profiles. A subsequent independent service
verification is recorded below.

## Actual export and ALM handoff

The unmanaged `careops_process` **1.0.0.0** solution was exported from the explicit
Developer target, preserving the original baseline ZIP separately. The new ZIP
is **24,313 bytes** and passes CRC verification:

```text
artifacts/alm/personal-dev-hub-app-20261017.zip
SHA-256 1702104fe75da16b8376e1429e160e680800f2781e0eb2fe9e1375fcfe472b96
```

Its three entries are `customizations.xml`, `solution.xml` and
`[Content_Types].xml`. The app and navigation are embedded in
`customizations.xml`: one AppModule, one AppModuleSiteMap and one SiteMap.
The solution declares four table root components, one sitemap and one app.
The baseline tables are included alongside the two new hub tables.

PAC export succeeded. A local receipt initially assumed separate app-component
files and failed its own format assertion; inspecting the actual ZIP reconciled
that assumption without re-exporting or modifying the package. The package is
not relabelled as a table-only artifact.

Reliability independently verified the ZIP hash/CRC and PAC unpacking, and found
the existing table-only ALM validator correctly rejects its additional formats.
An app-aware validator extension is separately owned by Reliability. Two declared
platform dependencies remain gates: the default app icon's AppModuleWebResources
dependency and the AppChannelSettingDefinition/AppFramework dependency. The two
app role-map references also require target sharing provenance. This export is
not evidence of tenant-neutral managed promotion, import or restore.

## Private evidence and remaining acceptance

Raw organization/user/row IDs, endpoint bindings, service bodies, operator
scripts and actual exports remain in ignored `artifacts/alm/` files. The relevant
private receipts are:

- `personal-dev-field-details-private.json` and `hub-preauthoring-private.json`:
  expected/fresh identity, baseline hash and initial table collision checks.
- `hub-schema-authoring-private.json`: actual table ownership/concurrency, payload
  capacity and original generated form/view templates.
- `hub-managed-app-create-private.json`, `hub-app-completion-private.json` and
  `hub-app-entity-correction-private.json`: draft/published distinction,
  component ownership, corrected entity linkage and final zero-issue validation.
- `hub-cas-rehearsal-private.json`: isolated migration, conditional request
  statuses, winner payload, replay checks and retained charged history.
- `hub-export-receipt-private.json`: exact owned-map cleanup and reconciled export
  hash/CRC/format; earlier failed outcomes are preserved separately.

The writer slot is explicitly released; no hub mutation/export process remains
running. The app was opened in the browser but reached VUW federated sign-in.
The user was offered sign-in or leaving UI verification pending. The previous browser
binding could not be recovered after interruption, so no successful
list/detail/create interaction or browser-runtime acceptance is claimed.

Remaining gates are browser sign-in and UI checks;
least-privilege/multi-user sharing and access tests; trusted hosted
worker/recipient authorization; crash/continuity and full schema/data recovery;
provider connection, idempotency and delivery reconciliation; app-aware ALM
validation plus dependency/role binding and target import/restore verification.
VUW-AI-TEST acceptance remains blocked by its rights constraints. No production,
clinical workflow, source ingestion or real notification was enabled.

## Receipt review

Checkpoint commit: `ff6cb803f6346f57e89cb73c56d655436e557971`. A separate
read-only local evidence review found no actionable issues. It independently
verified the ZIP size/hash/CRC, embedded components, six declared roots, two
dependencies and two app role-map entries, and checked the public claims against
the retained schema/app/CAS receipts. It found no raw GUIDs or endpoint URLs in
this note. That review performed no network, authentication or platform calls;
it does not close the pending independent live service verification or UI gates.
Conductor configuration validation and Git whitespace checks pass.

## Subsequent independent service verification

At **18 October 2026, 08:36:09 UTC** (18:36:09 Brisbane), the coordinator's
independent review agent completed fresh read-only verification using the restored
VUW configuration. The archived M365 chat remained archived.

- Fresh WhoAmI matched the pinned organization and operator.
- Actual ledger metadata matched the private binding and enabled optimistic
  concurrency. The exact primary-key read returned an ETag and the expected owner.
- The payload was decoded from the actual response, then matched against the
  expected final payload: revision **1**, **one charged reservation**, **one receipt**.
- The published app had exactly one component of each type **1, 26, 60 and 62**;
  its entity component matched the actual intake table metadata.
- Actual navigation contained one intake page and no ledger page.

The checker exited successfully without platform mutations, provider requests,
new authentication or private evidence copies. This verifies the current retained
synthetic Developer state and published app shell. It does not repeat the CAS
race/replay rehearsal, establish browser interaction, prove multi-user access or
close provider delivery, live-corpus or target deployment acceptance.
