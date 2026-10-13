# Historical Outlook backfill completion audit

Date: 14 October 2026, Australia/Brisbane. The full objective is implementation
of the selected Conductor track followed by its review, including the actual
complete authorised mailbox run. Local code/test completion is insufficient.

| Specification acceptance criterion | Authoritative evidence | State | Required next evidence |
| --- | --- | --- | --- |
| 1. Contract rejects incomplete/privacy-unsafe manifests | Backfill contract validator, strict folder/page models and M365 bound-run validator; 62 contract/reconciliation/integration tests and offline PowerShell regressions pass | Repository capability verified | Preserve these checks in final shared/hosted verification |
| 2. Cloud blueprint covers inventory, pagination, retries, checkpoints, idempotency and minimized Dataverse projection | Checked-in contract and operator runbook, folder traversal/scoped collector, page ledgers, reconciliation/closure interface | Design/local support verified; deployed binding unverified | Approved existing connection, flow/destination bindings and actual durable checkpoint behaviour |
| 3. Live authorised run records every included folder and exhausted page | No new live run; the user confirmed no approved pilot scope/destination; historical July denial is not current access proof | Missing | Owner/IG-approved scope and retention, authenticated operator and full frozen-folder acquisition |
| 4. Candidate/acquired/duplicate/rejected/dead-letter counts reconcile | Measured collector counters and synthetic supplied-destination reconciliation pass | Offline verified; live missing | Actual source and Dataverse snapshots, per-folder ledgers, exclusion/rejection accounting |
| 5. Unchanged rerun yields zero new identities | Synthetic exporter replay and initial/replay closure compatibility pass | Offline verified; live missing | Two actual approved source/destination runs with unchanged scope, values and reconciled identities |
| 6. OCEL findings trace to the same closed manifest and retain honest coverage | Strict consumer/hash/lineage support and synthetic integration tests | Repository capability verified; live output missing | Closed actual run, validated hashes and empirical process output over that run |
| 7. Governance approval, owner validation and Executive decision recorded before operational use | Approval checks fail closed; no real approval/owner/Executive records have been supplied | Missing | Actual approvals and validation in the approved evidence location; no fixture or tool can substitute |

Manual phase/final Conductor checkpoints remain open. The track's registry and
metadata remain `in_progress`; GitHub #30/#33/#34/#35 are open. The previous
formal review and the continuation review preserve these limits. No issue was
closed, deployment performed or live mailbox accessed by this work.

## Current execution boundary

Acquisition now requires `-PilotEntryPath` with strict approvals and a binding
to the exact keyed mailbox/folder/time/output scope. Preparation mode creates
only a false-flagged proposal, never consent. Azure CLI 2.91.0 is installed and
its version was verified. One VUW device sign-in completed successfully after
the operator's federated sign-in. No duplicate sign-in was started. M365 remains
logged out, and no project/user M365 app configuration was found. M365/PAC
executable presence does not prove mail access. The personal Azure account
remains unverified; a personal Azure
login does not by itself establish a Graph mail source.

Subsequent operator confirmation authorizes the proposed Inbox-only seven-day
metadata test stored locally outside Git. VUW is development testing;
Queensland Health is the actual pilot and requires its own approval evidence.
Azure login has now completed, and
Graph identity verification confirms the supplied mailbox address belongs to
the authenticated staff identity. Existing token permissions contain none of
Mail.ReadBasic, Mail.Read or Mail.ReadWrite. Requesting Mail.ReadBasic through
Azure CLI returned AADSTS65002 (application/resource preauthorization required),
so this CLI route cannot currently acquire mail. An approved mail-capable
application or existing Outlook connector is required; repeated device sign-in
does not repair that permission boundary. The operator selected the existing
VUW Power Automate Outlook connection. A Power Automate resource token was
obtained without logging it, and the installed FlowAgent bundle successfully
listed VUW environments. The operator selected their Developer environment.
Connection listing requires FlowAgent's separate Power Platform authentication;
the bounded local check ended before that sign-in completed. No connection
identity/status was verified, and no mailbox metadata has been acquired.
The private frozen configuration, retention decision and approval evidence must
still be recorded before acquisition. Account identifiers, device codes and
authentication screenshots are excluded from this repository record.

The sanctioned production acceptance route uses the approved Power Automate
Outlook connector and Dataverse. Graph/offline support does not replace that
route or its live verification. The remaining approved-source adapter and
destination binding must be validated in the selected authorised environment.

## Remaining handover

The operator must supply the actual approved scope/retention/destination
record and authenticated source connection before a live run can proceed.
Local preparation and test results do not fulfill those requirements. Preserve
the recorded evidence and review, then validate the complete population and
actual destination/replay results against the criteria above.
