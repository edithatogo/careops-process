# Low-privilege Microsoft 365 and Dataverse ingestion

- GitHub issue: https://github.com/edithatogo/careops-process/issues/3
- GHE issue: https://nswhealth.ghe.com/60217257/careops-process/issues/3
- GitHub Project: https://github.com/users/edithatogo/projects/26

## Specification

Build incremental, idempotent ingestion through existing user-scoped Outlook,
Power Automate, Approvals, Planner, and Dataverse connections without local
mailbox export or new Entra applications.

## Plan

- [x] Inventory approved connectors and source event contracts.
- [x] Implement synthetic adapter and contract tests first.
- [x] Implement an exclusive watermark and deterministic idempotent identifiers.
- [x] Prove raw-content rejection and keyed pseudonymization.
- [x] Define the live-pilot boundary; execution remains a platform-gated manual step.
- [x] Conductor - User Manual Verification.
