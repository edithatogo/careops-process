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

## Command-line Graph alternative

`scripts/Invoke-GraphMailboxBackfill.ps1` is a minimized message-collection
exporter, not a full-mailbox or Dataverse completeness certificate. It uses the
existing Azure CLI delegated token and writes `mail-events.jsonl` and an
`acquired` manifest. Its output omits subject, addresses, narrative, raw IDs and
mailbox identity. Message, conversation, folder and mailbox references use
domain-separated HMAC-SHA256 pseudonyms. A stable base64 key containing at least
32 random bytes must be supplied in `CAREOPS_MAIL_PSEUDONYM_KEY` from an approved
secret store. Never commit or print the key, and retain the same key for replay.

Offline verification needs no account:

```powershell
pwsh -NoProfile -File tests/powershell/test_graph_mailbox_backfill.ps1
```

The exporter deduplicates identities, rejects malformed candidates, detects
conflicting duplicates and unsafe/cyclic continuations, and retries transient
HTTP failures/timeouts at most three times. Retry-After is respected up to the
60-second local wait budget; longer waits fail closed. It stages both files and
publishes their directory together, with rollback for a failed publication and
a destination writer lock. It does not append to a previous run. Replay verifies
the prior file hash, mailbox/window/key binding, identity set and projection
content. Removed or changed facts cannot count as an unchanged replay.

The dedicated output directory must be new, or contain only a matching v2
exporter's two files. Legacy raw exports and unrelated files are rejected and
left intact. Output publication handles recoverable exceptions; abrupt process
termination can leave a lock or staging/backup directory. Recover under operator
control after checking that no writer remains: inspect the prior manifest and
file hash, restore a verified backup if needed, then remove the stale lock.
Never automatically delete an unknown directory or replace a backup with partial
output. Acquisition restarts from the first page; it has no durable page resume.

For acquired manifest fields, report-consumer mapping and the separate closure
gate, see [the acquired evidence interface](outlook-acquired-evidence.md). For
the proposed VUW pilot and later Queensland Health rollout, see
[the operator runbook](outlook-backfill-operator.md).

The July access denial is historical evidence, not a current account-access
assessment. No VUW or personal-account access was tested on 14 October 2026.
