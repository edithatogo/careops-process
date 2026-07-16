# Windows-native environment audit - 2026-07-16

This audit uses only user-scoped PAC/Azure CLI authentication and the Dataverse
Web API. It does not require WSL, Linux, Mojo, an Entra application, or tenant
administrator access.

## Accessible environments

| Environment | Web API | Current user | Approval metadata | CareOps custom table | Suitability |
|---|---:|---|---:|---:|---|
| Executive Team | yes | Dylan Mordaunt | yes | no | read-only comparison |
| NSW Health Department default | yes | Dylan Mordaunt | yes | no | source approval pilot; no custom schema privilege |
| PowerPagesDeveloper | yes | Dylan Mordaunt | yes | `cop_ProcessCheckpoint` | preferred destination |
| ISLHD personal environment | DNS unavailable | — | not verified | not verified | unavailable from this workstation |

## Findings

- The NSW Health default environment remains the source for minimized approval
  metadata. Existing `msdyn_flow_approval*` tables can be queried without
  reading message bodies, identities, comments, or payloads.
- `PowerPagesDeveloper` is the only verified environment with the privileges
  needed for a dedicated destination. Its current user has `System
  Administrator` and `Basic User` roles.
- `cop_ProcessCheckpoint` exists in `PowerPagesDeveloper` with the primary key
  field `cop_checkpointkey`. It currently has no rows.
- Dedicated event/dead-letter tables were not created yet. Dataverse returned a
  customization-lock response while another customization operation was in
  progress. Creation must be retried sequentially after the lock clears.
- Power BI/Fabric remains unavailable: the authenticated Power BI API returned
  zero accessible workspaces. No Fabric deployment is claimed.

## Operating decision

Use the NSW Health default environment only as the minimized source and use
PowerPagesDeveloper as the user-scoped checkpoint/event destination when its
customization lock permits. Keep all local and committed artefacts sanitized;
never export mailbox content. If the lock persists, continue with the existing
approval metadata and local JSON/PM4Py pipeline rather than weakening privacy or
permission boundaries.
