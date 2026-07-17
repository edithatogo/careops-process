# Implementation Plan: Teams clinical-governance workflows

## Phase 1: No-admin capability and sharing proof

- [ ] Task: Define executable capability-probe contracts
    - [ ] Add synthetic fixtures for environments, roles, Teams resources, connector availability and sharing outcomes.
    - [ ] Test explicit outcomes for Dataverse lane, existing-Team fallback and fail-closed state.
    - [ ] Test that no Entra application, tenant-admin or service-principal prerequisite is introduced.
- [ ] Task: Implement Windows-native user-scoped capability probes
    - [ ] Inspect PAC environments, roles, solutions, tables, auditing and application-sharing capabilities.
    - [ ] Inspect existing Team, SharePoint/List and Planner resources only through already-authorised delegated access.
    - [ ] Produce a privacy-safe capability and tenant-gate report.
- [ ] Task: Select and record the pilot deployment lane
    - [ ] Prefer the verified Dataverse/Power Apps lane when multi-user sharing is available.
    - [ ] Select the existing-Team/List fallback when Dataverse sharing is blocked.
    - [ ] Record all one-time resource-owner actions and residual licence or policy gates.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'No-admin capability and sharing proof' (Protocol adapted from workflow.md)

## Phase 2: Canonical case model and workflow engine

- [ ] Task: Define schemas and state-transition contracts
    - [ ] Model governance cases, risk, pathway, consultation, approval, decision, escalation, action, evidence reference and closure.
    - [ ] Define stable identifiers, allowed transitions, replay keys, version fields and provenance.
    - [ ] Add invalid, boundary, duplicate, stale and out-of-order transition tests.
- [ ] Task: Implement connector-neutral workflow logic
    - [ ] Implement PRA/Pitstop routing and EDMS escalation thresholds.
    - [ ] Implement routine and higher-risk research routing and safety-event escalation.
    - [ ] Keep operational accountability, clinical-governance input and medical-executive assurance distinct.
- [ ] Task: Implement privacy and access-control validators
    - [ ] Reject prohibited sensitive fields from collaboration projections and logs.
    - [ ] Validate role/pathway compatibility and least-privilege projections.
    - [ ] Add recoverable dead-letter records without sensitive payloads.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Canonical case model and workflow engine' (Protocol adapted from workflow.md)

## Phase 3: Power Platform solution and existing-Team fallback

- [ ] Task: Create failing solution-packaging and deployment tests
    - [ ] Validate solution structure, environment variables, connection references and versioning.
    - [ ] Validate that deployment scripts are Windows-native, user-scoped and secret-free.
    - [ ] Test dry-run, interrupted deployment and export-before-change behaviour.
- [ ] Task: Implement the preferred Dataverse and Power Apps solution
    - [ ] Add canonical tables, relationships, keys, least-privilege roles and auditing configuration.
    - [ ] Add a Teams-accessible intake, queue, case, review, escalation and closure experience.
    - [ ] Package solution-aware cloud flows and environment configuration.
- [ ] Task: Implement the no-admin existing-Team fallback
    - [ ] Provision or bind to approved existing Lists and document libraries without creating tenant-wide resources.
    - [ ] Map the canonical schema and state controls to the fallback store.
    - [ ] Preserve equivalent approval, action, audit and privacy behaviour.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Power Platform solution and existing-Team fallback' (Protocol adapted from workflow.md)

## Phase 4: Approvals, Planner and Teams interaction

- [ ] Task: Define approval and task-projection contract tests
    - [ ] Cover first response, everyone-must-respond, rejection, cancellation, reassignment and timeout outcomes.
    - [ ] Cover duplicate Planner creation, stale task updates, removed users and unavailable connections.
    - [ ] Verify that all collaboration text is privacy minimised.
- [ ] Task: Implement governed approval orchestration
    - [ ] Route approvals to authorised individuals or existing groups supported by the selected lane.
    - [ ] Persist approver, response, comments, timestamp and workflow version to the canonical record.
    - [ ] Implement reminders, escalation, cancellation and recovery.
- [ ] Task: Implement Planner action projection and reconciliation
    - [ ] Create privacy-minimised tasks only after governed assignment.
    - [ ] Synchronise ownership, due date and completion without allowing Planner to alter decisions.
    - [ ] Reconcile missing, deleted, duplicate and inaccessible tasks.
- [ ] Task: Implement Teams notifications and case links
    - [ ] Deliver authorised intake, approval, escalation, overdue and closure notifications.
    - [ ] Ensure every message exposes only the minimum metadata required for action.
    - [ ] Provide accessible links to the governed case experience.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Approvals, Planner and Teams interaction' (Protocol adapted from workflow.md)

## Phase 5: Multi-user pilot and operational resilience

- [ ] Task: Prepare multi-user onboarding and continuity controls
    - [ ] Document requester, reviewer, approver, assurance and maintainer onboarding and removal.
    - [ ] Configure at least two workflow owners or document the exact platform gate.
    - [ ] Add connection-expiry, owner-departure and access-revocation runbooks.
- [ ] Task: Execute synthetic multi-user pilot cases
    - [ ] Run routine and escalated PRA/Pitstop scenarios.
    - [ ] Run routine, higher-risk and adverse-event research scenarios.
    - [ ] Verify decisions, actions, evidence references, audit history and closure across at least three non-owner users.
- [ ] Task: Validate failure, recovery and rollback paths
    - [ ] Exercise unavailable approver, expired connection, inaccessible Planner plan and partial flow failure.
    - [ ] Verify idempotent replay and dead-letter recovery.
    - [ ] Export and restore the solution or fallback configuration using user-scoped procedures.
- [ ] Task: Conductor - Automated Review and Triangulated Verification 'Multi-user pilot and operational resilience' (Protocol adapted from workflow.md)

## Phase 6: Handoff and governance approval

- [ ] Task: Produce user, maintainer and deployment documentation
    - [ ] Document everyday use, pathway rules, escalation, action closure and support.
    - [ ] Document CLI deployment, configuration, validation, rollback and version upgrades.
    - [ ] Document tenant, licence, DLP, retention, auditing and information-governance gates.
- [ ] Task: Run complete repository and live-pilot verification
    - [ ] Run formatting, linting, typing, unit, property, privacy, security, dependency and secret checks.
    - [ ] Reconcile repository evidence with live environment, solution, flow, Teams, approval and Planner evidence.
    - [ ] Record residual limitations without claiming tenant-wide or production approval.
- [ ] Task: Obtain project-owner manual verification
    - [ ] Demonstrate the Teams experience using synthetic cases.
    - [ ] Confirm the implemented routing matches the approved governance model.
    - [ ] Record the explicit decision on whether to seek organisational production approval.
- [ ] Task: Conductor - User Manual Verification

