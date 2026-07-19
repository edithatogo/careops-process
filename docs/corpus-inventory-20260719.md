# Authorised M365 corpus inventory - 2026-07-19

## Classification

This is a privacy-safe capability and coverage inventory, not a process discovery
result. It reports only aggregate counts and access outcomes from Windows-native,
user-scoped probes. No resource names, identifiers, content, personal data, access
tokens or clinical data were recorded.

Tenant-wide coverage is unknown. A denied, unavailable or inconclusive source is
an explicit blind spot and must never be interpreted as zero activity.

## Current delegated probe

| Source surface | Outcome | Aggregate evidence | Coverage interpretation |
| --- | --- | ---: | --- |
| Microsoft Graph profile | accessible | 1 profile response | authentication check only |
| Outlook mail folders | denied (`HTTP 403`) | unknown | mailbox population unknown |
| Teams joined-team discovery | inconclusive (`HTTP 400`) | unknown | Team population unknown; endpoint or permission requires diagnosis |
| OneDrive root | unavailable (`HTTP 404`) | unknown | drive population unknown |
| Planner assigned tasks | accessible | 28 tasks returned | accessible assigned-task population at probe time; pagination and retention still require proof |
| SharePoint site search | denied (`HTTP 403`) | unknown | site and list populations unknown |
| Dataverse environments | previously verified; current PAC enumeration inconclusive | 4 environments in the 2026-07-16 audit | re-enumeration and per-table denominators required |
| Dataverse Approvals | accessible smoke-test source | 4 records in the 2026-07-16 run | connectivity evidence only; not representative |
| Power Automate flow history | not yet probed | unknown | population and retention unknown |
| Teams Approvals | not yet independently inventoried | unknown | Dataverse approval rows do not prove complete Approvals coverage |

## Immediate acquisition implications

1. Planner is the first currently proven Graph acquisition lane, but the 28-task
   response needs pagination, plan/container coverage and retention verification.
2. Outlook and SharePoint require an approved delegated connector/export or a
   resource-owner action; repeated calls with the current token will not broaden access.
3. Teams requires diagnosis of the `HTTP 400` response without treating it as an
   empty result or a permission denial.
4. Dataverse must be re-inventoried using the verified user-scoped connection and
   reconciled by table and observation period.
5. Graph Data Connect remains a separately governed, admin-gated expansion. This
   track must remain useful without it.

## Coverage status

- Evidence class: capability inventory and smoke test.
- Complete accessible-population extraction: not yet demonstrated.
- Cross-source corpus: not yet assembled.
- Main process families: not yet discovered.
- Organisational or tenant-wide completeness: not claimed.
