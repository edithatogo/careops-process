# Power Platform solution harvest — 2026-07-21

Historical evidence is retained below. Current offline structure validation,
PAC packaging, settings templates and promotion gates are documented in
[Local ALM](local-alm.md), verified on 14 October 2026. Those local checks do not
renew the historical account permissions or prove a live managed deployment.

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

## Remaining platform blocker

The authenticated PAC profile can inspect the PowerPagesDeveloper environment,
but `pac connection list` currently returns no connections there. There is
therefore no available Outlook connection reference to bind to a cloud-only
Power Automate workflow from this profile. PAC also provides no flow-authoring
command in this environment. This is an environment/connection provisioning
gate, not a repository implementation defect.

The default environment is separately blocked for Dataverse schema import by
`prvCreateEntity` at Basic depth. The populated schema is preserved in source
control and requires deployment by an environment maker/system customizer or
an approved managed-solution pipeline.
