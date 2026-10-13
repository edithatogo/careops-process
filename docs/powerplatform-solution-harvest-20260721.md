# Power Platform solution harvest — 2026-07-21

An authenticated PAC export from the PowerPagesDeveloper environment was
inspected and unpacked into `powerplatform/solutions/CareOpsProcess`.

The harvested unmanaged solution contains two deployable Dataverse entities:

- `cop_ProcessEvent`
- `cop_ProcessDeadLetter`

The export contains no Power Automate workflows. Therefore the harvest closes
the missing Dataverse-schema portion of the deployment blocker, but not the
historical Outlook flow or its connection reference. The flow remains a
tenant-side build/import/bind gate.

The harvested XML was scanned with Gitleaks; no leaks were found. No tenant
exports, records, mailbox content, connection IDs, tokens, or user identities
were added to the repository.
