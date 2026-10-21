# Synthetic template catalog and collaboration projections

These modules extend the IHG hub's local contracts. They do not authenticate
users, establish IHG delegations, persist records, create provider resources or
deliver approvals/tasks. All root records are synthetic. Operating-model and
pilot-lane confirmation remain pending.

## Template catalog

`hub_catalog.py` provides `TemplateCatalog`, `CatalogCommand`,
`register_template`, `activate_template` and `resolve_template`.

The immutable catalog is bounded to 128 definitions and 256 selection records.
Registering the same ID/version/content is idempotent; changing content under an
existing ID/version is rejected. Selection history is validated during loading,
including revision and registration order. Active matters continue to resolve
their exact pinned definition; selecting a new version affects future matters.

Activation requires explicit synthetic approval and fully configured roles,
transitions, outcomes, authority and records references. Empty pathway drafts
cannot activate. Forward version changes need a reviewed migration reference;
rollback additionally needs an explicit rollback approval and a registered,
compatible lower version. Missing IDs/versions, stale revisions, replay
collisions and incompatible selection histories fail closed.

These are pure transformations. Compare-and-swap is checked against the supplied
snapshot; a live store must perform the corresponding atomic write, authenticate
the maintainer and verify the referenced approvals. Catalog revision checks are
not a distributed transaction implementation.

## Approvals

`hub_projections.py` models `ApprovalEnvelope` and `ApprovalEvent` and exposes
`apply_approval_event`. Events bind to their exact request, matter, authority,
workflow version, actor, revision, event ID and replay reference. Responses keep
identity, outcome, timestamp and protected response reference. They remain
provisional input to the canonical collective evaluator; this module cannot
ratify a matter or replace the decision register.

Loading an envelope reconstructs contiguous, context-bound history and validates
derived status, assignee, response, authority, terminal transitions and unique
event/replay identifiers. Cancellation, rejection, timeout, reassignment,
unavailable users/connections, stale versions and replay conflicts use fixed
safe error codes. Sensitive comments and arbitrary response bodies are rejected.

## Planner

`PlannerProjection`, `create_planner_projection` and
`reconcile_planner_projection` retain an immutable canonical action snapshot and
stable matter/action projection key. Titles derive only from those opaque IDs.
Creation requires an assigned canonical action. Identical creation replay must
match the complete canonical content and revision; changed inputs require
explicit reconciliation instead of silently returning a stale task.

Reconciliation requires the canonical matter reference and verifies the complete
matter/action identity and key. Ownership, due-date, completion, cancellation,
revision and observation-time checks cannot mutate the original canonical action,
decision or matter. Equal-revision observations must agree with the full canonical
snapshot. Missing, deleted, duplicate and inaccessible task cases are explicit.
Cancellation remains visible through `canonical_action.state`.

Planner completion is only an observation. Canonical action completion requires
existing canonical closure evidence; the provider cannot manufacture it or close
a governance matter. A live adapter must separately establish classification,
access, resource ownership and continuity and retain an atomic projection
registry. These contracts intentionally do not infer those rights from a task
ID or a provider response.

## Verification

The catalog slice passed 12 synthetic tests, Ruff, strict typing and Bandit.
Projection review identified four important request/history/matter/snapshot
binding issues. Thirteen new regression cases failed before the fixes; a later
snapshot-consistency regression also failed before its fix. The final projection
slice passed 42 tests, Ruff, strict typing and Bandit. The parent integrates and
rechecks these files before its scoped commit.

Exported schemas describe structural contracts. Run executable validators for
history, replay, version, authority and snapshot consistency. Never log raw
validation exceptions or private record payloads. No synthetic test result is
live resource, policy or production approval evidence.
