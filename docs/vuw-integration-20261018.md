# VUW gate and default-branch integration checkpoint — 18 October 2026

This checkpoint combines the reviewed CareOps branch with default-branch revision
`1e092ffb11c165c7d23fc9a217a76783577b8624`. It does not merge PR 73, deploy
production, accept a clinical model or authorize real notification dispatch.

## Repository integration

The default branch added shared source-security checks, dependency qualification,
a source-only preview canary, and wheel candidates with separate inventories and
main-only attestations. Their pinned tools and exact Hatchling build dependency
are retained alongside the branch's Conductor validation, submodule checkout,
independent coverage gate, offline PowerShell regressions and optional mining job.
The mining job now exercises the actual alignment/store tests as well as imports.
The canary remains source-only evidence, not full Conductor/submodule or
PowerShell qualification; stable CI retains those additional gates.

Python updates remain owned by Renovate's `pep621` manager, including `uv.lock`.
Renovate also owns Git submodules; Dependabot owns GitHub Actions. The current
main scheduling and lock-maintenance policy are preserved. Explicit local and
package-rule automerge prohibitions remain in place. This supersedes the earlier
branch proposal to assign Python to Dependabot.

The combined metadata keeps `defusedxml` as a runtime dependency because the
packaged ALM and alignment modules import it. The lock was resolved with the
same uv 0.13.1 pinned in CI. Existing MIT notices were added to branch Python
files to meet the newer Ruff toolchain. One legacy CP1252 dash in a historical
plan was converted to UTF-8 without rewriting the plan's claims.

Local checks passed lint, formatting, strict typing, Conductor validation,
Bandit, dependency audit and both offline PowerShell suites. The first combined
installed-backend suite passed **1,717 tests, with eight skips**: seven hosted
Linux Bash receipt cases are unsupported on Windows, and the absent-backend
case intentionally skips when the pinned backend is installed. The seven receipt
cases subsequently passed locally after adding direct execution of the unchanged
Python receipt body on Windows; Linux retains execution of the Bash wrapper.
The full local suite then passed **1,724 tests with one intentional absent-backend
skip**. On published integration `ae2f234`, stable hosted CI passed 1,715 tests
with ten optional-backend skips, and both hosted source canaries passed 1,724
tests with one skip. CodeQL, shared source security and the wheel candidate also
passed on that exact revision. Later receipt wording changes need their own
exact-revision hosted checks.
A built wheel was installed into a separate runtime-only
environment and its XML, alignment and authenticated-store imports passed.

Windows denied replacement of a file in the prior shared virtual environment.
Qualification therefore used an isolated ignored integration environment; no
cache, credential or application was deleted or restarted. A CLI subprocess
initially selected the old environment, then passed with the isolated environment
selected explicitly. The full suite was rerun successfully under that setting.
These local results require exact published-revision hosted verification.

## Actual VUW gate evidence

Reliability freshly verified the TEST caller and all eleven required write
privileges: customization, import/export, publication and solution/publisher/app
capabilities remain absent. No TEST import or new permission was attempted.
The exact pre-import inventory contained no CareOps solution or matching four
tables. An authorized TEST operator must resolve the rights gate and revalidate
that inventory immediately before the bounded deployment.

An actual managed source export succeeded through the documented ExportSolution
action after PAC terminated with a confirmed Windows native application fault.
No XML flag was relabelled to manufacture the package. Independent local review
verified 24,222 bytes, CRC and SHA-256
`0bff972a5bb3bab121913ca26715ceacdce381b4ecd50864152214b447756473`.
Its manifest is `careops_process` 1.0.0.0, Managed=1, with four tables, sitemap and
app roots. App/form/view/navigation references resolve; two role mappings and
two declared dependencies remain. Eighteen generated form-label descriptions
are empty in the managed export compared with the earlier unmanaged artifact.

The actual managed artifact passed a fresh read-only TEST prerequisite assessment
at `2026-10-18T13:29:41.273676Z`: two exact dependencies and two restricted role
templates. Live Checker completed with zero findings, and settings generation
found no environment variables, connection references or agents in this package.
These results do not establish import rights, compatibility after import,
browser acceptance or recovery. A scoped Developer backup read returned an empty
collection; no restore or schema/data recovery was demonstrated.

The environment policy-assignment read returned HTTP 403. Effective DLP, Managed
Environment/Premium execution entitlement and a permitted conditional Dataverse
connection remain operator evidence gates. There is no verified cloud worker or
durable historical resume execution. Raw bindings, signed URLs and operator
receipts remain private.

An actual Renovate Python PR generated both manifest and lock changes and passed
its frozen-install checks. That is pre-integration bot evidence, not approval of
its proposed PM4Py version or proof that the combined 1,725-test suite passed on
that PR. Actual submodule-update operation, applicable repository security
settings, target deployment/recovery and human sign-off remain open.

Queensland Health live/pilot work remains deferred. The approved 23 October
13:03 Brisbane evidence/key disposal schedule and exact-file guards are unchanged.
