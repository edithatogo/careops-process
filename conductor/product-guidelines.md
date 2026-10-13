# Product Guidelines

## Purpose and users

CareOps Process must reduce operational and executive coordination burden while
preserving authority, accountability, privacy and an auditable record. Products
must be usable by ordinary authorised Microsoft 365 users and support multiple
owners without hidden tenant-administrator dependencies.

## Governance principles

1. Keep decisions at the lowest authorised level and escalate by defined exception.
2. Distinguish operational ownership, advice, consultation, assurance,
   endorsement, approval, noting and ratification.
3. Never infer authority from workflow participation or a Teams Approval.
4. Preserve the authority source, decision rule, participants, conflicts,
   rationale, outcome, actions and records reference for every governed decision.
5. Treat workflow templates and thresholds as controlled, versioned configuration.
6. Require human confirmation for governance rules, production use, exceptions
   and pathway expansion.

## Executive usability

- Present concise decision briefs, material exceptions, overdue actions and
  assurance gaps rather than routine process noise.
- Minimise clicks, repeated data entry, notifications and duplicate reporting.
- Support secretariat preparation, meeting decisions, out-of-session decisions,
  minute references and ratification.
- Make acting arrangements, delegates and organisational changes visible and
  auditable.
- Measure executive handling time and approval fatigue as product risks.

## Information handling

- Repository data and fixtures must be synthetic and tenant-neutral.
- Collaboration projections contain privacy-minimised metadata only.
- Protected narrative and evidence remain in an approved authoritative location.
- Planner, Teams messages, approval cards and generated agenda packs do not
  become the sole authoritative decision record.
- Every live pathway requires an explicit classification, access, audit,
  retention, disposal and records-export determination.
- Fail closed when access control, continuity, authority or recordkeeping cannot
  be verified.

## Low-privilege implementation

- Prefer Windows-native, user-scoped PAC, PowerShell and delegated APIs.
- Do not require Entra application registration, tenant-wide admin consent,
  service principals, tenant policy changes, WSL or Linux.
- Record unavoidable resource-owner or user-connection actions explicitly.
- Require multiple workflow owners, connection-health monitoring, export-before-
  change, rollback and owner-departure procedures.
- Separate repository capability, live tenant verification and external approval
  states in all status reporting.

## Quality and evidence

- Define observable acceptance criteria and failure paths before implementation.
- Use synthetic end-to-end scenarios, property tests and replay tests for routing,
  authority, privacy, transitions, approvals and task reconciliation.
- Maintain at least 90% line and branch coverage for executable code.
- Preserve provenance and configuration versions so every generated result can be
  traced to its inputs and rules.
- Report residual limitations directly; do not equate a successful import or
  flow run with production, clinical-governance or organisational approval.

## Change and release

- Introduce pathways through synthetic, low-sensitivity live and expansion stages.
- Define entry, stop, rollback and progression criteria for every stage.
- Require a documented post-pilot decision before production use or expansion.
- Never silently change an active pathway, authority rule, threshold, role,
  notification policy or records requirement.

