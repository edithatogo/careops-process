# Exported app role mapping candidates — 18 October 2026

Both Developer and TEST organization/user identities were freshly checked against
the pinned private bindings using the existing isolated VUW authentication.
Only the export's two role identifiers, exact template lookups, roles with those
template identities and their exact business-unit records were queried.

## Actual resolution

Direct source `roles(<exported-id>)` reads returned 404 for both IDs. They were not
treated as missing templates or access denials. Exact `roletemplates` lookups
resolved both exported identifiers. Each template matched exactly one role in
each environment, with no further page reported; each role's business unit has
no parent business unit, establishing root-business-unit placement.

| Exported template | Developer fact | TEST candidate |
| --- | --- | --- |
| System Administrator | One role with that exact template; root business unit | One role with the same template; root business unit |
| System Customizer | One role with that exact template; root business unit | One role with the same template; root business unit |

These are unambiguous technical candidates by stable template identity, not
matching display names alone. Raw source/target role and template identifiers,
business-unit bindings and service responses remain ignored in
`artifacts/alm/app-role-candidates-private-20261018.json`.

## Access decision and remaining authority boundary

Coordination recorded the delegated engineering decision on 18 October to retain
the existing System Administrator/System Customizer template restrictions for
bounded synthetic Developer/TEST preparation. This preserves the restricted
audience; it does not approve new sharing or principal assignments. No additional
local-plan approval is needed for retaining that restriction.

These privileged templates describe the export's current app role mappings.
They are not approval to assign those roles, share an app with ordinary users,
infer clinical/operational authority, or reuse source role-record IDs in TEST.
Any later widening to a different audience requires a separately approved
least-privilege sharing design and an authorized operator.
Candidate existence does not establish the current user's right to perform that
change. TEST deployment rights and actual import/runtime acceptance stay open.

No role, principal assignment, app sharing, import, grant, authentication profile
or validator rule was changed. Portable-source validation still refuses role maps;
this target-specific fact sheet is not an automatic validation exception.

## Target-scoped preflight proposal — design only

Keep `validate_solution` and portable packaging strict by default. A separate
preflight could assess a particular unchanged artifact against a particular
authorized target without relabelling it portable or bypassing generic validation.
Its result must be a distinct readiness report, not a reusable release-success flag.

The minimum evidence binding is the artifact SHA-256, actual manifest identity and
managed state, pinned target organization/environment, current authenticated
principal, protocol/version and observation time. Recompute the artifact digest
and retrieve actual service identity at evaluation; receipt-shaped caller JSON,
boolean allow flags and display-name matches alone cannot establish evidence.

For each declared dependency, read its exact identity/type and membership in the
named installed solution, together with the observed solution/package version.
Require an explicit version policy; a newer anchor alone does not prove complete
compatibility. Refuse missing, duplicate, inaccessible or paginated-unresolved
matches. For each app role mapping, resolve the exported stable template, exactly
one intended root-business-unit role in the target, and the retained-restriction
decision. Never create a role or infer a principal assignment from this lookup.

Keep real target-specific settings and role-record bindings in a separate private
sidecar tied to that artifact and target. Do not rewrite source XML or embed
identifiers into a portable template. The preflight must surface unverified
import rights, configuration/connection access and recovery limitations, and stop
on identity drift, expired observations, changed artifact or changed role policy.
An import execution gate would need its own explicit authorized operation and
fresh revalidation; this design does not introduce one.

Tests for any future implementation must reject cross-target receipt reuse,
tampered artifacts, stale or caller-fabricated evidence, wrong component/template
membership, duplicate root-role candidates and attempted access widening. Local
mock tests cannot certify tenant compatibility. Actual import, job completion,
app validation, post-state and bounded recovery remain separate service evidence.
No preflight implementation, portable-validator exception or platform write was
performed by this proposal.
