# Specification: IHG Governance and Executive Action Hub

## Overview

Implement a reusable, multi-user governance and executive-action hub surfaced
through Microsoft Teams for the IHG Executive Team. The product will manage a
generic `Governance Matter` and apply versioned workflow templates for different
matter types. The merged PRA/Pitstop review pathway and tiered research-
governance pathway are the first clinical-governance templates, not hard-coded
limits on future use.

The hub will support executive decision requests, endorsements, noting and
assurance items, policy or procedure reviews, operational exceptions, clinical-
risk escalations and actions arising from reviews. It will route matters to the
lowest authorised level and present the IHG Executive Team with decisions and
exceptions that genuinely require executive attention.

Teams is the collaboration surface. A governed data store is the authoritative
record; Teams messages, Approvals, agenda packs and Planner tasks are controlled
projections only.

The implementation must be deployable and supportable with Windows-native,
user-scoped command-line authentication. It must not depend on Entra app
registration, tenant-wide admin consent, Teams tenant administration, service
principals or access to a Power BI/Fabric workspace.

## Users and roles

- Requesters submit governance matters and view matters they are entitled to see.
- Operational owners retain accountability for decisions and corrective actions
  within their delegations.
- IHG Executive sponsors own the organisational outcome and escalation pathway.
- Executive decision owners hold the authority to decide or sponsor a collective
  decision request.
- IHG Executive Team members consider scheduled, urgent and assurance matters.
- The meeting chair applies meeting rules and confirms decision status.
- The Executive secretariat triages submissions, prepares agendas, records
  decisions, manages ratification and maintains the action register.
- Subject-matter advisers provide consultation without being represented as the
  decision maker.
- DMS reviewers provide routine delegated medical-governance oversight.
- Clinical Governance reviewers provide consultation and assurance input.
- EDMS reviewers decide or sponsor escalation of contested, controversial,
  material, district-significant or cross-service matters where authorised.
- District assurance and escalation recipients receive appropriately minimised
  views only where the approved pathway requires them.
- Workflow maintainers deploy and validate solutions using user-scoped PAC,
  PowerShell and delegated Microsoft Graph access where already available.
- The information steward owns classification, access, retention and records-
  management controls for the canonical store.

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
  standard Power Automate connectors, Teams Approvals and Planner only when the
  matter classification and verified access controls permit it.
- Restrict the fallback to privacy-minimised, low-sensitivity governance metadata
  unless an information steward formally approves stronger verified controls.
- Fail closed when neither lane can satisfy access control, auditability,
  continuity or information-governance requirements.

### 2. Generic governance-matter model and templates

- Maintain a generic `Governance Matter` with a stable identifier, classification,
  source, sponsor, authority, risk, decision type, pathway, dependencies,
  consultations, evidence references, decisions, actions and lifecycle state.
- Configure pathway behaviour through versioned templates rather than embedding
  clinical-governance rules directly in flow logic.
- Initially support templates for PRA/Pitstop, research governance, clinical-risk
  escalation, executive decision request, policy/procedure endorsement,
  operational exception and review-generated action.
- Validate template authority, decision semantics, escalation triggers, records
  requirements and notification policy before activation.
- Preserve the template and configuration version used for every decision.
- Support linked matters, duplicate consolidation, supersession and cross-service
  dependencies without losing provenance.

### 3. Canonical record and lifecycle

- Maintain structured records for intake, triage, classification, risk, pathway,
  consultation, approval, decision, escalation, action, evidence reference,
  assurance review, ratification, closure and archive.
- Support the lifecycle:
  `Draft -> Submitted -> Triaged -> Under review -> Decision required ->
  Provisionally decided -> Ratified -> Actions open -> Assurance review ->
  Closed -> Archived`.
- Also support withdrawal, rejection, return for information, cancellation,
  supersession, reopening and duplicate consolidation.
- Store approval identity, response, comments, timestamp, authority basis,
  workflow version and ratification status in the canonical record.
- Treat Planner tasks as action projections, not the decision or action register.
- Treat Teams approval cards, messages and agenda packs as projections, not the
  sole audit trail.
- Preserve replay safety, idempotency and an auditable state-transition history.

### 4. Executive authority and collective decisions

- Distinguish consultation, recommendation, endorsement, approval, noting,
  ratification, decline and return-for-further-work outcomes.
- Record the authority source, decision owner, decision-making body, required
  participants, quorum rule, conflicts, delegates, acting arrangements and any
  later ratification requirement.
