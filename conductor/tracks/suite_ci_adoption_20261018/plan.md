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
