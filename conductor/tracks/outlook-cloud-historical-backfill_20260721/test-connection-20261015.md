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