- Never represent an individual Teams Approval as a collective IHG Executive Team
  decision unless the approved decision rule is satisfied.
- Keep collective decisions provisional until quorum, conflicts, chair confirmation
  and minute or out-of-session ratification controls are satisfied.
- Support conflict declaration, recusal, reassignment and an auditable record of
  who participated in the decision.
- Make clear that the hub records authority and decisions but does not create a
  delegation or replace an approved terms of reference.

### 5. Meeting and out-of-session workflow

- Triage every matter to operational delegation, scheduled Executive Team agenda,
  urgent out-of-session decision, noting/assurance or district escalation.
- Generate a structured agenda entry and one-page decision brief containing the
  question, recommendation, alternatives, risks, authority, conflicts,
  consultations, supporting links and proposed actions.
- Maintain agenda status, meeting date, chair confirmation, decision/minute
  reference, ratification status and resulting actions.
- Support urgent out-of-session decisions with explicit urgency criteria,
  participating decision makers, expiry and later ratification where required.
- Export privacy-safe agenda, decision and action-register views without copying
  protected evidence into the collaboration surface.

### 6. Clinical-governance templates

#### PRA/Pitstop

- Provide one merged intake and proportionate review pathway.
- Keep corrective-action accountability with the operational line.
- Route routine medical-governance oversight to the DMS and consultation to
  Clinical Governance.
- Escalate contested, controversial, material, cross-service or otherwise
  threshold-triggering matters to the EDMS or IHG Executive pathway as configured.
- Provide minimised assurance visibility to authorised executive and district
  recipients.
- Support review, audit, withdrawal, reopening and closure with evidence.

#### Research governance

- Keep HREC review, research-governance review, site authorisation, investigator
  duties and operational accountability distinct and traceable.
- Route routine approved research through existing investigator, RGO and
  operational pathways without duplicating their authority.
- Require priority DMS/EDMS review for research classified as higher risk before
  commencement or material amendment.
- Escalate clinically significant adverse events, safety signals and unresolved
  clinical-risk issues to DMS/EDMS and IHG Executive oversight where configured.
- Keep research strategy and funding decisions outside this template unless a
  separate authority explicitly brings them into scope.

### 7. Executive attention and portfolio views

- Present executives with decisions required, material risks, contested matters,
  cross-service dependencies, overdue actions, impending escalation thresholds,
  ratification gaps and assurance exceptions.
- Allow routine matters to remain with authorised operational owners while still
  providing proportionate assurance.
- Provide configurable weekly digests and suppress routine event-by-event noise.
- Provide secretariat queues for incomplete submissions, agenda preparation,
  decision confirmation, ratification and action follow-up.
- Do not require Power BI/Fabric; provide governed in-app and exportable views.

### 8. Teams, Approvals and Planner experience

- Provide a Teams-accessible intake and case view using a shared Power App or an
  existing-Team fallback surface.
- Deliver actionable approval and escalation notifications to authorised users.
- Create Planner tasks only after a governed action is assigned, using a case ID
  and privacy-minimised title.
- Synchronise task ownership, due date and completion state back to the canonical
  record without allowing Planner to overwrite decisions or closure evidence.
- Send configurable reminders and escalation notifications for overdue or
  rejected actions without creating notification fatigue.
- Support desktop and web use and test the key executive actions on mobile where
  the organisation permits mobile Teams access.

### 9. Multi-user continuity and organisational change

- Support named users and existing Teams/Microsoft 365 groups where the current
  environment permits sharing without administrator intervention.
- Apply least-privilege requester, secretariat, adviser, reviewer, decision owner,
  executive, assurance, information-steward and maintainer roles.
- Document user onboarding, removal, acting-role changes, delegates, connection
  ownership and continuity arrangements.
- Require at least two and target three workflow co-owners, a connection register,
  named backup owners and scheduled connection-health tests.
- Detect and report user, licence, connector, environment-access and owner-
  continuity gaps rather than silently excluding a participant.
- Provide tested owner-departure, connection-expiry, Team-unavailable and manual-
  continuity procedures.

### 10. Command-line ALM and configuration governance

- Keep solution source, schemas, flow definitions, workflow templates,
  environment-variable templates and deployment scripts in version control
  without tenant secrets or production data.
- Use Windows-native PAC, PowerShell and delegated command-line APIs; do not
  require WSL or Linux.
