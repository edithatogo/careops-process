# Local solution ALM

Verified locally on 14 October 2026. This is shared engineering tooling; the Teams
track owns product flows, hub behaviour and the pilot. No command in the Python
tool authenticates, exports from a tenant, checks online or imports a solution.

## Inventory and scope

`powerplatform/solutions/CareOpsProcess` is the harvested unmanaged
`careops_process` version `1.0.0.0`, publisher `careops_publisher`, prefix `cop`.
Its two table roots are `cop_processevent` and `cop_processdeadletter`. Source
contains 29 files with their entity definitions, forms, views, ribbon and relationship XML.
`MissingDependencies` is empty, which is an export declaration rather than proof
that a target environment has every required dependency. There are no harvested
solution-aware cloud flows, connection references, environment-variable definitions,
apps or managed counterparts. Export scripts elsewhere in this repository are
operator tools and are not solution components.

The validator supports this table-only XML/JSON/RESX source profile. It rejects
unknown root component types and binary assets until a reviewed validation adapter
and synthetic tests are added. It checks local table references, XML structure,
four-part versioning, publisher prefix and known secret/bound-value patterns.
This conservative scan is not a complete secret detector or a Dataverse dependency
resolver. Keep the repository secret scan and online solution check as separate gates.

## Offline operator commands

Install Python 3.14 and Microsoft Power Platform CLI on the workstation, then run
`uv sync --locked --group dev`. PAC is an external prerequisite; it is not installed
or authenticated automatically. Installed PAC `2.13.1` was used for local packing
and settings generation. Its `pac solution pack help` confirms these flags.

```powershell
uv run python -m careops_process.local_alm validate powerplatform/solutions/CareOpsProcess
uv run python -m careops_process.local_alm pack powerplatform/solutions/CareOpsProcess artifacts/alm/release-1.0.0.0 --dry-run
uv run python -m careops_process.local_alm pack powerplatform/solutions/CareOpsProcess artifacts/alm/release-1.0.0.0
uv run python -m careops_process.local_alm verify artifacts/alm/release-1.0.0.0
uv run python -m careops_process.local_alm settings powerplatform/solutions/CareOpsProcess artifacts/alm/deployment-settings.json
```

Dry-run validates source and returns the PAC argument list without invoking PAC
or creating output. Packing stages a new ZIP and `release.json` on the same
filesystem and publishes the directory only after ZIP structure, solution identity,
CRC and SHA-256 checks pass. Existing release directories are never overwritten.
Failed or interrupted packing/settings generation cleans staging and leaves earlier
releases intact. Source hashes must agree before and after packing; freeze source
while packaging. SHA-256 detects alteration against the reviewed manifest, but an
attacker able to rewrite both can replace them. Retain the approved digest outside
the writable artifact directory, or sign artifacts in the future hosted release process.
The generated status remains `packaged-offline` and checker status remains `not-run`.

The supported `pac solution pack` command is a local file operation. Package type
follows source provenance. Do not change `<Managed>` or use a missing-managed-file
fallback to turn this unmanaged harvest into a claimed managed export. A downstream
package requires authorised managed export/unpack evidence. PAC archive timestamps
can vary between runs; source hashes are reproducible, ZIP hashes identify each
specific build. Bit-for-bit repeatability is not promised.

## Configuration and flow conventions

`powerplatform/config/deployment-settings.template.json` reflects this harvest:
empty collections are intentional. Generate settings from each reviewed solution
using PAC; do not invent environment-variable or connection-reference names and
assume those components exist. The generator accepts the optional empty
`CopilotAgents` collection emitted by PAC 2.13.1. Nonempty agent settings require
an additional adapter. Bound `Value`/`ConnectionId` entries cannot publish as a
tenant-neutral template.

`component-conventions.example.json` is a design example, not importable metadata.
Future solution-aware flows must live inside the product solution, use explicit
connection references and reference environment variables for target-specific
endpoints. Keep default/current values empty in committed source. Generate the
deployment file, bind values privately, and verify each logical name against actual
solution metadata. Store real bindings under ignored `secrets/` or `artifacts/`;
all ZIPs and these directories are already ignored. Never commit credentials or
bearer tokens, including in deployment settings. Secret environment variables need
the supported platform secret-store mechanism and its own access review.

## Promotion and rollback evidence

Develop in an unmanaged solution. Promote reviewed managed artifacts through
test before production. Increment the four-part solution version for each release;
do not reuse a release directory. Before any authorised change, verify account
and explicit target environment (`pac auth list` and `pac org who`), roles, licence,
consent, import permission, dependency availability and a maintenance window.
Export the current target solution before change and retain its immutable artifact,
hash, export timestamp, target identity and provenance privately. Obtain environment
backup/data-restore evidence where data/schema changes need it. A local packaging
manifest alone does not prove a backup was exported from the target.

```powershell
uv run python -m careops_process.local_alm prepare artifacts/alm/candidate artifacts/alm/pre-change-backup test
```

