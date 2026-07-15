# Low-privilege M365 pilot runbook

This runbook is intentionally connector-neutral. It is designed for a
Power Automate flow using existing user-scoped Outlook, Teams Approvals, and
Dataverse connections. It does not require an Entra application, tenant-wide
mailbox export, Fabric workspace, or administrator role.

## Flow contract

1. Trigger on a narrow, user-owned source (for example, a TESL approval email
   or Dataverse approval row).
2. Select only `id`, activity classification, timestamp, source system, and
   pseudonymous object references. Do not pass body, subject, sender, or
   recipient fields to the process log.
3. Read the single Dataverse checkpoint row described in
   `contracts/dataverse-checkpoint.mapping.json`.
4. Discard facts at or before `watermark_utc`; reject duplicate or tombstoned
   IDs; write minimized dead-letter metadata for malformed or transient facts.
5. Emit the contract in `contracts/m365-fact-projection.json` to the local/CI
   adapter or an approved Dataverse destination.
6. Advance the checkpoint only after the projection write succeeds.

## Pilot acceptance evidence

- A synthetic replay produces no duplicate event IDs.
- A tombstoned source row cannot reappear in the projection.
- A malformed record creates only a minimized dead-letter entry.
- Raw message fields are rejected by the adapter tests.
- The checkpoint advances monotonically and only after successful output.
- The flow run history contains no email body, subject, sender, or recipient
  values in its process-log action inputs or outputs.

## Tenant-gated steps

The actual flow connection, mailbox scope, Dataverse table creation, and live
pilot require the user to perform or approve the Power Automate actions in the
tenant UI. The repository can validate the contract and synthetic behavior but
cannot claim live operation without that run evidence.
