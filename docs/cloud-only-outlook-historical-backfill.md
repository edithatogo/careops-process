# Cloud-only Outlook historical backfill

## Decision

Use the existing TESL Office 365 Outlook connection in Power Automate. Do not
use Outlook desktop/COM for the production discovery route.

The existing TESL flow is trigger-based (`When a new email arrives (V3)`). That
captures future arrivals but cannot prove historical completeness. The required
backfill is a separate, manually controlled flow using `Get emails (V3)` and a
folder inventory.

## Flow design

1. **Create a run record** in Dataverse with a run ID, configuration version,
   authorised mailbox, observation boundary and operator.
2. **Enumerate folders** through the existing Office 365 Outlook connection,
   including nested user-created folders. Freeze and hash the folder inventory.
3. **For each admitted folder**, call `Get emails (V3)` with no date filter,
   request the maximum safe page size, and follow every continuation page until
   the connector reports no next page.
4. **Project only minimized facts**: pseudonymous message ID, timestamp,
   conversation reference where permitted, folder reference, attachment flag,
   importance and run ID. Never persist body, subject, sender, recipients or
   attachments.
5. **Write to Dataverse** using an idempotency key of source message ID plus
   folder ID. Invalid or duplicate records go to minimized telemetry/dead-letter
   records.
6. **Write one manifest per folder** containing page, count, watermark,
   duplicate, rejection, hash and exhaustion evidence.
7. **Close the run only when** every authorised folder is exhausted and all
   source-to-projection counts reconcile. An empty folder is a valid result;
   an inaccessible folder is an unknown, never zero activity.
8. **Run the OCEL projection and process discovery** only from the closed,
   reconciled run manifest.

## Full-mailbox acceptance gate

The result may be called a full historical mailbox backfill only if:

- the mailbox and folder scope were explicitly authorised;
- the folder inventory was captured before extraction;
- all included folders reached end-of-pagination;
- excluded/system folders are listed with reasons;
- every candidate, duplicate, rejection and dead letter is accounted for;
- the minimum and maximum observed timestamps are recorded;
- a repeat run produces no new identities for unchanged source data.

Power Automate run success alone is insufficient evidence of completeness.

## Tenant-side setup required

The workflow owner must create or duplicate the flow inside the approved Power
Automate environment using the existing Office 365 Outlook connection and
Dataverse destination. No new Entra application is required. The owner must
approve the mailbox/folder scope, retention period, destination table and
operator access before the backfill is run.

The machine-readable contract is
`contracts/power-automate-outlook-historical-backfill.json`.
