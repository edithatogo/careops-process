# Historical Outlook backfill completion audit

Current local review, 17 October 2026: the authorized 30-record VUW smoke test
has completed and been independently checked. The existing exact-file/key
disposal schedule remains active for 23 October at 13:03 Brisbane time.
Folder-disposition/runtime-shape repair `037cd90` and destination-provenance
repair `7f376db` pass 112 targeted tests together. See the
[readiness review and exact pilot inputs](readiness-review-20261017.md).
The dated audit below records earlier snapshots; its pending VUW setup and
retention decisions are superseded by the completed test receipt. The full
QH folder/Dataverse/resume/owner/Executive gates remain unmet, and unsupported
live closure now fails closed rather than trusting a destination boolean.

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
FlowAgent's separate cached Power Platform identity is now verified to match
Azure's VUW identity. Outlook-filtered and unfiltered connection listings both
returned empty in the operator-selected Developer environment and, following
the operator's next selection, the VUW STAFF Default environment. No existing
connection binding is available from those results. Creating a new connection
was not attempted. FlowAgent's find-only discovery was also checked in STAFF
Default: its PPAPI fallback returned NotFound with creation disabled. This
confirms the earlier empty-list result through the alternate discovery route.
Creating a new connection
or selecting another environment awaits the operator's decision. No mailbox
metadata has been acquired.

The operator subsequently authorized iterating through every VUW environment.
Find-only discovery (creation disabled) returned NotFound in VUW-PipelineHost-AU,
Centre Of Excellence Makers, Centre of Excellence - Starter Kit and VUW-AI-DEV.
Together with the earlier verified STAFF Default and personal Developer checks,
six environments have returned no Outlook connection. VUW-AI-TEST remains
unverified: the continuation failed to decrypt Azure's Power Automate token
cache (WinError 13). One fresh device login was completed in the browser with
the agent entering its code and selecting the existing VUW session; subsequent
token acquisition still returned the same decryption error. Browser sign-in
success does not establish usable CLI token access. Do not represent this
interrupted scan as a verified absence across all seven environments.

The remaining VUW-AI-TEST check was subsequently completed through the Power
Automate browser interface using the existing VUW session. Its selected
environment header and Connections page explicitly show no connections.
All seven accessible VUW environments have therefore been checked: six through
find-only discovery and the seventh through the browser. No existing Outlook
connection was found for this operator. No connection was created. Creating a
VUW development test connection requires the operator's next decision; it is
not established by the completed discovery scan.
The private frozen configuration, retention decision and approval evidence must
still be recorded before acquisition. Account identifiers, device codes and
authentication screenshots are excluded from this repository record.

The sanctioned production acceptance route uses the approved Power Automate
Outlook connector and Dataverse. Graph/offline support does not replace that
route or its live verification. The remaining approved-source adapter and
destination binding must be validated in the selected authorised environment.

## Remaining handover

Update, 15 October 2026: the operator authorized creating the VUW-AI-TEST
Outlook test connection. Creation completed and Connected was verified in the
browser. See the [connection receipt](test-connection-20261015.md) for current
test results, M365 coordination and the remaining acquisition/transport gates.
The earlier missing-connection decision is resolved. No live mailbox evidence
or pilot completeness is established by connection creation.

The operator must supply the actual approved scope/retention/destination
record and authenticated source connection before a live run can proceed.
Local preparation and test results do not fulfill those requirements. Preserve
the recorded evidence and review, then validate the complete population and
actual destination/replay results against the criteria above.
