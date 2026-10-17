# VUW cloud-worker capability check — 17 October 2026

Read-only assessment for the coordinator's candidate solution-aware Power
Automate worker using Dataverse plus HTTP with Microsoft Entra ID. The target
was the verified personal VUW Developer environment, explicitly bound from the
authenticated discovery handoff. Its environment ID was not substituted with
the Dataverse organisation UUID. Private identifiers and credentials are omitted.

## Actual evidence

| Check | Observed result | Limit |
| --- | --- | --- |
| Installed Microsoft 365 CLI | v11.11.0; `m365 status --output json` returned `Logged out` | Separate from the working Azure/PAC/SDK identity; no licence query was executed and no login was initiated |
| Supported licence command | Local help confirms `m365 entra user license list` supports user ID or user name | The command cannot supply current-user evidence through the logged-out session; this is not a demonstrated licence denial |
| DLP tooling | No native licence/DLP/policy query tool was found in the installed FlowAgent tool declarations; the attempted `pp dlp policy list` is not an installed m365 command | No effective tenant/environment DLP policy was retrieved; lack of a tool is not proof of permission denial or an unrestricted policy |
| Existing Flow identity | FlowAgent `whoami` returned a present Flow-token identity with no known Azure/Flow identity mismatch | No new authentication, consent, account switch or cache reset was requested; this does not establish connector-specific resource grants |
| HTTP connector catalog in selected Developer | `shared_webcontents` — HTTP with Microsoft Entra ID (preauthorized), Premium; `shared_webcontentsv2` — HTTP With Microsoft Entra ID, Premium | Catalog visibility is not user entitlement, a usable connection, effective DLP permission or target-resource approval |
| Dataverse catalog in selected Developer | `shared_commondataserviceforapps` and `shared_commondataservice` — Microsoft Dataverse, Premium | Does not establish a configured cloud-worker connection or the rights/licence needed to execute it |
| HTTP v2 operation index/schema | `InvokeHttp`, POST, five indexed parameters; action type `OpenApiConnection`; operation-details tool exposes a `request` input | The details tool flattens schema fields and does not expose the nested request-header contract; exact `If-Match` header support and conditional-write behaviour were not verified |

Connector and operation observations came from the installed FlowAgent
`list_connectors`, `get_connector` and `get_operation_details` read-only tools.
Its local implementation was checked before invocation: these catalog calls use
the existing Azure CLI Flow resource and do not invoke connection creation or an
interactive Connectivity sign-in. Queries used the explicit selected environment.
Responses were reduced in memory to public connector names, tiers and schema
shape. No tokens, private identities, tenant lists, licence records or source
contents were printed or copied into repository evidence.

## Exact remaining evidence needed

1. An accountable platform/licensing operator must confirm the actual user's
   entitlement for the selected worker, environment, trigger and Premium actions.
   A licence SKU assignment alone does not establish that the proposed execution
   context is licensed or permitted.
2. An authorised policy reader/admin must provide the effective DLP evaluation
   for this environment: the selected Dataverse and HTTP-with-Entra connector
   combination, connector grouping/blocking and any action/endpoint restrictions.
   Catalog visibility and the absence of a local DLP query command prove none
   of these decisions.
3. Confirm the approved connection owner/identity and target-resource permission
   for the exact Dataverse resource through the HTTP-with-Entra connector, with
   any required consent handled by the responsible operator. No connection or
   consent was created during this assessment.
4. Under separately authorised synthetic execution, demonstrate that the actual
   worker forwards an exact ETag in `If-Match`, rejects a stale ETag without a
   lost update, and handles replay/recovery. The installed SDK update surface
   and visible connector schema do not supply this runtime evidence. A durable
   cloud-worker deployment, solution bindings and operational ownership also
   remain to be established.

The coordinator can request these specific operator/admin confirmations rather
than another general sign-in. This assessment stops at verified read-only
capability and the identified API/permission/evidence gaps. It does not approve
a candidate architecture, purchase, policy exception or production deployment.

No new sign-in, profile change, consent, connection, flow, grant, metadata write,
record mutation, mailbox acquisition or retention expansion was performed.
Governance's active platform work was not interrupted. VUW-AI-TEST acceptance
and Queensland Health permissions remain separate.
