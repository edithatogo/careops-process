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

## Controlled Python runtime promotion — PR77

- [~] Repair the existing Python3.15 proposal: preserve Python3.14 compatibility,
  regenerate the lock without upgrading its package pins, run the full quality
  and domain suite on exact3.14.8 and3.15.0, and qualify the installed wheel on3.15.0.
- [ ] Verify all current-head checks and both canary matrices before normal merge;
  no automatic runtime adoption or release acceptance is inferred from metadata.

The prior bot proposal dropped3.14 while CI still selected it and the canary
intentionally refused a changed range. Keep the canary's candidate-only widening
review guard aligned with the supported range, including older supported runs.
