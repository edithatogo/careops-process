# IHG hub requirement and evidence matrix — 18 October 2026

The governance track remains in progress. Current work is the synthetic personal
VUW Developer slice; QH and real IHG pathway work remain deferred. This matrix
reconciles the [plan](../conductor/tracks/teams-governance-workflows_20260717/plan.md)
with the [actual rehearsal](vuw-hub-rehearsal-20261018.md), including independent
service verification recorded in commit `555f7d2`. Earlier local test counts
describe their own revisions and are not current full-repository results.

| Requirement / plan phase | Evidence established | Remaining requirement |
| --- | --- | --- |
| Capability and operating model — 1 | Local fail-closed capability contracts; actual authoring and readback in personal VUW Developer | IHG authority source/version, roles, quorum, conflicts, delegation, ratification and pilot approval; effective multi-user licence/DLP/access/audit/continuity proof |
| Canonical lifecycle and templates — 2 | Local lifecycle, replay, dependency, policy pinning and catalog activation/migration/rollback contracts | Persistent canonical matter/catalog adapters and approved pathway-specific configuration; synthetic pathway IDs do not establish clinical policy |
| Executive and meeting workflow — 3 | Local collective-decision, scoped routing/views, agenda/brief/minute and later-ratification contracts | Authenticated reference provenance, durable meeting orchestration and approved routing thresholds; actual executive experience |
| Dataverse and Power Apps — 4 | Two user-owned tables with optimistic concurrency; published intake-only model-driven shell with zero validation issues; actual main form/view/navigation and unmanaged export | Full canonical tables/relationships/keys, least-privilege roles/auditing, remaining experiences and packaged executable flows; target import/restore and browser acceptance |
| Durable notification admission — 3/5 | Product engine/store exercised through injected authenticated HTTP transport; actual competing writes returned 200/412; retained revision 1, one charged reservation and one receipt independently read-verified | Default CLI live transport, hosted worker identity/recipient authorization, crash continuity and provider delivery/reconciliation; dispatch remains disabled |
| Teams, Approvals and Planner — 5 | Local bound projection/reconciliation and notification-admission contracts | Executable provider orchestration, permitted connections/resources, actual task/card/message delivery, durable reconciliation and failure recovery; local projection tests do not prove provider calls |
| Packaging and recovery — 4/6 | Actual ZIP hash/CRC and embedded app/navigation inspected; baseline preserved; shared app-aware validation implementation exists for review | Validator repair/review/integration, two platform dependencies and two target role maps, TEST permissions, import/restore and full schema/data recovery |
| Multi-user pilot and continuity — 6 | Single-operator synthetic rehearsal only; fresh independent reader verified retained state and app shell | At least three non-owner pilot users, co-owners/backups, revocation/connection/failure scenarios and explicit stage decisions |
| Records and approval — 7 | Privacy-minimised local contracts and bounded evidence documentation | Steward-approved classification, protected records, retention/archive/legal hold, complete verification and project-owner/IHG post-pilot decision |

Browser inspection reached the normal VUW federation login form with an empty
password field. Hidden JavaScript fallback text is not a compatibility finding.
No app list, detail or create interaction has been accepted. Azure CLI identity
verification is separate from the browser session.

The immediate authorised implementation prerequisite is to finish the existing
shared ALM validator repair/review for the exported model-driven app format,
then reconcile its result with the hub release dry run. Reliability owns that
validator; this lane must preserve its explicit dependency/role review gates.
This requires no platform mutation and does not activate a pilot. Subsequent
worker/connector implementation needs an agreed runtime, scoped connection and
resource bindings, and durable authorization/recovery design before live use.

Human federation sign-in is the next browser prerequisite. IHG operating-model
confirmation remains explicitly pending; generic configurable contracts may be
tested synthetically while it remains pending. Target deployment, multi-user
sharing, real sources and live governance decisions keep their existing gates.
No live/pilot checkbox is completed by this reconciliation, and the released
writer slot and retained charged ledger history remain unchanged.
