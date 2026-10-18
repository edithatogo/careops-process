# Selected Developer environment lifecycle — 18 October 2026

## Observed state

Two read-only, explicitly targeted management queries succeeded for the existing
personal VUW Developer environment. PAC returned `type=Developer` and
`protectionLevel=Standard`. A separate Power Apps management response obtained
with the isolated VUW Azure configuration returned `environmentSku=Developer`
and `governanceConfiguration.protectionLevel=Standard` with extended governance
settings. Real bindings and raw responses remain in ignored local receipts:
`artifacts/alm/personal-dev-management-state-private.json` and
`artifacts/alm/personal-dev-bap-state-private.json`.

Microsoft's [Managed Environment configuration documentation](https://learn.microsoft.com/en-us/power-platform/admin/managed-environment-enable)
uses `Standard` to enable Managed Environments and `Basic` to disable them.
Applying that documented mapping to the actual governance response establishes
that the selected Developer environment is managed. This is independent of the
solution's managed/unmanaged package flag; its current solution export is unmanaged.

## Lifecycle applicability and licensing limit

The [Developer Plan guide](https://learn.microsoft.com/en-us/power-platform/developer/plan),
updated 16 October 2026 and checked 18 October, states that unmanaged Developer
environments are suspended starting 15 December 2026 and deleted starting
15 January 2027. Managed Developer environments are unaffected. Consequently,
the observed selected environment is not in that announced unmanaged retirement
scope. No retirement deadline is asserted for it from that notice.

The same guide says Developer Plan rights do not include Managed Environment
use rights. Actual Premium/Managed entitlement and connector licensing/DLP still
require verification. Coordination separately reports Graph license-detail
evidence of FLOW_FREE and M365EDU_A5_FACULTY, including a successful
FLOW_P2_VIRAL service plan and disabled DYN365_CDS_VIRAL. These service-plan labels
alone do not establish the required entitlement or an actual denial. This lane
did not repeat the Graph query or change any subscription or grant.

## Preservation and next prerequisite

Retain the baseline and actual app exports, their hashes, source metadata and
private recovery receipts. Existing export dependency and role-binding gates
remain in force; an export alone does not prove successful migration.
Before choosing a different durable target, verify destination rights, required
platform dependencies, role mappings, configuration/connection owners, licensing
and import/recovery acceptance. No migration is required solely by the unmanaged
retirement notice for the currently observed managed environment.

No managed setting was enabled or disabled, no environment was created/migrated,
and no license, consent, role or grant was changed during this assessment.
