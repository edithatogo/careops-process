# Suite CI adoption

- [x] Qualify current dependency lock and immutable action upgrades (PR #75; 43ca97b).
- [x] Adopt shared source security without removing domain quality/property/privacy checks; optional mining remains a declared dependency without an implemented provider adapter.
- [ ] Add scheduled development dependency/runtime candidates, receipts and automatic lock maintenance; promote only through passing source PRs.
- [ ] Exercise actual optional interfaces and build meaningful source/software releases with SPDX/provenance verification.
- [ ] Verify exact required checks, updater ownership and post-merge runs.

CI work is source-only. No tenant configuration, authentication, content processing
or native approvals. Existing domain tracks retain their source authority. A
canary failure does not justify weakening supported Python or coverage contracts.

## Actual software package delivery

- [x] Lock the exact Hatchling1.32.4 backend and all build dependencies; disable isolated network build resolution.
- [x] Prepare an actual wheel, its complete file SPDX inventory and a separate frozen lock-derived CycloneDX inventory of runtime/optional dependencies.
- [x] Exercise the installed wheel in an independent environment with hash-locked runtime dependencies and fictional inputs.
- [ ] Qualify current-head package/source checks, then verify downloaded package/SBOM and main-only OIDC signatures against exact source/workflow identity.

Resolved optional mining dependencies remain inventory, not provider adapter or
licence adoption. No PyPI publication, native writes or operational processing.

## Required Python runtime — PR96, 23 October 2026

- [x] Replace the historical Python3.14 compatibility proposal with the user's
  required exact Python3.15.1 runtime for active development, build, test, and CI.
- [x] Align `.python-version`, `pyproject.toml`, `uv.lock`, CI matrices, package
  workflows, runtime-candidate workflow, and current setup instructions; keep
  development dependency resolution isolated and do not promote a preview.
- [x] Verify PR96 exact-head results and merged main at
  `77c2e93c872ff4ddab445b2d0f14d06704f19f34`; its Python3.15 quality/tests,
  CodeQL, shared source security, candidate discovery, and wheel checks passed.
  Optional PM4Py qualification and main-only attestation were skipped by their
  declared conditions.

PR77's earlier Python3.14/3.15.0 candidate receipts are historical. The current
main source is pinned to Python3.15.1. The separate Dependabot uv graph updater
still fails before graph analysis because its provider supports only through
Python3.14; the exact failure remains recorded and the required runtime is not
downgraded. The module's frozen dependency graph workflow passed at current main.

## Frozen graph provider qualification

Use the existing CareOps immutable snapshot adapter for a main-only dependency
submission from all frozen lock groups/extras. Preserve the Python 3.15.1 runtime,
package pins, optional-provider boundaries and all existing source/security gates.
Verify the actual 72-package/84-edge candidate payload locally, fail-closed
acceptance/readback cases and current-head hosted checks, then verify one accepted
main submission and package-identity graph readback. Do not equate exported edges
with readback edges or optional declarations with installed runtime capabilities.
Keep accepted handles for reconciliation; no automatic retry or tenant change.
