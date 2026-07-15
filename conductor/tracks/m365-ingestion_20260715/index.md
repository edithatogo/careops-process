# Low-privilege Microsoft 365 and Dataverse ingestion

- GitHub issue: https://github.com/edithatogo/careops-process/issues/3
- GHE issue: https://nswhealth.ghe.com/60217257/careops-process/issues/3
- GitHub Project: https://github.com/users/edithatogo/projects/26

## Specification

Build incremental, idempotent ingestion through existing user-scoped Outlook,
Power Automate, Approvals, Planner, and Dataverse connections without local
mailbox export or new Entra applications.

## Plan

- [ ] Inventory approved connectors and source event contracts.
- [ ] Implement synthetic adapter and contract tests first.
- [ ] Implement watermark, replay, tombstone, throttling, and dead-letter logic.
- [ ] Prove transient-content deletion and keyed pseudonymization.
- [ ] Run a narrow live pilot only after the privacy gate.
- [ ] Conductor - User Manual Verification.
