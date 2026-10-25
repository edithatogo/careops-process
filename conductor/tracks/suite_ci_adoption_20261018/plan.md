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

## Historical Python runtime promotion — PR77 (reconciled 25 October 2026)

- [x] Reconcile PR77's historical Python3.14/3.15 compatibility candidate with
  the portfolio's current exact Python3.15.1 requirement. PR77 merged as
  `5436642c31510dbdee5e90c5aa0c697616a1689c`; its required PR checks passed and
  its canary tested Python3.14.8 and3.15.0. These are historical receipts, not
  current supported runtimes.
- [x] Confirm current stable CI and package workflows use Python3.15.1, while
  the isolated development canary limits discovered candidates to the 3.15
  line. Preserve its review guard; do not execute older compatibility runners.

The original PR77 rationale was that a bot proposal dropped3.14 while CI still
selected it. That was the source-time decision record and is superseded by the
user-selected Python3.15.1-only stable runtime policy. Keep the old receipts for
provenance; any future candidate stays isolated and within the required 3.15
line. See the active full-surface audit in
`../python315_qualification_20261023/plan.md`.

## Frozen graph provider qualification

Use the existing CareOps immutable snapshot adapter for a main-only dependency
submission from all frozen lock groups/extras. Preserve the Python 3.15.1 runtime,
package pins, optional-provider boundaries and all existing source/security gates.
Verify the actual 72-package/84-edge candidate payload locally, fail-closed
acceptance/readback cases and current-head hosted checks, then verify one accepted
main submission and package-identity graph readback. Do not equate exported edges
with readback edges or optional declarations with installed runtime capabilities.
Keep accepted handles for reconciliation; no automatic retry or tenant change.
