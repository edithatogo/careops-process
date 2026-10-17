# Dataverse governance adapter scaffold

The selected non-production lane is Dataverse plus a model-driven Power App in
VUW-AI-TEST. `hub_dataverse_adapter.py` adds executable managed-CLI identity and
conditional ledger persistence scaffolding around the notification engine.
It does not create tables, roles, apps, flows, auth profiles or notifications.
Intake/list/detail remains the selected first app surface; transitions and
decision controls must remain unavailable until server-side authenticated atomic
command handling is implemented and verified.

## Managed implementation path

`StoreConfig` takes an explicitly selected HTTPS organization endpoint, expected
organization GUID, discovered logical table/entity-set/payload-column mapping
and an independently approved allowlist of Dataverse system-user GUIDs. No
publisher prefix or clinical role is supplied by default. Writes default off.
The installed Dataverse CLI handles authentication; the runner never reads token
caches, creates/selects profiles or implements another sign-in flow.

Every load and commit runs `WhoAmI`, verifies the organization and allowlisted
principal, then queries the configured table's actual entity-set mapping and
`IsOptimisticConcurrencyEnabled`. Dataverse row/column privileges still apply.
This allowlist is a worker-access gate, not an IHG delegation, recipient grant
resolver or authenticated source/classification approval. App users must not be
given direct write access to protected ledger state simply to bypass the worker.

The complete notification ledger, including reservation/evidence/command
receipts, is serialized into one existing memo/text column. Restore rejects
unknown fields, duplicate JSON keys, non-array history shapes, changed effect
bindings and invalid nested concrete records through the existing ledger
validator. The bounded payload is at most 900,000 UTF-8 bytes; it fails closed
at capacity rather than pruning history. Schema length limits and long-term
history design must be checked before a real workload.

The row GUID is deterministic from organization and opaque tenant/recipient/
channel binding. Scope, policy, window and history origin cannot select fresh
storage rows. Load additionally checks the stored scope and history origin.
Missing/forbidden/failed reads never return a fresh empty ledger. There is no
upsert or automatic initialization fallback. A first row must be provisioned by
an explicitly authorized migration with its complete trusted history/origin;
that migration is not implemented here.

Commit sends one PATCH with the exact loaded `If-Match` ETag and
`Prefer:return=representation`, storing state and receipt in the same row.
An enabled optimistic-concurrency table must enforce the conditional operation.
Only a successful response with identical full payload and a changed valid ETag
returns confirmed commit context. Conflict, timeout, empty/malformed output or
unexpected representation yields a fixed `commit_unconfirmed` error. Do not
automatically resend; reload and reconcile the original command receipt. A
failure may have happened after the server committed.

Each operation explicitly passes the selected environment URL to
`dataverse api request`. The runner uses argv without a shell, places large
write bodies in a temporary file and removes it after execution. It captures
responses in memory and never includes raw bodies, credentials or identity
details in exception messages. Provider-response formatting must be verified
against the installed CLI after authentication; synthetic JSON fixtures cannot
prove live representation behavior.

`prepare_delivery` accepts only the latest confirmed admission/retry context
from that invocation and prepares reservation, provider-idempotency and content
fingerprint metadata. Dispatch is always disabled. A loaded/replayed or
reconciliation result cannot prepare another attempt. These Python objects are
trusted in-process context, not signed capabilities that may be accepted from
an untrusted caller. No Teams/Graph sender, recipient resolver, body renderer,
flow or outbox dispatcher is supplied. Real provider permission, idempotency,
complete-attempt evidence and crash recovery remain necessary.

## Current target and tooling evidence — 17 October 2026

The shared reviewed branch was inspected at `ffbc8f6`. The coordinator has
already verified VUW-AI-TEST as a Dataverse-linked Sandbox. This chat did not
repeat environment inventory or query that environment using an unrelated PAC
profile. Read-only PAC profile inspection returned existing profiles without a
matching CareOps/VUW entry. The missing `@microsoft/dataverse` CLI was installed;
`dataverse auth who` returned no active authentication profile. No PAC profile
was switched/deleted and no `.env` or credentials were created or overwritten.
The previously expired device code was not reused.

Before environment authoring or deployment, the following evidence is required:

1. Fresh authorized VUW authentication for the managed Dataverse CLI and PAC,
   preserving unrelated profiles; verify actual organization/user identity.
2. Exact target endpoint/organization GUID and effective customization,
   create/read/write, import/export, sharing and audit rights. Discovery of a
   Sandbox is not proof of those rights.
3. Existing publisher/prefix and solution, discovered entity-set/column mapping,
   actual memo capacity, concurrency-enabled table, protected worker principal
   mapping, row/column access and trusted first-row/history provisioning.
4. Environment-first authored intake table/forms/views and model-driven app,
   actual exports and pre-change/restore evidence. No placeholder solution XML
   or invented deployment package is generated.
5. Approved governance authority/roles and source/recipient/classification rules,
   authenticated worker hosting, provider connection/idempotency/evidence rules,
   licensing/DLP, co-owners, continuity and multi-user fault tests before enabling
   transitions or notifications. Operating-model confirmation remains pending.

Because target data-plane authentication and effective rights are unverified,
no environment schema/app/flow was created, no real ledger was written and no
real notification was sent. The scaffold is callable after its prerequisites
are supplied; it is not a deployed app, completed platform adapter or pilot.

## Validation and sources

Synthetic tests exercise identity and metadata mismatches, scope/row binding,
strict history restore, exact conditional headers, full-state response
verification, missing records, ambiguous commits, default write denial,
non-dispatching delivery plans and temporary payload cleanup. These are local
adapter tests, not evidence of live atomic concurrency or effective access.

Supported API behavior was checked against the installed CLI's
`api request --help` and Microsoft documentation:

- [Dataverse CLI API request reference](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/cli/reference#api-request-command)
- [Conditional operations and optimistic concurrency](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/perform-conditional-operations-using-web-api)

The Dataverse skills require environment-first authoring; actual metadata must
be authored in the approved environment and exported, not hand-written as
solution XML.