- Provide non-interactive dry-run, validation, export, pack, import and smoke-test
  commands wherever platform APIs permit.
- Separate repository tests from live tenant evidence and record unavoidable
  one-time user connection or resource-owner actions.
- Provide export-before-change, rollback and disaster-recovery procedures that do
  not require tenant administration.
- Require reviewed, versioned changes for templates, thresholds, roles,
  notifications and decision rules; never silently change an active pathway.

## Information governance and security

- Use synthetic fixtures in the repository and initial test environments.
- Do not place patient identifiers, clinical narrative, approval comments,
  attachments or sensitive evidence in Git, Planner titles, Teams notification
  text or telemetry.
- Store only privacy-minimised case metadata in collaboration surfaces; reference
  detailed evidence in an approved protected record location.
- Define classification, authoritative record, retention, disposal, legal hold,
  archive and records-export requirements before live operation.
- Enforce explicit access checks, audit settings and connector/DLP compatibility
  before live use.
- Record every deployment environment, solution version, connection owner and
  live verification result.
- Prevent custom connectors, application identities or broad Graph permissions
  from becoming hidden prerequisites.
- Maintain a break-glass and downtime process that preserves later reconciliation
  without using the hub as an emergency clinical-care system.

## Non-functional requirements

- Accessible and usable within Teams desktop and web clients.
- Executive decisions should ordinarily require no more than a concise brief and
  one governed action from each decision maker.
- Idempotent, replay-safe workflow transitions and task creation.
- Deterministic configuration and solution packaging.
- Actionable errors and dead-letter handling without sensitive payload capture.
- Automated tests for routing, authority, quorum, conflicts, ratification,
  permissions, privacy minimisation, failure paths, approval persistence, Planner
  reconciliation and state transitions.
- At least 90% line and branch coverage for executable repository code.

## Pilot and success measures

- Begin with synthetic cases and then one low-sensitivity real IHG pathway.
- Use explicit entry, stop, rollback and progression criteria for each pilot stage.
- Measure submission-to-triage time, decision time, executive handling time,
  percentage resolved under delegation, overdue-action rate, ratification backlog,
  return-for-information rate, correct escalation, evidence-backed closure,
  connection failures and requester/secretariat/executive usability.
- Review notification volume and approval behaviour for signs of fatigue or
  rubber-stamping.
- Require a documented post-pilot decision before adding another pathway.

## Acceptance criteria

- A capability report proves which no-admin deployment lane is usable for at
  least one current environment and existing IHG Team or collaboration resource.
- The IHG Executive Team or authorised project owner confirms the decision
  taxonomy, authority model, meeting pathway, escalation thresholds and
  ratification rules before live implementation.
- At least three non-owner test users, including a secretariat user and an
  executive decision maker, can use the pilot through ordinary resource
  membership, or the exact tenant/licensing gate is documented with a tested
  fallback.
- Synthetic cases demonstrate operational delegation, scheduled executive
  decision, urgent out-of-session decision, ratification, PRA/Pitstop escalation,
  higher-risk research and adverse-event escalation.
- A low-sensitivity real pilot demonstrates one complete matter from submission
  through decision, actions, assurance and archive without sensitive data leakage.
- Approval, quorum, conflict, decision, minute/ratification and Planner action
  states reconcile to the canonical record.
- Removing a user, changing an acting role, revoking a connection or losing a
  workflow owner produces a visible, recoverable error rather than silent loss.
- At least two workflow co-owners are verified; three is the target. If this is
  impossible, the pilot cannot progress beyond synthetic testing without an
  approved continuity exception.
- Repository quality, privacy, security, packaging and replay tests pass.
- User, secretariat, executive, maintainer and deployment runbooks plus a
  configuration register, records model and tenant-gate report are complete.
- The project owner manually verifies the Teams experience and the IHG Executive
  Team makes an explicit post-pilot decision before production use or expansion.

## Out of scope

- Creating or administering Entra tenants, app registrations or security groups.
- Tenant-wide Teams policy changes or custom-app approval.
- Creating new authority, replacing terms of reference or changing delegations.
- Replacing HREC, RGO, site-authorisation, incident-management, records-management
  or other authoritative specialist systems.
- Using the hub for urgent clinical-care communication or emergency response.
- Storing patient records, clinical notes or source attachments in this repo.
- Claiming production readiness without organisational information-governance,
  clinical-governance, IHG Executive and platform-owner approval.
- Power BI/Fabric publication unless access is separately proven.