`prepare` verifies both artifacts and their solution identities, requires backup
evidence as an input, enforces managed candidates for test/prod and returns a review
record. Test/prod candidates must have a strictly newer version than the supplied
backup. It does not execute deployment, write a success marker or certify the backup's
target provenance. Save the review record with target/settings digest, connection
owner/permissions, checker results, dependency review, approval identity/time and
post-import tests. Interruptions cannot turn a preparation record into deployed evidence.

Before import, run authorised `pac solution check` against the intended geography,
retain findings and resolve or formally accept them. It uploads the package to
the checker service; it is not the offline XML validator. Verify import-job completion,
component presence, flow activation, connection access and smoke tests after import.
Connection references point to actual target connections: confirm their owners and
sharing rights, licensing and the identity that will run each flow. Never assume
an importer's connection automatically gives every user access.

Rollback means an operator-approved recovery procedure. Keep the exported baseline
and settings alongside a tested data/environment restore plan. Importing an older
managed ZIP is not a guaranteed downgrade; removed components and changed data
need separate recovery. Prefer a reviewed forward fix when platform version rules
prevent downgrade. Do not uninstall a managed solution as an automatic rollback:
that can remove components and data. Record recovery tests in the authorised
non-production environment before production approval. No live rollback is verified here.

## Optional platform capabilities and official references

Current feature choices were checked against official Microsoft documentation on
14 October 2026. The [PAC solution reference](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/solution)
documents local pack/unpack and create-settings plus online export/import/check.
We use local packaging/settings now; online operations remain Phase 6 gates.

[Power Platform pipelines setup](https://learn.microsoft.com/en-us/power-platform/alm/set-up-pipelines)
describes pipeline host and environment setup. Native pipelines remain optional:
confirm current Managed Environment/licensing requirements, authorised environments,
pipeline administration and deployment rights before selecting them. This track
creates no host environment, application identity or pipeline infrastructure.
Pipeline approvals and deployment history can provide hosted evidence once available.

[Fabric CI/CD workflow options](https://learn.microsoft.com/en-us/fabric/cicd/manage-deployment)
and [Fabric CI/CD planning](https://learn.microsoft.com/en-us/fabric/fundamentals/understand-best-practices-fabric-cicd)
describe Git and deployment alternatives. Adopt only for a real authorised Fabric
workspace with suitable subscription/capacity, repository access, workspace and
pipeline permissions. They are separate from this Dataverse package. Inventory
supported item types, bindings and provider limitations before promotion.
[Data Factory CI/CD limitations](https://learn.microsoft.com/en-us/fabric/data-factory/git-integration-deployment-pipelines)
include reauthentication for Teams/Outlook OAuth activities after promotion.
Do not claim that Git sync or pipeline creation proves data/connection portability.

## Verification limits

### Bounded model-driven app source profile

The offline validator also supports the PAC-unpacked `AppModules/*/AppModule.xml`
and `AppModuleSiteMaps/*/AppModuleSiteMap.xml` profile observed in the actual
Developer export. Root component 80 resolves an app and 62 resolves its navigation;
both identities must match their source folders and each other. App entity,
form (60), view (26) and navigation (62) references must resolve to the exported
entity sources; form/view identifiers must match their files and belong to an
entity included by the app. Missing, duplicate and unknown references fail closed.
Navigation supports entity subareas only; external links require another adapter.
Area IDs must be nonempty and unique within their sitemap, Group IDs within their
Area, and SubArea IDs within their Group. Missing, whitespace-only and padded IDs
are rejected rather than normalized into ambiguous navigation identities.

Only the observed `AppChannel` app setting with numeric value `1` and a Boolean
customizability flag is exempted from the generic bound-value scan, inside the
validated app source context. Other values/settings and original XML comments
remain scanned. This is not a general exemption for XML `value` elements.

Declared `MissingDependencies` still prevent packaging. The inspected real export
declares platform icon and AppChannel dependencies and contains app role mappings;
those mappings require target-specific sharing review and are refused by this
portable source profile. No dependency resolution, role reassignment, live
navigation/UI behavior or managed promotion is inferred from offline validation.
The actual exported package is unchanged and is not certified portable by adding
this adapter. Synthetic fixtures contain no real role, tenant or app identifiers.

Synthetic tests cover malformed versions/XML, missing components/dependencies,
protected/bound content, tampering, private diagnostics, dry-run, interrupted writes,
settings schemas and export-before-change preparation. Local PAC packing and settings
generation were executed without authentication against the harvested table solution.
Hosted checker results, managed export, import, real connection binding, native
pipeline licensing/permissions and rollback remain unverified external gates.

Two independent local PAC builds had identical hashes for all 29 source files,
but different ZIP digests (`2aaecb13eefd82aa4041d832288c872ab13840a0000977c2522ac11f258ffd38`
and `9b2d8462d8d9e97e620ae53133ba1e544992219ec2fe981dafb62846e2364c49`).
Both ZIPs passed structural/identity/integrity checks. They remain ignored local
artifacts, not hosted release or tenant evidence.
