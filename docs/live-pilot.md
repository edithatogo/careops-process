# Low-privilege M365 pilot runbook

This runbook describes the selected standard-connector source design. It uses
the existing user-scoped Office 365 Outlook and SharePoint connector operations;
Planner is available only for a specifically selected task source. It does not
require an Entra application, tenant-wide mailbox export, Fabric workspace, or
administrator role. Native bindings are not established by this source contract.

## Flow contract

The machine-readable flow contract is `contracts/power-automate-tesl-flow.json`
and its List bindings are in `contracts/sharepoint-m365-ingestion.json`. The
validator is `careops_process.flow_contract.validate_flow_contract`.

1. Trigger or poll only a narrow, explicitly authorized source. The selected
   TESL path uses Outlook metadata; Planner task acquisition remains limited to
   selected plans and supported standard connector operations.
2. Select only `id`, activity classification, timestamp, source system, and
   pseudonymous object references. Do not pass body, subject, sender, or
   recipient fields to the process log.
3. Read the source partition checkpoint from the SharePoint List specified by
   `contracts/sharepoint-m365-ingestion.json`.
4. Discard facts at or before `watermark_utc`; reject duplicate or tombstoned
   IDs; write minimized dead-letter metadata for malformed or transient facts.
   Reuse the existing keyed HMAC pseudonymization contract for source identity
   and folder/conversation references; raw IDs must remain transient. The
   standard-connector invocation of that operation is not currently qualified,
   so stop before any live write until it is.
5. Create the uniquely keyed queue item. After an uncertain result, read it back
   by exact `fact_id` and compare every minimized field before retrying.
6. Publish the existing portable JSONL event-file contract, then advance the
   checkpoint only after the queue/file outcome is verified. A single writer
   per partition and serial flow runs are required because SharePoint List
   updates do not provide the historical Dataverse compare-and-swap behavior.

## Pilot acceptance evidence

- A synthetic replay produces no duplicate event IDs.
- A tombstoned source row cannot reappear in the projection.
- A malformed record creates only a minimized dead-letter entry.
- Raw message fields are rejected by the adapter tests.
- The checkpoint advances monotonically and only after successful output.
- The flow run history contains no email body, subject, sender, or recipient
  values in its process-log action inputs or outputs.
- Queue-item readback confirms identity and minimized fields after uncertain
  creates; checkpoint conflicts stop for reconciliation.

## Tenant-gated steps

The actual environment, site, list IDs, connector references, mailbox or Planner
scope, owner and retention policy must be read back from the authorized native
target before execution. No native binding or run evidence is available in this
source update. A supported keyed pseudonymization step is also required before
native execution. The prior Dataverse checkpoint mapping remains as historical
evidence and is not the selected route.
