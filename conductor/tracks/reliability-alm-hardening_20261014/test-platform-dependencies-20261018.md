# TEST platform dependency readback — 18 October 2026

Result: both declared platform component prerequisites are present in the verified
VUW-AI-TEST organization. This is read-only readiness evidence, not import approval.

Fresh isolated VUW authentication and `WhoAmI` matched the pinned TEST organization
and user before any query. Queries were limited to the three named solutions,
the two named dependency components and their exact solution memberships.

| Export declaration | Actual TEST component evidence |
| --- | --- |
| Default app icon, AppModuleWebResources 2.5 | Managed solution `AppModuleWebResources` version 2.5 exists. Exact web-resource name `msdyn_/Images/AppModule_Default_Icon.png` resolves to the icon ID embedded in the export, type 5. A solution-component row of type 61 links that exact resource to this solution. |
| AppChannel setting definition, msdyn_AppFrameworkInfraExtensions 1.0.0.20; App Framework anchor 1.0.0.25 | Managed `msdyn_AppFrameworkInfraExtensions` version 1.0.0.20 and `PowerAppsAppFramework_Anchor` version 1.0.0.26 exist. Exact setting unique name `AppChannel` resolves to one definition. A solution-component row of type 10094 links that definition to the named infrastructure extension solution. |

The initial conventional `webresources` entity-set guess returned 404. Exact
metadata discovery returned `webresourceset`, and the corrected read succeeded.
The 404 was not interpreted as missing icon or missing permissions. No broad
solution inventory or binary resource download was needed.

Raw responses and real organization/user/component bindings remain ignored in
`artifacts/alm/test-platform-dependencies-private-20261018.json`. The receipt
preserves the metadata discovery, exact records and solution-component joins.

## Remaining gates

- The package still declares dependencies; the generic portable-source validator
  continues to refuse them. This target-specific receipt does not alter its policy.
- Existing TEST customization/import/export/publisher/solution/app write rights
  remain unverified or previously absent. Component read success grants none.
- Actual import compatibility, app validation, configuration binding, target role
  sharing decisions and post-import/recovery acceptance remain separate work.
- A newer anchor version is observed, not proof of complete runtime compatibility.

No profile, role, grant, solution, resource, setting or validator was changed.
