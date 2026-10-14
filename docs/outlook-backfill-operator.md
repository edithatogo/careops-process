# Outlook backfill operator runbook

Update, 15 October 2026: the authorized Office 365 Outlook connection was
created in VUW-AI-TEST and verified Connected. See the
[development connection receipt](../conductor/tracks/outlook-cloud-historical-backfill_20260721/test-connection-20261015.md).
The connection-creation decision below is historical; the current next gate is
usable automation transport and the private scope-bound acquisition record.

Current state, 14 October 2026: local synthetic exporter tests pass. The operator
authorized the proposed VUW Inbox-only seven-day metadata test stored locally
outside Git and selected an existing Power Automate Outlook connection.
VUW Azure/Graph identity and Power Automate environment access are verified;
all seven accessible VUW environments were checked, with no existing Outlook
connection found for the operator. A new test connection awaits the operator's
environment/creation decision. Azure CLI's
Graph token lacks mail-read permission, and Mail.ReadBasic acquisition returned
AADSTS65002. Use the selected connector route rather than repeating Azure login.
Frozen configuration, retention and approval evidence still require recording.
VUW supplies development test evidence only. Queensland Health is the actual
pilot and requires its own source, destination and governance records; see the
[account and stage boundary](m365-test-to-pilot-boundary.md). A personal Azure
source remains a separate access proposal.
Keep account addresses, tenant IDs, real approval records and bindings outside
Git. An Azure login alone does not establish an Outlook mailbox or Graph access.

## Authentication handoff

For an authorized device-code login, enter the code returned by the active
login process into the verified Microsoft device-login page automatically.
Enter the supplied account identifier and advance the routine login flow.
Do not ask the operator to copy a code already available to the agent. Hand
off when a password, MFA or another required human action is reached.
Never commit device codes, credentials, tokens or account identifiers.

The operator authorizes using browser-managed saved credentials for VUW and
Queensland Health routine sign-in while away. Use autofill in the intended
service's browser login; do not extract passwords into scripts or files.
MFA remains an operator action. This authorization does not extend mailbox
scope, approve new app permissions or replace acquisition governance records.
The requested notifier, Velma, means ChatGPT Dot. No direct Dot notification
tool is exposed in this session; do not claim an MFA alert was delivered.

The VUW Azure device code was entered by the agent and that login completed;
it is not a pending operator step. FlowAgent connection management uses a
separate browser callback login, not that Azure device code. The first bounded
check ended before authentication completed, but subsequent cached sign-in
was verified to match Azure's VUW identity. Both the Outlook-filtered and full
connection lists returned empty for the selected Developer environment.
The operator then selected VUW STAFF Default; both its Outlook-filtered and
full connection lists also returned empty. Following the operator's instruction
to iterate through every environment, find-only discovery checked the other
four environments and found no Outlook connection. The final VUW-AI-TEST check
was completed in the browser, which explicitly showed no connections. CLI
token-cache decryption failed even after one successful fresh browser device
sign-in; the browser check completed discovery without weakening encryption.
The next step is the pending operator decision to create a VUW test connection
in VUW-AI-TEST or their Developer environment. Do not repeat the completed scan.
If later sign-in is needed, use
one live request's own browser flow; never reuse the completed Azure code.
If human authentication is required while the operator is away, stop checks
and preserve a precise handoff rather than repeatedly polling or restarting.

## Pilot preparation

Record in the approved evidence store: mailbox owner, explicitly authorised
folders and observation period, classification/IG decision, operator,
destination/access controls, retention/disposal rules and rollback owner.
Freeze and hash that configuration. Start with synthetic or an explicitly
approved low-sensitivity mailbox scope. The current collector queries the
mailbox-wide message collection unless `-FolderId` is supplied; its default
includes folders outside an Inbox-only scope. For a narrower scope use the
tested folder-specific mode with the approved source folder binding. Date
windows bound time, not folder scope. Nested inventory traversal and offline
ledger/destination validation are available through the
[reconciliation support](outlook-acquired-evidence.md); an approved connection
adapter must supply the actual inventory pages and destination snapshots.

Use the existing user-scoped connection or delegated account, without new app
registration or tenant policy changes. Verify account and mailbox access through
the agreed setup procedure; never log access tokens or raw token claims. Verify
the minimal permission needed by the selected projection and source. The Graph
message API documents `Mail.ReadBasic` as its least-privileged delegated read
permission; the historic track names `Mail.Read`. Do not escalate merely to
match that old label. Folder access, connector actions and organisational policy
must also be checked. Authentication failures remain external gates.

Supply `CAREOPS_MAIL_PSEUDONYM_KEY` through the approved secret mechanism, then
prepare a scope-bound draft in the private evidence location:

```powershell
pwsh -NoProfile -File scripts/Invoke-GraphMailboxBackfill.ps1 `
  -Mailbox '<candidate approved mailbox>' -OutputDirectory '<candidate artifact directory>' `
  -FolderId '<candidate approved folder ID>' `
  -Since '2026-01-01T00:00:00Z' -Until '2026-01-02T00:00:00Z' `
  -PreparePilotEntryPath '<new private pilot-entry JSON path>'
```

