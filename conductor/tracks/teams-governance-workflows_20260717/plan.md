# Implementation Plan: IHG Governance and Executive Action Hub

## Shared ALM dependency

Reuse the solution validation, packaging, configuration templates and release
controls from the
[reliability and ALM hardening plan](../reliability-alm-hardening_20261014/plan.md).
Canonical governance components, product-specific flows, deployment and pilot
approval remain in this track; the shared hardening track does not implement the
governance hub or approve its production use.

## Phase 1: IHG operating model and no-admin capability proof

- [ ] Task: Define executable capability-probe contracts
    - [ ] Add synthetic fixtures for environments, roles, Teams resources, connector availability, sharing and continuity outcomes.
    - [ ] Test explicit outcomes for Dataverse lane, restricted existing-Team fallback and fail-closed state.
    - [ ] Test that no Entra application, tenant-admin or service-principal prerequisite is introduced.
- [ ] Task: Implement Windows-native user-scoped capability probes
    - [ ] Inspect PAC environments, roles, solutions, tables, auditing and application-sharing capabilities.
    - [ ] Inspect existing IHG Team, SharePoint/List and Planner resources only through already-authorised delegated access.
    - [ ] Produce a privacy-safe capability, sharing, continuity and tenant-gate report.
- [ ] Task: Confirm the IHG Executive operating model
    - [ ] Record executive roles, secretariat, chair, advisers, information steward, decision owners, delegates and acting arrangements.
    - [ ] Record decision types, authority sources, quorum, conflict, out-of-session, ratification and district-escalation rules.
    - [ ] Record meeting cadence, agenda deadlines, decision-brief requirements and action-follow-up expectations.
- [ ] Task: Select and record the pilot deployment lane
    - [ ] Prefer the verified Dataverse/Power Apps lane when multi-user sharing is available.
    - [ ] Permit the existing-Team/List fallback only for approved low-sensitivity metadata.
    - [ ] Record one-time resource-owner actions, residual licence/policy gates and fail-closed conditions.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'IHG operating model and no-admin capability proof' (Protocol adapted from workflow.md)

## Phase 2: Generic governance model and configurable pathways

- [ ] Task: Define canonical schemas and lifecycle contracts
    - [ ] Model governance matters, classification, authority, risk, pathway, consultation, decision, meeting, ratification, action, evidence and archive.
    - [ ] Define stable identifiers, lifecycle transitions, replay keys, template versions and provenance.
    - [ ] Add invalid, boundary, duplicate, stale, superseded and out-of-order transition tests.
- [ ] Task: Define versioned workflow-template contracts
    - [ ] Model roles, decision semantics, thresholds, escalation, notifications, records and closure rules as configuration.
    - [ ] Add activation, migration, rollback and compatibility checks for template changes.
    - [ ] Prevent silent changes to rules governing active matters.
- [ ] Task: Implement connector-neutral workflow logic
    - [ ] Implement the generic Governance Matter engine and linked-matter dependencies.
    - [ ] Implement PRA/Pitstop and research-governance templates.
    - [ ] Implement executive decision, policy endorsement, operational exception, clinical-risk escalation and review-action templates.
- [ ] Task: Implement privacy, authority and access validators
    - [ ] Reject prohibited sensitive fields from collaboration projections and logs.
    - [ ] Validate role, authority, classification, pathway and least-privilege compatibility.
    - [ ] Add recoverable dead-letter records without sensitive payloads.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Generic governance model and configurable pathways' (Protocol adapted from workflow.md)

## Phase 3: Executive decision, meeting and secretariat workflow

- [ ] Task: Define collective-decision contract tests
    - [ ] Cover consultation, recommendation, endorsement, approval, noting, ratification, decline and return-for-information.
    - [ ] Cover quorum, conflict declaration, recusal, delegates, acting roles and chair confirmation.
    - [ ] Prove that an individual approval cannot be represented as a collective decision without the configured rule being satisfied.
- [ ] Task: Implement triage and executive-attention routing
    - [ ] Route matters to operational delegation, scheduled agenda, urgent out-of-session, assurance/noting or district escalation.
    - [ ] Implement materiality, cross-service, contest, urgency and escalation-threshold rules.
    - [ ] Provide an exception-focused executive queue and secretariat work queue.
- [ ] Task: Implement agenda, brief, minute and ratification records
    - [ ] Generate a structured agenda entry and one-page decision brief.
    - [ ] Record meeting, participants, conflicts, chair confirmation, outcome, minute reference and resulting actions.
    - [ ] Implement out-of-session expiry and later ratification where required.
- [ ] Task: Implement executive portfolio and digest views
    - [ ] Show decisions required, material risk, overdue actions, cross-service dependencies, ratification gaps and assurance exceptions.
    - [ ] Generate configurable weekly digests without requiring Power BI/Fabric.
    - [ ] Measure and constrain notification volume.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Executive decision, meeting and secretariat workflow' (Protocol adapted from workflow.md)

## Phase 4: Power Platform solution and restricted fallback

- [ ] Task: Create failing solution-packaging and deployment tests
    - [ ] Validate solution structure, environment variables, connection references and versioning.
    - [ ] Validate that deployment scripts are Windows-native, user-scoped and secret-free.
    - [ ] Test dry-run, interrupted deployment, export-before-change and rollback behaviour.
