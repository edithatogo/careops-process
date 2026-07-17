# Specification: Teams clinical-governance workflows

## Overview

Implement reusable, multi-user clinical-governance workflows surfaced through
Microsoft Teams. The first supported pathways are the merged PRA/Pitstop review
and assurance pathway and the tiered research-governance pathway defined by the
ISLHD delegations work.

Teams is the collaboration surface. A governed data store is the authoritative
record; Teams messages, Approvals and Planner tasks are interaction and work-
management projections only.

The implementation must be deployable and supportable with Windows-native,
user-scoped command-line authentication. It must not depend on Entra app
registration, tenant-wide admin consent, Teams tenant administration, service
principals or access to a Power BI/Fabric workspace.

## Users and roles

- Requesters submit governance matters and view matters they are entitled to see.
- Operational owners remain accountable for decisions and corrective actions.
- DMS reviewers provide routine delegated medical-governance oversight.
- Clinical Governance reviewers provide consultation and assurance input.
- EDMS reviewers decide escalated, contested, controversial, material or cross-
  service matters.
- EDMSCG, EDONCG and EDCO assurance users receive appropriately minimised
  oversight views.
- Workflow maintainers deploy and validate solutions using user-scoped PAC,
  PowerShell and delegated Microsoft Graph access where already available.

Users must be authorised through existing Microsoft 365, Team, environment or
resource membership. The product must not assume that the maintainer can create
Entra groups, grant tenant permissions, approve custom Teams applications or
change organisation-wide policies.

## Functional requirements

### 1. Capability discovery and deployment lanes

- Probe accessible Power Platform environments, current roles, connector
  availability, solution import rights, application sharing rights, Dataverse
  auditing and existing Team/SharePoint/Planner resources using user-scoped
  command-line tools.
- Prefer a solution-aware Dataverse and Power Apps deployment when the required
  user-scoped capabilities are verified.
- Provide a no-admin fallback using an existing Team, SharePoint/Microsoft Lists,
  standard Power Automate connectors, Teams Approvals and Planner when Dataverse
  application sharing or environment access cannot be granted.
- Fail closed when neither lane can satisfy access control, auditability or
  information-governance requirements.

### 2. Canonical governance record

- Maintain stable case identifiers and structured records for intake, risk,
  pathway, consultation, approval, decision, escalation, action, evidence
  reference, assurance review and closure.
- Store approval identity, response, comments, timestamp and workflow version in
  the canonical record.
- Treat Planner tasks as action projections, not the decision register.
- Treat Teams approval cards and messages as interaction surfaces, not the sole
  audit trail.
- Preserve replay safety, idempotency and an auditable state-transition history.

### 3. PRA/Pitstop pathway

- Provide one merged intake and proportionate review pathway.
- Keep corrective-action accountability with the operational line.
- Route routine medical-governance oversight to the DMS and consultation to
  Clinical Governance.
- Escalate contested, controversial, material, cross-service or otherwise
  threshold-triggering matters to the EDMS.
- Provide minimised joint-assurance visibility for EDMSCG, EDONCG and EDCO.
- Support review, audit, withdrawal, reopening and closure with evidence.

### 4. Research-governance pathway

- Keep HREC review, research-governance review, site authorisation, investigator
  duties and operational accountability distinct and traceable.
- Route routine approved research through existing investigator, RGO and
  operational pathways without duplicating their authority.
- Require priority DMS/EDMS review for research classified as higher risk before
  commencement or material amendment.
- Escalate clinically significant adverse events, safety signals and unresolved
  clinical-risk issues to DMS/EDMS oversight.
- Keep research strategy and funding decisions outside this workflow unless a
  separate authority explicitly brings them into scope.

### 5. Teams, Approvals and Planner experience

- Provide a Teams-accessible intake and case view using a shared Power App or an
  existing-team fallback surface.
- Deliver actionable approval and escalation notifications to authorised users.
- Create Planner tasks only after a governed action is assigned, using a case ID
  and privacy-minimised title.
- Synchronise task ownership, due date and completion state back to the canonical
  record without allowing Planner to overwrite governance decisions.
- Send reminders and escalation notifications for overdue or rejected actions.

### 6. Multi-user operation

- Support named users and existing Teams/Microsoft 365 groups where the current
  environment permits sharing without administrator intervention.
- Apply least-privilege requester, reviewer, approver, assurance and maintainer
  roles using controls available to the resource or environment owner.
- Document user onboarding, removal, role changes, connection ownership and
  continuity arrangements.
- Avoid a single-person dependency by supporting at least two workflow owners or
  co-owners where Microsoft 365 permits it.
- Detect and report user, licence, connector or environment-access gaps rather
  than silently excluding a participant.

### 7. Command-line ALM and verification

- Keep solution source, schemas, flow definitions, environment-variable
  templates and deployment scripts in version control without tenant secrets or
  production data.
- Use Windows-native PAC, PowerShell and delegated command-line APIs; do not
  require WSL or Linux.
- Provide non-interactive dry-run, validation, export, pack, import and smoke-test
  commands wherever platform APIs permit.
- Separate repository tests from live tenant evidence and record any unavoidable
  one-time user connection or resource-owner action.
- Provide rollback and export-before-change procedures that do not require tenant
  administration.

## Information governance and security

- Use synthetic fixtures in the repository and test environments.
- Do not place patient identifiers, clinical narrative, approval comments,
  attachments or sensitive evidence in Git, Planner titles, Teams notification
  text or telemetry.
- Store only privacy-minimised case metadata in collaboration surfaces; reference
  detailed evidence in an approved protected location.
- Enforce explicit access checks, retention expectations, audit settings and
  connector/DLP compatibility before live use.
- Record every deployment environment, solution version, connection owner and
  live verification result.
- Prevent custom connectors, application identities or broad Graph permissions
  from becoming hidden prerequisites.

## Non-functional requirements

- Accessible and usable within Teams desktop and web clients.
- Idempotent, replay-safe workflow transitions and task creation.
- Deterministic configuration and solution packaging.
- Actionable errors and dead-letter handling without sensitive payload capture.
- Automated tests for routing, permissions, privacy minimisation, failure paths,
  approval persistence, Planner synchronisation and state transitions.
- At least 90% line and branch coverage for executable repository code.

## Acceptance criteria

- A capability report proves which no-admin deployment lane is usable for at
  least one current environment and existing Team or collaboration resource.
- At least three non-owner test users can use the pilot through ordinary resource
  membership, or the exact tenant/licensing gate preventing this is documented
  with a tested fallback.
- Synthetic end-to-end cases demonstrate routine PRA/Pitstop, EDMS escalation,
  routine research, higher-risk research and adverse-event escalation.
- Approval decisions and Planner action states reconcile to the canonical record.
- Removing a user or revoking a connection produces a visible, recoverable error
  rather than silent workflow loss.
- Repository quality, privacy, security, packaging and replay tests pass.
- A user runbook, maintainer runbook, deployment manifest and tenant-gate report
  are complete.
- The project owner manually verifies the Teams experience and confirms that the
  workflow reflects the approved governance model before any production use.

## Out of scope

- Creating or administering Entra tenants, app registrations or security groups.
- Tenant-wide Teams policy changes or custom-app approval.
- Replacing HREC, RGO, site-authorisation or formal delegations processes.
- Storing patient records, clinical notes or source attachments in this repo.
- Claiming production readiness without organisational information-governance,
  clinical-governance and platform-owner approval.
- Power BI/Fabric publication unless access is separately proven.

