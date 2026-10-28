# Read-only target prerequisite assessment

`careops_process.alm_target_preflight.assess_target(artifact, binding)` produces a
separate point-in-time prerequisite report. It does not call import, alter the
artifact, approve sharing or weaken `local_alm.validate_solution`/portable packing.
The current actual app export still fails portable dependency and role-map gates.

The private binding object has exactly these fields: `environment_url`,
`organization_id`, `user_id`, `environment_id`, `artifact_sha256`, `decision`, and
`reviewed_at`. Pin these to the reviewed target/artifact and retain the sidecar
outside Git. `decision` must be `retain-existing-restrictions`; it is a scope
restriction, not evidence of service authority. An aware review timestamp must
be no older than 15 minutes and not in the future, including at completion.
Additional receipt/observation/allow fields are rejected.

The function hashes one bounded in-memory artifact snapshot, checks its manifest
identity, CRC and supported declared prerequisites, and verifies the on-disk
artifact remains unchanged after reads. Unhandled dependencies and malformed or
duplicate declarations fail closed. This is a narrow profile for the inspected
app export, not a general Dataverse dependency resolver or full app-schema review.
Prerequisite container cardinality and child tags are checked before extraction:
exactly one MissingDependencies container per manifest, at most one AppModules
container, and exactly one AppModuleRoleMaps container per included app. Unknown
dependency/app/role children and malformed or duplicate containers are rejected,
rather than silently counted as zero requirements.

Existing Azure CLI delegated authentication must already work. Set the existing approved private configuration directory on the calling process,
never globally. Supply its location locally:

```powershell
$env:AZURE_CONFIG_DIR = $env:CAREOPS_AZURE_CONFIG_DIR
```

The module attempts no login and stores no credentials. It uses the existing
ignored ALM SDK interpreter under `artifacts/alm/sdk-venv/Scripts/python.exe`,
official Dataverse SDK 1.1.0 and AzureCliCredential with skill attribution. Missing
runtime/auth fails with sanitized diagnostics. WhoAmI and environment management
reads use bounded HTTPS responses with redirects disabled. The actual principal
and organization must match before component reads; exact environment management
identity and linked organization URL must also match. No tenant enumeration occurs.

Supported dependency policy is deliberately pinned: AppModuleWebResources 2.5,
its exact default icon identity, msdyn_AppFrameworkInfraExtensions 1.0.0.20 and
PowerAppsAppFramework_Anchor 1.0.0.26. The export's AppChannel package declaration
must still specify 1.0.0.25. These are the inspected versions, not a claim that all
newer releases are compatible. A changed installed version requires review and
an explicit code-policy update. Unique actual component records and exact solution
memberships must match; solution names or versions alone are insufficient.

Each exported role identifier must resolve through a stable role template to a
single restricted System Administrator or System Customizer role in the target
root business unit. Multiple candidates are refused conservatively; no roles or
assignments are created. Retaining restrictions does not authorize ordinary-user
sharing or clinical authority. New sharing policy needs its own decision.

Reports bind the artifact digest, solution identity and a digest of the complete
private target sidecar, plus observation time and checked counts. They always
leave import rights and recovery `unverified`, with portable validation unchanged.
They have no reusable approval token or importer integration; later operations
must revalidate actual identity, rights, settings and service state. Real bindings
and raw service responses must remain private. Synthetic tests do not establish
tenant deployment compatibility or a successful app import/recovery rehearsal.