Preparation makes no token request or mailbox read, never overwrites an existing
record, and leaves every approval flag false. The record binds keyed mailbox,
folder and output-directory references plus exact UTC bounds. Owners must review
the actual corresponding source/destination, complete the frozen configuration
hash and evidence reference, confirm the approved partition list and record the
required human decisions. For mailbox-wide acquisition, preparation leaves the
partition inventory empty and whole-mailbox approval false; the operator must
supply the complete approved frozen folder list and explicit mailbox-wide
approval. Do not use a mailbox reference as a substitute for folder inventory.

Only after those approvals exist, invoke the collector with the matching private
record, stable key and a dedicated output path outside Git. Example placeholders
below are not executable approval records:

```powershell
pwsh -NoProfile -File scripts/Invoke-GraphMailboxBackfill.ps1 `
  -Mailbox '<approved mailbox>' -OutputDirectory '<approved new artifact directory>' `
  -Since '2026-01-01T00:00:00Z' -Until '2026-01-02T00:00:00Z' `
  -PilotEntryPath '<approved private pilot-entry JSON path>'
```

For a folder-only pilot, additionally supply `-FolderId '<approved folder ID>'`.
Treat that binding as protected transient configuration outside Git. No account
or tenant is inferred from these placeholders. Dates require an explicit offset
or `Z`; invalid date/page-size input fails without echoing its value.

The exporter rejects missing/false/type-confused approval, unknown record fields,
duplicate partitions, mismatched mailbox/folder/window/output bindings and an
unapproved mailbox-wide route before token acquisition. Folder-specific reads
also require the folder reference in the approved partition list. Every acquired
manifest retains approval-file and frozen-configuration hashes; replay requires
the same approval record. This checks consistency of the recorded decision, not
the authenticity or organisational authority of a signature. Keep real approval
records outside Git; the script's synthetic tests are not evidence of consent.

For `Get emails (V3)`, explicitly disable unread-only and attachment-only filters
and attachment content, and leave subject/address/importance/search filters
unset for the full population. Microsoft documents first-250-message limitations
for several action filters. Verify the deployed connector's pagination settings
and observed page exhaustion; an action's Top setting alone is not proof of
full folder coverage. Secure connector inputs/outputs and approved run-history
retention are necessary because action responses can contain raw mail even when
the final Dataverse projection is minimized.

Run the same frozen scope/key twice and inspect candidates, acquisitions,
duplicates, rejections, file hash, identity set and replay flag. Resolve every
rejection before considering a complete-population run. Record the permission
and connection result without copying raw source responses into logs or Git.
The acquired output remains a pilot artifact; use the
[closure interface](outlook-acquired-evidence.md) to identify the missing
folder and Dataverse evidence before process reporting.

## Full historical and deployment gates

For full historical acquisition, remove pilot date bounds, explicitly approve
all included folders, inventory nested/hidden folders, record exclusions, freeze
the observation end and establish per-folder exhaustion. Freeze a start bound
earlier than the mailbox's authorised history for the closed evidence's temporal
configuration; do not apply an arbitrary convenience cutoff to extraction.
Source changes during acquisition must be accounted for by the approved
snapshot/reconciliation method; repeated reads alone do not create a snapshot.

After source-to-Dataverse reconciliation and an unchanged replay, run the
closed-evidence validator and report command. Obtain operational-owner review
of proposed process families and the Executive fit-for-purpose decision before
operational use. Queensland Health needs its own approvals, connections,
classification and retention determination; a VUW pilot grants none of these.
The historical NSW Health/TESL bindings are not assumed portable to either tenant.

## Stop and rollback

Stop on missing access/approval, changed inventory/configuration, unexhausted
pages, conflicting identity, unreconciled counts, unexpected protected output
or unapproved destination. The collector preserves previous valid output on
recoverable failure, but has no durable page checkpoint/resume. After a crash,
inspect locks and verified backups as described in the
[acquisition instructions](cloud-only-outlook-historical-backfill.md).

For Dataverse rollback, use the run lineage and approved retention process to
withdraw this run's projections; never remove unrelated records or source mail.
Export required evidence before a destination change. The operator and workflow
owner must confirm the recovery and retention decision. Re-run the approved
scope after resolution; never mark a partial run complete.

## Primary references checked

- [Graph list messages: permissions, select, pagination and mailbox-wide scope](https://learn.microsoft.com/en-us/graph/api/user-list-messages?view=graph-rest-1.0)
- [Graph paging](https://learn.microsoft.com/en-us/graph/paging)
- [Graph child-folder enumeration](https://learn.microsoft.com/en-us/graph/api/mailfolder-list-childfolders?view=graph-rest-1.0)
- [Office 365 Outlook connector reference](https://learn.microsoft.com/en-us/connectors/office365/)
