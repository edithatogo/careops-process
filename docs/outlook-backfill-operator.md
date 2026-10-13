# Outlook backfill operator runbook

Current state, 14 October 2026: local synthetic exporter tests pass. The operator
authorized the proposed VUW Inbox-only seven-day metadata test stored locally
outside Git and selected an existing Power Automate Outlook connection.
VUW Azure/Graph identity and Power Automate environment access are verified;
the selected environment and connection binding remain pending. Azure CLI's
Graph token lacks mail-read permission, and Mail.ReadBasic acquisition returned
AADSTS65002. Use the selected connector route rather than repeating Azure login.
Frozen configuration, retention and approval evidence still require recording.
VUW supplies development test evidence only. Queensland Health is the actual
pilot and requires its own source, destination and governance records; see the
[account and stage boundary](m365-test-to-pilot-boundary.md). A personal Azure
source remains a separate access proposal.
Keep account addresses, tenant IDs, real approval records and bindings outside
Git. An Azure login alone does not establish an Outlook mailbox or Graph access.

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
