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

## Operator decision still required

These privileged templates describe the export's current app role mappings.
They are not approval to assign those roles, share an app with ordinary users,
infer clinical/operational authority, or reuse source role-record IDs in TEST.
An accountable operator must decide whether the app should retain these access
restrictions or adopt a separately approved least-privilege sharing design.
Candidate existence does not establish the current user's right to perform that
change. TEST deployment rights and actual import/runtime acceptance stay open.

No role, principal assignment, app sharing, import, grant, authentication profile
or validator rule was changed. Portable-source validation still refuses role maps;
this target-specific fact sheet is not an automatic validation exception.