- [ ] Task: Implement the preferred Dataverse and Power Apps solution
    - [ ] Add canonical tables, relationships, keys, least-privilege roles and auditing configuration.
    - [ ] Add Teams-accessible intake, triage, agenda, case, review, decision, action, assurance and archive experiences.
    - [ ] Package solution-aware cloud flows, workflow templates and environment configuration.
- [ ] Task: Implement the restricted no-admin existing-Team fallback
    - [ ] Provision or bind to approved existing Lists and document libraries without tenant-wide resource creation.
    - [ ] Enforce low-sensitivity metadata, classification gates and approved protected-record links.
    - [ ] Map canonical lifecycle, decision, action and audit controls to the fallback store.
    - [ ] Fail closed when item-level access, auditability or continuity cannot be verified.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Power Platform solution and restricted fallback' (Protocol adapted from workflow.md)

## Phase 5: Approvals, Planner and Teams interaction

- [ ] Task: Define approval and task-projection contract tests
    - [ ] Cover first response, collective response, rejection, cancellation, reassignment, timeout and ratification outcomes.
    - [ ] Cover duplicate Planner creation, stale task updates, removed users and unavailable connections.
    - [ ] Verify that all collaboration text is privacy minimised.
- [ ] Task: Implement governed approval orchestration
    - [ ] Route approvals to authorised individuals or existing groups supported by the selected lane.
    - [ ] Persist authority, participant, conflict, response, comments, timestamp, workflow version and ratification state.
    - [ ] Implement reminders, escalation, cancellation, return-for-information and recovery.
- [ ] Task: Implement Planner action projection and reconciliation
    - [ ] Create privacy-minimised tasks only after a governed action is assigned.
    - [ ] Synchronise ownership, due date and completion without allowing Planner to alter decisions or closure evidence.
    - [ ] Reconcile missing, deleted, duplicate and inaccessible tasks.
- [ ] Task: Implement Teams notifications, digests and case links
    - [ ] Deliver authorised intake, decision, escalation, overdue, ratification and closure notifications.
    - [ ] Generate secretariat and executive digests with configurable frequency.
    - [ ] Ensure every message exposes only the minimum metadata required for action.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Approvals, Planner and Teams interaction' (Protocol adapted from workflow.md)

## Phase 6: Multi-user staged pilot and operational resilience

- [ ] Task: Prepare onboarding, ownership and continuity controls
    - [ ] Document requester, secretariat, adviser, decision-owner, executive, assurance, information-steward and maintainer onboarding/removal.
    - [ ] Configure at least two and target three workflow co-owners plus named backups and a connection register.
    - [ ] Add scheduled connection-health, acting-role, owner-departure and access-revocation checks.
- [ ] Task: Define staged pilot gates
    - [ ] Define synthetic, low-sensitivity live and expansion stages with explicit entry, stop, rollback and progression criteria.
    - [ ] Define usability, executive-load, timeliness, escalation, ratification, action and reliability measures.
    - [ ] Require a documented post-stage decision before progression.
- [ ] Task: Execute synthetic multi-user pilot cases
    - [ ] Run operational delegation, scheduled decision, out-of-session decision, ratification and return-for-information scenarios.
    - [ ] Run PRA/Pitstop, higher-risk research and adverse-event escalation scenarios.
    - [ ] Verify records and experience across at least three non-owner users including secretariat and an executive decision maker.
- [ ] Task: Execute one low-sensitivity real IHG pathway
    - [ ] Confirm classification, authority, participants, protected-record location and pilot approval.
    - [ ] Run one complete matter through submission, decision, actions, assurance and archive.
    - [ ] Measure executive effort, notification volume, timeliness, errors and user experience.
- [ ] Task: Validate failure, downtime and rollback paths
    - [ ] Exercise unavailable approver, expired connection, owner departure, inaccessible Planner plan and partial flow failure.
    - [ ] Verify idempotent replay, dead-letter recovery, manual continuity and later reconciliation.
    - [ ] Export and restore the solution or fallback configuration using user-scoped procedures.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Multi-user staged pilot and operational resilience' (Protocol adapted from workflow.md)

## Phase 7: Records, handoff and governance approval

- [ ] Task: Finalise information and records governance
    - [ ] Confirm classification, access, authoritative record, retention, disposal, legal hold, archive and records-export controls.
    - [ ] Confirm that Planner, Teams messages and approval cards remain non-authoritative projections.
    - [ ] Verify the downtime process is not used for urgent clinical-care communication.
- [ ] Task: Produce user, secretariat, executive, maintainer and deployment documentation
    - [ ] Document everyday use, meeting workflow, decision rules, escalation, ratification, action closure and support.
    - [ ] Document CLI deployment, configuration governance, validation, rollback and version upgrades.
    - [ ] Document tenant, licence, DLP, retention, auditing, ownership and information-governance gates.
- [ ] Task: Run complete repository and live-pilot verification
    - [ ] Run formatting, linting, typing, unit, property, privacy, security, dependency and secret checks.
    - [ ] Reconcile repository evidence with live environment, solution, flow, Teams, approval, Planner, meeting and archive evidence.
    - [ ] Record residual limitations without claiming tenant-wide or production approval.
- [ ] Task: Obtain project-owner and IHG Executive post-pilot decisions
    - [ ] Demonstrate the Teams experience and pilot evidence.
    - [ ] Confirm implemented routing, authority and meeting semantics match the approved IHG operating model.
    - [ ] Record the explicit decision on production approval, pathway expansion, remediation or closure.
- [ ] Task: Conductor - User Manual Verification

