# VUW development connection receipt — 15 October 2026

The operator explicitly authorized creating an Office 365 Outlook connection
in VUW-AI-TEST, continuing the existing limited VUW testing scope, and
coordinating with the M365 agent. Creation completed through the authenticated
Power Automate browser session. The connection list and details page both
show `CareOps VUW development test`, Office 365 Outlook, status `Connected`.
No password, MFA or additional permission-consent prompt appeared.

The actual connection/environment binding and screenshot are saved in the
private local evidence directory outside Git. The M365 agent received those
paths and confirmed its consumer is ready. This is development connection
setup evidence, not a mailbox acquisition or a closed backfill run.

Verification on the current checkout: 62 Outlook contract/reconciliation/
integration tests pass. The PowerShell exporter approval, privacy, pagination,
replay, window and failure regressions pass. These are offline regressions;
they do not prove live connector pagination or mailbox completeness. The M365
agent separately reports 46 downstream tests passing in its current checkout.

The FlowAgent identity check matches the existing VUW Connectivity identity,
but its Flow token identity is absent. Earlier Flow token acquisition returned
a Windows token-cache decryption error, despite successful browser sign-in.
Connection creation resolved the missing-connection gate; usable automation
transport and a scope-bound minimized acquisition still require verification.
No mailbox read, destination write, empirical source count or replay was
performed in this setup operation. Do not weaken cache encryption to repair
transport, and do not request duplicate browser login merely because CLI
token access is unavailable.

The next acquisition must bind the authorized Inbox-only seven-day window,
local destination, retention and private approval/configuration evidence.
Provide real minimized facts and independently measured source/page,
destination and replay evidence to M365 when acquired. Queensland Health
remains the actual pilot target and has its own approval requirements.

## Supported transport recovery

The bounded diagnosis reproduced Azure CLI exit 1 with Decryption failed /
WinError 13 under the default Azure profile and the expected VUW account.
Following the [MSAL persistence recovery guidance](https://github.com/AzureAD/microsoft-authentication-extensions-for-python/wiki/PersistenceDecryptionError),
the old encrypted cache was preserved under a backup filename in its existing
private directory, and the expendable active cache was reset by renaming it.
One new device sign-in completed using the existing VUW browser session, with
the agent entering the code. The CLI process finished successfully, and a
subsequent Power Automate token request succeeded. Encryption remained enabled;
no passwords or tokens were displayed or persisted in the repository.

FlowAgent now verifies matching Azure, Flow-token and Connectivity identities.
Office 365 Outlook operation/schema discovery succeeds, including GetEmailsV3
and HttpRequest. This supersedes the earlier transport blocker. The M365 agent
was notified. No mailbox read was needed for diagnosis or schema discovery;
the minimized metadata acquisition and its measured evidence remain pending.

## Bound test controls

Existing private records were inspected. They contain the connected binding
and earlier unapproved proposals, but no approved retention/disposal decision.
A new private test-controls proposal records the fixed seven-day Inbox window,
verified connection, metadata allowlist, local-only destination, operator's
source-test authorization and rollback restricted to this run's derived files.
It proposes disposal of derived evidence and the pseudonym key seven days
after completion. Retention and configuration-freeze flags remain false;
execution has not started. The operator was asked only for that remaining
retention/disposal decision. Source authorization is recorded as the operator's
assertion, not independently verified institutional authority. No Queensland
Health approval is inferred.

## Completed bounded metadata test — 16 October 2026

The coordinator relayed direct human approval to dispose of both the derived
test evidence and pseudonym key seven days after completion and proceed.
That decision and its coordinator-chat provenance were recorded privately.
The original fixed observation window was preserved: 7 October 2026 14:56:44
UTC inclusive through 14 October 2026 14:56:44 UTC exclusive. No rolling window
or additional folder was substituted. The configuration was frozen and hashed
before source acquisition; retention approval is no longer pending.

The existing connection was verified Connected with the expected VUW identity
through FlowAgent's documented connection check. A first private preflight
attempt used an incorrect connection-status endpoint and returned HTTP 404
before any mailbox request or evidence directory creation. It was corrected
to use that documented service check. No authentication loop or permission
expansion was required.

The bounded acquisition used the existing Office 365 Outlook connection's
HttpRequest operation, with its actual service swagger/runtime contract. Only
source GET requests were made. The request selected the seven approved metadata
fields; identifiers were pseudonymized in memory using a unique test key.
No cloud flow or raw-payload run history was created. The key is protected with
Windows DPAPI outside Git and is not shared with any other run.

| Measured check | Result |
| --- | --- |
| Source-reported count for the bounded query | 30 |
| Initial candidates / acquired / duplicate / rejected / dead letter | 30 / 30 / 0 / 0 / 0 |
| Initial pages / final continuation | 1 / exhausted |
| Local canonical destination records read back | 30 |
| Second source acquisition / pages | 30 / 1 exhausted |
| Replay new identities / content drift | 0 / none |

A separate Python process validated the persisted records against the strict
repository CollectorMailFact and CanonicalMailFact models, recalculated
configuration/approval/content hashes, compared the actual destination readback
and replay, and verified the exact disposal file allowlist. The adapter's
synthetic guard checks also passed for metadata privacy, wrong folder/window,
unsafe continuations and deterministic pseudonyms.

The evidence remains `smoke_test`: a single bounded Inbox and a local JSONL
destination. The second acquisition is a separate source read, not independent
population ground truth. The source count comes from the same service. There
is no full-mailbox, nested-folder, Dataverse, Queensland Health pilot or
Executive-validation claim. These results do not close the original track.

Completion: **2026-10-16T03:02:12.371001Z**. Approved disposal deadline:
**2026-10-23T03:02:12.371001Z** (23 October, 13:02 Brisbane time).
The private run directory contains its measured manifests, initial/replay
facts and page ledgers, canonical destination, frozen controls and independent
verification. Its disposal manifest lists exactly 14 derived files including
the unique DPAPI-protected pseudonym key; no legal hold is recorded. Root and
M365 received private artifact paths, counts, completion/deadline and evidence
limits. Its downstream check also passed strict fact/page schemas, hashes,
counts, destination equality and unchanged replay; it correctly rejected using
the scoped Inbox descriptor as a full folder-inventory closure contract.

Root confirmed creation of the active Codex follow-up
`dispose-bounded-vuw-test-evidence`, scheduled for 23 October at 13:03 Brisbane
time, immediately after the precise seven-day deadline. It pins the 14-file
allowlist, unique encrypted key, manifest timestamps and path/shared-key/
legal-hold safeguards, and requires final absence verification and a minimal
receipt. No duplicate scheduler was created by Outlook. Disposal is scheduled,
not completed; execution requires Codex to be available and is not guaranteed
while offline.

## Local follow-on review — 17 October 2026

The completed bounded acquisition was not repeated or expanded. The saved
disposal automation was verified active with unchanged 23 October 13:03
Brisbane timing and the exact 14-file/key safeguards; nothing was deleted.
The [readiness review](readiness-review-20261017.md) records seven new synthetic
folder/disposition/malformed-response regressions, coordinated destination
provenance hardening, 112 passing targeted checks and the smallest actual-pilot
input set. Full-mailbox, durable deployed resume and Dataverse provenance
remain unverified. No VUW evidence is relabelled as QH pilot evidence.
