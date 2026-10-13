# Planner-only partial discovery - 2026-07-19

## Evidence boundary

This analysis uses the complete response returned by the delegated
`/me/planner/tasks` endpoint during adapter validation: 28 tasks, 38 lifecycle
events and 35 task/plan/bucket objects. It contains no task narrative, direct
identity or assignment membership.

It is a single-source partial discovery result. It does not identify IHG's main
processes and cannot be generalized to Teams, Outlook, SharePoint, Dataverse,
Approvals, Power Automate, other users, or the tenant.

## Empirical result

- Candidate families: 1
- Family members: 35 objects
- Unique events represented: 38
- Source systems represented: 1
- Dominant observed sequence: `planner_task_created`
- Family confidence under the deterministic token baseline: approximately 0.986
- Sequence stability across member objects: approximately 0.514
- Source dependence: 1.0

The high family confidence reflects similarity within this narrow source, not
organisational representativeness. Source dependence of 1.0 is a hard warning
that cross-system process discovery has not yet occurred.

## Decision

Do not name this family as an IHG organisational process and do not create an
improvement recommendation from it. Retain it as adapter and analytics validation
evidence. Populate the human review queue only after additional approved source
families have been acquired and the coverage ledger has been refreshed.
