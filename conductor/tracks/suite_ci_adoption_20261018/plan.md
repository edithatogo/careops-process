# Suite CI adoption

- [x] Qualify current dependency lock and immutable action upgrades (PR #75; 43ca97b).
- [x] Adopt shared source security without removing domain quality/property/privacy checks; optional mining remains a declared dependency without an implemented provider adapter.
- [ ] Add scheduled development dependency/runtime candidates, receipts and automatic lock maintenance; promote only through passing source PRs.
- [ ] Exercise actual optional interfaces and build meaningful source/software releases with SPDX/provenance verification.
- [ ] Verify exact required checks, updater ownership and post-merge runs.

CI work is source-only. No tenant configuration, authentication, content processing
or native approvals. Existing domain tracks retain their source authority. A
canary failure does not justify weakening supported Python or coverage contracts.
