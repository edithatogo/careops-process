# IHG hub synthetic domain and decision contracts

The local hub core is a synthetic implementation of canonical metadata,
configurable lifecycle, collective-decision checks and privacy-minimised views.
It is not a deployed Teams application or an approved IHG operating model.
Every matter, collective rule, session, routing result and digest is explicitly
synthetic. The user has left operating-model confirmation pending.

## Implemented local behavior

`hub_domain.py` models matters, authority, consultations, decisions, meetings,
ratification, actions, linked matters and transition audit history. The canonical
record stores opaque references rather than narrative, attachments or approval
comments. Unknown fields and ambiguous timestamps are rejected.

Every new matter is pinned to a template ID, semantic version and complete
configuration fingerprint. Templates define role-authorised transition edges,
escalation triggers and policy references, outcomes, notification policy and
records requirements. Creating a synthetic matter requires explicit test-policy,
authority and records references; a pathway name alone confers no authority.
Seven initial pathway definitions exist as unconfigured drafts. None establishes
an IHG role mapping, clinical threshold, research authorisation or quorum rule.

Transitions require an exact expected revision, actor scope, configured role,
event identity, replay key, timezone-aware timestamp and evidence reference.
An identical replay returns the current record after subsequent events. Reused
keys with different payloads, reused event IDs, future/stale/out-of-order events,
illegal transitions and silent template changes are rejected before mutation.
Equivalent UTC/local timestamp spellings produce the same replay fingerprint.

Loaded history must contain legal, chronological state transitions and distinct
event/replay identifiers. Before applying another transition, recorded edges and
authority references must match the pinned template. Linked dependencies hold
decision progression until caller-supplied canonical dependency states resolve.
Supersession and consolidation require a distinct destination and retain their
direction and evidence provenance.

Action completion requires canonical closure evidence. Matter closure requires
closure evidence and resolved actions; archive additionally requires an archive
record reference. Reopening starts a new review cycle, clears current closure,
archive and ratification, and preserves prior decisions and ratification records.
The new cycle cannot be decided from the preceding cycle's decision records.

## Collective decisions

`hub_decisions.py` requires explicit eligible principals, quorum, voting method,
majority denominator, conflict policy, chair, decision semantics, ratification
requirement, authority and approved-policy references. There is no IHG quorum
default. Synthetic fixtures use their own labelled two-of-three test policy.

Only the matching decision outcome counts as an affirmative response.
Consultation, recommendation, noting, endorsement, approval, ratification,
decline and return-for-further-work remain distinct. Conflicted, recused or
ineligible participants cannot manufacture quorum. Delegates/acting participants
need their authority references, and a person cannot occupy multiple seats.

The **common** `apply_transition` boundary checks collective policy whenever the
template declares `decision_rule_ref`. The template must also pin the complete
collective-rule fingerprint. Calling the general lifecycle API cannot bypass
the voting checks. `apply_decision_transition` is a convenience wrapper through
that same boundary and forwards resolved dependency states.

Session, matter, scope, review cycle, template version, decision, outcome and
authority must agree. Votes and canonical decision evidence must predate the
transition. Provisional decisions require the configured voting rule. Final
ratification additionally requires chair confirmation, minutes and configured
ratification controls. Its canonical decision and confirmation references must
match the evaluated session. Exact historical replay is recognised before
time-dependent session checks, so expiry cannot create a second decision or
invalidate an already-recorded transition.

These functions validate **synthetic context**, not the authenticity of people,
delegation documents, chair confirmation or protected references. A live adapter
must authenticate the caller, resolve current membership/acting authority and
row-level access, and load evidence from a controlled record. Client-supplied
role strings, scope strings or approval references are never live authorization.

## Triage, portfolio and digest candidates

`hub_views.py` accepts an explicitly ordered routing policy with authority and
owner-role references. It routes only on supplied, evaluated trigger flags:
operational delegation, scheduled agenda, urgent out-of-session, assurance and
district escalation. It does not infer clinical urgency, delegation, materiality
or district thresholds. Missing routes or classification hold for triage.

Executive portfolio items expose only low-sensitivity IDs, lifecycle/pathway,
fixed attention reasons and overdue-action counts within the authorised scope.
Protected and inaccessible matters are excluded. Routine intake appears in a
separate secretariat queue, and completed/archived matters do not populate open
exceptions. Duplicate canonical source rows are rejected within the selected
scope before classification, state or reason filtering. Resolved linked
dependencies do not become executive exceptions; absent dependency evidence
stays unresolved.

Digest policy explicitly supplies frequency and item cap. Disabled, empty and
already-emitted intervals are suppressed. The returned digest is a candidate;
there is no notification delivery. A future connector must persist digest keys
transactionally and apply recipient-specific access before sending.
Changing the item cap changes the candidate's policy fingerprint and may create
another key in the same interval. This is a documented minor limitation; a live
sender still needs an independent interval gate rather than treating the
candidate fingerprint as its only delivery-frequency control.

The decision-brief renderer is a one-page **scaffold** listing question,
recommendation, alternatives, risks, authority, conflicts, consultations and
actions. It does not retrieve protected content, fill unconfirmed policy or
claim an agenda pack is complete. Binding approved brief sources and recording
actual agenda/minute events remain later tasks.

## Validation and remaining work

The executable Pydantic models are authoritative. Exported JSON schemas describe
shape; consumers must also run the executable validation for cross-field,
history, role and evidence rules. Never log raw validation exceptions, canonical
records, command payloads or protected evidence. The capability CLI sanitizes its
configuration and runtime errors separately.

The reviews identified two probe issues, seven domain/decision issues and two
view correctness issues.
Each important finding has a synthetic failing reproduction followed by a
passing regression test. The capability slice is committed separately from the
domain/decision/view slice. The capability JSON Schema's conditional
verified-evidence requirement remains a documented minor limitation: Python
validation requires the evidence reference even though structural JSON Schema
alone does not. No completion or live approval is inferred from fixtures.

Independent local tasks still available include a persistent template catalog,
activation/migration/rollback registry, recovery/dead-letter contracts, approval
and Planner projection contracts, approved brief-source binding, meeting event
orchestration, notification delivery/reconciliation and release configuration.
Their remaining work is explicit in the Conductor plan; these foundations do not
mark entire phases complete. Reference-only canonical records do not implement
all clinical-pathway decision logic or every records-management control.

Live implementation needs the confirmed pilot environment/resource IDs, an
existing delegated M365 sign-in where required, effective write/share/audit
rights, information-steward classification/records decisions, named co-owners
and backups, and the approved IHG authority/quorum/conflict/ratification model.
Phase 4 environment authoring must create actual Power Platform components in
the selected environment before export; placeholder solution XML is not a
substitute. Shared ALM packaging and release controls belong to the hardening
track. Live pilot, organisational approval and manual verification remain open.
